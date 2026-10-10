import { useEffect, useRef, useState } from "react";
import {
  Bell,
  Check,
  CheckCheck,
  Trash2,
  X,
} from "lucide-react";
import { useNavigate } from "react-router-dom";

import notificationService from "../../services/notificationService";

import "./NotificationCenter.css";

function NotificationCenter() {
  const navigate = useNavigate();

  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(false);

  const wrapperRef = useRef(null);

  async function loadNotifications() {
    try {
      setLoading(true);

      const data =
        await notificationService.getNotifications();

      if (Array.isArray(data)) {
        setNotifications(data);
      } else if (Array.isArray(data?.items)) {
        setNotifications(data.items);
      } else if (Array.isArray(data?.notifications)) {
        setNotifications(data.notifications);
      } else {
        setNotifications([]);
      }
    } catch (error) {
      console.error(
        "Failed to load notifications:",
        error,
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadNotifications();

    const interval = setInterval(() => {
      loadNotifications();
    }, 30000);

    return () => {
      clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    function handleOutsideClick(event) {
      if (
        wrapperRef.current &&
        !wrapperRef.current.contains(event.target)
      ) {
        setOpen(false);
      }
    }

    document.addEventListener(
      "mousedown",
      handleOutsideClick,
    );

    return () => {
      document.removeEventListener(
        "mousedown",
        handleOutsideClick,
      );
    };
  }, []);

  const unreadCount = notifications.filter(
    (item) => !item.is_read,
  ).length;

  async function handleMarkRead(notification) {
    if (notification.is_read) {
      if (notification.action_url) {
        navigate(notification.action_url);
        setOpen(false);
      }

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

      if (notification.action_url) {
        navigate(notification.action_url);
        setOpen(false);
      }
    } catch (error) {
      console.error(
        "Failed to mark notification as read:",
        error,
      );
    }
  }

  async function handleMarkAllRead() {
    try {
      await notificationService.markAllAsRead();

      setNotifications((current) =>
        current.map((item) => ({
          ...item,
          is_read: true,
        })),
      );
    } catch (error) {
      console.error(
        "Failed to mark all notifications as read:",
        error,
      );
    }
  }

  async function handleDelete(
    event,
    notificationId,
  ) {
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
    } catch (error) {
      console.error(
        "Failed to delete notification:",
        error,
      );
    }
  }

  function formatDate(value) {
    if (!value) {
      return "";
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
      return "";
    }

    return date.toLocaleString([], {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }

  return (
    <div
      className="notification-center"
      ref={wrapperRef}
    >
      <button
        type="button"
        className="notification-trigger"
        onClick={() =>
          setOpen((current) => !current)
        }
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
                  onClick={handleMarkAllRead}
                  title="Mark all as read"
                >
                  <CheckCheck size={17} />
                </button>
              )}

              <button
                type="button"
                onClick={() => setOpen(false)}
                title="Close"
              >
                <X size={17} />
              </button>
            </div>
          </div>

          <div className="notification-list">
            {loading &&
            notifications.length === 0 ? (
              <div className="notification-empty">
                Loading notifications...
              </div>
            ) : notifications.length === 0 ? (
              <div className="notification-empty">
                <Bell size={25} />

                <strong>
                  No notifications
                </strong>

                <span>
                  New activity will appear here.
                </span>
              </div>
            ) : (
              notifications.map((notification) => (
                <button
                  type="button"
                  key={notification.id}
                  className={`notification-item ${
                    notification.is_read
                      ? "is-read"
                      : "is-unread"
                  }`}
                  onClick={() =>
                    handleMarkRead(notification)
                  }
                >
                  <div className="notification-item-icon">
                    <Bell size={16} />
                  </div>

                  <div className="notification-item-content">
                    <div className="notification-item-top">
                      <strong>
                        {notification.title}
                      </strong>

                      {!notification.is_read && (
                        <span className="notification-unread-dot" />
                      )}
                    </div>

                    <p>
                      {notification.message}
                    </p>

                    <span className="notification-time">
                      {formatDate(
                        notification.created_at,
                      )}
                    </span>
                  </div>

                  <div className="notification-item-actions">
                    {!notification.is_read && (
                      <span
                        className="notification-action"
                        title="Mark as read"
                      >
                        <Check size={15} />
                      </span>
                    )}

                    <span
                      className="notification-action delete"
                      title="Delete"
                      onClick={(event) =>
                        handleDelete(
                          event,
                          notification.id,
                        )
                      }
                    >
                      <Trash2 size={15} />
                    </span>
                  </div>
                </button>
              ))
            )}
          </div>

          <div className="notification-panel-footer">
            <button
              type="button"
              onClick={() => {
                navigate("/settings");
                setOpen(false);
              }}
            >
              Notification settings
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default NotificationCenter;