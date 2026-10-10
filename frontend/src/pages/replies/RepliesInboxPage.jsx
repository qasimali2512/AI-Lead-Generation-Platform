import {
  Archive,
  ArrowDownLeft,
  ChevronLeft,
  ChevronRight,
  Clock3,
  Mail,
  MessageSquare,
  RefreshCw,
  Search,
  UserRound,
  X,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { toast } from "react-toastify";

import replyService from "../../services/replyService";
import "./RepliesInboxPage.css";

function normalizeThreads(data) {
  if (Array.isArray(data)) {
    return data;
  }

  if (data && Array.isArray(data.items)) {
    return data.items;
  }

  if (data && Array.isArray(data.threads)) {
    return data.threads;
  }

  return [];
}

function normalizeMessages(data) {
  if (Array.isArray(data)) {
    return data;
  }

  if (data && Array.isArray(data.items)) {
    return data.items;
  }

  if (data && Array.isArray(data.messages)) {
    return data.messages;
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

  return date.toLocaleDateString(undefined, {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function formatDateTime(value) {
  if (!value) {
    return "—";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "—";
  }

  return date.toLocaleString(undefined, {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatRelativeTime(value) {
  if (!value) {
    return "No activity";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "No activity";
  }

  const difference = Date.now() - date.getTime();
  const minutes = Math.floor(difference / 60000);

  if (minutes < 1) {
    return "Just now";
  }

  if (minutes < 60) {
    return `${minutes}m ago`;
  }

  const hours = Math.floor(minutes / 60);

  if (hours < 24) {
    return `${hours}h ago`;
  }

  const days = Math.floor(hours / 24);

  if (days < 7) {
    return `${days}d ago`;
  }

  return formatDate(value);
}

function getThreadStatus(thread) {
  return String(thread?.status || "replied").toLowerCase();
}

function getThreadSubject(thread) {
  return thread?.subject || "No subject";
}

function getMessagePreview(message) {
  const body = message?.body_text || "";

  if (!body) {
    return "No message preview available.";
  }

  return body.replace(/\s+/g, " ").trim();
}

function getMessageSender(message) {
  return message?.from_email || "Unknown sender";
}

function RepliesInboxPage() {
  const [threads, setThreads] = useState([]);
  const [selectedThread, setSelectedThread] = useState(null);
  const [messages, setMessages] = useState([]);

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const [loadingThreads, setLoadingThreads] = useState(true);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const [error, setError] = useState("");

  const [page, setPage] = useState(0);
  const pageSize = 50;

  async function loadThreads(showRefreshState = false) {
    try {
      if (showRefreshState) {
        setRefreshing(true);
      } else {
        setLoadingThreads(true);
      }

      setError("");

      const data = await replyService.getThreads({
        status: statusFilter || undefined,
        skip: page * pageSize,
        limit: pageSize,
      });

      const normalized = normalizeThreads(data);

      setThreads(normalized);

      if (
        selectedThread &&
        !normalized.some(
          (thread) => thread.id === selectedThread.id,
        )
      ) {
        setSelectedThread(null);
        setMessages([]);
      }
    } catch (requestError) {
      console.error(requestError);

      setError(
        requestError?.response?.data?.detail ||
          "Unable to load reply threads.",
      );
    } finally {
      setLoadingThreads(false);
      setRefreshing(false);
    }
  }

  async function openThread(thread) {
    try {
      setSelectedThread(thread);
      setMessages([]);
      setLoadingMessages(true);

      const data = await replyService.getThreadMessages(
        thread.id,
      );

      setMessages(normalizeMessages(data));
    } catch (requestError) {
      console.error(requestError);

      toast.error(
        requestError?.response?.data?.detail ||
          "Unable to load conversation.",
      );
    } finally {
      setLoadingMessages(false);
    }
  }

  useEffect(() => {
    loadThreads();
  }, [statusFilter, page]);

  const filteredThreads = useMemo(() => {
    const query = search.trim().toLowerCase();

    if (!query) {
      return threads;
    }

    return threads.filter((thread) => {
      const subject = String(
        thread?.subject || "",
      ).toLowerCase();

      const provider = String(
        thread?.provider || "",
      ).toLowerCase();

      const status = String(
        thread?.status || "",
      ).toLowerCase();

      const leadId = String(
        thread?.lead_id || "",
      ).toLowerCase();

      return (
        subject.includes(query) ||
        provider.includes(query) ||
        status.includes(query) ||
        leadId.includes(query)
      );
    });
  }, [threads, search]);

  const stats = useMemo(() => {
    const total = threads.length;

    const replied = threads.filter(
      (thread) => getThreadStatus(thread) === "replied",
    ).length;

    const outbound = threads.filter(
      (thread) =>
        String(thread?.last_direction || "").toLowerCase() ===
        "outbound",
    ).length;

    const inbound = threads.filter(
      (thread) =>
        String(thread?.last_direction || "").toLowerCase() ===
        "inbound",
    ).length;

    return {
      total,
      replied,
      inbound,
      outbound,
    };
  }, [threads]);

  function handlePreviousPage() {
    if (page === 0) {
      return;
    }

    setPage((current) => current - 1);
  }

  function handleNextPage() {
    if (threads.length < pageSize) {
      return;
    }

    setPage((current) => current + 1);
  }

  function clearSearch() {
    setSearch("");
  }

  return (
    <section className="replies-page">
      <div className="replies-page-header">
        <div>
          <span className="replies-eyebrow">
            Communication
          </span>

          <h1>Replies Inbox</h1>

          <p>
            Review conversations from leads and keep follow-up
            activity organized in one place.
          </p>
        </div>

        <button
          type="button"
          className={`replies-refresh-button ${
            refreshing ? "is-refreshing" : ""
          }`}
          onClick={() => loadThreads(true)}
          disabled={refreshing}
        >
          <RefreshCw size={17} />
          {refreshing ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      <div className="replies-stats">
        <div className="replies-stat-card">
          <div className="replies-stat-icon">
            <MessageSquare size={18} />
          </div>

          <div>
            <span>Total Threads</span>
            <strong>{stats.total}</strong>
          </div>
        </div>

        <div className="replies-stat-card">
          <div className="replies-stat-icon replies-stat-icon-green">
            <ArrowDownLeft size={18} />
          </div>

          <div>
            <span>Inbound</span>
            <strong>{stats.inbound}</strong>
          </div>
        </div>

        <div className="replies-stat-card">
          <div className="replies-stat-icon replies-stat-icon-blue">
            <Mail size={18} />
          </div>

          <div>
            <span>Outbound</span>
            <strong>{stats.outbound}</strong>
          </div>
        </div>

        <div className="replies-stat-card">
          <div className="replies-stat-icon replies-stat-icon-maroon">
            <Clock3 size={18} />
          </div>

          <div>
            <span>Replied</span>
            <strong>{stats.replied}</strong>
          </div>
        </div>
      </div>

      <div className="replies-toolbar">
        <div className="replies-search">
          <Search size={18} />

          <input
            type="text"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search subject, provider or lead..."
          />

          {search && (
            <button
              type="button"
              onClick={clearSearch}
              aria-label="Clear search"
            >
              <X size={16} />
            </button>
          )}
        </div>

        <div className="replies-filter">
          <label htmlFor="reply-status">
            Status
          </label>

          <select
            id="reply-status"
            value={statusFilter}
            onChange={(event) => {
              setPage(0);
              setStatusFilter(event.target.value);
            }}
          >
            <option value="">All statuses</option>
            <option value="replied">Replied</option>
          </select>
        </div>
      </div>

      {error && (
        <div className="replies-error">
          <div>
            <strong>Unable to load replies</strong>
            <span>{error}</span>
          </div>

          <button
            type="button"
            onClick={() => loadThreads()}
          >
            Try again
          </button>
        </div>
      )}

      <div className="replies-workspace">
        <div className="replies-thread-panel">
          <div className="replies-panel-header">
            <div>
              <h2>Conversations</h2>
              <span>
                {filteredThreads.length} visible thread
                {filteredThreads.length === 1 ? "" : "s"}
              </span>
            </div>
          </div>

          <div className="replies-thread-list">
            {loadingThreads ? (
              <div className="replies-loading">
                <RefreshCw
                  size={22}
                  className="replies-spinner"
                />
                <span>Loading conversations...</span>
              </div>
            ) : filteredThreads.length === 0 ? (
              <div className="replies-empty">
                <div className="replies-empty-icon">
                  <MessageSquare size={24} />
                </div>

                <h3>No replies yet</h3>

                <p>
                  Incoming replies will appear here when they
                  are ingested into the system.
                </p>
              </div>
            ) : (
              filteredThreads.map((thread) => {
                const isSelected =
                  selectedThread?.id === thread.id;

                return (
                  <button
                    type="button"
                    key={thread.id}
                    className={`replies-thread-item ${
                      isSelected ? "selected" : ""
                    }`}
                    onClick={() => openThread(thread)}
                  >
                    <div className="replies-thread-avatar">
                      <UserRound size={18} />
                    </div>

                    <div className="replies-thread-content">
                      <div className="replies-thread-top">
                        <strong>
                          {getThreadSubject(thread)}
                        </strong>

                        <span>
                          {formatRelativeTime(
                            thread.last_message_at,
                          )}
                        </span>
                      </div>

                      <div className="replies-thread-meta">
                        <span>
                          {thread.provider || "Unknown"}
                        </span>

                        <span className="replies-dot">
                          •
                        </span>

                        <span>
                          {String(
                            thread.last_direction || "inbound",
                          ).toLowerCase() === "inbound"
                            ? "Incoming reply"
                            : "Outgoing message"}
                        </span>
                      </div>

                      <div className="replies-thread-bottom">
                        <span className="replies-lead-id">
                          Lead{" "}
                          {String(thread.lead_id).slice(
                            0,
                            8,
                          )}
                        </span>

                        <span
                          className={`replies-status status-${getThreadStatus(
                            thread,
                          )}`}
                        >
                          {getThreadStatus(thread)}
                        </span>
                      </div>
                    </div>
                  </button>
                );
              })
            )}
          </div>

          <div className="replies-pagination">
            <span>
              Page {page + 1}
            </span>

            <div>
              <button
                type="button"
                onClick={handlePreviousPage}
                disabled={page === 0}
                aria-label="Previous page"
              >
                <ChevronLeft size={17} />
              </button>

              <button
                type="button"
                onClick={handleNextPage}
                disabled={threads.length < pageSize}
                aria-label="Next page"
              >
                <ChevronRight size={17} />
              </button>
            </div>
          </div>
        </div>

        <div className="replies-conversation-panel">
          {!selectedThread ? (
            <div className="replies-conversation-empty">
              <div className="replies-conversation-empty-icon">
                <Mail size={28} />
              </div>

              <h2>Select a conversation</h2>

              <p>
                Choose a thread from the inbox to view the
                complete conversation.
              </p>
            </div>
          ) : (
            <>
              <div className="replies-conversation-header">
                <div className="replies-conversation-title">
                  <div className="replies-conversation-avatar">
                    <UserRound size={20} />
                  </div>

                  <div>
                    <h2>
                      {getThreadSubject(selectedThread)}
                    </h2>

                    <div>
                      <span>
                        {selectedThread.provider ||
                          "Unknown provider"}
                      </span>

                      <span className="replies-dot">
                        •
                      </span>

                      <span>
                        Lead{" "}
                        {String(
                          selectedThread.lead_id,
                        ).slice(0, 8)}
                      </span>
                    </div>
                  </div>
                </div>

                <button
                  type="button"
                  className="replies-archive-button"
                  title="Archive"
                  disabled
                >
                  <Archive size={18} />
                </button>
              </div>

              <div className="replies-conversation-body">
                {loadingMessages ? (
                  <div className="replies-loading">
                    <RefreshCw
                      size={22}
                      className="replies-spinner"
                    />
                    <span>
                      Loading conversation...
                    </span>
                  </div>
                ) : messages.length === 0 ? (
                  <div className="replies-empty replies-empty-conversation">
                    <div className="replies-empty-icon">
                      <MessageSquare size={24} />
                    </div>

                    <h3>No messages found</h3>

                    <p>
                      This thread does not contain any
                      messages yet.
                    </p>
                  </div>
                ) : (
                  <div className="replies-message-list">
                    {messages.map((message) => {
                      const isInbound =
                        String(
                          message.direction || "",
                        ).toLowerCase() === "inbound";

                      return (
                        <article
                          key={message.id}
                          className={`replies-message ${
                            isInbound
                              ? "inbound"
                              : "outbound"
                          }`}
                        >
                          <div className="replies-message-header">
                            <div>
                              <strong>
                                {isInbound
                                  ? getMessageSender(
                                      message,
                                    )
                                  : "You"}
                              </strong>

                              <span>
                                {isInbound
                                  ? "Incoming reply"
                                  : "Outgoing message"}
                              </span>
                            </div>

                            <time>
                              {formatDateTime(
                                message.received_at ||
                                  message.sent_at ||
                                  message.created_at,
                              )}
                            </time>
                          </div>

                          <div className="replies-message-recipient">
                            {message.to_emails?.length
                              ? `To: ${message.to_emails.join(
                                  ", ",
                                )}`
                              : "Recipient information unavailable"}
                          </div>

                          {message.subject && (
                            <div className="replies-message-subject">
                              {message.subject}
                            </div>
                          )}

                          <div className="replies-message-body">
                            {message.body_text ||
                              "No message body available."}
                          </div>
                        </article>
                      );
                    })}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </section>
  );
}

export default RepliesInboxPage;