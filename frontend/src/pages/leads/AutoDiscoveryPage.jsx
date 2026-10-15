import { useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowLeft,
  Check,
  LoaderCircle,
  MapPin,
  Play,
  RotateCcw,
  Square,
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

const EMPTY_FORM = {
  industry: "",
  batch_size: 50,
  require_email: false,
  require_website: false,
  run_every_minutes: 30,
  countries: [],
};

function getErrorMessage(error) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") return detail;
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
        countries: data.countries || [],
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
        setAllCountries(countries);
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

  function toggleCountry(country) {
    setForm((current) => ({
      ...current,
      countries: current.countries.includes(country)
        ? current.countries.filter((c) => c !== country)
        : [...current.countries, country],
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
        "Started for the next location. Results appear in 1-3 minutes.",
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
      toast.success("Will start again from the first location.");
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
              Choose an industry once. The system searches whole cities (no
              radius), moves to a new country, state and city after every
              batch, and never saves the same business twice.
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
            <label>
              Countries{" "}
              <span className="auto-hint">
                (none selected = all countries)
              </span>
            </label>
            <div className="auto-chip-row">
              {allCountries.map((country) => {
                const selected = form.countries.includes(country);
                return (
                  <button
                    key={country}
                    type="button"
                    className={`auto-chip ${selected ? "selected" : ""}`}
                    onClick={() => toggleCountry(country)}
                    aria-pressed={selected}
                  >
                    {selected && <Check size={12} />}
                    {country}
                  </button>
                );
              })}
            </div>
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
              Run next location now
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
              <strong>{status?.last_location || "-"}</strong>
              <small>
                {status?.last_location
                  ? `${status.last_run_found} new leads`
                  : ""}
              </small>
            </div>
            <div className="auto-stat">
              <span>Next location</span>
              <strong>{status?.next_location || "-"}</strong>
              <small>of {status?.total_locations ?? 0} locations</small>
            </div>
            <div className="auto-stat">
              <span>Last run</span>
              <strong>{formatTime(status?.last_run_at)}</strong>
            </div>
          </div>

          {status?.last_error && (
            <div className="auto-error">
              Last problem: {status.last_error}
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
              Start from first location
            </button>
          </div>
        </section>

      </div>
    </main>
  );
}

export default AutoDiscoveryPage;