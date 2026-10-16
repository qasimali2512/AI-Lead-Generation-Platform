import {
  AlertTriangle,
  ArrowLeft,
  Check,
  ChevronDown,
  ChevronUp,
  Clock,
  Mail,
  Megaphone,
  Pause,
  Play,
  RefreshCw,
  Send,
  Sparkles,
  Trash2,
  Users,
  X,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { toast } from "react-toastify";

import campaignService from "../../services/campaignService";
import "./CampaignDetailPage.css";

// ---------------------------------------------------------------------------
// Constants
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

const LEAD_STATUS_LABELS = {
  pending_ai: "Pending AI",
  generating_ai: "Generating…",
  queued: "Queued",
  sent: "Sent",
  failed: "Failed",
  skipped: "Skipped",
  paused: "Paused",
  cancelled: "Cancelled",
  retry: "Retrying",
};

const LEAD_STATUS_CLASSES = {
  pending_ai: "ls-pending",
  generating_ai: "ls-generating",
  queued: "ls-queued",
  sent: "ls-sent",
  failed: "ls-failed",
  skipped: "ls-skipped",
  paused: "ls-paused",
  cancelled: "ls-cancelled",
  retry: "ls-retry",
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDateTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  if (isNaN(d)) return "—";
  return d.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatDate(value) {
  if (!value) return "—";
  const d = new Date(value);
  if (isNaN(d)) return "—";
  return d.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function countByStatus(leads, ...statuses) {
  return leads.filter((l) => statuses.includes(l.status)).length;
}

// ---------------------------------------------------------------------------
// Expandable email body row
// ---------------------------------------------------------------------------

function LeadEmailRow({ lead, index }) {
  const [expanded, setExpanded] = useState(false);

  const statusLabel =
    LEAD_STATUS_LABELS[lead.status] || lead.status;
  const statusClass =
    LEAD_STATUS_CLASSES[lead.status] || "ls-pending";

  return (
    <>
      <tr
        className={`detail-lead-row ${expanded ? "row-expanded" : ""}`}
        onClick={() => lead.email_subject && setExpanded((v) => !v)}
        style={{ cursor: lead.email_subject ? "pointer" : "default" }}
      >
        {/* # */}
        <td className="lead-num">{index + 1}</td>

        {/* Business */}
        <td>
          <div className="lead-name-cell">
            <div className="lead-avatar">
              {(lead.lead_name || "?").charAt(0).toUpperCase()}
            </div>
            <div>
              <strong>{lead.lead_name || "—"}</strong>
              <span>{lead.lead_industry || ""}</span>
            </div>
          </div>
        </td>

        {/* Recipient email */}
        <td>
          <span className="detail-meta">
            {lead.recipient_email || lead.lead_email || "—"}
          </span>
        </td>

        {/* Subject */}
        <td>
          <span className="email-subject-preview">
            {lead.email_subject
              ? lead.email_subject.length > 55
                ? lead.email_subject.slice(0, 55) + "…"
                : lead.email_subject
              : <em className="no-email-yet">Not generated yet</em>}
          </span>
        </td>

        {/* Scheduled time */}
        <td>
          <div className="schedule-cell">
            {lead.queue_scheduled_at ? (
              <>
                <Clock size={12} />
                <span>{formatDateTime(lead.queue_scheduled_at)}</span>
              </>
            ) : (
              <span className="detail-meta">—</span>
            )}
          </div>
        </td>

        {/* From (sender email account) */}
        <td>
          <div className="sender-email-cell">
            {lead.sender_email ? (
              <span className="sender-email-badge" title={lead.sender_display_name || lead.sender_email}>
                {lead.sender_email}
              </span>
            ) : (
              <span className="detail-meta">—</span>
            )}
          </div>
        </td>

        {/* Status */}
        <td>
          <span className={`lead-status-badge ${statusClass}`}>
            {statusLabel}
          </span>
        </td>

        {/* Expand toggle */}
        <td className="expand-cell">
          {lead.email_subject && (
            <button
              type="button"
              className="expand-btn"
              aria-label={expanded ? "Collapse" : "Expand"}
              onClick={(e) => {
                e.stopPropagation();
                setExpanded((v) => !v);
              }}
            >
              {expanded ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
            </button>
          )}
        </td>
      </tr>

      {/* Expanded email body */}
      {expanded && lead.email_body && (
        <tr className="email-body-row">
          <td colSpan={8}>
            <div className="email-body-panel">
              <div className="email-body-header">
                <Mail size={14} />
                <strong>Full email — {lead.lead_name}</strong>
                <span className="email-body-to">
                  To: {lead.recipient_email || lead.lead_email}
                </span>
              </div>

              <div className="email-body-subject">
                <span>Subject</span>
                <strong>{lead.email_subject}</strong>
              </div>

              <div className="email-body-text">
                {lead.email_body.split("\n").map((line, i) => (
                  <p key={i}>{line}</p>
                ))}
              </div>

              {lead.last_error && (
                <div className="email-body-error">
                  <AlertTriangle size={13} />
                  {lead.last_error}
                </div>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function CampaignDetailPage() {
  const { campaignId } = useParams();
  const navigate = useNavigate();

  const [campaign, setCampaign] = useState(null);
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [actionLoading, setActionLoading] = useState(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [lastRefreshed, setLastRefreshed] = useState(null);

  // Auto-refresh interval ref
  const refreshTimerRef = useRef(null);

  // -------------------------------------------------------------------------
  // Load
  // -------------------------------------------------------------------------

  const loadDetail = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    setLoadError(null);

    try {
      const data = await campaignService.getCampaign(campaignId);

      // Backend returns flat object: { id, name, status, ..., leads: [...] }
      const c = data?.id ? data : data?.campaign ?? data;

      if (!c?.id) {
        throw new Error("Invalid response from server.");
      }

      setCampaign(c);
      setLeads(Array.isArray(c?.leads) ? c.leads : []);
      setLastRefreshed(new Date());
    } catch (err) {
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail;

      if (status === 401) {
        // Token expired — redirect to login
        navigate("/login");
        return;
      }

      if (status === 404) {
        setLoadError("Campaign not found. It may have been deleted.");
      } else {
        setLoadError(
          detail || err?.message || "Unable to load campaign details.",
        );
      }

      if (!silent) {
        console.error("[CampaignDetail] load error:", err);
      }
    } finally {
      setLoading(false);
    }
  }, [campaignId, navigate]);

  // Initial load
  useEffect(() => {
    if (campaignId) loadDetail(false);
  }, [campaignId, loadDetail]);

  // Auto-refresh every 20 seconds when campaign is active
  useEffect(() => {
    if (campaign?.status === "active") {
      refreshTimerRef.current = setInterval(() => loadDetail(true), 20000);
    }
    return () => {
      if (refreshTimerRef.current) clearInterval(refreshTimerRef.current);
    };
  }, [campaign?.status, loadDetail]);

  // -------------------------------------------------------------------------
  // Actions
  // -------------------------------------------------------------------------

  const runAction = async (fn, label, successMsg) => {
    setActionLoading(label);
    try {
      await fn();
      toast.success(successMsg);
      await loadDetail(false);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      toast.error(detail || `Unable to ${label} campaign.`);
    } finally {
      setActionLoading(null);
    }
  };

  const handlePause = () =>
    runAction(
      () => campaignService.pauseCampaign(campaignId),
      "pause",
      "Campaign paused.",
    );

  const handleResume = () =>
    runAction(
      () => campaignService.resumeCampaign(campaignId),
      "resume",
      "Campaign resumed.",
    );

  const handleCancel = () =>
    runAction(
      () => campaignService.cancelCampaign(campaignId),
      "cancel",
      "Campaign cancelled.",
    );

  const handleDelete = async () => {
    setActionLoading("delete");
    try {
      await campaignService.deleteCampaign(campaignId);
      toast.success("Campaign deleted.");
      navigate("/campaigns");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Unable to delete campaign.");
      setActionLoading(null);
      setShowDeleteConfirm(false);
    }
  };

  // -------------------------------------------------------------------------
  // Derived stats
  // -------------------------------------------------------------------------

  const stats = campaign
    ? {
        total: leads.length,
        queued: countByStatus(leads, "queued"),
        sent: countByStatus(leads, "sent"),
        failed: countByStatus(leads, "failed"),
        skipped: countByStatus(leads, "skipped"),
        pending: countByStatus(leads, "pending_ai", "generating_ai", "retry"),
      }
    : {};

  const settings = campaign?.sending_settings || {};

  // -------------------------------------------------------------------------
  // Render — loading
  // -------------------------------------------------------------------------

  if (loading) {
    return (
      <div className="cd-page">
        <div className="cd-loading">
          <div className="cd-spinner" />
          <p>Loading campaign details…</p>
        </div>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="cd-page">
        <button
          type="button"
          className="cd-back"
          onClick={() => navigate("/campaigns")}
        >
          <ArrowLeft size={15} />
          Back to campaigns
        </button>
        <div className="cd-loading">
          <div className="cd-error-icon">
            <AlertTriangle size={26} />
          </div>
          <p className="cd-error-msg">{loadError}</p>
          <div className="cd-error-actions">
            <button
              type="button"
              className="cd-btn-primary"
              onClick={() => loadDetail(false)}
            >
              <RefreshCw size={15} />
              Try again
            </button>
            <button
              type="button"
              className="cd-btn-ghost"
              onClick={() => navigate("/campaigns")}
            >
              Back to campaigns
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!campaign) {
    return (
      <div className="cd-page">
        <div className="cd-loading">
          <p>Campaign not found.</p>
          <button type="button" onClick={() => navigate("/campaigns")}>
            Back to campaigns
          </button>
        </div>
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------

  return (
    <div className="cd-page">
      {/* Delete confirm modal */}
      {showDeleteConfirm && (
        <div
          className="cd-modal-backdrop"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) setShowDeleteConfirm(false);
          }}
        >
          <div className="cd-confirm-modal">
            <div className="cd-confirm-icon">
              <Trash2 size={22} />
            </div>
            <h3>Delete campaign?</h3>
            <p>
              This will permanently delete <strong>{campaign.name}</strong> and
              all associated lead records. This cannot be undone.
            </p>
            <div className="cd-confirm-actions">
              <button
                type="button"
                className="cd-btn-ghost"
                onClick={() => setShowDeleteConfirm(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="cd-btn-danger"
                disabled={actionLoading === "delete"}
                onClick={handleDelete}
              >
                {actionLoading === "delete" ? "Deleting…" : "Delete campaign"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Back nav */}
      <button
        type="button"
        className="cd-back"
        onClick={() => navigate("/campaigns")}
      >
        <ArrowLeft size={15} />
        Back to campaigns
      </button>

      {/* Header */}
      <header className="cd-header">
        <div className="cd-header-left">
          <div className="cd-title-icon">
            <Megaphone size={20} />
          </div>
          <div>
            <div className="cd-kicker">Campaign details</div>
            <h1>{campaign.name}</h1>
            <div className="cd-header-meta">
              <span
                className={`cd-status-badge ${STATUS_CLASSES[campaign.status] || ""}`}
              >
                {STATUS_LABELS[campaign.status] || campaign.status}
              </span>
              <span className="cd-meta-dot">·</span>
              <span className="cd-meta-text">
                Created {formatDate(campaign.created_at)}
              </span>
              {campaign.started_at && (
                <>
                  <span className="cd-meta-dot">·</span>
                  <span className="cd-meta-text">
                    Started {formatDateTime(campaign.started_at)}
                  </span>
                </>
              )}
              {campaign.completed_at && (
                <>
                  <span className="cd-meta-dot">·</span>
                  <span className="cd-meta-text">
                    Completed {formatDateTime(campaign.completed_at)}
                  </span>
                </>
              )}
              {lastRefreshed && (
                <>
                  <span className="cd-meta-dot">·</span>
                  <span className="cd-meta-text cd-sync-time">
                    {campaign.status === "active" && (
                      <span className="cd-auto-dot" title="Auto-refreshing every 20s" />
                    )}
                    Updated {lastRefreshed.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                  </span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Action buttons */}
        <div className="cd-header-actions">
          {campaign.status === "active" && (
            <button
              type="button"
              className="cd-btn-secondary"
              disabled={Boolean(actionLoading)}
              onClick={handlePause}
            >
              <Pause size={15} />
              {actionLoading === "pause" ? "Pausing…" : "Pause"}
            </button>
          )}

          {campaign.status === "paused" && (
            <button
              type="button"
              className="cd-btn-primary"
              disabled={Boolean(actionLoading)}
              onClick={handleResume}
            >
              <Play size={15} />
              {actionLoading === "resume" ? "Resuming…" : "Resume"}
            </button>
          )}

          {!["completed", "cancelled"].includes(campaign.status) && (
            <button
              type="button"
              className="cd-btn-secondary"
              disabled={Boolean(actionLoading)}
              onClick={handleCancel}
            >
              <X size={15} />
              {actionLoading === "cancel" ? "Cancelling…" : "Cancel"}
            </button>
          )}

          <button
            type="button"
            className="cd-btn-danger-outline"
            disabled={campaign.status === "active" || Boolean(actionLoading)}
            title={
              campaign.status === "active"
                ? "Pause or cancel the campaign before deleting"
                : "Delete campaign"
            }
            onClick={() => setShowDeleteConfirm(true)}
          >
            <Trash2 size={15} />
            Delete
          </button>
        </div>
      </header>

      {/* Error banner */}
      {campaign.last_error && (
        <div className="cd-error-banner">
          <AlertTriangle size={15} />
          <span>{campaign.last_error}</span>
        </div>
      )}

      {/* Top grid: stats + settings */}
      <div className="cd-grid">

        {/* Stats */}
        <section className="cd-card">
          <div className="cd-card-header">
            <Users size={16} />
            <h2>Lead progress</h2>
          </div>

          <div className="cd-stats">
            <div className="cd-stat">
              <span>Total leads</span>
              <strong>{stats.total}</strong>
            </div>
            <div className="cd-stat">
              <span>Queued</span>
              <strong className="stat-queued">{stats.queued}</strong>
            </div>
            <div className="cd-stat">
              <span>Sent</span>
              <strong className="stat-sent">{stats.sent}</strong>
            </div>
            <div className="cd-stat">
              <span>Pending</span>
              <strong>{stats.pending}</strong>
            </div>
            <div className="cd-stat">
              <span>Skipped</span>
              <strong>{stats.skipped}</strong>
            </div>
            <div className="cd-stat">
              <span>Failed</span>
              <strong className={stats.failed > 0 ? "stat-failed" : ""}>
                {stats.failed}
              </strong>
            </div>
          </div>

          {/* Progress bar */}
          {stats.total > 0 && (
            <div className="cd-progress-wrap">
              <div
                className="cd-progress-bar"
                style={{
                  width: `${Math.round(
                    ((stats.sent + stats.queued) / stats.total) * 100,
                  )}%`,
                }}
              />
            </div>
          )}
          <p className="cd-progress-label">
            {stats.sent + stats.queued} of {stats.total} emails queued or sent
          </p>
        </section>

        {/* Sending settings */}
        <section className="cd-card">
          <div className="cd-card-header">
            <Clock size={16} />
            <h2>Sending settings</h2>
          </div>

          <div className="cd-settings-grid">
            <div className="cd-setting">
              <span>Daily limit</span>
              <strong>{settings.daily_limit ?? "—"} emails / day</strong>
            </div>
            <div className="cd-setting">
              <span>Sending window</span>
              <strong>
                {settings.start_time ?? "—"} – {settings.end_time ?? "—"}
              </strong>
            </div>
            <div className="cd-setting">
              <span>Delay between emails</span>
              <strong>
                {settings.delay_min_minutes ?? "—"} –{" "}
                {settings.delay_max_minutes ?? "—"} min
              </strong>
            </div>
            <div className="cd-setting">
              <span>Business days only</span>
              <strong>
                {settings.business_days_only ? "Yes" : "No"}
              </strong>
            </div>
          </div>
        </section>

        {/* Follow-ups */}
        {Array.isArray(campaign.follow_up_settings) &&
          campaign.follow_up_settings.length > 0 && (
            <section className="cd-card">
              <div className="cd-card-header">
                <Sparkles size={16} />
                <h2>Follow-up sequence</h2>
              </div>

              <div className="cd-followups">
                {campaign.follow_up_settings.map((fu, i) => (
                  <div key={i} className="cd-followup-row">
                    <div className="cd-followup-num">{i + 1}</div>
                    <div>
                      <strong>{fu.label || `Follow-up ${i + 1}`}</strong>
                      <span>
                        Send after {fu.delay} {fu.unit}
                      </span>
                    </div>
                    <span
                      className={`fu-badge ${fu.enabled ? "fu-on" : "fu-off"}`}
                    >
                      {fu.enabled ? "Enabled" : "Disabled"}
                    </span>
                  </div>
                ))}
              </div>
            </section>
          )}

        {/* Account IDs */}
        <section className="cd-card">
          <div className="cd-card-header">
            <Send size={16} />
            <h2>Email accounts</h2>
          </div>

          <div className="cd-accounts">
            {Array.isArray(campaign.email_account_ids) &&
            campaign.email_account_ids.length > 0 ? (
              campaign.email_account_ids.map((id) => (
                <div key={id} className="cd-account-row">
                  <Mail size={13} />
                  <span className="cd-account-id">{id}</span>
                </div>
              ))
            ) : (
              <span className="cd-meta-text">No accounts linked.</span>
            )}
          </div>
        </section>
      </div>

      {/* Emails table */}
      <section className="cd-emails-section">
        <div className="cd-emails-header">
          <div>
            <span className="cd-kicker">Outreach emails</span>
            <h2>{leads.length} lead{leads.length !== 1 ? "s" : ""} in this campaign</h2>
          </div>
          <button
            type="button"
            className="cd-refresh-btn"
            onClick={() => loadDetail(false)}
            disabled={loading}
          >
            <RefreshCw size={13} className={loading ? "cd-spin-icon" : ""} />
            {loading ? "Refreshing…" : "Refresh"}
          </button>
        </div>

        {leads.length === 0 ? (
          <div className="cd-empty">
            <Users size={28} />
            <p>No leads attached to this campaign.</p>
          </div>
        ) : (
          <div className="cd-table-wrap">
            <table className="cd-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Business</th>
                  <th>Recipient</th>
                  <th>Subject</th>
                  <th>Scheduled for</th>
                  <th>From</th>
                  <th>Status</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {leads.map((lead, i) => (
                  <LeadEmailRow key={lead.id || i} lead={lead} index={i} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
