import { useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowLeft,
  Check,
  LoaderCircle,
  MapPin,
  Play,
  RotateCcw,
  Square,
  X,
  Zap,
} from "lucide-react";
import { toast } from "react-toastify";
import { useNavigate } from "react-router-dom";

import autoDiscoveryService from "../../services/autoDiscoveryService";
import "./LeadDiscoveryPage.css";
import "./AutoDiscoveryPage.css";

const BATCH_OPTIONS = [50, 100, 200];
const INTERVAL_OPTIONS = [
  { value: 15, label: "15 min" },
  { value: 30, label: "30 min" },
  { value: 60, label: "1 hour" },
];

const CITY_SIZE_OPTIONS = [
  { value: "big", label: "Big", hint: "300k+ people" },
  { value: "medium", label: "Medium", hint: "50k - 300k" },
  { value: "small", label: "Small", hint: "5k - 50k" },
  { value: "mix", label: "Mix", hint: "3 small : 1 big" },
];

const EMPTY_FORM = {
  industry: "",
  batch_size: 50,
  require_email: false,
  require_website: false,
  run_every_minutes: 30,
  city_size: "mix",
  countries: [],
};

/* ---------- Safe helpers (objects ko JSX mein jane se rokte hain) ---------- */

// Kisi bhi value ko safe text bana do
function asText(value) {
  if (value === null || value === undefined) return "";
  if (typeof value === "object") {
    return String(value.name || value.code || value.message || "");
  }
  return String(value);
}

// Aik country item (string ya {code, name}) -> code string
function toCountryCode(item) {
  if (typeof item === "string") return item;
  if (item && typeof item === "object") return String(item.code || item.name || "");
  return "";
}

// Saved countries list -> unique code strings
function normalizeCountries(list) {
  if (!Array.isArray(list)) return [];
  return [...new Set(list.map(toCountryCode).filter(Boolean))];
}

// Full countries list (dropdown ke liye) -> [{code, name}]
function normalizeAllCountries(list) {
  const arr = Array.isArray(list)
    ? list
    : Array.isArray(list?.countries)
      ? list.countries
      : [];

  return arr
    .map((c) => {
      if (typeof c === "string") return { code: c, name: c };
      if (c && typeof c === "object") {
        const code = String(c.code ?? c.name ?? "");
        return { code, name: String(c.name ?? c.code ?? "") };
      }
      return null;
    })
    .filter((c) => c && c.code);
}

function getErrorMessage(error) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return (
      detail
        .map((d) => (typeof d === "string" ? d : d?.msg || ""))
        .filter(Boolean)
        .join(", ") || "Invalid request."
    );
  }
  return error?.message || "Something went wrong.";
}

function formatTime(value) {
  if (!value) return "Not run yet";
  return new Date(value).toLocaleString();
}

function AutoDiscoveryPage() {
  const navigate = useNavigate();

  const [form, setForm] = useState(EMPTY_FORM);
  const [status, setStatus] = useState(null);
  const [allCountries, setAllCountries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [running, setRunning] = useState(false);
  const formLoaded = useRef(false);

  const applyServerState = useCallback((data, { updateForm }) => {
    setStatus(data);
    if (updateForm) {
      setForm({
        industry: data.industry || "",
        batch_size: data.batch_size,
        require_email: data.require_email,
        require_website: data.require_website,
        run_every_minutes: data.run_every_minutes,
        city_size: data.city_size || "mix",
        countries: normalizeCountries(data.countries),
      });
    }
  }, []);

  // First load
  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [settings, countries] = await Promise.all([
          autoDiscoveryService.getSettings(),
          autoDiscoveryService.getCountries(),
        ]);
        if (cancelled) return;
        setAllCountries(normalizeAllCountries(countries));
        applyServerState(settings, { updateForm: true });
        formLoaded.current = true;
      } catch (error) {
        toast.error(getErrorMessage(error));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [applyServerState]);

  // Status refresh (form ko touch nahi karta)
  useEffect(() => {
    const timer = setInterval(async () => {
      if (!formLoaded.current) return;
      try {
        const data = await autoDiscoveryService.getSettings();
        applyServerState(data, { updateForm: false });
      } catch {
        /* ignore polling errors */
      }
    }, 15000);

    return () => clearInterval(timer);
  }, [applyServerState]);

  function setField(name, value) {
    setForm((current) => ({ ...current, [name]: value }));
  }

  function addCountry(code) {
    if (!code) return;
    setForm((current) =>
      current.countries.includes(code)
        ? current
        : { ...current, countries: [...current.countries, code] },
    );
  }

  function removeCountry(code) {
    setForm((current) => ({
      ...current,
      countries: current.countries.filter((c) => c !== code),
    }));
  }

  async function save(enabled) {
    if (enabled && !form.industry.trim()) {
      toast.error("Please type an industry first.");
      return;
    }

    setSaving(true);
    try {
      const data = await autoDiscoveryService.updateSettings({
        ...form,
        industry: form.industry.trim() || null,
        enabled,
      });
      applyServerState(data, { updateForm: true });
      toast.success(
        enabled
          ? "Auto-discovery is ON. New leads will appear in Leads."
          : "Settings saved.",
      );
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setSaving(false);
    }
  }

  async function stop() {
    setSaving(true);
    try {
      const data = await autoDiscoveryService.updateSettings({
        ...form,
        industry: form.industry.trim() || null,
        enabled: false,
      });
      applyServerState(data, { updateForm: true });
      toast.info("Auto-discovery stopped.");
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setSaving(false);
    }
  }

  async function runNow() {
    setRunning(true);
    try {
      // Pehle settings save karo taake latest industry/filters use hon
      await autoDiscoveryService.updateSettings({
        ...form,
        industry: form.industry.trim() || null,
        enabled: status?.enabled || false,
      });
      await autoDiscoveryService.runNow();
      toast.success(
        "Started. It can take a few minutes; new leads appear in Leads.",
      );
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setRunning(false);
    }
  }

  async function resetLocation() {
    try {
      const data = await autoDiscoveryService.resetLocation();
      applyServerState(data, { updateForm: false });
      toast.success("Visited cities cleared. Starting over.");
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  }

  if (loading) {
    return (
      <main className="lead-discovery-page">
        <div className="lead-discovery-shell">
          <div className="discovery-loading">
            <LoaderCircle className="discovery-spin" size={28} />
          </div>
        </div>
      </main>
    );
  }

  const isOn = Boolean(status?.enabled);

  const countryNames = Object.fromEntries(
    allCountries.map((country) => [country.code, country.name]),
  );
  const selectedCodes = new Set(form.countries.map(toCountryCode).filter(Boolean));
  const availableCountries = allCountries.filter(
    (country) => !selectedCodes.has(country.code),
  );

  return (
    <main className="lead-discovery-page">
      <div className="lead-discovery-shell">

        <header className="lead-discovery-header">
          <div>
            <button
              type="button"
              className="lead-back-button"
              onClick={() => navigate("/leads/discover")}
            >
              <ArrowLeft size={16} />
              Discover Leads
            </button>

            <div className="lead-discovery-eyebrow">AUTO DISCOVERY</div>

            <h1>
              Leads on
              <span> autopilot.</span>
            </h1>

            <p className="lead-discovery-description">
              Choose an industry once. The system searches whole cities
              anywhere in the world (big or small), moves on to the next city
              until each batch is full, and never saves the same business
              twice.
            </p>
          </div>
        </header>

        <section className="discovery-search-panel">
          <div className="discovery-panel-header">
            <div>
              <span className="discovery-panel-label">SETTINGS</span>
              <h2>What should it look for?</h2>
            </div>

            <div className="auto-status-pill-wrap">
              <span className={`auto-status-pill ${isOn ? "on" : "off"}`}>
                <span className="auto-status-dot" />
                {isOn ? "Running" : "Stopped"}
              </span>
            </div>
          </div>

          <div className="auto-form">
            <div className="discovery-field auto-wide">
              <label htmlFor="auto-industry">Industry</label>
              <input
                id="auto-industry"
                type="text"
                placeholder="e.g. hotel, restaurant, dentist"
                value={form.industry}
                maxLength={100}
                onChange={(event) => setField("industry", event.target.value)}
              />
            </div>

            <div className="discovery-field">
              <label>Require leads with</label>
              <div className="discovery-filter-options" role="group">
                <button
                  type="button"
                  className={`discovery-filter-option ${
                    form.require_email ? "selected" : ""
                  }`}
                  onClick={() =>
                    setField("require_email", !form.require_email)
                  }
                  aria-pressed={form.require_email}
                >
                  <span className="discovery-filter-check">
                    {form.require_email && <Check size={12} />}
                  </span>
                  Email
                </button>

                <button
                  type="button"
                  className={`discovery-filter-option ${
                    form.require_website ? "selected" : ""
                  }`}
                  onClick={() =>
                    setField("require_website", !form.require_website)
                  }
                  aria-pressed={form.require_website}
                >
                  <span className="discovery-filter-check">
                    {form.require_website && <Check size={12} />}
                  </span>
                  Website
                </button>
              </div>
            </div>

            <div className="discovery-field">
              <label>Leads per location</label>
              <div className="discovery-filter-options" role="group">
                {BATCH_OPTIONS.map((size) => (
                  <button
                    key={size}
                    type="button"
                    className={`discovery-filter-option ${
                      form.batch_size === size ? "selected" : ""
                    }`}
                    onClick={() => setField("batch_size", size)}
                    aria-pressed={form.batch_size === size}
                  >
                    {size}
                  </button>
                ))}
              </div>
            </div>

            <div className="discovery-field">
              <label>Run every</label>
              <div className="discovery-filter-options" role="group">
                {INTERVAL_OPTIONS.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    className={`discovery-filter-option ${
                      form.run_every_minutes === option.value
                        ? "selected"
                        : ""
                    }`}
                    onClick={() =>
                      setField("run_every_minutes", option.value)
                    }
                    aria-pressed={form.run_every_minutes === option.value}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="discovery-field auto-countries">
            <label>City size</label>
            <div className="discovery-filter-options" role="group">
              {CITY_SIZE_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  className={`discovery-filter-option ${
                    form.city_size === option.value ? "selected" : ""
                  }`}
                  onClick={() => setField("city_size", option.value)}
                  aria-pressed={form.city_size === option.value}
                >
                  {option.label}
                  <span className="auto-size-hint">{option.hint}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="discovery-field auto-countries">
            <label>
              Countries{" "}
              <span className="auto-hint">
                (none selected = the whole world)
              </span>
            </label>

            <select
              className="auto-country-select"
              value=""
              onChange={(event) => addCountry(event.target.value)}
              disabled={availableCountries.length === 0}
            >
              <option value="">
                {allCountries.length === 0
                  ? "Country list is loading..."
                  : "Add a country..."}
              </option>
              {availableCountries.map((country) => (
                <option key={country.code} value={country.code}>
                  {country.name}
                </option>
              ))}
            </select>

            {form.countries.length > 0 && (
              <div className="auto-chip-row">
                {form.countries.map((code) => {
                  const codeStr = toCountryCode(code) || String(code);
                  return (
                    <button
                      key={codeStr}
                      type="button"
                      className="auto-chip selected"
                      onClick={() => removeCountry(code)}
                      title="Remove"
                    >
                      {countryNames[codeStr] || codeStr}
                      <X size={12} />
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          <div className="auto-actions">
            {isOn ? (
              <button
                type="button"
                className="discovery-submit-button auto-stop"
                onClick={stop}
                disabled={saving}
              >
                <Square size={15} />
                Stop auto-discovery
              </button>
            ) : (
              <button
                type="button"
                className="discovery-submit-button"
                onClick={() => save(true)}
                disabled={saving}
              >
                {saving ? (
                  <LoaderCircle className="discovery-spin" size={15} />
                ) : (
                  <Play size={15} />
                )}
                Start auto-discovery
              </button>
            )}

            <button
              type="button"
              className="auto-secondary"
              onClick={() => save(isOn)}
              disabled={saving}
            >
              Save settings
            </button>

            <button
              type="button"
              className="auto-secondary"
              onClick={runNow}
              disabled={running || !form.industry.trim()}
            >
              {running ? (
                <LoaderCircle className="discovery-spin" size={14} />
              ) : (
                <Zap size={14} />
              )}
              Run now
            </button>
          </div>
        </section>

        <section className="discovery-search-panel auto-status-panel">
          <div className="discovery-panel-header">
            <div>
              <span className="discovery-panel-label">PROGRESS</span>
              <h2>What it has done</h2>
            </div>

            <div className="discovery-panel-icon">
              <MapPin size={20} />
            </div>
          </div>

          <div className="auto-stats">
            <div className="auto-stat">
              <span>Total leads found</span>
              <strong>{status?.total_found ?? 0}</strong>
            </div>
            <div className="auto-stat">
              <span>Last location</span>
              <strong>{asText(status?.last_location) || "-"}</strong>
              <small>
                {status?.last_location
                  ? `${status.last_run_found ?? 0} new leads in the last run`
                  : ""}
              </small>
            </div>
            <div className="auto-stat">
              <span>Next location</span>
              <strong>{asText(status?.next_location) || "-"}</strong>
              <small>
                {status?.next_location && status?.next_location_count > 0
                  ? `of ${status.next_location_count} locations`
                  : ""}
              </small>
            </div>
            <div className="auto-stat">
              <span>Cities done</span>
              <strong>{status?.cities_visited ?? 0}</strong>
              <small>for this industry</small>
            </div>
            <div className="auto-stat">
              <span>Last run</span>
              <strong>{formatTime(status?.last_run_at)}</strong>
            </div>
          </div>

          {status?.last_error && (
            <div className="auto-error">
              Last problem: {asText(status.last_error)}
            </div>
          )}

          <div className="auto-actions">
            <button
              type="button"
              className="auto-secondary"
              onClick={() => navigate("/leads")}
            >
              View saved leads
            </button>

            <button
              type="button"
              className="auto-secondary"
              onClick={resetLocation}
            >
              <RotateCcw size={14} />
              Start over (forget visited cities)
            </button>
          </div>
        </section>

      </div>
    </main>
  );
}

export default AutoDiscoveryPage;