import {
  AlertCircle,
  CheckCircle2,
  ChevronRight,
  Clock3,
  ExternalLink,
  Mail,
  MousePointerClick,
  RefreshCw,
  Search,
  ShieldAlert,
  UserMinus,
  X,
  XCircle,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "react-toastify";

import deliveryService from "../../services/deliveryService";
import "./DeliveryMonitorPage.css";

const STATUS_OPTIONS = [
  { value: "", label: "All statuses" },
  { value: "queued", label: "Queued" },
  { value: "sending", label: "Sending" },
  { value: "sent", label: "Sent" },
  { value: "delivered", label: "Delivered" },
  { value: "opened", label: "Opened" },
  { value: "clicked", label: "Clicked" },
  { value: "bounced", label: "Bounced" },
  { value: "complained", label: "Complained" },
  { value: "unsubscribed", label: "Unsubscribed" },
  { value: "failed", label: "Failed" },
];

const STATUS_META = {
  queued: {
    label: "Queued",
    className: "delivery-status-queued",
    icon: Clock3,
  },
  sending: {
    label: "Sending",
    className: "delivery-status-sending",
    icon: RefreshCw,
  },
  sent: {
    label: "Sent",
    className: "delivery-status-sent",
    icon: CheckCircle2,
  },
  delivered: {
    label: "Delivered",
    className: "delivery-status-delivered",
    icon: CheckCircle2,
  },
  opened: {
    label: "Opened",
    className: "delivery-status-opened",
    icon: Mail,
  },
  clicked: {
    label: "Clicked",
    className: "delivery-status-clicked",
    icon: MousePointerClick,
  },
  bounced: {
    label: "Bounced",
    className: "delivery-status-bounced",
    icon: XCircle,
  },
  complained: {
    label: "Complaint",
    className: "delivery-status-complained",
    icon: ShieldAlert,
  },
  unsubscribed: {
    label: "Unsubscribed",
    className: "delivery-status-unsubscribed",
    icon: UserMinus,
  },
  failed: {
    label: "Failed",
    className: "delivery-status-failed",
    icon: AlertCircle,
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

function getStatusMeta(status) {
  return (
    STATUS_META[status] || {
      label: status || "Unknown",
      className: "delivery-status-default",
      icon: Mail,
    }
  );
}

function StatusBadge({ status }) {
  const meta = getStatusMeta(status);
  const Icon = meta.icon;

  return (
    <span className={`delivery-status ${meta.className}`}>
      <Icon size={13} />
      {meta.label}
    </span>
  );
}

function DeliveryMonitorPage() {
  const [items, setItems] = useState([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedDelivery, setSelectedDelivery] = useState(null);

  const loadDeliveries = useCallback(
    async (showRefresh = false) => {
      try {
        if (showRefresh) {
          setRefreshing(true);
        } else {
          setLoading(true);
        }

        const data = await deliveryService.getDeliveries(
          statusFilter
            ? { delivery_status: statusFilter }
            : {},
        );

        setItems(normalizeItems(data));
      } catch (error) {
        toast.error(
          error.response?.data?.detail ||
            "Unable to load delivery records.",
        );
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [statusFilter],
  );

  useEffect(() => {
    loadDeliveries();
  }, [loadDeliveries]);

  const filteredItems = useMemo(() => {
    const query = search.trim().toLowerCase();

    if (!query) {
      return items;
    }

    return items.filter((item) =>
      [
        item.recipient_email,
        item.sender_email,
        item.subject,
        item.provider,
        item.status,
        item.bounce_type,
        item.bounce_reason,
        item.failure_reason,
        item.complaint_type,
      ]
        .filter(Boolean)
        .some((value) =>
          String(value).toLowerCase().includes(query),
        ),
    );
  }, [items, search]);

  const stats = useMemo(() => {
    return {
      total: items.length,
      sent: items.filter(
        (item) =>
          ["sent", "delivered", "opened", "clicked"].includes(
            item.status,
          ),
      ).length,
      delivered: items.filter(
        (item) =>
          ["delivered", "opened", "clicked"].includes(
            item.status,
          ),
      ).length,
      opened: items.filter(
        (item) =>
          ["opened", "clicked"].includes(item.status),
      ).length,
      clicked: items.filter(
        (item) => item.status === "clicked",
      ).length,
      bounced: items.filter(
        (item) => item.status === "bounced",
      ).length,
      failed: items.filter(
        (item) => item.status === "failed",
      ).length,
      complaints: items.filter(
        (item) => item.status === "complained",
      ).length,
      unsubscribed: items.filter(
        (item) => item.status === "unsubscribed",
      ).length,
    };
  }, [items]);

  const deliveryRate = useMemo(() => {
    if (!stats.sent) {
      return 0;
    }

    return Math.round(
      (stats.delivered / stats.sent) * 100,
    );
  }, [stats.delivered, stats.sent]);

  const openRate = useMemo(() => {
    if (!stats.delivered) {
      return 0;
    }

    return Math.round(
      (stats.opened / stats.delivered) * 100,
    );
  }, [stats.delivered, stats.opened]);

  const clickRate = useMemo(() => {
    if (!stats.delivered) {
      return 0;
    }

    return Math.round(
      (stats.clicked / stats.delivered) * 100,
    );
  }, [stats.delivered, stats.clicked]);

  return (
    <section className="delivery-page">
      <div className="delivery-page-header">
        <div>
          <span className="delivery-eyebrow">
            DELIVERY OPERATIONS
          </span>

          <h1>Email Delivery</h1>

          <p>
            Track message delivery events, engagement signals,
            failures, bounces, complaints, and unsubscribe
            activity.
          </p>
        </div>

        <button
          type="button"
          className="delivery-refresh-button"
          onClick={() => loadDeliveries(true)}
          disabled={refreshing}
        >
          <RefreshCw
            size={17}
            className={refreshing ? "delivery-spin" : ""}
          />

          {refreshing ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      <div className="delivery-stats-grid">
        <div className="delivery-stat-card">
          <div className="delivery-stat-icon delivery-stat-total">
            <Mail size={18} />
          </div>

          <div>
            <span>Total</span>
            <strong>{stats.total}</strong>
          </div>
        </div>

        <div className="delivery-stat-card">
          <div className="delivery-stat-icon delivery-stat-delivered">
            <CheckCircle2 size={18} />
          </div>

          <div>
            <span>Delivered</span>
            <strong>{stats.delivered}</strong>
            <small>{deliveryRate}% of sent</small>
          </div>
        </div>

        <div className="delivery-stat-card">
          <div className="delivery-stat-icon delivery-stat-opened">
            <Mail size={18} />
          </div>

          <div>
            <span>Opened</span>
            <strong>{stats.opened}</strong>
            <small>{openRate}% of delivered</small>
          </div>
        </div>

        <div className="delivery-stat-card">
          <div className="delivery-stat-icon delivery-stat-clicked">
            <MousePointerClick size={18} />
          </div>

          <div>
            <span>Clicked</span>
            <strong>{stats.clicked}</strong>
            <small>{clickRate}% of delivered</small>
          </div>
        </div>

        <div className="delivery-stat-card">
          <div className="delivery-stat-icon delivery-stat-bounced">
            <XCircle size={18} />
          </div>

          <div>
            <span>Bounced</span>
            <strong>{stats.bounced}</strong>
          </div>
        </div>

        <div className="delivery-stat-card">
          <div className="delivery-stat-icon delivery-stat-failed">
            <AlertCircle size={18} />
          </div>

          <div>
            <span>Failed</span>
            <strong>{stats.failed}</strong>
          </div>
        </div>
      </div>

      <div className="delivery-risk-row">
        <div className="delivery-risk-card">
          <ShieldAlert size={17} />

          <div>
            <strong>{stats.complaints}</strong>
            <span>complaints</span>
          </div>
        </div>

        <div className="delivery-risk-card">
          <UserMinus size={17} />

          <div>
            <strong>{stats.unsubscribed}</strong>
            <span>unsubscribes</span>
          </div>
        </div>
      </div>

      <div className="delivery-panel">
        <div className="delivery-toolbar">
          <div className="delivery-search">
            <Search size={17} />

            <input
              type="text"
              value={search}
              onChange={(event) =>
                setSearch(event.target.value)
              }
              placeholder="Search recipient, sender, subject..."
            />
          </div>

          <select
            className="delivery-filter"
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
        </div>

        <div className="delivery-summary">
          <div>
            <strong>{filteredItems.length}</strong>
            <span>
              {search || statusFilter
                ? " matching records"
                : " delivery records"}
            </span>
          </div>

          <span>
            Records are ordered by most recent activity.
          </span>
        </div>

        {loading ? (
          <div className="delivery-state">
            <RefreshCw
              size={22}
              className="delivery-spin"
            />

            <strong>Loading delivery records...</strong>

            <span>
              Fetching the latest delivery activity.
            </span>
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="delivery-state">
            <div className="delivery-empty-icon">
              <Mail size={24} />
            </div>

            <strong>No delivery records found</strong>

            <span>
              Delivery records will appear here after queue
              items are converted into delivery records.
            </span>
          </div>
        ) : (
          <div className="delivery-table-wrap">
            <table className="delivery-table">
              <thead>
                <tr>
                  <th>Recipient</th>
                  <th>Subject</th>
                  <th>Provider</th>
                  <th>Status</th>
                  <th>Sent</th>
                  <th>Activity</th>
                  <th></th>
                </tr>
              </thead>

              <tbody>
                {filteredItems.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <button
                        type="button"
                        className="delivery-recipient"
                        onClick={() =>
                          setSelectedDelivery(item)
                        }
                      >
                        <span className="delivery-recipient-icon">
                          <Mail size={14} />
                        </span>

                        <span>
                          <strong>
                            {item.recipient_email}
                          </strong>

                          <small>
                            {item.sender_email ||
                              "Sender unavailable"}
                          </small>
                        </span>
                      </button>
                    </td>

                    <td>
                      <button
                        type="button"
                        className="delivery-subject"
                        onClick={() =>
                          setSelectedDelivery(item)
                        }
                      >
                        {item.subject || "No subject"}
                      </button>
                    </td>

                    <td>
                      <span className="delivery-provider">
                        {item.provider || "—"}
                      </span>
                    </td>

                    <td>
                      <StatusBadge status={item.status} />
                    </td>

                    <td>
                      <div className="delivery-time">
                        {formatDate(item.sent_at)}
                      </div>
                    </td>

                    <td>
                      <div className="delivery-activity">
                        <span
                          className={
                            item.delivered_at
                              ? "active"
                              : ""
                          }
                          title="Delivered"
                        >
                          <CheckCircle2 size={13} />
                        </span>

                        <ChevronRight size={11} />

                        <span
                          className={
                            item.opened_at ? "active" : ""
                          }
                          title="Opened"
                        >
                          <Mail size={13} />
                        </span>

                        <ChevronRight size={11} />

                        <span
                          className={
                            item.clicked_at ? "active" : ""
                          }
                          title="Clicked"
                        >
                          <MousePointerClick size={13} />
                        </span>
                      </div>
                    </td>

                    <td>
                      <button
                        type="button"
                        className="delivery-view-button"
                        onClick={() =>
                          setSelectedDelivery(item)
                        }
                      >
                        View
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {selectedDelivery && (
        <div
          className="delivery-modal-backdrop"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              setSelectedDelivery(null);
            }
          }}
        >
          <div className="delivery-modal">
            <div className="delivery-modal-header">
              <div>
                <span className="delivery-eyebrow">
                  DELIVERY RECORD
                </span>

                <h2>Message activity</h2>
              </div>

              <button
                type="button"
                className="delivery-modal-close"
                onClick={() =>
                  setSelectedDelivery(null)
                }
                aria-label="Close"
              >
                <X size={19} />
              </button>
            </div>

            <div className="delivery-modal-status">
              <StatusBadge
                status={selectedDelivery.status}
              />

              <span>
                Updated{" "}
                {formatDate(selectedDelivery.updated_at)}
              </span>
            </div>

            <div className="delivery-detail-grid">
              <div className="delivery-detail-card">
                <span>Recipient</span>
                <strong>
                  {selectedDelivery.recipient_email}
                </strong>
              </div>

              <div className="delivery-detail-card">
                <span>Sender</span>
                <strong>
                  {selectedDelivery.sender_email || "—"}
                </strong>
              </div>

              <div className="delivery-detail-card">
                <span>Provider</span>
                <strong>
                  {selectedDelivery.provider || "—"}
                </strong>
              </div>

              <div className="delivery-detail-card">
                <span>Provider message ID</span>
                <strong>
                  {selectedDelivery.provider_message_id ||
                    "—"}
                </strong>
              </div>
            </div>

            <div className="delivery-timeline">
              <div className="delivery-timeline-title">
                <span>Activity timeline</span>
              </div>

              {[
                ["Created", selectedDelivery.created_at],
                ["Sent", selectedDelivery.sent_at],
                ["Delivered", selectedDelivery.delivered_at],
                ["Opened", selectedDelivery.opened_at],
                ["Clicked", selectedDelivery.clicked_at],
                ["Bounced", selectedDelivery.bounced_at],
                [
                  "Complaint",
                  selectedDelivery.complained_at,
                ],
                [
                  "Unsubscribed",
                  selectedDelivery.unsubscribed_at,
                ],
                ["Failed", selectedDelivery.failed_at],
              ]
                .filter(([, value]) => value)
                .map(([label, value]) => (
                  <div
                    className="delivery-timeline-item"
                    key={label}
                  >
                    <div className="delivery-timeline-dot" />

                    <div>
                      <strong>{label}</strong>
                      <span>{formatDate(value)}</span>
                    </div>
                  </div>
                ))}
            </div>

            <div className="delivery-detail-section">
              <span>Subject</span>

              <div className="delivery-message-box">
                {selectedDelivery.subject ||
                  "No subject"}
              </div>
            </div>

            {selectedDelivery.body_text && (
              <div className="delivery-detail-section">
                <span>Message</span>

                <div className="delivery-message-box delivery-body">
                  {selectedDelivery.body_text}
                </div>
              </div>
            )}

            {(selectedDelivery.bounce_reason ||
              selectedDelivery.failure_reason ||
              selectedDelivery.complaint_type) && (
              <div className="delivery-warning-box">
                <AlertCircle size={18} />

                <div>
                  <strong>Delivery issue</strong>

                  {selectedDelivery.bounce_reason && (
                    <p>
                      Bounce:{" "}
                      {selectedDelivery.bounce_reason}
                    </p>
                  )}

                  {selectedDelivery.bounce_type && (
                    <p>
                      Bounce type:{" "}
                      {selectedDelivery.bounce_type}
                    </p>
                  )}

                  {selectedDelivery.failure_reason && (
                    <p>
                      Failure:{" "}
                      {selectedDelivery.failure_reason}
                    </p>
                  )}

                  {selectedDelivery.complaint_type && (
                    <p>
                      Complaint:{" "}
                      {selectedDelivery.complaint_type}
                    </p>
                  )}
                </div>
              </div>
            )}

            <div className="delivery-modal-footer">
              <span>
                Queue ID:{" "}
                {selectedDelivery.queue_id || "—"}
              </span>

              <button
                type="button"
                className="delivery-close-button"
                onClick={() =>
                  setSelectedDelivery(null)
                }
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

export default DeliveryMonitorPage;