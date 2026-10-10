import {
  ArrowRight,
  Check,
  ChevronLeft,
  ChevronRight,
  Loader,
  Megaphone,
  Pause,
  Play,
  Plus,
  Send,
  Sparkles,
  Users,
  X,
} from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "react-toastify";
import { useNavigate } from "react-router-dom";

import campaignService from "../../services/campaignService";
import "./CampaignsListPage.css";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const STATUS_LABELS = {
  draft: "Draft",
  active: "Active",
  paused: "Paused",
  completed: "Completed",
  cancelled: "Cancelled",
};

const STATUS_CLASSES = {
  draft: "status-draft",
  active: "status-active",
  paused: "status-paused",
  completed: "status-completed",
  cancelled: "status-cancelled",
};

function formatDate(value) {
  if (!value) return "—";
  return new Date(value).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function normalizeCampaigns(response) {
  if (Array.isArray(response)) return response;
  if (Array.isArray(response?.items)) return response.items;
  if (Array.isArray(response?.campaigns)) return response.campaigns;
  return [];
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function CampaignsListPage() {
  const navigate = useNavigate();

  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState({});

  const [page, setPage] = useState(1);
  const PAGE_SIZE = 10;

  // -------------------------------------------------------------------------
  // Load
  // -------------------------------------------------------------------------

  const loadCampaigns = async () => {
    try {
      setLoading(true);
      const data = await campaignService.getCampaigns();
      setCampaigns(normalizeCampaigns(data));
    } catch (err) {
      console.error("Unable to load campaigns:", err);
      toast.error("Unable to load campaigns.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCampaigns();
  }, []);

  // -------------------------------------------------------------------------
  // Actions
  // -------------------------------------------------------------------------

  const runAction = async (campaignId, action, label) => {
    setActionLoading((prev) => ({ ...prev, [campaignId]: action }));

    try {
      await action(campaignId);
      toast.success(`Campaign ${label}.`);
      await loadCampaigns();
    } catch (err) {
      toast.error(err?.response?.data?.detail || `Unable to ${label} campaign.`);
    } finally {
      setActionLoading((prev) => ({ ...prev, [campaignId]: null }));
    }
  };

  const handlePause = (id) =>
    runAction(id, campaignService.pauseCampaign.bind(campaignService), "paused");

  const handleResume = (id) =>
    runAction(id, campaignService.resumeCampaign.bind(campaignService), "resumed");

  const handleCancel = (id) => {
    if (!window.confirm("Cancel this campaign? This cannot be undone.")) return;
    runAction(id, campaignService.cancelCampaign.bind(campaignService), "cancelled");
  };

  // -------------------------------------------------------------------------
  // Pagination
  // -------------------------------------------------------------------------

  const totalPages = Math.max(1, Math.ceil(campaigns.length / PAGE_SIZE));
  const visible = campaigns.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  // -------------------------------------------------------------------------
  // Stats
  // -------------------------------------------------------------------------

  const stats = {
    total: campaigns.length,
    active: campaigns.filter((c) => c.status === "active").length,
    completed: campaigns.filter((c) => c.status === "completed").length,
    totalLeads: campaigns.reduce((s, c) => s + (c.selected_lead_count || 0), 0),
  };

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------

  return (
    <div className="campaigns-page">
      {/* Header */}
      <header className="campaigns-header">
        <div className="campaigns-heading">
          <div className="campaigns-title-icon">
            <Megaphone size={22} />
          </div>
          <div>
            <div className="campaigns-kicker">Outreach Automation</div>
            <h1>Campaigns</h1>
            <p>
              Create, monitor and manage your outreach campaigns. Each campaign
              generates a personalized AI email per lead and queues them for
              sending.
            </p>
          </div>
        </div>

        <button
          type="button"
          className="new-campaign-button"
          onClick={() => navigate("/campaigns/new")}
        >
          <Plus size={16} />
          New Campaign
        </button>
      </header>

      {/* Stats */}
      <section className="campaigns-stats">
        <div className="campaign-stat-card">
          <span>Total campaigns</span>
          <strong>{stats.total}</strong>
        </div>
        <div className="campaign-stat-card stat-active">
          <span>Active</span>
          <strong>{stats.active}</strong>
        </div>
        <div className="campaign-stat-card">
          <span>Completed</span>
          <strong>{stats.completed}</strong>
        </div>
        <div className="campaign-stat-card">
          <span>Total leads</span>
          <strong>{stats.totalLeads}</strong>
        </div>
      </section>

      {/* Table */}
      <section className="campaigns-content">
        <div className="campaigns-content-header">
          <div>
            <span className="campaigns-section-kicker">All campaigns</span>
            <h2>{campaigns.length} campaign{campaigns.length !== 1 ? "s" : ""}</h2>
          </div>

          <button
            type="button"
            className="campaigns-refresh"
            onClick={loadCampaigns}
            disabled={loading}
          >
            {loading ? "Refreshing..." : "Refresh"}
          </button>
        </div>

        {loading ? (
          <div className="campaigns-loading">
            <div className="campaigns-spinner" />
            <h3>Loading campaigns</h3>
            <p>Fetching your outreach campaigns.</p>
          </div>
        ) : campaigns.length === 0 ? (
          <div className="campaigns-empty">
            <div className="campaigns-empty-icon">
              <Megaphone size={28} />
            </div>
            <h3>No campaigns yet</h3>
            <p>
              Go to the Leads page, select businesses, and click Create
              Campaign to get started.
            </p>
            <button
              type="button"
              className="campaigns-empty-action"
              onClick={() => navigate("/leads")}
            >
              Go to Leads
              <ArrowRight size={16} />
            </button>
          </div>
        ) : (
          <>
            <div className="campaigns-table-wrap">
              <table className="campaigns-table">
                <thead>
                  <tr>
                    <th>Campaign</th>
                    <th>Status</th>
                    <th>Leads</th>
                    <th>Daily limit</th>
                    <th>Window</th>
                    <th>Created</th>
                    <th />
                  </tr>
                </thead>

                <tbody>
                  {visible.map((campaign) => {
                    const settings = campaign.sending_settings || {};
                    const isLoading = actionLoading[campaign.id];

                    return (
                      <tr key={campaign.id}>
                        {/* Name */}
                        <td>
                          <div className="campaign-name-cell">
                            <div className="campaign-icon-badge">
                              <Send size={15} />
                            </div>
                            <div>
                              <strong>{campaign.name}</strong>
                              {campaign.last_error && (
                                <span className="campaign-error-badge">
                                  Error
                                </span>
                              )}
                            </div>
                          </div>
                        </td>

                        {/* Status */}
                        <td>
                          <span
                            className={`campaign-status-badge ${STATUS_CLASSES[campaign.status] || ""}`}
                          >
                            {STATUS_LABELS[campaign.status] || campaign.status}
                          </span>
                        </td>

                        {/* Leads */}
                        <td>
                          <div className="campaign-leads-cell">
                            <Users size={13} />
                            <span>{campaign.selected_lead_count ?? 0}</span>
                          </div>
                        </td>

                        {/* Daily limit */}
                        <td>
                          <span className="campaign-meta">
                            {settings.daily_limit ?? "—"} / day
                          </span>
                        </td>

                        {/* Window */}
                        <td>
                          <span className="campaign-meta">
                            {settings.start_time ?? "—"} – {settings.end_time ?? "—"}
                          </span>
                        </td>

                        {/* Created */}
                        <td>
                          <span className="campaign-meta">
                            {formatDate(campaign.created_at)}
                          </span>
                        </td>

                        {/* Actions */}
                        <td>
                          <div className="campaign-actions">
                            {campaign.status === "active" && (
                              <button
                                type="button"
                                className="campaign-action-btn"
                                title="Pause"
                                disabled={Boolean(isLoading)}
                                onClick={() => handlePause(campaign.id)}
                              >
                                {isLoading === campaignService.pauseCampaign ? (
                                  <Loader size={14} className="campaign-spin" />
                                ) : (
                                  <Pause size={14} />
                                )}
                              </button>
                            )}

                            {campaign.status === "paused" && (
                              <button
                                type="button"
                                className="campaign-action-btn action-resume"
                                title="Resume"
                                disabled={Boolean(isLoading)}
                                onClick={() => handleResume(campaign.id)}
                              >
                                {isLoading ? (
                                  <Loader size={14} className="campaign-spin" />
                                ) : (
                                  <Play size={14} />
                                )}
                              </button>
                            )}

                            {campaign.status === "completed" && (
                              <span className="campaign-done-badge">
                                <Check size={13} /> Done
                              </span>
                            )}

                            {!["completed", "cancelled"].includes(campaign.status) && (
                              <button
                                type="button"
                                className="campaign-action-btn action-cancel"
                                title="Cancel"
                                disabled={Boolean(isLoading)}
                                onClick={() => handleCancel(campaign.id)}
                              >
                                <X size={14} />
                              </button>
                            )}

                            <button
                              type="button"
                              className="campaign-view-btn"
                              onClick={() =>
                                navigate(`/campaigns/${campaign.id}`)
                              }
                            >
                              Details
                              <ArrowRight size={13} />
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {totalPages > 1 && (
              <div className="campaigns-pagination">
                <span>
                  Showing <strong>{(page - 1) * PAGE_SIZE + 1}</strong>–
                  <strong>{Math.min(page * PAGE_SIZE, campaigns.length)}</strong>{" "}
                  of <strong>{campaigns.length}</strong>
                </span>

                <div className="campaigns-pagination-controls">
                  <button
                    type="button"
                    disabled={page <= 1}
                    onClick={() => setPage((p) => p - 1)}
                    aria-label="Previous"
                  >
                    <ChevronLeft size={16} />
                  </button>
                  <span>{page} / {totalPages}</span>
                  <button
                    type="button"
                    disabled={page >= totalPages}
                    onClick={() => setPage((p) => p + 1)}
                    aria-label="Next"
                  >
                    <ChevronRight size={16} />
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </section>
    </div>
  );
}
