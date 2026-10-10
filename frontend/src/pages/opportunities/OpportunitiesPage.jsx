import {
  ArrowRight,
  Building2,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  Globe,
  Mail,
  Phone,
  Plus,
  RefreshCw,
  Search,
  Sparkles,
  Target,
  Trash2,
  TrendingUp,
  Users,
  X,
  Zap,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "react-toastify";

import opportunityService from "../../services/opportunityService";
import leadsService from "../../services/leadsService";
import "./OpportunitiesPage.css";

// ---------------------------------------------------------------------------
// Response normalizers
// ---------------------------------------------------------------------------

function normalizeList(response) {
  if (Array.isArray(response)) return response;
  if (Array.isArray(response?.opportunities)) return response.opportunities;
  if (Array.isArray(response?.data)) return response.data;
  if (Array.isArray(response?.items)) return response.items;
  return [];
}

function normalizeLeadsList(response) {
  if (Array.isArray(response)) return response;
  if (Array.isArray(response?.leads)) return response.leads;
  if (Array.isArray(response?.data)) return response.data;
  return [];
}

function normalizeItem(response) {
  if (!response) return null;
  if (response?.opportunity_id) return response;
  if (response?.opportunity) return response.opportunity;
  return response;
}

// ---------------------------------------------------------------------------
// Opportunity field accessors
// ---------------------------------------------------------------------------

function getOpportunityId(item) {
  return item?.opportunity_id || item?.id || "";
}

function getLeadId(item) {
  return item?.lead_id || "";
}

function getBusinessName(item) {
  return item?.business_name || item?.name || "Unnamed business";
}

function getIndustry(item) {
  return item?.industry || "Business";
}

function getLocation(item) {
  return item?.location_summary || item?.city || "";
}

function getEmail(item) {
  return item?.email || "";
}

function getPhone(item) {
  return item?.phone || "";
}

function getOpportunitySummary(item) {
  return (
    item?.opportunity_summary ||
    "This business appears to be a potential website-development opportunity."
  );
}

function getRecommendedSolution(item) {
  return (
    item?.recommended_solution ||
    "Offer a professional website tailored to the business."
  );
}

function getSalesAngle(item) {
  return item?.sales_angle || "";
}

function getBusinessSummary(item) {
  return item?.business_summary || "";
}

function getPersonalizationPoints(item) {
  const pts = item?.personalization_points;
  return Array.isArray(pts) ? pts : [];
}

function getSuggestedFeatures(item) {
  const feats = item?.suggested_features;
  return Array.isArray(feats) ? feats : [];
}

function getLevel(item) {
  return String(item?.qualification_level || "medium").toLowerCase();
}

function getOpportunityStatus(item) {
  return item?.opportunity_status || "open";
}

function getQualificationStatus(item) {
  return item?.qualification_status || "pending";
}

// ---------------------------------------------------------------------------
// Display helpers
// ---------------------------------------------------------------------------

function getLevelClass(level) {
  if (level === "high") return "level-high";
  if (level === "low") return "level-low";
  return "level-medium";
}

function getLevelLabel(level) {
  if (level === "high") return "High potential";
  if (level === "low") return "Low potential";
  return "Medium potential";
}

const STATUS_LABELS = {
  open: "Open",
  contacted: "Contacted",
  converted: "Converted",
  closed: "Closed",
  ignored: "Ignored",
};

const STATUS_CLASSES = {
  open: "level-medium",
  contacted: "level-high",
  converted: "level-high",
  closed: "level-low",
  ignored: "level-low",
};

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

function OpportunitiesPage() {
  // Tab: "opportunities" | "generate"
  const [activeTab, setActiveTab] = useState("opportunities");

  // Opportunities list
  const [opportunities, setOpportunities] = useState([]);
  const [loadingOpps, setLoadingOpps] = useState(true);
  const [selectedOpportunity, setSelectedOpportunity] = useState(null);
  const [updatingStatus, setUpdatingStatus] = useState(false);

  // No-website leads (for generate tab)
  const [noWebsiteLeads, setNoWebsiteLeads] = useState([]);
  const [loadingLeads, setLoadingLeads] = useState(false);
  // Track which lead IDs are currently being generated and which already have opps
  const [generating, setGenerating] = useState({});
  const [generatedLeadIds, setGeneratedLeadIds] = useState(new Set());

  // Search / filter / sort (opportunities tab)
  const [search, setSearch] = useState("");
  const [levelFilter, setLevelFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [sortBy, setSortBy] = useState("date");

  // Lead search (generate tab)
  const [leadSearch, setLeadSearch] = useState("");

  // Bulk generate state
  const [bulkGenerating, setBulkGenerating] = useState(false);

  // Delete state
  const [deletingId, setDeletingId] = useState(null);

  // Pagination
  const [page, setPage] = useState(1);
  const pageSize = 10;

  // -------------------------------------------------------------------------
  // Load opportunities
  // -------------------------------------------------------------------------

  const loadOpportunities = async () => {
    try {
      setLoadingOpps(true);

      const response = await opportunityService.getOpportunities({
        limit: 100,
      });

      const list = normalizeList(response);
      setOpportunities(list);

      // Track which lead IDs already have an opportunity generated
      setGeneratedLeadIds(
        new Set(list.map((item) => getLeadId(item)).filter(Boolean)),
      );
    } catch (error) {
      console.error("Unable to load opportunities:", error);
      toast.error(
        error?.response?.data?.detail ||
          "Unable to load website opportunities.",
      );
      setOpportunities([]);
    } finally {
      setLoadingOpps(false);
    }
  };

  // -------------------------------------------------------------------------
  // Load no-website leads
  // -------------------------------------------------------------------------

  const loadNoWebsiteLeads = async () => {
    try {
      setLoadingLeads(true);

      const response = await leadsService.getLeads({
        website_status: "no_website",
        page_size: 100,
      });

      setNoWebsiteLeads(normalizeLeadsList(response));
    } catch (error) {
      console.error("Unable to load no-website leads:", error);
      toast.error("Unable to load leads without websites.");
      setNoWebsiteLeads([]);
    } finally {
      setLoadingLeads(false);
    }
  };

  useEffect(() => {
    loadOpportunities();
  }, []);

  useEffect(() => {
    if (activeTab === "generate" && noWebsiteLeads.length === 0) {
      loadNoWebsiteLeads();
    }
  }, [activeTab]);

  // Auto-refresh when tab becomes visible again
  useEffect(() => {
    const handleVisibility = () => {
      if (!document.hidden) {
        loadOpportunities();
      }
    };
    document.addEventListener("visibilitychange", handleVisibility);
    return () => document.removeEventListener("visibilitychange", handleVisibility);
  }, []);

  // -------------------------------------------------------------------------
  // Delete opportunity
  // -------------------------------------------------------------------------

  const handleDelete = async (opportunityId) => {
    const confirmed = window.confirm(
      "Delete this opportunity? This cannot be undone.",
    );
    if (!confirmed) return;

    setDeletingId(opportunityId);
    try {
      await opportunityService.deleteOpportunity(opportunityId);
      setOpportunities((prev) =>
        prev.filter((item) => getOpportunityId(item) !== opportunityId),
      );
      setSelectedOpportunity(null);
      toast.success("Opportunity deleted.");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Unable to delete opportunity.");
    } finally {
      setDeletingId(null);
    }
  };

  // -------------------------------------------------------------------------
  // Bulk generate
  // -------------------------------------------------------------------------

  const handleBulkGenerate = async () => {
    const pending = noWebsiteLeads.filter(
      (l) => !generatedLeadIds.has(l.id),
    ).length;

    if (pending === 0) {
      toast.info("All no-website leads already have opportunities.");
      return;
    }

    setBulkGenerating(true);
    try {
      const result = await opportunityService.bulkGenerate(
        Math.min(pending, 20),
      );

      const { generated = 0, skipped = 0, failed = 0 } = result;

      if (generated > 0) {
        toast.success(
          `${generated} opportunit${generated !== 1 ? "ies" : "y"} generated.` +
            (skipped > 0 ? ` ${skipped} skipped.` : "") +
            (failed > 0 ? ` ${failed} failed.` : ""),
        );
        await loadOpportunities();
      } else if (failed > 0) {
        toast.error(`Generation failed for ${failed} lead(s).`);
      } else {
        toast.info("No new opportunities to generate.");
      }
    } catch (err) {
      toast.error(
        err?.response?.data?.detail || "Bulk generation failed.",
      );
    } finally {
      setBulkGenerating(false);
    }
  };

  // -------------------------------------------------------------------------
  // Generate opportunity for a lead
  // -------------------------------------------------------------------------

  const handleGenerate = async (leadId) => {
    setGenerating((prev) => ({ ...prev, [leadId]: true }));

    try {
      const result = await opportunityService.createOpportunity(leadId);
      const normalized = normalizeItem(result);

      if (normalized) {
        setOpportunities((prev) => [normalized, ...prev]);
        setGeneratedLeadIds((prev) => new Set([...prev, leadId]));
        toast.success(`Opportunity generated for ${normalized.business_name || "this lead"}.`);
      }
    } catch (error) {
      const detail = error?.response?.data?.detail;

      if (error?.response?.status === 409) {
        // Already exists — mark as generated and reload
        setGeneratedLeadIds((prev) => new Set([...prev, leadId]));
        toast.info("An opportunity already exists for this lead.");
        await loadOpportunities();
      } else {
        console.error("Unable to generate opportunity:", error);
        toast.error(
          typeof detail === "string"
            ? detail
            : "Unable to generate opportunity.",
        );
      }
    } finally {
      setGenerating((prev) => ({ ...prev, [leadId]: false }));
    }
  };

  // -------------------------------------------------------------------------
  // Status update (inside modal)
  // -------------------------------------------------------------------------

  const handleStatusUpdate = async (
    opportunityId,
    newOpportunityStatus,
    newQualificationStatus,
  ) => {
    setUpdatingStatus(true);

    try {
      const updated = await opportunityService.updateOpportunityStatus(
        opportunityId,
        {
          opportunity_status: newOpportunityStatus,
          qualification_status: newQualificationStatus,
        },
      );

      const normalized = normalizeItem(updated);

      setOpportunities((prev) =>
        prev.map((item) =>
          getOpportunityId(item) === opportunityId
            ? { ...item, ...normalized }
            : item,
        ),
      );

      setSelectedOpportunity((prev) =>
        prev ? { ...prev, ...normalized } : prev,
      );

      toast.success("Status updated.");
    } catch (error) {
      console.error("Unable to update status:", error);
      toast.error(
        error?.response?.data?.detail || "Unable to update status.",
      );
    } finally {
      setUpdatingStatus(false);
    }
  };

  // -------------------------------------------------------------------------
  // Filter + sort (opportunities tab)
  // -------------------------------------------------------------------------

  const filteredOpportunities = useMemo(() => {
    const query = search.trim().toLowerCase();

    const filtered = opportunities.filter((item) => {
      const name = getBusinessName(item).toLowerCase();
      const industry = getIndustry(item).toLowerCase();
      const location = getLocation(item).toLowerCase();
      const email = getEmail(item).toLowerCase();
      const level = getLevel(item);
      const opStatus = getOpportunityStatus(item);

      const matchesSearch =
        !query ||
        name.includes(query) ||
        industry.includes(query) ||
        location.includes(query) ||
        email.includes(query);

      const matchesLevel = levelFilter === "all" || level === levelFilter;
      const matchesStatus = statusFilter === "all" || opStatus === statusFilter;

      return matchesSearch && matchesLevel && matchesStatus;
    });

    return [...filtered].sort((a, b) => {
      if (sortBy === "name")
        return getBusinessName(a).localeCompare(getBusinessName(b));
      if (sortBy === "industry")
        return getIndustry(a).localeCompare(getIndustry(b));
      if (sortBy === "level") {
        const order = { high: 0, medium: 1, low: 2 };
        return (order[getLevel(a)] ?? 1) - (order[getLevel(b)] ?? 1);
      }
      // Default: newest first
      return new Date(b.created_at || 0) - new Date(a.created_at || 0);
    });
  }, [opportunities, search, levelFilter, statusFilter, sortBy]);

  const totalPages = Math.max(
    1,
    Math.ceil(filteredOpportunities.length / pageSize),
  );

  const visibleOpportunities = filteredOpportunities.slice(
    (page - 1) * pageSize,
    page * pageSize,
  );

  useEffect(() => {
    if (page > totalPages) setPage(totalPages);
  }, [page, totalPages]);

  // -------------------------------------------------------------------------
  // Filter no-website leads (generate tab)
  // -------------------------------------------------------------------------

  const filteredLeads = useMemo(() => {
    const query = leadSearch.trim().toLowerCase();
    if (!query) return noWebsiteLeads;

    return noWebsiteLeads.filter((lead) => {
      const name = (lead.name || lead.business_name || "").toLowerCase();
      const industry = (lead.industry || "").toLowerCase();
      const city = (lead.city || "").toLowerCase();
      return (
        name.includes(query) ||
        industry.includes(query) ||
        city.includes(query)
      );
    });
  }, [noWebsiteLeads, leadSearch]);

  // -------------------------------------------------------------------------
  // Stats
  // -------------------------------------------------------------------------

  const stats = useMemo(() => {
    const total = opportunities.length;
    const high = opportunities.filter((item) => getLevel(item) === "high").length;
    const medium = opportunities.filter((item) => getLevel(item) === "medium").length;
    const open = opportunities.filter(
      (item) => getOpportunityStatus(item) === "open",
    ).length;
    return { total, high, medium, open };
  }, [opportunities]);

  // -------------------------------------------------------------------------
  // Modal
  // -------------------------------------------------------------------------

  const openDetails = (item) => setSelectedOpportunity(item);
  const closeDetails = () => setSelectedOpportunity(null);

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------

  return (
    <div className="opportunities-page">
      {/* HERO */}
      <section className="opportunities-hero">
        <div className="opportunities-hero-copy">
          <div className="opportunities-eyebrow">
            <Sparkles size={15} />
            Website Opportunities
          </div>
          <h1>No website? Find the opportunity.</h1>
          <p>
            Review businesses that appear to have no website and identify which
            ones may be relevant for website outreach.
          </p>
        </div>
        <div className="opportunities-hero-icon">
          <Globe size={34} />
        </div>
      </section>

      {/* STATS */}
      <section className="opportunity-stats">
        <div className="opportunity-stat-card">
          <div className="opportunity-stat-icon blue">
            <Target size={19} />
          </div>
          <div>
            <span>Total opportunities</span>
            <strong>{stats.total}</strong>
          </div>
        </div>

        <div className="opportunity-stat-card">
          <div className="opportunity-stat-icon maroon">
            <TrendingUp size={19} />
          </div>
          <div>
            <span>High potential</span>
            <strong>{stats.high}</strong>
          </div>
        </div>

        <div className="opportunity-stat-card">
          <div className="opportunity-stat-icon sage">
            <Users size={19} />
          </div>
          <div>
            <span>Medium potential</span>
            <strong>{stats.medium}</strong>
          </div>
        </div>

        <div className="opportunity-stat-card">
          <div className="opportunity-stat-icon indigo">
            <Zap size={19} />
          </div>
          <div>
            <span>Open</span>
            <strong>{stats.open}</strong>
          </div>
        </div>
      </section>

      {/* TABS */}
      <div className="opp-tabs">
        <button
          type="button"
          className={`opp-tab ${activeTab === "opportunities" ? "opp-tab-active" : ""}`}
          onClick={() => setActiveTab("opportunities")}
        >
          <Sparkles size={15} />
          Opportunities
          {opportunities.length > 0 && (
            <span className="opp-tab-badge">{opportunities.length}</span>
          )}
        </button>

        <button
          type="button"
          className={`opp-tab ${activeTab === "generate" ? "opp-tab-active" : ""}`}
          onClick={() => setActiveTab("generate")}
        >
          <Plus size={15} />
          Generate
          {noWebsiteLeads.length > 0 && (
            <span className="opp-tab-badge opp-tab-badge-neutral">
              {noWebsiteLeads.filter((l) => !generatedLeadIds.has(l.id)).length}
            </span>
          )}
        </button>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* TAB: OPPORTUNITIES                                                  */}
      {/* ------------------------------------------------------------------ */}

      {activeTab === "opportunities" && (
        <>
          {/* Toolbar */}
          <section className="opportunities-toolbar">
            <div className="opportunity-search">
              <Search size={18} />
              <input
                type="text"
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setPage(1);
                }}
                placeholder="Search business, industry, location or email..."
              />
              {search && (
                <button
                  type="button"
                  className="search-clear"
                  onClick={() => {
                    setSearch("");
                    setPage(1);
                  }}
                  aria-label="Clear search"
                >
                  <X size={16} />
                </button>
              )}
            </div>

            <div className="opportunities-filters">
              <select
                value={levelFilter}
                onChange={(e) => {
                  setLevelFilter(e.target.value);
                  setPage(1);
                }}
              >
                <option value="all">All levels</option>
                <option value="high">High potential</option>
                <option value="medium">Medium potential</option>
                <option value="low">Low potential</option>
              </select>

              <select
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  setPage(1);
                }}
              >
                <option value="all">All statuses</option>
                <option value="open">Open</option>
                <option value="contacted">Contacted</option>
                <option value="converted">Converted</option>
                <option value="closed">Closed</option>
                <option value="ignored">Ignored</option>
              </select>

              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
              >
                <option value="date">Sort by date</option>
                <option value="level">Sort by level</option>
                <option value="name">Sort by business</option>
                <option value="industry">Sort by industry</option>
              </select>
            </div>
          </section>

          {/* Table */}
          <section className="opportunities-content">
            <div className="opportunities-section-header">
              <div>
                <span className="section-kicker">Lead opportunities</span>
                <h2>{filteredOpportunities.length} businesses found</h2>
              </div>
              <button
                type="button"
                className="refresh-opportunities"
                onClick={loadOpportunities}
                disabled={loadingOpps}
              >
                {loadingOpps ? "Refreshing..." : "Refresh"}
              </button>
            </div>

            {loadingOpps ? (
              <div className="opportunities-loading">
                <div className="opportunity-spinner" />
                <h3>Loading opportunities</h3>
                <p>We are retrieving businesses without detected websites.</p>
              </div>
            ) : visibleOpportunities.length === 0 ? (
              <div className="opportunities-empty">
                <div className="opportunities-empty-icon">
                  <Globe size={30} />
                </div>
                <h3>No opportunities yet</h3>
                <p>
                  Go to the <strong>Generate</strong> tab to create AI-powered
                  opportunities from your no-website leads.
                </p>
                <button
                  type="button"
                  className="opportunity-empty-action"
                  onClick={() => setActiveTab("generate")}
                >
                  Generate opportunities
                  <ArrowRight size={17} />
                </button>
              </div>
            ) : (
              <>
                <div className="opportunities-table-wrap">
                  <table className="opportunities-table">
                    <thead>
                      <tr>
                        <th>Business</th>
                        <th>Industry</th>
                        <th>Location</th>
                        <th>Potential</th>
                        <th>Status</th>
                        <th />
                      </tr>
                    </thead>
                    <tbody>
                      {visibleOpportunities.map((item) => {
                        const level = getLevel(item);
                        const opStatus = getOpportunityStatus(item);
                        return (
                          <tr
                            key={
                              getOpportunityId(item) ||
                              getLeadId(item) ||
                              `${getBusinessName(item)}-${Math.random()}`
                            }
                          >
                            <td>
                              <div className="business-cell">
                                <div className="business-avatar">
                                  <Building2 size={18} />
                                </div>
                                <div>
                                  <strong>{getBusinessName(item)}</strong>
                                  {getEmail(item) && (
                                    <span>{getEmail(item)}</span>
                                  )}
                                </div>
                              </div>
                            </td>
                            <td>
                              <span className="industry-text">
                                {getIndustry(item)}
                              </span>
                            </td>
                            <td>
                              <span className="location-text">
                                {getLocation(item) || "—"}
                              </span>
                            </td>
                            <td>
                              <span
                                className={`opportunity-level ${getLevelClass(level)}`}
                              >
                                {getLevelLabel(level)}
                              </span>
                            </td>
                            <td>
                              <span
                                className={`opportunity-level ${STATUS_CLASSES[opStatus] || "level-medium"}`}
                              >
                                {STATUS_LABELS[opStatus] || opStatus}
                              </span>
                            </td>
                            <td>
                              <button
                                type="button"
                                className="view-opportunity"
                                onClick={() => openDetails(item)}
                              >
                                View
                                <ArrowRight size={15} />
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

                <div className="opportunities-pagination">
                  <span>
                    Showing{" "}
                    <strong>{(page - 1) * pageSize + 1}</strong>
                    {" – "}
                    <strong>
                      {Math.min(
                        page * pageSize,
                        filteredOpportunities.length,
                      )}
                    </strong>
                    {" of "}
                    <strong>{filteredOpportunities.length}</strong>
                  </span>
                  <div className="pagination-controls">
                    <button
                      type="button"
                      disabled={page <= 1}
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      aria-label="Previous page"
                    >
                      <ChevronLeft size={17} />
                    </button>
                    <span className="pagination-page">
                      {page} / {totalPages}
                    </span>
                    <button
                      type="button"
                      disabled={page >= totalPages}
                      onClick={() =>
                        setPage((p) => Math.min(totalPages, p + 1))
                      }
                      aria-label="Next page"
                    >
                      <ChevronRight size={17} />
                    </button>
                  </div>
                </div>
              </>
            )}
          </section>
        </>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* TAB: GENERATE                                                       */}
      {/* ------------------------------------------------------------------ */}

      {activeTab === "generate" && (
        <section className="opportunities-content">
          <div className="opportunities-section-header">
            <div>
              <span className="section-kicker">No-website leads</span>
              <h2>
                {filteredLeads.filter((l) => !generatedLeadIds.has(l.id)).length} leads
                ready to analyse
              </h2>
            </div>

            <div style={{ display: "flex", gap: 10 }}>
              {/* inline search for this tab */}
              <div
                className="opportunity-search"
                style={{ maxWidth: 320, minWidth: 200 }}
              >
                <Search size={16} />
                <input
                  type="text"
                  value={leadSearch}
                  onChange={(e) => setLeadSearch(e.target.value)}
                  placeholder="Search leads..."
                />
                {leadSearch && (
                  <button
                    type="button"
                    className="search-clear"
                    onClick={() => setLeadSearch("")}
                    aria-label="Clear"
                  >
                    <X size={15} />
                  </button>
                )}
              </div>

              {/* Generate All button */}
              <button
                type="button"
                className="bulk-generate-btn"
                onClick={handleBulkGenerate}
                disabled={bulkGenerating || loadingLeads}
                title="Generate opportunities for all pending leads (up to 20 at once)"
              >
                {bulkGenerating ? (
                  <>
                    <RefreshCw size={14} className="opp-spin" />
                    Generating…
                  </>
                ) : (
                  <>
                    <Sparkles size={14} />
                    Generate All
                  </>
                )}
              </button>

              <button
                type="button"
                className="refresh-opportunities"
                onClick={loadNoWebsiteLeads}
                disabled={loadingLeads}
              >
                {loadingLeads ? "Loading..." : "Refresh"}
              </button>
            </div>
          </div>

          {loadingLeads ? (
            <div className="opportunities-loading">
              <div className="opportunity-spinner" />
              <h3>Loading leads</h3>
              <p>Fetching businesses without detected websites.</p>
            </div>
          ) : filteredLeads.length === 0 ? (
            <div className="opportunities-empty">
              <div className="opportunities-empty-icon">
                <Users size={30} />
              </div>
              <h3>No leads without a website</h3>
              <p>
                Discover more businesses first — leads with no detected website
                will appear here.
              </p>
              <a href="/leads/discover" className="opportunity-empty-action">
                Discover leads
                <ArrowRight size={17} />
              </a>
            </div>
          ) : (
            <div className="opportunities-table-wrap">
              <table className="opportunities-table">
                <thead>
                  <tr>
                    <th>Business</th>
                    <th>Industry</th>
                    <th>Location</th>
                    <th>Contact</th>
                    <th>AI Analysis</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredLeads.map((lead) => {
                    const leadId = lead.id;
                    const alreadyDone = generatedLeadIds.has(leadId);
                    const isGenerating = generating[leadId];

                    return (
                      <tr key={leadId}>
                        <td>
                          <div className="business-cell">
                            <div className="business-avatar">
                              <Building2 size={18} />
                            </div>
                            <div>
                              <strong>
                                {lead.name || lead.business_name || "Unnamed"}
                              </strong>
                              {lead.email && (
                                <span>{lead.email}</span>
                              )}
                            </div>
                          </div>
                        </td>

                        <td>
                          <span className="industry-text">
                            {lead.industry || "Business"}
                          </span>
                        </td>

                        <td>
                          <span className="location-text">
                            {lead.city || lead.address || "—"}
                          </span>
                        </td>

                        <td>
                          <div
                            style={{
                              display: "flex",
                              flexDirection: "column",
                              gap: 3,
                              fontSize: 12,
                              color: "var(--color-graphite-soft)",
                            }}
                          >
                            {lead.email && (
                              <span style={{ display: "flex", alignItems: "center", gap: 5 }}>
                                <Mail size={12} />
                                {lead.email}
                              </span>
                            )}
                            {lead.phone && (
                              <span style={{ display: "flex", alignItems: "center", gap: 5 }}>
                                <Phone size={12} />
                                {lead.phone}
                              </span>
                            )}
                            {!lead.email && !lead.phone && (
                              <span style={{ color: "var(--color-muted)" }}>
                                No contact
                              </span>
                            )}
                          </div>
                        </td>

                        <td>
                          {alreadyDone ? (
                            <span
                              className="opportunity-level level-high"
                              style={{ gap: 5, display: "inline-flex", alignItems: "center" }}
                            >
                              <Sparkles size={12} />
                              Generated
                            </span>
                          ) : (
                            <button
                              type="button"
                              className="generate-opp-btn"
                              disabled={isGenerating}
                              onClick={() => handleGenerate(leadId)}
                            >
                              {isGenerating ? (
                                <>
                                  <span className="generate-opp-spinner" />
                                  Generating...
                                </>
                              ) : (
                                <>
                                  <Sparkles size={14} />
                                  Generate
                                </>
                              )}
                            </button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* DETAIL MODAL                                                        */}
      {/* ------------------------------------------------------------------ */}

      {selectedOpportunity && (
        <div
          className="opportunity-modal-backdrop"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) closeDetails();
          }}
        >
          <div className="opportunity-modal">
            {/* Header */}
            <div className="opportunity-modal-header">
              <div>
                <span className="section-kicker">Opportunity details</span>
                <h2>{getBusinessName(selectedOpportunity)}</h2>
              </div>
              <button
                type="button"
                className="modal-close"
                onClick={closeDetails}
                aria-label="Close"
              >
                <X size={19} />
              </button>
            </div>

            {/* Level + status row */}
            <div className="opportunity-modal-score">
              <div>
                <span>Potential level</span>
                <strong
                  className={`opportunity-level ${getLevelClass(
                    getLevel(selectedOpportunity),
                  )}`}
                  style={{ marginTop: 6, display: "inline-flex" }}
                >
                  {getLevelLabel(getLevel(selectedOpportunity))}
                </strong>
              </div>
              <span
                className={`opportunity-level ${
                  STATUS_CLASSES[getOpportunityStatus(selectedOpportunity)] ||
                  "level-medium"
                }`}
              >
                {STATUS_LABELS[getOpportunityStatus(selectedOpportunity)] ||
                  getOpportunityStatus(selectedOpportunity)}
              </span>
            </div>

            {/* Detail grid */}
            <div className="opportunity-detail-grid">
              <div className="opportunity-detail">
                <span>Industry</span>
                <strong>{getIndustry(selectedOpportunity)}</strong>
              </div>
              <div className="opportunity-detail">
                <span>Location</span>
                <strong>
                  {getLocation(selectedOpportunity) || "Not available"}
                </strong>
              </div>
              <div className="opportunity-detail">
                <span>Email</span>
                <strong>
                  {getEmail(selectedOpportunity) || "Not available"}
                </strong>
              </div>
              <div className="opportunity-detail">
                <span>Phone</span>
                <strong>
                  {getPhone(selectedOpportunity) || "Not available"}
                </strong>
              </div>
            </div>

            {/* Business summary */}
            {getBusinessSummary(selectedOpportunity) && (
              <div className="opportunity-detail-block">
                <span>About this business</span>
                <p>{getBusinessSummary(selectedOpportunity)}</p>
              </div>
            )}

            {/* Opportunity summary */}
            <div className="opportunity-detail-block">
              <span>Why this is an opportunity</span>
              <p>{getOpportunitySummary(selectedOpportunity)}</p>
            </div>

            {/* Recommended solution */}
            <div className="opportunity-detail-block recommendation">
              <div className="recommendation-title">
                <Sparkles size={17} />
                Recommended solution
              </div>
              <p>{getRecommendedSolution(selectedOpportunity)}</p>
            </div>

            {/* Sales angle */}
            {getSalesAngle(selectedOpportunity) && (
              <div className="opportunity-detail-block">
                <span>Sales angle</span>
                <p>{getSalesAngle(selectedOpportunity)}</p>
              </div>
            )}

            {/* Personalization points */}
            {getPersonalizationPoints(selectedOpportunity).length > 0 && (
              <div className="opportunity-detail-block">
                <span>Personalization points</span>
                <ul className="opp-list">
                  {getPersonalizationPoints(selectedOpportunity).map(
                    (pt, i) => <li key={i}>{pt}</li>,
                  )}
                </ul>
              </div>
            )}

            {/* Suggested features */}
            {getSuggestedFeatures(selectedOpportunity).length > 0 && (
              <div className="opportunity-detail-block">
                <span>Suggested features</span>
                <ul className="opp-list">
                  {getSuggestedFeatures(selectedOpportunity).map(
                    (feat, i) => <li key={i}>{feat}</li>,
                  )}
                </ul>
              </div>
            )}

            {/* Status update */}
            <div className="opportunity-detail-block" style={{ marginTop: 15 }}>
              <span>Update status</span>
              <div className="opp-status-row">
                <select
                  disabled={updatingStatus}
                  value={getOpportunityStatus(selectedOpportunity)}
                  onChange={(e) =>
                    handleStatusUpdate(
                      getOpportunityId(selectedOpportunity),
                      e.target.value,
                      getQualificationStatus(selectedOpportunity),
                    )
                  }
                  className="opp-status-select"
                  aria-label="Opportunity status"
                >
                  <option value="open">Open</option>
                  <option value="contacted">Contacted</option>
                  <option value="converted">Converted</option>
                  <option value="closed">Closed</option>
                  <option value="ignored">Ignored</option>
                </select>

                <select
                  disabled={updatingStatus}
                  value={getQualificationStatus(selectedOpportunity)}
                  onChange={(e) =>
                    handleStatusUpdate(
                      getOpportunityId(selectedOpportunity),
                      getOpportunityStatus(selectedOpportunity),
                      e.target.value,
                    )
                  }
                  className="opp-status-select"
                  aria-label="Qualification status"
                >
                  <option value="pending">Pending</option>
                  <option value="qualified">Qualified</option>
                  <option value="unqualified">Unqualified</option>
                </select>
              </div>
            </div>

            {/* Action buttons */}
            <div className="opportunity-modal-actions">
              {getEmail(selectedOpportunity) && (
                <a
                  href={`mailto:${getEmail(selectedOpportunity)}`}
                  className="opportunity-action primary"
                >
                  <Mail size={17} />
                  Contact business
                </a>
              )}
              {getPhone(selectedOpportunity) && (
                <a
                  href={`tel:${getPhone(selectedOpportunity)}`}
                  className="opportunity-action secondary"
                >
                  <Phone size={16} />
                  {getPhone(selectedOpportunity)}
                </a>
              )}
              {getLeadId(selectedOpportunity) && (
                <a
                  href={`/email/editor?lead_id=${getLeadId(selectedOpportunity)}`}
                  className="opportunity-action secondary"
                >
                  <Mail size={16} />
                  Write email
                </a>
              )}
              {getLeadId(selectedOpportunity) && (
                <a
                  href={`/leads?search=${encodeURIComponent(getBusinessName(selectedOpportunity))}`}
                  className="opportunity-action secondary"
                >
                  Open lead
                  <ExternalLink size={16} />
                </a>
              )}
              {/* Delete */}
              <button
                type="button"
                className="opportunity-action opp-delete-btn"
                disabled={deletingId === getOpportunityId(selectedOpportunity)}
                onClick={() =>
                  handleDelete(getOpportunityId(selectedOpportunity))
                }
              >
                {deletingId === getOpportunityId(selectedOpportunity) ? (
                  <RefreshCw size={15} className="opp-spin" />
                ) : (
                  <Trash2 size={15} />
                )}
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default OpportunitiesPage;
