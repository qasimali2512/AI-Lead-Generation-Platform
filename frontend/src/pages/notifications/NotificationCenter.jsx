import { useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  Bell,
  Check,
  CheckCheck,
  ChevronRight,
  Info,
  Mail,
  MessageCircle,
  RefreshCw,
  Trash2,
  UserPlus,
  X,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { toast } from "react-toastify";

import notificationService from "../../services/notificationService";

import "./NotificationCenter.css";

function getNotificationIcon(type) {
  switch (type) {
    case "lead":
      return UserPlus;

    case "email":
      return Mail;

    case "reply":
      return MessageCircle;

    case "error":
      return AlertCircle;

    case "success":
      return Check;

    case "warning":
      return AlertCircle;

    case "website":
      return RefreshCw;

    default:
      return Info;
  }
}

function formatNotificationTime(value) {
  if (!value) {
    return "";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "";
  }

  const now = new Date();
  const difference = now.getTime() - date.getTime();

  const minute = 60 * 1000;
  const hour = 60 * minute;
  const day = 24 * hour;

  if (difference < minute) {
    return "Just now";
  }

  if (difference < hour) {
    return `${Math.floor(difference / minute)}m ago`;
  }

  if (difference < day) {
    return `${Math.floor(difference / hour)}h ago`;
  }

  if (difference < 7 * day) {
    return `${Math.floor(difference / day)}d ago`;
  }

  return date.toLocaleDateString([], {
    month: "short",
    day: "numeric",
    year:
      date.getFullYear() !== now.getFullYear()
        ? "numeric"
        : undefined,
  });
}

function NotificationCenter() {
  const navigate = useNavigate();
  const containerRef = useRef(null);

  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);

  const [loading, setLoading] = useState(false);
  const [markingAll, setMarkingAll] = useState(false);

  useEffect(() => {
    loadNotifications();

    const interval = window.setInterval(() => {
      loadNotifications(true);
    }, 30000);

    return () => {
      window.clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    function handleOutsideClick(event) {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target)
      ) {
        setOpen(false);
      }
    }

    if (open) {
      document.addEventListener(
        "mousedown",
        handleOutsideClick,
      );
    }

    return () => {
      document.removeEventListener(
        "mousedown",
        handleOutsideClick,
      );
    };
  }, [open]);

  async function loadNotifications(silent = false) {
    try {
      if (!silent) {
        setLoading(true);
      }

      const data =
        await notificationService.getNotifications({
          skip: 0,
          limit: 20,
        });

      setNotifications(
        Array.isArray(data?.items)
          ? data.items
          : [],
      );

      setUnreadCount(
        Number(data?.unread_count || 0),
      );
    } catch (error) {
      if (!silent) {
        toast.error(
          error?.response?.data?.detail ||
            "Unable to load notifications.",
        );
      }
    } finally {
      if (!silent) {
        setLoading(false);
      }
    }
  }

  async function handleMarkRead(notification) {
    if (notification.is_read) {
      handleAction(notification);
      return;
    }

    try {
      await notificationService.markAsRead(
        notification.id,
      );

      setNotifications((current) =>
        current.map((item) =>
          item.id === notification.id
            ? {
                ...item,
                is_read: true,
              }
            : item,
        ),
      );

      setUnreadCount((current) =>
        Math.max(0, current - 1),
      );

      handleAction({
        ...notification,
        is_read: true,
      });
    } catch (error) {
      toast.error(
        error?.response?.data?.detail ||
          "Unable to update notification.",
      );
    }
  }

  async function handleMarkAllRead() {
    if (!unreadCount) {
      return;
    }

    try {
      setMarkingAll(true);

      await notificationService.markAllAsRead();

      setNotifications((current) =>
        current.map((item) => ({
          ...item,
          is_read: true,
        })),
      );

      setUnreadCount(0);

      toast.success(
        "All notifications marked as read.",
      );
    } catch (error) {
      toast.error(
        error?.response?.data?.detail ||
          "Unable to mark notifications as read.",
      );
    } finally {
      setMarkingAll(false);
    }
  }

  async function handleDelete(event, notificationId) {
    event.stopPropagation();

    try {
      await notificationService.deleteNotification(
        notificationId,
      );

      setNotifications((current) =>
        current.filter(
          (item) => item.id !== notificationId,
        ),
      );

      setUnreadCount((current) => {
        const removed = notifications.find(
          (item) => item.id === notificationId,
        );

        if (removed && !removed.is_read) {
          return Math.max(0, current - 1);
        }

        return current;
      });
    } catch (error) {
      toast.error(
        error?.response?.data?.detail ||
          "Unable to delete notification.",
      );
    }
  }

  function handleAction(notification) {
    setOpen(false);

    if (notification.action_url) {
      navigate(notification.action_url);
    }
  }

  return (
    <div
      className="notification-center"
      ref={containerRef}
    >
      <button
        type="button"
        className={`notification-trigger ${
          open ? "active" : ""
        }`}
        onClick={() => setOpen((current) => !current)}
        aria-label="Notifications"
        aria-expanded={open}
      >
        <Bell size={19} />

        {unreadCount > 0 && (
          <span className="notification-badge">
            {unreadCount > 99
              ? "99+"
              : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="notification-panel">
          <div className="notification-panel-header">
            <div>
              <h3>Notifications</h3>
              <span>
                {unreadCount > 0
                  ? `${unreadCount} unread`
                  : "You're all caught up"}
              </span>
            </div>

            <div className="notification-header-actions">
              {unreadCount > 0 && (
                <button
                  type="button"
                  className="notification-mark-all"
                  onClick={handleMarkAllRead}
                  disabled={markingAll}
                >
                  <CheckCheck size={14} />
                  {markingAll
                    ? "Saving..."
                    : "Mark all read"}
                </button>
              )}

              <button
                type="button"
                className="notification-close"
                onClick={() => setOpen(false)}
                aria-label="Close notifications"
              >
                <X size={17} />
              </button>
            </div>
          </div>

          <div className="notification-list">
            {loading ? (
              <div className="notification-state">
                <span className="notification-loader" />
                <p>Loading notifications...</p>
              </div>
            ) : notifications.length === 0 ? (
              <div className="notification-empty">
                <div className="notification-empty-icon">
                  <Bell size={22} />
                </div>

                <h4>No notifications</h4>

                <p>
                  New activity and important updates
                  will appear here.
                </p>
              </div>
            ) : (
              notifications.map((notification) => {
                const Icon = getNotificationIcon(
                  notification.notification_type,
                );

                return (
                  <div
                    key={notification.id}
                    className={`notification-item ${
                      !notification.is_read
                        ? "unread"
                        : ""
                    }`}
                    onClick={() =>
                      handleMarkRead(notification)
                    }
                  >
                    <div
                      className={`notification-icon ${
                        notification.notification_type ||
                        "info"
                      }`}
                    >
                      <Icon size={17} />
                    </div>

                    <div className="notification-content">
                      <div className="notification-title-row">
                        <h4>
                          {notification.title}
                        </h4>

                        {!notification.is_read && (
                          <span className="notification-unread-dot" />
                        )}
                      </div>

                      <p>
                        {notification.message}
                      </p>

                      <div className="notification-meta">
                        <span>
                          {formatNotificationTime(
                            notification.created_at,
                          )}
                        </span>

                        {notification.action_url && (
                          <span className="notification-action">
                            View
                            <ChevronRight
                              size={13}
                            />
                          </span>
                        )}
                      </div>
                    </div>

                    <button
                      type="button"
                      className="notification-delete"
                      onClick={(event) =>
                        handleDelete(
                          event,
                          notification.id,
                        )
                      }
                      aria-label="Delete notification"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                );
              })
            )}
          </div>

          <div className="notification-panel-footer">
            <button
              type="button"
              onClick={() => {
                setOpen(false);
                navigate("/settings");
              }}
            >
              Notification settings
              <ChevronRight size={14} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default NotificationCenter;