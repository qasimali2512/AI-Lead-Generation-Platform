import { useCallback, useEffect, useRef, useState } from "react";
import {
  ChevronLeft,
  ChevronRight,
  Globe,
  LoaderCircle,
  Mail,
  MapPin,
  Phone,
  Search,
  SlidersHorizontal,
  Target,
  Users,
  X,
} from "lucide-react";
import { toast } from "react-toastify";
import { useNavigate, useSearchParams } from "react-router-dom";

import leadsService from "../../services/leadsService";
import "./LeadsPage.css";


// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getLeadId(lead)       { return lead?.id || null; }
function getLeadName(lead)     { return lead.business_name || lead.name || lead.company_name || "Unnamed business"; }
function getIndustry(lead)     { return lead.industry || lead.category || lead.business_type || lead.type || "Business"; }
function getLocation(lead)     { return lead.location || lead.address || lead.city || lead.display_name || "Location unavailable"; }
function getWebsite(lead)      { return lead.website || lead.website_url || lead.url || null; }
function getEmail(lead)        { return lead.email || lead.email_address || null; }
function getPhone(lead)        { return lead.phone || lead.phone_number || null; }

function getQualification(lead) {
  const q = lead.qualification_level || lead.qualification || lead.qualification_status;
  return q ? String(q) : "Not qualified";
}

function getQualificationClass(lead) {
  const v = getQualification(lead).toLowerCase().replaceAll("_", " ");
  if (v.includes("qualified") && !v.includes("unqualified")) return "qualified";
  if (v.includes("high") || v.includes("ready")) return "high";
  if (v.includes("low") || v.includes("not")) return "low";
  return "neutral";
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

const PAGE_SIZE = 25;

export default function LeadsPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  // ------------------------------------------------------------------
  // Server-side filter state
  // ------------------------------------------------------------------
  const [search,            setSearch]            = useState(() => searchParams.get("search") || "");
  const [searchInput,       setSearchInput]       = useState(() => searchParams.get("search") || "");
  const [websiteFilter,     setWebsiteFilter]     = useState("all");
  const [emailFilter,       setEmailFilter]       = useState("all");
  const [qualificationFilter, setQualificationFilter] = useState("all");
  const [dateFilter,        setDateFilter]        = useState("1");
  const [sortBy,            setSortBy]            = useState("date");

  // ------------------------------------------------------------------
  // Pagination from server
  // ------------------------------------------------------------------
  const [page,      setPage]      = useState(1);
  const [total,     setTotal]     = useState(0);
  const [leads,     setLeads]     = useState([]);
  const [loading,   setLoading]   = useState(true);

  // Selection (persists across pages)
  const [selectedIds, setSelectedIds] = useState([]);

  // Debounce search input
  const debounceRef = useRef(null);
  const handleSearchInput = (value) => {
    setSearchInput(value);
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setSearch(value);
      setPage(1);
    }, 400);
  };

  // ------------------------------------------------------------------
  // Fetch — single API call, 25 leads, all filters on DB side
  // ------------------------------------------------------------------
  const fetchLeads = useCallback(async () => {
    setLoading(true);
    try {
      const params = {
        page,
        page_size: PAGE_SIZE,
        sort_by:   sortBy,
      };

      // Date
      if (dateFilter !== "all") params.days = Number(dateFilter);

      // Search
      if (search.trim()) params.search = search.trim();

      // Website
      if (websiteFilter === "with")    params.has_website = "yes";
      if (websiteFilter === "without") params.has_website = "no";

      // Email
      if (emailFilter === "with")    params.has_email = "yes";
      if (emailFilter === "without") params.has_email = "no";

      // Qualification
      if (qualificationFilter !== "all") params.qualification = qualificationFilter;

      const data = await leadsService.getLeads(params);

      const pageLeads = Array.isArray(data?.leads)   ? data.leads
                      : Array.isArray(data?.results)  ? data.results
                      : Array.isArray(data)            ? data
                      : [];

      setLeads(pageLeads);
      setTotal(data?.total ?? pageLeads.length);
    } catch (err) {
      if (err?.response?.status === 404) { setLeads([]); setTotal(0); return; }
      const detail = err?.response?.data?.detail;
      toast.error(typeof detail === "string" ? detail : "Unable to load leads right now.");
    } finally {
      setLoading(false);
    }
  }, [page, sortBy, dateFilter, search, websiteFilter, emailFilter, qualificationFilter]);

  useEffect(() => { fetchLeads(); }, [fetchLeads]);

  // ------------------------------------------------------------------
  // Derived
  // ------------------------------------------------------------------
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const selectedVisibleCount = leads.filter(l => selectedIds.includes(getLeadId(l))).length;

  const hasFilters =
    search.trim() ||
    websiteFilter !== "all" ||
    emailFilter !== "all" ||
    qualificationFilter !== "all" ||
    dateFilter !== "1";

  // ------------------------------------------------------------------
  // Actions
  // ------------------------------------------------------------------
  const clearFilters = () => {
    setSearchInput(""); setSearch("");
    setWebsiteFilter("all");
    setEmailFilter("all");
    setQualificationFilter("all");
    setDateFilter("1");
    setSortBy("date");
    setPage(1);
  };

  const toggleLead = (leadId) => {
    setSelectedIds(cur =>
      cur.includes(leadId) ? cur.filter(id => id !== leadId) : [...cur, leadId]
    );
  };

  const toggleVisibleLeads = () => {
    const visibleIds = leads.map(l => getLeadId(l));
    const allSelected = visibleIds.length > 0 && visibleIds.every(id => selectedIds.includes(id));
    if (allSelected) {
      setSelectedIds(cur => cur.filter(id => !visibleIds.includes(id)));
    } else {
      setSelectedIds(cur => [...new Set([...cur, ...visibleIds])]);
    }
  };

  const createCampaignFromSelected = () => {
    if (selectedIds.length === 0) { toast.info("Select at least one lead first."); return; }
    const selectedLeadIds = selectedIds.map(String);
    localStorage.setItem("leadflow_selected_lead_ids", JSON.stringify(selectedLeadIds));
    navigate("/campaigns/new", { state: { selectedLeadIds, selectedCount: selectedLeadIds.length } });
  };

  const goToPage = (next) => setPage(Math.max(1, Math.min(next, totalPages)));

  // Filter change resets to page 1
  const changeFilter = (setter) => (val) => { setter(val); setPage(1); };

  // ------------------------------------------------------------------
  // Render
  // ------------------------------------------------------------------
  return (
    <main className="leads-page">
      <div className="leads-shell">

        {/* HEADER */}
        <header className="leads-header">
          <div>
            <div className="leads-eyebrow">LEAD MANAGEMENT</div>
            <h1>Your business <span> pipeline.</span></h1>
            <p className="leads-description">
              Review discovered businesses, filter opportunities, and
              prepare leads for website analysis and outreach.
            </p>
          </div>

          <button
            type="button"
            className="leads-refresh-button"
            onClick={fetchLeads}
            disabled={loading}
          >
            <LoaderCircle size={16} className={loading ? "leads-spin" : ""} />
            Refresh
          </button>
        </header>


        {/* SUMMARY */}
        <section className="leads-summary">
          <div className="lead-summary-card maroon">
            <div className="lead-summary-icon"><Users size={18} /></div>
            <div>
              <span>Total leads</span>
              <strong>{total}</strong>
            </div>
          </div>

          <div className="lead-summary-card blue">
            <div className="lead-summary-icon"><Globe size={18} /></div>
            <div>
              <span>Showing</span>
              <strong>{leads.length}</strong>
            </div>
          </div>

          <div className="lead-summary-card sage">
            <div className="lead-summary-icon"><Target size={18} /></div>
            <div>
              <span>Selected</span>
              <strong>{selectedIds.length}</strong>
            </div>
          </div>
        </section>


        {/* FILTER PANEL */}
        <section className="leads-filter-panel">
          <div className="leads-filter-top">
            <div>
              <span className="leads-panel-label">LEAD DATABASE</span>
              <h2>Search and filter leads</h2>
            </div>
            <div className="leads-filter-icon"><SlidersHorizontal size={19} /></div>
          </div>

          <div className="leads-filters">
            {/* Search — debounced, sent to backend */}
            <div className="leads-search">
              <Search size={17} />
              <input
                type="text"
                value={searchInput}
                onChange={e => handleSearchInput(e.target.value)}
                placeholder="Search business, industry, location..."
              />
              {searchInput && (
                <button
                  type="button"
                  onClick={() => { setSearchInput(""); setSearch(""); setPage(1); }}
                  aria-label="Clear search"
                >
                  <X size={15} />
                </button>
              )}
            </div>

            {/* Website filter */}
            <select
              value={websiteFilter}
              onChange={e => { setWebsiteFilter(e.target.value); setPage(1); }}
            >
              <option value="all">All websites</option>
              <option value="with">With website</option>
              <option value="without">No website</option>
            </select>

            {/* Email filter */}
            <select
              value={emailFilter}
              onChange={e => { setEmailFilter(e.target.value); setPage(1); }}
            >
              <option value="all">All emails</option>
              <option value="with">Has email</option>
              <option value="without">No email</option>
            </select>

            {/* Qualification filter */}
            <select
              value={qualificationFilter}
              onChange={e => { setQualificationFilter(e.target.value); setPage(1); }}
            >
              <option value="all">All qualification</option>
              <option value="qualified">Qualified</option>
              <option value="ready">Outreach ready</option>
              <option value="unqualified">Unqualified</option>
            </select>

            {/* Date range filter */}
            <select
              value={dateFilter}
              onChange={e => { setDateFilter(e.target.value); setPage(1); }}
            >
              <option value="1">Last 1 day</option>
              <option value="3">Last 3 days</option>
              <option value="7">Last 7 days</option>
              <option value="30">Last 30 days</option>
              <option value="all">All time</option>
            </select>

            {/* Sort */}
            <select
              value={sortBy}
              onChange={e => { setSortBy(e.target.value); setPage(1); }}
            >
              <option value="date">Sort: Newest</option>
              <option value="name">Sort: Name</option>
              <option value="industry">Sort: Industry</option>
            </select>

            {hasFilters && (
              <button type="button" className="leads-clear-button" onClick={clearFilters}>
                Clear
              </button>
            )}
          </div>
        </section>


        {/* RESULTS */}
        <section className="leads-results-section">
          <div className="leads-results-header">
            <div>
              <span className="leads-panel-label">RESULTS</span>
              <h2>{total} {total === 1 ? "lead" : "leads"}</h2>
            </div>

            <div className="leads-selection-info">
              {selectedIds.length > 0 && (
                <span>{selectedIds.length} selected</span>
              )}

              {selectedIds.length > 0 && (
                <button
                  type="button"
                  className="leads-create-campaign-button"
                  onClick={createCampaignFromSelected}
                >
                  Create Campaign
                </button>
              )}

              <button
                type="button"
                onClick={toggleVisibleLeads}
                disabled={leads.length === 0}
              >
                {selectedVisibleCount === leads.length && leads.length > 0
                  ? "Clear visible"
                  : "Select visible"}
              </button>
            </div>
          </div>


          {/* Loading state */}
          {loading ? (
            <div className="leads-empty-state">
              <div className="leads-empty-icon">
                <LoaderCircle size={24} className="leads-spin" />
              </div>
              <h3>Loading your leads</h3>
              <p>Fetching from your lead database…</p>
            </div>

          /* Empty state */
          ) : leads.length === 0 ? (
            <div className="leads-empty-state">
              <div className="leads-empty-icon"><Users size={23} /></div>
              <h3>{hasFilters ? "No leads match your filters" : "No leads yet"}</h3>
              <p>
                {hasFilters
                  ? "Try changing your search or filters to see more leads."
                  : "Discover businesses first and your leads will appear here."}
              </p>
              {hasFilters && (
                <button type="button" className="leads-empty-action" onClick={clearFilters}>
                  Clear filters
                </button>
              )}
            </div>

          /* Table */
          ) : (
            <div className="leads-table-wrapper">
              <div className="leads-table-head">
                <span className="lead-table-check">
                  <button
                    type="button"
                    onClick={toggleVisibleLeads}
                    aria-label="Select visible leads"
                  >
                    <span className={selectedVisibleCount === leads.length ? "checked" : ""}>
                      {selectedVisibleCount === leads.length && leads.length > 0 && <span />}
                    </span>
                  </button>
                </span>
                <span>Business</span>
                <span>Location</span>
                <span>Contact</span>
                <span>Website</span>
                <span>Email</span>
              </div>

              <div className="leads-table-body">
                {leads.map((lead) => {
                  const leadId    = getLeadId(lead);
                  const website   = getWebsite(lead);
                  const email     = getEmail(lead);
                  const phone     = getPhone(lead);
                  const isSelected = selectedIds.includes(leadId);

                  return (
                    <article
                      key={leadId}
                      className={`lead-row ${isSelected ? "selected" : ""}`}
                    >
                      <div className="lead-row-check">
                        <button
                          type="button"
                          onClick={() => toggleLead(leadId)}
                          aria-label={`Select ${getLeadName(lead)}`}
                        >
                          <span className={isSelected ? "checked" : ""}>
                            {isSelected && <span />}
                          </span>
                        </button>
                      </div>

                      <div className="lead-business-cell">
                        <div className="lead-business-avatar">
                          {getLeadName(lead).charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <strong>{getLeadName(lead)}</strong>
                          <span>{getIndustry(lead)}</span>
                        </div>
                      </div>

                      <div className="lead-location-cell">
                        <MapPin size={14} />
                        <span>{getLocation(lead)}</span>
                      </div>

                      <div className="lead-contact-cell">
                        {email && (
                          <div><Mail size={13} /><span>{email}</span></div>
                        )}
                        {phone && (
                          <div><Phone size={13} /><span>{phone}</span></div>
                        )}
                        {!email && !phone && (
                          <span className="lead-not-available">No contact</span>
                        )}
                      </div>

                      <div className="lead-website-cell">
                        {website ? (
                          <a href={website} target="_blank" rel="noreferrer">
                            <Globe size={14} />Website
                          </a>
                        ) : (
                          <span className="lead-no-website">No website</span>
                        )}
                      </div>

                      <div className="lead-email-col">
                        {email ? (
                          <a href={`mailto:${email}`} className="lead-email-link">
                            <Mail size={13} /><span>{email}</span>
                          </a>
                        ) : (
                          <span className="lead-not-available">No email</span>
                        )}
                      </div>
                    </article>
                  );
                })}
              </div>
            </div>
          )}


          {/* PAGINATION */}
          {total > PAGE_SIZE && (
            <div className="leads-pagination">
              <span>
                Showing {Math.min((page - 1) * PAGE_SIZE + 1, total)}
                {" – "}
                {Math.min(page * PAGE_SIZE, total)} of {total}
              </span>

              <div className="leads-pagination-controls">
                <button
                  type="button"
                  onClick={() => goToPage(page - 1)}
                  disabled={page === 1}
                  aria-label="Previous page"
                >
                  <ChevronLeft size={16} />
                </button>

                <span>{page} / {totalPages}</span>

                <button
                  type="button"
                  onClick={() => goToPage(page + 1)}
                  disabled={page >= totalPages}
                  aria-label="Next page"
                >
                  <ChevronRight size={16} />
                </button>
              </div>
            </div>
          )}

        </section>
      </div>
    </main>
  );
}