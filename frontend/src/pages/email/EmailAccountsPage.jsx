import {
  AlertCircle,
  Check,
  CirclePause,
  CirclePlay,
  Edit2,
  Link2Off,
  Mail,
  MoreVertical,
  Plus,
  RefreshCw,
  RotateCcw,
  Save,
  Send,
  ShieldCheck,
  Trash2,
  X,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { toast } from "react-toastify";

import api from "../../api/client";
import emailAccountService from "../../services/emailAccountService";
import "./EmailAccountsPage.css";


/* ------------------------------------------------------------- */
/* Helpers                                                       */
/* ------------------------------------------------------------- */

function normalizeList(response) {
  if (Array.isArray(response)) {
    return response;
  }

  if (Array.isArray(response?.accounts)) {
    return response.accounts;
  }

  if (Array.isArray(response?.data)) {
    return response.data;
  }

  if (Array.isArray(response?.items)) {
    return response.items;
  }

  return [];
}


function getValue(item, keys, fallback = "") {
  for (const key of keys) {
    if (
      item?.[key] !== undefined &&
      item?.[key] !== null &&
      item?.[key] !== ""
    ) {
      return item[key];
    }
  }

  return fallback;
}


function normalizeProvider(value) {
  const provider = String(value || "").toLowerCase();

  if (provider === "google") {
    return "Google";
  }

  if (provider === "microsoft") {
    return "Microsoft";
  }

  if (provider === "smtp") {
    return "SMTP";
  }

  return provider || "Email";
}


function normalizeStatus(value) {
  return String(value || "disabled").toLowerCase();
}


function getAccountName(account) {
  return getValue(
    account,
    [
      "display_name",
      "name",
    ],
    "Email account",
  );
}


function getAccountEmail(account) {
  return getValue(
    account,
    [
      "email",
      "email_address",
    ],
    "No email",
  );
}


function getProvider(account) {
  return normalizeProvider(
    getValue(
      account,
      ["provider"],
      "",
    ),
  );
}


function getStatus(account) {
  return normalizeStatus(
    getValue(
      account,
      ["status"],
      "disabled",
    ),
  );
}


function getDailyLimit(account) {
  const value = Number(
    getValue(
      account,
      [
        "daily_send_limit",
        "daily_limit",
      ],
      0,
    ),
  );

  return Number.isFinite(value)
    ? value
    : 0;
}


function getSentToday(account) {
  const value = Number(
    getValue(
      account,
      ["sent_today"],
      0,
    ),
  );

  return Number.isFinite(value)
    ? value
    : 0;
}


function getInitials(name) {
  return String(name || "E")
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}


function providerClass(provider) {
  return provider.toLowerCase();
}


function statusLabel(status) {
  const labels = {
    active: "Active",
    paused: "Paused",
    reauth_required: "Re-auth required",
    disabled: "Disabled",
  };

  return (
    labels[status] ||
    status.replace(/_/g, " ")
  );
}


function statusClass(status) {
  if (status === "active") {
    return "account-status-active";
  }

  if (status === "paused") {
    return "account-status-paused";
  }

  if (status === "reauth_required") {
    return "account-status-warning";
  }

  return "account-status-disabled";
}


/* ------------------------------------------------------------- */
/* Page                                                          */
/* ------------------------------------------------------------- */

function EmailAccountsPage() {
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);

  const [showAddModal, setShowAddModal] =
    useState(false);

  const [selectedAccount, setSelectedAccount] =
    useState(null);

  const [showMenu, setShowMenu] =
    useState(null);

  const [provider, setProvider] =
    useState("google");

  const [email, setEmail] =
    useState("");

  const [displayName, setDisplayName] =
    useState("");

  const [dailySendLimit, setDailySendLimit] =
    useState("50");

  const [accessToken, setAccessToken] =
    useState("");

  const [refreshToken, setRefreshToken] =
    useState("");

  const [providerAccountId, setProviderAccountId] =
    useState("");

  const [scopes, setScopes] =
    useState("");

  const [submitting, setSubmitting] =
    useState(false);

  const [actionLoading, setActionLoading] =
    useState(null);

  // Details modal edit state
  const [editingLimit, setEditingLimit]     = useState(false);
  const [editLimitValue, setEditLimitValue] = useState("");
  const [savingLimit, setSavingLimit]       = useState(false);
  const [disconnecting, setDisconnecting]   = useState(false);


  /* ----------------------------------------------------------- */
  /* Load accounts                                               */
  /* ----------------------------------------------------------- */

  const loadAccounts = async () => {
    try {
      setLoading(true);

      const response =
        await emailAccountService.getAccounts();

      setAccounts(
        normalizeList(response),
      );
    } catch (error) {
      console.error(
        "Unable to load email accounts:",
        error,
      );

      toast.error(
        error?.response?.data?.detail ||
          "Unable to load email accounts.",
      );

      setAccounts([]);
    } finally {
      setLoading(false);
    }
  };


  /* ----------------------------------------------------------- */
  /* Initial load + Google OAuth callback                        */
  /* ----------------------------------------------------------- */

  useEffect(() => {
    loadAccounts();

    const params = new URLSearchParams(
      window.location.search,
    );

    const googleStatus =
      params.get("google");

    const message =
      params.get("message");

    const connectedEmail =
      params.get("email");

    if (googleStatus === "connected") {
      toast.success(
        connectedEmail
          ? `${connectedEmail} connected successfully.`
          : "Google account connected successfully.",
      );

      window.history.replaceState(
        {},
        document.title,
        "/email/accounts",
      );

      return;
    }

    if (googleStatus === "error") {
      toast.error(
        message ||
          "Google account connection failed.",
      );

      window.history.replaceState(
        {},
        document.title,
        "/email/accounts",
      );
    }
  }, []);


  /* ----------------------------------------------------------- */
  /* Stats                                                       */
  /* ----------------------------------------------------------- */

  const stats = useMemo(() => {
    const total =
      accounts.length;

    const active =
      accounts.filter(
        (account) =>
          getStatus(account) ===
          "active",
      ).length;

    const paused =
      accounts.filter(
        (account) =>
          getStatus(account) ===
          "paused",
      ).length;

    const reauth =
      accounts.filter(
        (account) =>
          getStatus(account) ===
          "reauth_required",
      ).length;

    const totalDailyCapacity =
      accounts.reduce(
        (sum, account) => {
          if (
            getStatus(account) !==
            "active"
          ) {
            return sum;
          }

          return (
            sum +
            getDailyLimit(account)
          );
        },
        0,
      );

    return {
      total,
      active,
      paused,
      reauth,
      totalDailyCapacity,
    };
  }, [accounts]);


  /* ----------------------------------------------------------- */
  /* Reset form                                                  */
  /* ----------------------------------------------------------- */

  const resetForm = () => {
    setProvider("google");
    setEmail("");
    setDisplayName("");
    setDailySendLimit("50");
    setAccessToken("");
    setRefreshToken("");
    setProviderAccountId("");
    setScopes("");
  };


  /* ----------------------------------------------------------- */
  /* Close modal                                                 */
  /* ----------------------------------------------------------- */

  const closeAddModal = () => {
    if (submitting) {
      return;
    }

    setShowAddModal(false);
    resetForm();
  };


  /* ----------------------------------------------------------- */
  /* Start Google OAuth                                          */
  /* ----------------------------------------------------------- */

  const handleGoogleConnect = async () => {
    try {
      setSubmitting(true);

      const response =
        await api.get(
          "/email-accounts/google/connect",
        );

      const authorizationUrl =
        response?.data?.authorization_url;

      if (!authorizationUrl) {
        throw new Error(
          "Google authorization URL was not returned.",
        );
      }

      window.location.assign(
        authorizationUrl,
      );
    } catch (error) {
      console.error(
        "Unable to start Google OAuth:",
        error,
      );

      toast.error(
        error?.response?.data?.detail ||
          "Unable to connect Google account.",
      );

      setSubmitting(false);
    }
  };


  /* ----------------------------------------------------------- */
  /* Manual account creation                                    */
  /* ----------------------------------------------------------- */

  const handleCreate = async (event) => {
    event.preventDefault();

    /*
     * Google accounts are connected through
     * OAuth instead of manually entering tokens.
     */
    if (provider === "google") {
      await handleGoogleConnect();
      return;
    }

    if (!email.trim()) {
      toast.error(
        "Email address is required.",
      );
      return;
    }

    const parsedLimit =
      Number(dailySendLimit);

    if (
      !Number.isInteger(parsedLimit) ||
      parsedLimit < 1 ||
      parsedLimit > 10000
    ) {
      toast.error(
        "Daily send limit must be between 1 and 10,000.",
      );
      return;
    }

    try {
      setSubmitting(true);

      const payload = {
        provider,
        email: email.trim(),

        display_name:
          displayName.trim() ||
          undefined,

        provider_account_id:
          providerAccountId.trim() ||
          undefined,

        access_token:
          accessToken.trim() ||
          undefined,

        refresh_token:
          refreshToken.trim() ||
          undefined,

        scopes: scopes
          .split(",")
          .map(
            (scope) =>
              scope.trim(),
          )
          .filter(Boolean),

        provider_metadata: {},

        daily_send_limit:
          parsedLimit,
      };

      await emailAccountService.createAccount(
        payload,
      );

      toast.success(
        "Email account added successfully.",
      );

      closeAddModal();

      await loadAccounts();
    } catch (error) {
      console.error(
        "Unable to create email account:",
        error,
      );

      toast.error(
        error?.response?.data?.detail ||
          "Unable to add this email account.",
      );
    } finally {
      setSubmitting(false);
    }
  };


  /* ----------------------------------------------------------- */
  /* Account status                                             */
  /* ----------------------------------------------------------- */

  const handleStatusChange = async (
    account,
    nextStatus,
  ) => {
    const accountId =
      getValue(
        account,
        [
          "id",
          "account_id",
        ],
      );

    if (!accountId) {
      return;
    }

    try {
      setActionLoading(accountId);

      await emailAccountService.updateStatus(
        accountId,
        nextStatus,
      );

      toast.success(
        `Account ${statusLabel(
          nextStatus,
        ).toLowerCase()}.`,
      );

      setShowMenu(null);

      await loadAccounts();
    } catch (error) {
      console.error(
        "Unable to update account status:",
        error,
      );

      toast.error(
        error?.response?.data?.detail ||
          "Unable to update account status.",
      );
    } finally {
      setActionLoading(null);
    }
  };


  /* ----------------------------------------------------------- */
  /* Delete account                                              */
  /* ----------------------------------------------------------- */

  const handleDelete = async (
    account,
  ) => {
    const accountId =
      getValue(
        account,
        [
          "id",
          "account_id",
        ],
      );

    if (!accountId) {
      return;
    }

    const accountEmail =
      getAccountEmail(account);

    const confirmed =
      window.confirm(
        `Remove ${accountEmail} from your email accounts?`,
      );

    if (!confirmed) {
      return;
    }

    try {
      setActionLoading(accountId);

      await emailAccountService.deleteAccount(
        accountId,
      );

      toast.success(
        "Email account removed.",
      );

      setShowMenu(null);
      setSelectedAccount(null);

      await loadAccounts();
    } catch (error) {
      console.error(
        "Unable to delete email account:",
        error,
      );

      toast.error(
        error?.response?.data?.detail ||
          "Unable to remove this account.",
      );
    } finally {
      setActionLoading(null);
    }
  };


  /* ----------------------------------------------------------- */
  /* Disconnect account (from details modal)                     */
  /* ----------------------------------------------------------- */

  const handleDisconnect = async (account) => {
    const accountId = getValue(account, ["id", "account_id"]);
    if (!accountId) return;

    const accountEmail = getAccountEmail(account);
    const confirmed = window.confirm(
      `Disconnect ${accountEmail}?\n\nThis will remove the account from LeadFlow. You can reconnect it at any time.`,
    );
    if (!confirmed) return;

    try {
      setDisconnecting(true);
      await emailAccountService.deleteAccount(accountId);
      toast.success(`${accountEmail} disconnected.`);
      setSelectedAccount(null);
      setEditingLimit(false);
      await loadAccounts();
    } catch (err) {
      toast.error(
        err?.response?.data?.detail || "Unable to disconnect the account.",
      );
    } finally {
      setDisconnecting(false);
    }
  };


  /* ----------------------------------------------------------- */
  /* Update daily send limit (from details modal)                */
  /* ----------------------------------------------------------- */

  const handleUpdateLimit = async (account) => {
    const accountId = getValue(account, ["id", "account_id"]);
    if (!accountId) return;

    const parsed = Number(editLimitValue);
    if (!Number.isInteger(parsed) || parsed < 1 || parsed > 10000) {
      toast.error("Daily limit must be between 1 and 10,000.");
      return;
    }

    try {
      setSavingLimit(true);
      const updated = await emailAccountService.updateAccount(accountId, {
        daily_send_limit: parsed,
      });
      // Sync selectedAccount with updated data
      setSelectedAccount((prev) => ({ ...prev, ...updated }));
      // Also update the list row
      setAccounts((prev) =>
        prev.map((a) =>
          getValue(a, ["id", "account_id"]) === accountId
            ? { ...a, daily_send_limit: parsed }
            : a,
        ),
      );
      setEditingLimit(false);
      toast.success("Daily send limit updated.");
    } catch (err) {
      toast.error(
        err?.response?.data?.detail || "Unable to update daily limit.",
      );
    } finally {
      setSavingLimit(false);
    }
  };


  /* ----------------------------------------------------------- */
  /* Reconnect Google (from details modal)                       */
  /* ----------------------------------------------------------- */

  const handleReconnectGoogle = async () => {
    try {
      const response = await api.get("/email-accounts/google/connect");
      const authorizationUrl = response?.data?.authorization_url;
      if (!authorizationUrl) throw new Error("No authorization URL returned.");
      window.location.assign(authorizationUrl);
    } catch (err) {
      toast.error(
        err?.response?.data?.detail || "Unable to start Google reconnect.",
      );
    }
  };


  /* ----------------------------------------------------------- */
  /* Render                                                      */
  /* ----------------------------------------------------------- */

  return (
    <div className="email-accounts-page">

      {/* ----------------------------------------------------- */}
      {/* Hero                                                  */}
      {/* ----------------------------------------------------- */}

      <section className="email-accounts-hero">
        <div>
          <div className="email-accounts-eyebrow">
            <ShieldCheck size={15} />
            Email infrastructure
          </div>

          <h1>
            Email accounts
          </h1>

          <p>
            Manage the authorized email
            accounts that can be used by
            your outreach system.
          </p>
        </div>

        <button
          type="button"
          className="add-email-account-button"
          onClick={() =>
            setShowAddModal(true)
          }
        >
          <Plus size={17} />
          Add email account
        </button>
      </section>


      {/* ----------------------------------------------------- */}
      {/* Stats                                                 */}
      {/* ----------------------------------------------------- */}

      <section className="email-account-stats">

        <div className="email-account-stat">
          <div className="email-stat-icon blue">
            <Mail size={18} />
          </div>

          <div>
            <span>
              Total accounts
            </span>

            <strong>
              {stats.total}
            </strong>
          </div>
        </div>


        <div className="email-account-stat">
          <div className="email-stat-icon sage">
            <Check size={18} />
          </div>

          <div>
            <span>
              Active
            </span>

            <strong>
              {stats.active}
            </strong>
          </div>
        </div>


        <div className="email-account-stat">
          <div className="email-stat-icon warning">
            <AlertCircle size={18} />
          </div>

          <div>
            <span>
              Re-auth required
            </span>

            <strong>
              {stats.reauth}
            </strong>
          </div>
        </div>


        <div className="email-account-stat">
          <div className="email-stat-icon indigo">
            <Send size={18} />
          </div>

          <div>
            <span>
              Daily capacity
            </span>

            <strong>
              {stats.totalDailyCapacity}
            </strong>
          </div>
        </div>

      </section>


      {/* ----------------------------------------------------- */}
      {/* Connected accounts                                    */}
      {/* ----------------------------------------------------- */}

      <section className="email-accounts-card">

        <div className="email-accounts-card-header">
          <div>
            <span className="email-section-kicker">
              Connected accounts
            </span>

            <h2>
              Your sending accounts
            </h2>
          </div>

          <button
            type="button"
            className="refresh-accounts-button"
            onClick={loadAccounts}
            disabled={loading}
          >
            <RefreshCw
              size={15}
              className={
                loading
                  ? "accounts-spinning"
                  : ""
              }
            />

            Refresh
          </button>
        </div>


        {/* Loading */}
        {loading ? (
          <div className="email-accounts-loading">

            <div className="email-account-spinner" />

            <h3>
              Loading email accounts
            </h3>

            <p>
              Retrieving your authorized
              sending accounts...
            </p>

          </div>
        ) : accounts.length === 0 ? (

          /* Empty */
          <div className="email-accounts-empty">

            <div className="empty-email-icon">
              <Mail size={29} />
            </div>

            <h3>
              No email accounts connected
            </h3>

            <p>
              Add an authorized email account
              to prepare your outreach
              infrastructure.
            </p>

            <button
              type="button"
              onClick={() =>
                setShowAddModal(true)
              }
            >
              <Plus size={16} />
              Add your first account
            </button>

          </div>

        ) : (

          /* Accounts */
          <div className="email-account-list">

            {accounts.map((account) => {
              const accountId =
                getValue(
                  account,
                  [
                    "id",
                    "account_id",
                  ],
                );

              const name =
                getAccountName(
                  account,
                );

              const accountEmail =
                getAccountEmail(
                  account,
                );

              const currentProvider =
                getProvider(
                  account,
                );

              const status =
                getStatus(
                  account,
                );

              const sentToday =
                getSentToday(
                  account,
                );

              const dailyLimit =
                getDailyLimit(
                  account,
                );

              const usage =
                dailyLimit > 0
                  ? Math.min(
                      (sentToday /
                        dailyLimit) *
                        100,
                      100,
                    )
                  : 0;

              return (
                <article
                  className="email-account-row"
                  key={accountId}
                >

                  {/* Identity */}
                  <div className="email-account-identity">

                    <div
                      className={`email-account-avatar ${providerClass(
                        currentProvider,
                      )}`}
                    >
                      {getInitials(
                        name,
                      )}
                    </div>

                    <div className="email-account-info">

                      <div className="email-account-name-row">

                        <strong>
                          {name}
                        </strong>

                        <span
                          className={`provider-badge ${providerClass(
                            currentProvider,
                          )}`}
                        >
                          {currentProvider}
                        </span>

                      </div>

                      <span className="email-account-address">
                        {accountEmail}
                      </span>

                    </div>

                  </div>


                  {/* Status */}
                  <div className="email-account-status">

                    <span
                      className={`account-status ${statusClass(
                        status,
                      )}`}
                    >
                      <span className="status-dot" />

                      {statusLabel(
                        status,
                      )}
                    </span>

                  </div>


                  {/* Usage */}
                  <div className="email-account-usage">

                    <div className="usage-heading">

                      <span>
                        Today's sending
                      </span>

                      <strong>
                        {sentToday} /{" "}
                        {dailyLimit}
                      </strong>

                    </div>

                    <div className="usage-track">

                      <span
                        style={{
                          width:
                            `${usage}%`,
                        }}
                      />

                    </div>

                  </div>


                  {/* Actions */}
                  <div className="email-account-actions">

                    <button
                      type="button"
                      className="account-view-button"
                      onClick={() =>
                        setSelectedAccount(
                          account,
                        )
                      }
                    >
                      Details
                    </button>


                    <div className="account-menu-wrap">

                      <button
                        type="button"
                        className="account-menu-button"
                        onClick={() =>
                          setShowMenu(
                            showMenu ===
                              accountId
                              ? null
                              : accountId,
                          )
                        }
                        aria-label="Account actions"
                      >
                        <MoreVertical
                          size={17}
                        />
                      </button>


                      {showMenu ===
                        accountId && (
                        <div className="account-menu">

                          {status ===
                          "active" ? (

                            <button
                              type="button"
                              onClick={() =>
                                handleStatusChange(
                                  account,
                                  "paused",
                                )
                              }
                            >
                              <CirclePause
                                size={15}
                              />

                              Pause account
                            </button>

                          ) : (

                            <button
                              type="button"
                              onClick={() =>
                                handleStatusChange(
                                  account,
                                  "active",
                                )
                              }
                            >
                              <CirclePlay
                                size={15}
                              />

                              Activate account
                            </button>
                          )}


                          <button
                            type="button"
                            className="danger-menu-item"
                            onClick={() =>
                              handleDelete(
                                account,
                              )
                            }
                          >
                            <Trash2
                              size={15}
                            />

                            Remove account
                          </button>

                        </div>
                      )}

                    </div>

                  </div>


                  {/* Row loading */}
                  {actionLoading ===
                    accountId && (
                    <div className="account-row-loading">
                      Updating...
                    </div>
                  )}

                </article>
              );
            })}

          </div>
        )}

      </section>


      {/* ----------------------------------------------------- */}
      {/* Security note                                         */}
      {/* ----------------------------------------------------- */}

      <section className="email-account-note">

        <ShieldCheck size={17} />

        <div>

          <strong>
            Account security
          </strong>

          <p>
            Access and refresh credentials
            are handled by the backend.
            They are not displayed in the
            account list.
          </p>

        </div>

      </section>


      {/* ----------------------------------------------------- */}
      {/* Add account modal                                     */}
      {/* ----------------------------------------------------- */}

      {showAddModal && (

        <div
          className="email-modal-backdrop"
          onMouseDown={(event) => {
            if (
              event.target ===
              event.currentTarget
            ) {
              closeAddModal();
            }
          }}
        >

          <div className="email-modal">

            {/* Modal header */}
            <div className="email-modal-header">

              <div>

                <span className="email-section-kicker">
                  New connection
                </span>

                <h2>
                  Add email account
                </h2>

                <p>
                  Connect an authorized account
                  for future outreach sending.
                </p>

              </div>


              <button
                type="button"
                className="email-modal-close"
                onClick={closeAddModal}
                aria-label="Close"
              >
                <X size={18} />
              </button>

            </div>


            {/* Form */}
            <form
              className="email-account-form"
              onSubmit={handleCreate}
            >

              {/* Provider + email */}
              <div className="form-grid">

                <label className="account-form-field">

                  <span>
                    Provider
                  </span>

                  <select
                    value={provider}
                    onChange={(event) => {
                      setProvider(
                        event.target.value,
                      );

                      if (
                        event.target.value ===
                        "google"
                      ) {
                        setEmail("");
                        setAccessToken("");
                        setRefreshToken("");
                        setProviderAccountId("");
                        setScopes("");
                      }
                    }}
                  >

                    <option value="google">
                      Google
                    </option>

                    <option value="microsoft">
                      Microsoft
                    </option>

                    <option value="smtp">
                      SMTP
                    </option>

                  </select>

                </label>


                {/* Email only for non-Google */}
                {provider !==
                  "google" && (
                  <label className="account-form-field">

                    <span>
                      Email address
                    </span>

                    <input
                      type="email"
                      value={email}
                      onChange={(event) =>
                        setEmail(
                          event.target.value,
                        )
                      }
                      placeholder="you@company.com"
                      required
                    />

                  </label>
                )}

              </div>


              {/* Google OAuth */}
              {provider ===
              "google" ? (

                <div className="google-oauth-connect">

                  <div className="google-oauth-content">

                    <div className="google-oauth-icon">
                      G
                    </div>

                    <div>

                      <strong>
                        Connect with Google
                      </strong>

                      <p>
                        Sign in with the Gmail
                        account you want to use
                        for your outreach system.
                      </p>

                    </div>

                  </div>


                  <div className="google-oauth-security">

                    <ShieldCheck
                      size={16}
                    />

                    <span>
                      Your Gmail credentials
                      are handled by Google's
                      OAuth authorization flow.
                      Passwords and tokens are
                      not entered into this form.
                    </span>

                  </div>


                  <button
                    type="submit"
                    className="email-primary-button google-connect-button"
                    disabled={
                      submitting
                    }
                  >

                    {submitting
                      ? "Connecting..."
                      : "Continue with Google"}

                  </button>

                </div>

              ) : (

                <>
                  {/* Display name */}
                  <label className="account-form-field">

                    <span>
                      Display name
                    </span>

                    <input
                      type="text"
                      value={displayName}
                      onChange={(event) =>
                        setDisplayName(
                          event.target.value,
                        )
                      }
                      placeholder="Your name or business name"
                    />

                  </label>


                  {/* Daily limit */}
                  <label className="account-form-field">

                    <span>
                      Daily send limit
                    </span>

                    <input
                      type="number"
                      min="1"
                      max="10000"
                      value={
                        dailySendLimit
                      }
                      onChange={(event) =>
                        setDailySendLimit(
                          event.target.value,
                        )
                      }
                    />

                    <small>
                      Maximum allowed by the
                      configured account
                      setting.
                    </small>

                  </label>


                  {/* Advanced credentials */}
                  <div className="advanced-account-fields">

                    <div className="advanced-heading">

                      <span>
                        Provider credentials
                      </span>

                      <small>
                        Credentials are stored
                        encrypted by the backend.
                      </small>

                    </div>


                    {/* Provider account ID */}
                    <label className="account-form-field">

                      <span>
                        Provider account ID
                      </span>

                      <input
                        type="text"
                        value={
                          providerAccountId
                        }
                        onChange={(event) =>
                          setProviderAccountId(
                            event.target.value,
                          )
                        }
                        placeholder="Provider account ID"
                      />

                    </label>


                    {/* Access token */}
                    <label className="account-form-field">

                      <span>
                        Access token
                      </span>

                      <input
                        type="password"
                        value={
                          accessToken
                        }
                        onChange={(event) =>
                          setAccessToken(
                            event.target.value,
                          )
                        }
                        placeholder="Access token"
                        autoComplete="off"
                      />

                    </label>


                    {/* Refresh token */}
                    <label className="account-form-field">

                      <span>
                        Refresh token
                      </span>

                      <input
                        type="password"
                        value={
                          refreshToken
                        }
                        onChange={(event) =>
                          setRefreshToken(
                            event.target.value,
                          )
                        }
                        placeholder="Refresh token"
                        autoComplete="off"
                      />

                    </label>


                    {/* Scopes */}
                    <label className="account-form-field">

                      <span>
                        Scopes
                      </span>

                      <input
                        type="text"
                        value={scopes}
                        onChange={(event) =>
                          setScopes(
                            event.target.value,
                          )
                        }
                        placeholder="scope1, scope2"
                      />

                      <small>
                        Separate multiple
                        scopes with commas.
                      </small>

                    </label>

                  </div>


                  {/* Security note */}
                  <div className="email-form-security-note">

                    <ShieldCheck
                      size={16}
                    />

                    <span>
                      Credentials are submitted
                      to the backend over the
                      configured API connection
                      and are not displayed after
                      account creation.
                    </span>

                  </div>


                  {/* Actions */}
                  <div className="email-modal-actions">

                    <button
                      type="button"
                      className="email-secondary-button"
                      onClick={
                        closeAddModal
                      }
                      disabled={
                        submitting
                      }
                    >
                      Cancel
                    </button>


                    <button
                      type="submit"
                      className="email-primary-button"
                      disabled={
                        submitting
                      }
                    >

                      <Plus size={16} />

                      {submitting
                        ? "Adding..."
                        : "Add account"}

                    </button>

                  </div>
                </>
              )}

            </form>

          </div>

        </div>
      )}


      {/* ----------------------------------------------------- */}
      {/* Account details modal                                 */}
      {/* ----------------------------------------------------- */}

      {selectedAccount && (

        <div
          className="email-modal-backdrop"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              setSelectedAccount(null);
              setEditingLimit(false);
            }
          }}
        >

          <div className="account-details-modal">

            {/* Modal header */}
            <div className="email-modal-header">
              <div>
                <span className="email-section-kicker">Account details</span>
                <h2>{getAccountName(selectedAccount)}</h2>
                <p>{getAccountEmail(selectedAccount)}</p>
              </div>

              <button
                type="button"
                className="email-modal-close"
                onClick={() => {
                  setSelectedAccount(null);
                  setEditingLimit(false);
                }}
                aria-label="Close"
              >
                <X size={18} />
              </button>
            </div>


            {/* Detail rows */}
            <div className="account-detail-list">

              <div>
                <span>Provider</span>
                <strong>{getProvider(selectedAccount)}</strong>
              </div>

              <div>
                <span>Status</span>
                <strong
                  className={`detail-status-pill ${statusClass(getStatus(selectedAccount))}`}
                >
                  <span className="status-dot" />
                  {statusLabel(getStatus(selectedAccount))}
                </strong>
              </div>

              {/* ── Daily limit — editable ── */}
              <div className="detail-limit-row">
                <span>Daily send limit</span>

                {editingLimit ? (
                  <div className="detail-limit-edit">
                    <input
                      type="number"
                      min="1"
                      max="10000"
                      value={editLimitValue}
                      onChange={(e) => setEditLimitValue(e.target.value)}
                      className="detail-limit-input"
                      autoFocus
                      onKeyDown={(e) => {
                        if (e.key === "Enter")  handleUpdateLimit(selectedAccount);
                        if (e.key === "Escape") setEditingLimit(false);
                      }}
                    />
                    <button
                      type="button"
                      className="detail-limit-save"
                      onClick={() => handleUpdateLimit(selectedAccount)}
                      disabled={savingLimit}
                      title="Save"
                    >
                      {savingLimit ? <RefreshCw size={13} className="accounts-spinning" /> : <Save size={13} />}
                    </button>
                    <button
                      type="button"
                      className="detail-limit-cancel"
                      onClick={() => setEditingLimit(false)}
                      title="Cancel"
                    >
                      <X size={13} />
                    </button>
                  </div>
                ) : (
                  <div className="detail-limit-display">
                    <strong>{getDailyLimit(selectedAccount)} emails / day</strong>
                    <button
                      type="button"
                      className="detail-limit-edit-btn"
                      onClick={() => {
                        setEditLimitValue(String(getDailyLimit(selectedAccount)));
                        setEditingLimit(true);
                      }}
                      title="Edit daily limit"
                    >
                      <Edit2 size={13} />
                      Edit
                    </button>
                  </div>
                )}
              </div>

              <div>
                <span>Sent today</span>
                <strong>
                  {getSentToday(selectedAccount)} / {getDailyLimit(selectedAccount)}
                </strong>
              </div>

              <div>
                <span>Bounces</span>
                <strong>{getValue(selectedAccount, ["bounce_count", "bounces"], 0)}</strong>
              </div>

              <div>
                <span>Complaints</span>
                <strong>{getValue(selectedAccount, ["complaint_count", "complaints"], 0)}</strong>
              </div>

              <div>
                <span>Unsubscribes</span>
                <strong>{getValue(selectedAccount, ["unsubscribe_count", "unsubscribes"], 0)}</strong>
              </div>

              <div>
                <span>Last sent</span>
                <strong>
                  {getValue(selectedAccount, ["last_sent_at"], null)
                    ? new Date(selectedAccount.last_sent_at).toLocaleString([], {
                        dateStyle: "medium",
                        timeStyle: "short",
                      })
                    : "Not yet"}
                </strong>
              </div>

            </div>


            {/* Re-auth / reconnect banner */}
            {getStatus(selectedAccount) === "reauth_required" && (
              <div className="detail-reauth-banner">
                <AlertCircle size={15} />
                <span>
                  This account needs to be reconnected — the token has expired or
                  been revoked.
                </span>
                {getProvider(selectedAccount) === "Google" && (
                  <button
                    type="button"
                    className="detail-reconnect-btn"
                    onClick={handleReconnectGoogle}
                  >
                    <RotateCcw size={14} />
                    Reconnect Google
                  </button>
                )}
              </div>
            )}

            {/* Token expired error banner (active but failing) */}
            {getStatus(selectedAccount) === "active" &&
              getValue(selectedAccount, ["last_error"], null)?.toLowerCase().includes("token") && (
              <div className="detail-reauth-banner">
                <AlertCircle size={15} />
                <span>
                  Token expired or revoked — emails are failing. Reconnect to fix.
                </span>
                {getProvider(selectedAccount) === "Google" && (
                  <button
                    type="button"
                    className="detail-reconnect-btn"
                    onClick={handleReconnectGoogle}
                  >
                    <RotateCcw size={14} />
                    Reconnect Google
                  </button>
                )}
              </div>
            )}


            {/* Footer actions */}
            <div className="account-details-actions">

              {/* Pause / Activate */}
              {getStatus(selectedAccount) === "active" ? (
                <button
                  type="button"
                  className="detail-action-btn detail-pause-btn"
                  disabled={!!actionLoading}
                  onClick={() => {
                    handleStatusChange(selectedAccount, "paused");
                    setSelectedAccount((prev) => ({ ...prev, status: "paused" }));
                  }}
                >
                  <CirclePause size={15} />
                  Pause sending
                </button>
              ) : getStatus(selectedAccount) === "paused" ? (
                <button
                  type="button"
                  className="detail-action-btn detail-activate-btn"
                  disabled={!!actionLoading}
                  onClick={() => {
                    handleStatusChange(selectedAccount, "active");
                    setSelectedAccount((prev) => ({ ...prev, status: "active" }));
                  }}
                >
                  <CirclePlay size={15} />
                  Activate account
                </button>
              ) : null}

              {/* Disconnect */}
              <button
                type="button"
                className="detail-action-btn detail-disconnect-btn"
                disabled={disconnecting}
                onClick={() => handleDisconnect(selectedAccount)}
              >
                {disconnecting ? (
                  <RefreshCw size={15} className="accounts-spinning" />
                ) : (
                  <Link2Off size={15} />
                )}
                {disconnecting ? "Disconnecting…" : "Disconnect account"}
              </button>

            </div>


            <div className="account-details-footer">
              <ShieldCheck size={15} />
              <span>Credentials are encrypted and excluded from this view.</span>
            </div>

          </div>

        </div>
      )}

    </div>
  );
}


export default EmailAccountsPage;