import { useMemo, useState } from "react";
import {
  ArrowLeft,
  ArrowUpDown,
  Check,
  Globe,
  LoaderCircle,
  MapPin,
  Search,
  SlidersHorizontal,
  Users,
  X,
} from "lucide-react";
import { toast } from "react-toastify";
import { useNavigate } from "react-router-dom";

import discoveryService from "../../services/discoveryService";
import "./LeadDiscoveryPage.css";

function normalizeResults(data) {
  if (Array.isArray(data)) {
    return data;
  }

  if (Array.isArray(data?.businesses)) {
    return data.businesses;
  }

  if (Array.isArray(data?.results)) {
    return data.results;
  }

  if (Array.isArray(data?.data)) {
    return data.data;
  }

  return [];
}

function getBusinessId(business, index) {
  return (
    business.id ||
    business.place_id ||
    business.osm_id ||
    business.external_id ||
    `business-${index}`
  );
}

function getBusinessName(business) {
  return (
    business.name ||
    business.business_name ||
    business.display_name?.split(",")[0] ||
    "Unnamed business"
  );
}

function getIndustry(business) {
  return (
    business.industry ||
    business.category ||
    business.type ||
    business.business_type ||
    "Business"
  );
}

function getLocation(business) {
  return (
    business.location ||
    business.address ||
    business.display_name ||
    "Location unavailable"
  );
}

function getWebsite(business) {
  return (
    business.website ||
    business.website_url ||
    business.url ||
    null
  );
}

function getEmail(business) {
  return (
    business.email ||
    business.email_address ||
    null
  );
}

function getPhone(business) {
  return (
    business.phone ||
    business.phone_number ||
    null
  );
}

function LeadDiscoveryPage() {
  const navigate = useNavigate();

  const [form, setForm] = useState({
    country: "",
    state: "",
    city: "",
    industry: "",
    lead_limit: 100,
    filters: [],
  });

  const [results, setResults] = useState([]);
  const [searchMeta, setSearchMeta] = useState({
    candidatesScanned: 0,
    alreadySaved: 0,
    filters: [],
  });
  const [selectedIds, setSelectedIds] = useState([]);
  const [loading, setLoading] = useState(false);
  const [sortBy, setSortBy] = useState("name");
  const [hasSearched, setHasSearched] = useState(false);

  const updateField = (field, value) => {
    setForm((current) => ({
      ...current,
      [field]: value,
    }));
  };

  const toggleFilter = (filter) => {
    setForm((current) => ({
      ...current,
      filters: current.filters.includes(filter)
        ? current.filters.filter((item) => item !== filter)
        : [...current.filters, filter],
    }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!form.country.trim()) {
      toast.error("Please enter a country.");
      return;
    }

    if (!form.city.trim()) {
      toast.error("Please enter a city.");
      return;
    }

    if (!form.industry.trim()) {
      toast.error("Please enter an industry.");
      return;
    }

    const leadLimit = Number(form.lead_limit);

    if (
      Number.isNaN(leadLimit) ||
      leadLimit < 1
    ) {
      toast.error("Lead limit must be at least 1.");
      return;
    }

    setLoading(true);
    setHasSearched(true);
    setSelectedIds([]);

    try {
      const data = await discoveryService.discoverBusinesses({
        country: form.country.trim(),
        state: form.state.trim() || null,
        city: form.city.trim(),
        industry: form.industry.trim(),
        limit: leadLimit,
        filters: form.filters,
      });

      const discoveredBusinesses = normalizeResults(data);

      setResults(discoveredBusinesses);
      setSearchMeta({
        candidatesScanned: Number(data?.candidates_scanned) || 0,
        alreadySaved: Number(data?.already_saved_skipped) || 0,
        filters: Array.isArray(data?.filters_applied)
          ? data.filters_applied
          : [],
      });

      if (discoveredBusinesses.length === 0) {
        toast.info(
          Number(data?.already_saved_skipped) > 0
            ? `No new businesses: ${Number(data.already_saved_skipped)} found were already in your leads.`
            : "No businesses were found for this search.",
        );
      } else {
        toast.success(
          `${discoveredBusinesses.length} businesses discovered.`,
        );
      }
    } catch (error) {
      console.error("Business discovery failed:", error);

      const detail = error?.response?.data?.detail;
      const httpStatus = error?.response?.status;

      let message = "Unable to discover businesses right now. Please try again.";

      if (typeof detail === "string" && detail.length > 0) {
        message = detail;
      } else if (httpStatus === 404) {
        message = `Location not found — check spelling of "${form.city}" or try a nearby larger city.`;
      } else if (httpStatus === 504) {
        message = "Discovery timed out. Overpass servers are busy — try again in a moment.";
      } else if (httpStatus === 502) {
        message = "Discovery service unavailable right now. Try again in a moment.";
      }

      toast.error(message, { autoClose: 8000 });
      setResults([]);
      setSearchMeta({ candidatesScanned: 0, filters: [] });
    } finally {
      setLoading(false);
    }
  };

  const sortedResults = useMemo(() => {
    const copied = [...results];

    copied.sort((first, second) => {
      if (sortBy === "website") {
        const firstWebsite = getWebsite(first) ? 1 : 0;
        const secondWebsite = getWebsite(second) ? 1 : 0;

        return secondWebsite - firstWebsite;
      }

      return getBusinessName(first).localeCompare(
        getBusinessName(second),
      );
    });

    return copied;
  }, [results, sortBy]);

  const toggleSelection = (businessId) => {
    setSelectedIds((current) => {
      if (current.includes(businessId)) {
        return current.filter(
          (id) => id !== businessId,
        );
      }

      return [...current, businessId];
    });
  };

  const toggleSelectAll = () => {
    if (
      selectedIds.length === sortedResults.length &&
      sortedResults.length > 0
    ) {
      setSelectedIds([]);
      return;
    }

    setSelectedIds(
      sortedResults.map((business, index) =>
        getBusinessId(business, index),
      ),
    );
  };

  const clearResults = () => {
    setResults([]);
    setSelectedIds([]);
    setSearchMeta({ candidatesScanned: 0, filters: [] });
    setHasSearched(false);
  };

  return (
    <main className="lead-discovery-page">
      <div className="lead-discovery-shell">

        <header className="lead-discovery-header">
          <div>
            <button
              type="button"
              className="lead-back-button"
              onClick={() => navigate("/dashboard")}
            >
              <ArrowLeft size={16} />
              Dashboard
            </button>

            <div className="lead-discovery-eyebrow">
              LEAD DISCOVERY
            </div>

            <h1>
              Find businesses
              <span> worth reaching.</span>
            </h1>

            <p className="lead-discovery-description">
              Search businesses by location and industry,
              then identify which ones have a website and
              which ones may need one.
            </p>
          </div>
        </header>

        <section className="discovery-search-panel">
          <div className="discovery-panel-header">
            <div>
              <span className="discovery-panel-label">
                SEARCH CRITERIA
              </span>

              <h2>
                Define your target market
              </h2>
            </div>

            <div className="discovery-panel-icon">
              <SlidersHorizontal size={20} />
            </div>
          </div>

          <form
            className="discovery-form"
            onSubmit={handleSubmit}
          >
            <div className="discovery-field">
              <label htmlFor="country">
                Country
              </label>

              <input
                id="country"
                type="text"
                value={form.country}
                onChange={(event) =>
                  updateField(
                    "country",
                    event.target.value,
                  )
                }
                placeholder="e.g. United States"
              />
            </div>

            <div className="discovery-field">
              <label htmlFor="state">
                State / Province
              </label>

              <input
                id="state"
                type="text"
                value={form.state}
                onChange={(event) =>
                  updateField(
                    "state",
                    event.target.value,
                  )
                }
                placeholder="e.g. Texas"
              />
            </div>

            <div className="discovery-field">
              <label htmlFor="city">
                City
              </label>

              <input
                id="city"
                type="text"
                value={form.city}
                onChange={(event) =>
                  updateField(
                    "city",
                    event.target.value,
                  )
                }
                placeholder="e.g. Austin"
              />
            </div>

            <div className="discovery-field">
              <label htmlFor="industry">
                Industry
              </label>

              <input
                id="industry"
                type="text"
                value={form.industry}
                onChange={(event) =>
                  updateField(
                    "industry",
                    event.target.value,
                  )
                }
                placeholder="Any business type: Steel manufacturer, Shipping, Solar installer..."
              />
            </div>

            <div className="discovery-field discovery-limit-field">
              <label htmlFor="lead_limit">
                Lead limit
              </label>

              <input
                id="lead_limit"
                type="number"
                min="1"
                value={form.lead_limit}
                onChange={(event) =>
                  updateField(
                    "lead_limit",
                    event.target.value,
                  )
                }
              />
            </div>

            <div className="discovery-field discovery-filter-field">
              <label>
                Require leads with
              </label>

              <div
                className="discovery-filter-options"
                role="group"
                aria-label="Required lead filters"
              >
                <button
                  type="button"
                  className={`discovery-filter-option ${
                    form.filters.includes("has_email") ? "selected" : ""
                  }`}
                  onClick={() => toggleFilter("has_email")}
                  aria-pressed={form.filters.includes("has_email")}
                >
                  <span className="discovery-filter-check">
                    {form.filters.includes("has_email") && <Check size={12} />}
                  </span>
                  Email
                </button>

                <button
                  type="button"
                  className={`discovery-filter-option ${
                    form.filters.includes("has_website") ? "selected" : ""
                  }`}
                  onClick={() => toggleFilter("has_website")}
                  aria-pressed={form.filters.includes("has_website")}
                >
                  <span className="discovery-filter-check">
                    {form.filters.includes("has_website") && <Check size={12} />}
                  </span>
                  Website
                </button>
              </div>
            </div>

            <button
              type="submit"
              className="discovery-submit-button"
              disabled={loading}
            >
              {loading ? (
                <>
                  <LoaderCircle
                    size={17}
                    className="discovery-spin"
                  />
                  Discovering...
                </>
              ) : (
                <>
                  <Search size={17} />
                  Discover leads
                </>
              )}
            </button>
          </form>
        </section>

        {loading && (
          <section className="discovery-loading">
            <div className="discovery-loading-icon">
              <LoaderCircle
                size={24}
                className="discovery-spin"
              />
            </div>

            <div>
              <h3>
                Discovering businesses
              </h3>

              <p>
                Searching the selected location and
                industry for relevant businesses.
              </p>
            </div>
          </section>
        )}

        {!loading && hasSearched && (
          <section className="discovery-results-section">

            <div className="results-header">
              <div>
                <span className="discovery-panel-label">
                  DISCOVERY RESULTS
                </span>

                <h2>
                  {results.length} businesses found
                </h2>
                {searchMeta.candidatesScanned > 0 && (
                  <p className="discovery-result-summary">
                    {searchMeta.candidatesScanned} candidates scanned; {results.length} qualified leads returned
                    {searchMeta.filters.length > 0
                      ? ` (${searchMeta.filters.map((filter) => filter === "has_email" ? "email required" : "website required").join(", ")})`
                      : ""}.
                    {searchMeta.alreadySaved > 0
                      ? ` ${searchMeta.alreadySaved} businesses were skipped because they are already in your leads.`
                      : ""}
                  </p>
                )}
              </div>

              <div className="results-actions">
                {results.length > 0 && (
                  <>
                    <button
                      type="button"
                      className="results-select-button"
                      onClick={toggleSelectAll}
                    >
                      <Check size={15} />
                      {selectedIds.length ===
                        results.length
                        ? "Clear selection"
                        : "Select all"}
                    </button>

                    <button
                      type="button"
                      className="results-sort-button"
                      onClick={() =>
                        setSortBy((current) =>
                          current === "name"
                            ? "website"
                            : "name",
                        )
                      }
                    >
                      <ArrowUpDown size={15} />
                      Sort:{" "}
                      {sortBy === "name"
                        ? "Name"
                        : "Website"}
                    </button>
                  </>
                )}

                {results.length > 0 && (
                  <button
                    type="button"
                    className="results-clear-button"
                    onClick={clearResults}
                    aria-label="Clear results"
                  >
                    <X size={16} />
                  </button>
                )}
              </div>
            </div>

            {results.length === 0 ? (
              <div className="discovery-empty">
                <div className="discovery-empty-icon">
                  <Search size={23} />
                </div>

                <h3>
                  No businesses found
                </h3>

                <p>
                  {searchMeta.alreadySaved > 0
                    ? `${searchMeta.alreadySaved} businesses matched but are already in your leads. Try a different city or industry.`
                    : "Try a different city, industry, or search area to discover more businesses."}
                </p>
              </div>
            ) : (
              <>
                <div className="selection-summary">
                  <Users size={16} />

                  <span>
                    {selectedIds.length} selected
                  </span>

                  <span className="selection-summary-divider">
                    |
                  </span>

                  <span>
                    {results.length} total results
                  </span>
                </div>

                <div className="lead-results-list">
                  {sortedResults.map(
                    (business, index) => {
                      const businessId =
                        getBusinessId(
                          business,
                          index,
                        );

                      const name =
                        getBusinessName(
                          business,
                        );

                      const website =
                        getWebsite(
                          business,
                        );

                      const email =
                        getEmail(
                          business,
                        );

                      const phone =
                        getPhone(
                          business,
                        );

                      const isSelected =
                        selectedIds.includes(
                          businessId,
                        );

                      return (
                        <article
                          key={businessId}
                          className={`lead-result-card ${
                            isSelected
                              ? "selected"
                              : ""
                          }`}
                        >
                          <button
                            type="button"
                            className={`lead-select-box ${
                              isSelected
                                ? "checked"
                                : ""
                            }`}
                            onClick={() =>
                              toggleSelection(
                                businessId,
                              )
                            }
                            aria-label={
                              isSelected
                                ? `Deselect ${name}`
                                : `Select ${name}`
                            }
                          >
                            {isSelected && (
                              <Check size={14} />
                            )}
                          </button>

                          <div className="lead-result-main">
                            <div className="lead-result-top">
                              <div>
                                <h3>
                                  {name}
                                </h3>

                                <span className="lead-industry">
                                  {getIndustry(
                                    business,
                                  )}
                                </span>
                              </div>

                              <span
                                className={`website-status ${
                                  website
                                    ? "has-website"
                                    : "no-website"
                                }`}
                              >
                                <Globe size={13} />

                                {website
                                  ? "Website available"
                                  : "No website"}
                              </span>
                            </div>

                            <div className="lead-result-details">
                              <div className="lead-detail">
                                <MapPin
                                  size={15}
                                />

                                <span>
                                  {getLocation(
                                    business,
                                  )}
                                </span>
                              </div>

                              {website && (
                                <div className="lead-detail">
                                  <Globe
                                    size={15}
                                  />

                                  <a
                                    href={website}
                                    target="_blank"
                                    rel="noreferrer"
                                    onClick={(event) =>
                                      event.stopPropagation()
                                    }
                                  >
                                    {website}
                                  </a>
                                </div>
                              )}

                              {email && (
                                <div className="lead-detail">
                                  <span className="lead-detail-label">
                                    Email
                                  </span>

                                  <span>
                                    {email}
                                  </span>
                                </div>
                              )}

                              {phone && (
                                <div className="lead-detail">
                                  <span className="lead-detail-label">
                                    Phone
                                  </span>

                                  <span>
                                    {phone}
                                  </span>
                                </div>
                              )}
                            </div>
                          </div>
                        </article>
                      );
                    },
                  )}
                </div>
              </>
            )}
          </section>
        )}

        {!hasSearched && (
          <section className="discovery-intro-grid">
            <div className="discovery-intro-card">
              <div className="discovery-intro-icon maroon">
                <Search size={20} />
              </div>

              <h3>
                Search by location
              </h3>

              <p>
                Choose a country, state, and city to
                narrow the business discovery area.
              </p>
            </div>

            <div className="discovery-intro-card">
              <div className="discovery-intro-icon blue">
                <Users size={20} />
              </div>

              <h3>
                Target an industry
              </h3>

              <p>
                Focus discovery on the type of businesses
                you want to reach.
              </p>
            </div>

            <div className="discovery-intro-card">
              <div className="discovery-intro-icon sage">
                <Globe size={20} />
              </div>

              <h3>
                Find opportunities
              </h3>

              <p>
                Separate businesses with websites from
                businesses that may need one.
              </p>
            </div>
          </section>
        )}

      </div>
    </main>
  );
}

export default LeadDiscoveryPage;