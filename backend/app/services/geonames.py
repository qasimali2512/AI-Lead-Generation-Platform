"""
GeoNames se duniya ke shehron ki list (free, CC BY 4.0 -- https://www.geonames.org).

cities5000.zip mein har wo shehr/qasba hai jis ki abadi 5,000 ya zyada ho
(duniya bhar mein ~50,000).  File pehli baar download hoti hai, phir disk par
cache rehti hai (30 din) aur memory mein ek baar load hoti hai.

Size buckets:
    big     : abadi >= 300,000
    medium  : 50,000 - 299,999
    small   : 5,000  - 49,999
"""
from __future__ import annotations

import logging
import os
import random
import tempfile
import threading
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import httpx

logger = logging.getLogger("ai-lead-geonames")

BASE_URL = "https://download.geonames.org/export/dump"
CITIES_ZIP = "cities5000.zip"
CITIES_TXT = "cities5000.txt"
COUNTRY_INFO = "countryInfo.txt"
ADMIN1_FILE = "admin1CodesASCII.txt"

CACHE_MAX_AGE_SECONDS = 30 * 24 * 3600
DOWNLOAD_TIMEOUT = 120.0

BIG_MIN_POPULATION = 300_000
MEDIUM_MIN_POPULATION = 50_000

CITY_SIZES = ("big", "medium", "small", "mix")

# "mix" = 3 chhote shehar, phir 1 bara shehar (phir dobara)
MIX_PATTERN = ("small", "small", "small", "big")
ALL_BUCKETS = ("big", "medium", "small")


class GeoDataUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class City:
    geoname_id: int
    name: str
    ascii_name: str
    latitude: float
    longitude: float
    country_code: str
    admin1: str | None
    population: int

    @property
    def bucket(self) -> str:
        if self.population >= BIG_MIN_POPULATION:
            return "big"
        if self.population >= MEDIUM_MIN_POPULATION:
            return "medium"
        return "small"


@dataclass
class GeoData:
    cities: list[City]
    country_names: dict[str, str]
    admin1_names: dict[str, str]
    by_bucket: dict[str, list[City]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.by_bucket = {bucket: [] for bucket in ALL_BUCKETS}
        for city in self.cities:
            self.by_bucket[city.bucket].append(city)

    def country_name(self, code: str) -> str:
        return self.country_names.get(code, code)

    def state_name(self, city: City) -> str | None:
        if not city.admin1:
            return None
        return self.admin1_names.get(f"{city.country_code}.{city.admin1}")

    def countries(self) -> list[dict[str, str]]:
        codes = {city.country_code for city in self.cities}
        return sorted(
            ({"code": code, "name": self.country_name(code)} for code in codes),
            key=lambda item: item["name"].lower(),
        )


# ---------------------------------------------------------
# Parsing (pure functions -- easy to test)
# ---------------------------------------------------------

def parse_cities(lines) -> list[City]:
    cities: list[City] = []
    for raw in lines:
        parts = raw.rstrip("\n\r").split("\t")
        if len(parts) < 15:
            continue
        try:
            cities.append(
                City(
                    geoname_id=int(parts[0]),
                    name=parts[1],
                    ascii_name=parts[2] or parts[1],
                    latitude=float(parts[4]),
                    longitude=float(parts[5]),
                    country_code=parts[8].strip().upper(),
                    admin1=parts[10].strip() or None,
                    population=int(parts[14] or 0),
                )
            )
        except ValueError:
            continue
    return [c for c in cities if len(c.country_code) == 2]


def parse_country_names(lines) -> dict[str, str]:
    names: dict[str, str] = {}
    for raw in lines:
        if raw.startswith("#") or not raw.strip():
            continue
        parts = raw.rstrip("\n\r").split("\t")
        if len(parts) > 4 and parts[0] and parts[4]:
            names[parts[0].strip().upper()] = parts[4].strip()
    return names


def parse_admin1_names(lines) -> dict[str, str]:
    names: dict[str, str] = {}
    for raw in lines:
        parts = raw.rstrip("\n\r").split("\t")
        if len(parts) >= 2 and parts[0]:
            names[parts[0].strip()] = (parts[2] if len(parts) > 2 and parts[2] else parts[1]).strip()
    return names


def build_geo_data(city_lines, country_lines, admin1_lines) -> GeoData:
    cities = parse_cities(city_lines)
    if not cities:
        raise GeoDataUnavailable("GeoNames city list is empty.")
    return GeoData(
        cities=cities,
        country_names=parse_country_names(country_lines),
        admin1_names=parse_admin1_names(admin1_lines),
    )


# ---------------------------------------------------------
# Download + cache
# ---------------------------------------------------------

def _cache_dir() -> Path:
    path = Path(
        os.environ.get("GEONAMES_CACHE_DIR")
        or os.path.join(tempfile.gettempdir(), "leadflow_geonames")
    )
    path.mkdir(parents=True, exist_ok=True)
    return path


def _ensure_file(filename: str) -> Path:
    target = _cache_dir() / filename
    fresh = (
        target.exists()
        and time.time() - target.stat().st_mtime < CACHE_MAX_AGE_SECONDS
    )
    if fresh:
        return target

    url = f"{BASE_URL}/{filename}"
    partial = target.with_suffix(target.suffix + ".part")
    try:
        with httpx.stream(
            "GET", url, timeout=DOWNLOAD_TIMEOUT, follow_redirects=True
        ) as response:
            response.raise_for_status()
            with open(partial, "wb") as handle:
                for chunk in response.iter_bytes():
                    handle.write(chunk)
        partial.replace(target)
        logger.info("Downloaded %s", url)
    except (httpx.HTTPError, OSError) as exc:
        partial.unlink(missing_ok=True)
        if target.exists():
            logger.warning("GeoNames download failed (%s); using old cache.", exc)
            return target
        raise GeoDataUnavailable(
            f"Could not download the city list from GeoNames ({filename}): {exc}"
        ) from exc

    return target


def _read_lines(path: Path):
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        return handle.readlines()


def _load_from_disk() -> GeoData:
    zip_path = _ensure_file(CITIES_ZIP)
    with zipfile.ZipFile(zip_path) as archive:
        with archive.open(CITIES_TXT) as handle:
            city_lines = handle.read().decode("utf-8", errors="replace").splitlines()

    # Country / state names sirf display ke liye hain -- fail hon to bhi chalo
    try:
        country_lines = _read_lines(_ensure_file(COUNTRY_INFO))
    except GeoDataUnavailable:
        country_lines = []
    try:
        admin1_lines = _read_lines(_ensure_file(ADMIN1_FILE))
    except GeoDataUnavailable:
        admin1_lines = []

    return build_geo_data(city_lines, country_lines, admin1_lines)


_cache: GeoData | None = None
_lock = threading.Lock()


def get_geo_data() -> GeoData:
    """Blocking -- async code ise asyncio.to_thread() se bulaye."""
    global _cache
    with _lock:
        if _cache is None:
            _cache = _load_from_disk()
        return _cache


def set_geo_data_for_tests(data: GeoData | None) -> None:
    global _cache
    _cache = data


# ---------------------------------------------------------
# City selection
# ---------------------------------------------------------

def choose_bucket(city_size: str, position: int) -> str:
    if city_size == "mix":
        return MIX_PATTERN[position % len(MIX_PATTERN)]
    return city_size if city_size in ALL_BUCKETS else "small"


def bucket_candidates(
    data: GeoData, bucket: str, countries: set[str]
) -> list[City]:
    return [
        city
        for city in data.by_bucket.get(bucket, [])
        if not countries or city.country_code in countries
    ]


def pick_city(
    data: GeoData,
    *,
    city_size: str,
    position: int,
    countries: set[str],
    excluded_ids: set[int],
    rng: random.Random,
) -> tuple[City | None, str]:
    """
    Agla shehar chuno.  Pehle country random chunte hain (taake India/China jaise
    bare mulk sab par na chha jayen), phir us mulk ka koi shehar.

    Returns (city, status): status "ok" | "exhausted" | "no_match".
      exhausted -> is size ke sab shehar visit ho chuke (progress reset karo)
      no_match  -> country/size ke hisaab se koi shehar hai hi nahi
    """
    primary = choose_bucket(city_size, position)
    buckets = [primary]
    if city_size == "mix":
        buckets += [b for b in ("medium", "small", "big") if b != primary]

    any_candidates = False
    for bucket in buckets:
        candidates = bucket_candidates(data, bucket, countries)
        if not candidates:
            continue
        any_candidates = True

        by_country: dict[str, list[City]] = {}
        for city in candidates:
            if city.geoname_id in excluded_ids:
                continue
            by_country.setdefault(city.country_code, []).append(city)

        if by_country:
            country_code = rng.choice(sorted(by_country))
            return rng.choice(by_country[country_code]), "ok"

    return None, ("exhausted" if any_candidates else "no_match")