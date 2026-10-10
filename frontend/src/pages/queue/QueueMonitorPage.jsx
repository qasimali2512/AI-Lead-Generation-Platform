import {
  AlertCircle,
  CheckCircle2,
  Clock3,
  Mail,
  PauseCircle,
  PlayCircle,
  RefreshCw,
  RotateCcw,
  Search,
  Send,
  X,
  XCircle,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "react-toastify";

import queueService from "../../services/queueService";
import "./QueueMonitorPage.css";

const STATUS_OPTIONS = [
  { value: "", label: "All queue items" },
  { value: "pending", label: "Pending" },
  { value: "scheduled", label: "Scheduled" },
  { value: "processing", label: "Processing" },
  { value: "sent", label: "Sent" },
  { value: "failed", label: "Failed" },
  { value: "cancelled", label: "Cancelled" },
];

const STATUS_META = {
  pending: {
    label: "Pending",
    className: "queue-status-pending",
    icon: Clock3,
  },
  scheduled: {
    label: "Scheduled",
    className: "queue-status-scheduled",
    icon: Clock3,
  },
  processing: {
    label: "Processing",
    className: "queue-status-processing",
    icon: PlayCircle,
  },
  sent: {
    label: "Sent",
    className: "queue-status-sent",
    icon: CheckCircle2,
  },
  failed: {
    label: "Failed",
    className: "queue-status-failed",
    icon: AlertCircle,
  },
  cancelled: {
    label: "Cancelled",
    className: "queue-status-cancelled",
    icon: XCircle,
  },
};

function normalizeItems(data) {
  if (Array.isArray(data)) {
    return data;
  }

  if (data && Array.isArray(data.items)) {
    return data.items;
  }

  return [];
}

function formatDate(value) {
  if (!value) {
    return "—";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "—";
  }

  return date.toLocaleString([], {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function formatRelativeTime(value) {
  if (!value) {
    return "—";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "—";
  }

  const diff = date.getTime() - Date.now();
  const minutes = Math.round(diff / 60000);

  if (Math.abs(minutes) < 1) {
    return "Now";
  }

  if (minutes > 0) {
    if (minutes < 60) {
      return `in ${minutes} min`;
    }

    const hours = Math.round(minutes / 60);

    if (hours < 24) {
      return `in ${hours} hr`;
    }

    return `in ${Math.round(hours / 24)} days`;
  }

  const elapsed = Math.abs(minutes);

  if (elapsed < 60) {
    return `${elapsed} min ago`;
  }

  const hours = Math.round(elapsed / 60);

  if (hours < 24) {
    return `${hours} hr ago`;
  }

  return `${Math.round(hours / 24)} days ago`;
}

function getStatusMeta(status) {
  return (
    STATUS_META[status] || {
      label: status || "Unknown",
      className: "queue-status-default",
      icon: Mail,
    }
  );
}

function QueueStatusBadge({ status }) {
  const meta = getStatusMeta(status);
  const Icon = meta.icon;

  return (
    <span className={`queue-status ${meta.className}`}>
      <Icon size={14} />
      {meta.label}
    </span>
  );
}

function QueueMonitorPage() {
  const [items, setItems] = useState([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedItem, setSelectedItem] = useState(null);
  const [actionId, setActionId] = useState(null);
  const [processing, setProcessing] = useState(false);
  // Days filter — 3 = last 3 days (default), 0 = all time
  const [daysFilter, setDaysFilter] = useState(3);

  const handleProcessQueue = async () => {
    setProcessing(true);
    try {
      const result = await queueService.processQueue(20);
      const { sent = 0, failed = 0, processed = 0 } = result;

      if (processed === 0) {
        toast.info("No emails are due to send right now.");
      } else if (sent > 0) {
        toast.success(
          `${sent} email${sent !== 1 ? "s" : ""} sent.${
            failed > 0 ? ` ${failed} failed.` : ""
          }`,
        );
      } else {
        toast.error(`All ${failed} emails failed to send. Check account status.`);
      }

      // Refresh queue after processing
      await loadQueue(true);
    } catch (err) {
      toast.error(
        err?.response?.data?.detail || "Queue processing failed.",
      );
    } finally {
      setProcessing(false);
    }
  };

  const loadQueue = useCallback(
    async (showRefresh = false) => {
      try {
        if (showRefresh) {
          setRefreshing(true);
        } else {
          setLoading(true);
        }

        const data = await queueService.getQueue(statusFilter, daysFilter);
        setItems(normalizeItems(data));
      } catch (error) {
        toast.error(
          error.response?.data?.detail ||
            "Unable to load the email queue.",
        );
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [statusFilter, daysFilter],
  );

  useEffect(() => {
    loadQueue();
  }, [loadQueue]);

  const filteredItems = useMemo(() => {
    const query = search.trim().toLowerCase();

    if (!query) {
      return items;
    }

    return items.filter((item) => {
      return [
        item.recipient_email,
        item.subject,
        item.queue_type,
        item.status,
        item.last_error,
      ]
        .filter(Boolean)
        .some((value) =>
          String(value).toLowerCase().includes(query),
        );
    });
  }, [items, search]);

  const stats = useMemo(() => {
    return {
      total: items.length,
      pending: items.filter((item) => item.status === "pending")
        .length,
      scheduled: items.filter(
        (item) => item.status === "scheduled",
      ).length,
      processing: items.filter(
        (item) => item.status === "processing",
      ).length,
      sent: items.filter((item) => item.status === "sent").length,
      failed: items.filter((item) => item.status === "failed").length,
      cancelled: items.filter(
        (item) => item.status === "cancelled",
      ).length,
    };
  }, [items]);

  async function handleCancel(item) {
    if (!item?.id) {
      return;
    }

    try {
      setActionId(item.id);

      const updated = await queueService.cancel(item.id);

      setItems((current) =>
        current.map((queueItem) =>
          queueItem.id === updated.id ? updated : queueItem,
        ),
      );

      setSelectedItem(updated);
      toast.success("Queue item cancelled.");
    } catch (error) {
      toast.error(
        error.response?.data?.detail ||
          "Unable to cancel this queue item.",
      );
    } finally {
      setActionId(null);
    }
  }

  async function handleRetry(item) {
    if (!item?.id) {
      return;
    }

    try {
      setActionId(item.id);

      const updated = await queueService.retry(item.id);

      setItems((current) =>
        current.map((queueItem) =>
          queueItem.id === updated.id ? updated : queueItem,
        ),
      );

      setSelectedItem(updated);
      toast.success("Queue item moved back to pending.");
    } catch (error) {
      toast.error(
        error.response?.data?.detail ||
          "Unable to retry this queue item.",
      );
    } finally {
      setActionId(null);
    }
  }

  async function handleStatusChange(item, status) {
    if (!item?.id || !status) {
      return;
    }

    try {
      setActionId(item.id);

      const updated = await queueService.updateStatus(
        item.id,
        status,
      );

      setItems((current) =>
        current.map((queueItem) =>
          queueItem.id === updated.id ? updated : queueItem,
        ),
      );

      setSelectedItem(updated);
      toast.success(`Queue status changed to ${status}.`);
    } catch (error) {
      toast.error(
        error.response?.data?.detail ||
          "Unable to update queue status.",
      );
    } finally {
      setActionId(null);
    }
  }

  return (
    <section className="queue-page">
      <div className="queue-page-header">
        <div>
          <span className="queue-eyebrow">EMAIL OPERATIONS</span>

          <h1>Email Queue</h1>

          <p>
            Monitor scheduled outreach, delivery processing,
            retries, and completed messages from one place.
          </p>
        </div>

        <div style={{ display: "flex", gap: 10, flexShrink: 0 }}>
          <button
            type="button"
            className="queue-refresh-button"
            onClick={() => loadQueue(true)}
            disabled={refreshing}
          >
            <RefreshCw
              size={17}
              className={refreshing ? "queue-spin" : ""}
            />
            {refreshing ? "Refreshing..." : "Refresh queue"}
          </button>

          <button
            type="button"
            className="queue-process-button"
            onClick={handleProcessQueue}
            disabled={processing || refreshing}
          >
            {processing ? (
              <>
                <RefreshCw size={17} className="queue-spin" />
                Sending...
              </>
            ) : (
              <>
                <Send size={17} />
                Send due emails
              </>
            )}
          </button>
        </div>
      </div>

      <div className="queue-stats-grid">
        <div className="queue-stat-card">
          <div className="queue-stat-icon queue-stat-icon-total">
            <Mail size={19} />
          </div>

          <div>
            <span>Total</span>
            <strong>{stats.total}</strong>
          </div>
        </div>

        <div className="queue-stat-card">
          <div className="queue-stat-icon queue-stat-icon-pending">
            <Clock3 size={19} />
          </div>

          <div>
            <span>Pending</span>
            <strong>{stats.pending}</strong>
          </div>
        </div>

        <div className="queue-stat-card">
          <div className="queue-stat-icon queue-stat-icon-scheduled">
            <Clock3 size={19} />
          </div>

          <div>
            <span>Scheduled</span>
            <strong>{stats.scheduled}</strong>
          </div>
        </div>

        <div className="queue-stat-card">
          <div className="queue-stat-icon queue-stat-icon-processing">
            <Send size={19} />
          </div>

          <div>
            <span>Processing</span>
            <strong>{stats.processing}</strong>
          </div>
        </div>

        <div className="queue-stat-card">
          <div className="queue-stat-icon queue-stat-icon-sent">
            <CheckCircle2 size={19} />
          </div>

          <div>
            <span>Sent</span>
            <strong>{stats.sent}</strong>
          </div>
        </div>

        <div className="queue-stat-card">
          <div className="queue-stat-icon queue-stat-icon-failed">
            <AlertCircle size={19} />
          </div>

          <div>
            <span>Failed</span>
            <strong>{stats.failed}</strong>
          </div>
        </div>
      </div>

      <div className="queue-panel">
        <div className="queue-toolbar">
          <div className="queue-search">
            <Search size={17} />

            <input
              type="text"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search recipient, subject, status..."
            />
          </div>

          <select
            className="queue-filter"
            value={statusFilter}
            onChange={(event) =>
              setStatusFilter(event.target.value)
            }
          >
            {STATUS_OPTIONS.map((option) => (
              <option
                key={option.value || "all"}
                value={option.value}
              >
                {option.label}
              </option>
            ))}
          </select>

          {/* Days range toggle */}
          <div className="queue-days-toggle">
            <button
              type="button"
              className={`queue-days-btn ${daysFilter === 3 ? "active" : ""}`}
              onClick={() => setDaysFilter(3)}
            >
              Last 3 days
            </button>
            <button
              type="button"
              className={`queue-days-btn ${daysFilter === 7 ? "active" : ""}`}
              onClick={() => setDaysFilter(7)}
            >
              7 days
            </button>
            <button
              type="button"
              className={`queue-days-btn ${daysFilter === 0 ? "active" : ""}`}
              onClick={() => setDaysFilter(0)}
            >
              All time
            </button>
          </div>
        </div>

        <div className="queue-summary-row">
          <div>
            <strong>{filteredItems.length}</strong>
            <span>
              {search || statusFilter
                ? " matching queue items"
                : ` queue items${daysFilter > 0 ? ` · last ${daysFilter} days` : ""}`}
            </span>
          </div>

          <span className="queue-order-note">
            Latest emails shown first.
          </span>
        </div>

        {loading ? (
          <div className="queue-state">
            <RefreshCw size={22} className="queue-spin" />
            <strong>Loading queue...</strong>
            <span>Fetching your current email workload.</span>
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="queue-state">
            <div className="queue-empty-icon">
              <Mail size={25} />
            </div>

            <strong>No queue items found</strong>

            <span>
              Approved email drafts will appear here once they
              are added to the sending queue.
            </span>
          </div>
        ) : (
          <div className="queue-table-wrap">
            <table className="queue-table">
              <thead>
                <tr>
                  <th>Recipient</th>
                  <th>Subject</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th>Scheduled</th>
                  <th>Attempts</th>
                  <th>Actions</th>
                </tr>
              </thead>

              <tbody>
                {filteredItems.map((item) => {
                  const busy = actionId === item.id;

                  return (
                    <tr key={item.id}>
                      <td>
                        <button
                          type="button"
                          className="queue-recipient"
                          onClick={() => setSelectedItem(item)}
                        >
                          <span className="queue-recipient-icon">
                            <Mail size={15} />
                          </span>

                          <span>
                            <strong>
                              {item.recipient_email}
                            </strong>

                            <small>
                              {item.id?.slice(0, 8) || "—"}
                            </small>
                          </span>
                        </button>
                      </td>

                      <td>
                        <button
                          type="button"
                          className="queue-subject"
                          onClick={() => setSelectedItem(item)}
                        >
                          {item.subject || "No subject"}
                        </button>
                      </td>

                      <td>
                        <span className="queue-type">
                          {item.queue_type || "initial"}
                        </span>
                      </td>

                      <td>
                        <QueueStatusBadge status={item.status} />
                      </td>

                      <td>
                        <div className="queue-time">
                          <strong>
                            {formatRelativeTime(
                              item.scheduled_at,
                            )}
                          </strong>

                          <small>
                            {formatDate(item.scheduled_at)}
                          </small>
                        </div>
                      </td>

                      <td>
                        <span className="queue-attempts">
                          {item.attempt_count || 0}
                          <span>
                            / {item.max_attempts || 0}
                          </span>
                        </span>
                      </td>

                      <td>
                        <div className="queue-actions">
                          <button
                            type="button"
                            className="queue-action-button queue-action-view"
                            onClick={() =>
                              setSelectedItem(item)
                            }
                            title="View details"
                          >
                            View
                          </button>

                          {item.status === "failed" && (
                            <button
                              type="button"
                              className="queue-action-button queue-action-retry"
                              onClick={() =>
                                handleRetry(item)
                              }
                              disabled={busy}
                              title="Retry"
                            >
                              <RotateCcw size={14} />
                            </button>
                          )}

                          {[
                            "pending",
                            "scheduled",
                            "processing",
                          ].includes(item.status) && (
                            <button
                              type="button"
                              className="queue-action-button queue-action-cancel"
                              onClick={() =>
                                handleCancel(item)
                              }
                              disabled={busy}
                              title="Cancel"
                            >
                              <X size={14} />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {selectedItem && (
        <div
          className="queue-modal-backdrop"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              setSelectedItem(null);
            }
          }}
        >
          <div className="queue-modal">
            <div className="queue-modal-header">
              <div>
                <span className="queue-eyebrow">
                  QUEUE ITEM
                </span>

                <h2>Message details</h2>
              </div>

              <button
                type="button"
                className="queue-modal-close"
                onClick={() => setSelectedItem(null)}
                aria-label="Close details"
              >
                <X size={19} />
              </button>
            </div>

            <div className="queue-modal-status">
              <QueueStatusBadge
                status={selectedItem.status}
              />

              <span>
                {formatDate(selectedItem.updated_at)}
              </span>
            </div>

            <div className="queue-detail-grid">
              <div className="queue-detail-card">
                <span>Recipient</span>
                <strong>
                  {selectedItem.recipient_email || "—"}
                </strong>
              </div>

              <div className="queue-detail-card">
                <span>Queue type</span>
                <strong>
                  {selectedItem.queue_type || "—"}
                </strong>
              </div>

              <div className="queue-detail-card">
                <span>Priority</span>
                <strong>
                  {selectedItem.priority ?? "—"}
                </strong>
              </div>

              <div className="queue-detail-card">
                <span>Attempts</span>
                <strong>
                  {selectedItem.attempt_count || 0} /{" "}
                  {selectedItem.max_attempts || 0}
                </strong>
              </div>

              <div className="queue-detail-card">
                <span>Scheduled at</span>
                <strong>
                  {formatDate(selectedItem.scheduled_at)}
                </strong>
              </div>

              <div className="queue-detail-card">
                <span>Last attempt</span>
                <strong>
                  {formatDate(selectedItem.last_attempt_at)}
                </strong>
              </div>
            </div>

            <div className="queue-detail-section">
              <span>Subject</span>

              <div className="queue-message-box">
                {selectedItem.subject || "No subject"}
              </div>
            </div>

            <div className="queue-detail-section">
              <span>Message</span>

              <div className="queue-message-box queue-message-body">
                {selectedItem.body_text || "No message body."}
              </div>
            </div>

            {selectedItem.last_error && (
              <div className="queue-error-box">
                <AlertCircle size={18} />

                <div>
                  <strong>Last error</strong>
                  <p>{selectedItem.last_error}</p>

                  {selectedItem.next_retry_at && (
                    <small>
                      Next retry:{" "}
                      {formatDate(selectedItem.next_retry_at)}
                    </small>
                  )}
                </div>
              </div>
            )}

            <div className="queue-modal-actions">
              {selectedItem.status === "failed" && (
                <button
                  type="button"
                  className="queue-primary-action"
                  onClick={() => handleRetry(selectedItem)}
                  disabled={actionId === selectedItem.id}
                >
                  <RotateCcw size={16} />
                  Retry
                </button>
              )}

              {[
                "pending",
                "scheduled",
                "processing",
              ].includes(selectedItem.status) && (
                <button
                  type="button"
                  className="queue-secondary-action"
                  onClick={() => handleCancel(selectedItem)}
                  disabled={actionId === selectedItem.id}
                >
                  <PauseCircle size={16} />
                  Cancel queue item
                </button>
              )}

              <button
                type="button"
                className="queue-secondary-action"
                onClick={() => setSelectedItem(null)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

export default QueueMonitorPage;