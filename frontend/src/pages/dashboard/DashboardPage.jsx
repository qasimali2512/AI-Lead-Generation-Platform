import {
  Activity,
  ArrowUpRight,
  BarChart3,
  Building2,
  ChevronRight,
  Globe2,
  Mail,
  RefreshCw,
  Search,
  Send,
  Sparkles,
  Target,
  TrendingUp,
  Users,
  Wifi,
  WifiOff,
} from "lucide-react";

import { useRealtimeDashboard } from "../../hooks/useRealtimeDashboard";
import "./DashboardPage.css";

// ---------------------------------------------------------------------------
// Number formatters
// ---------------------------------------------------------------------------

function fmt(n) {
  if (n === null || n === undefined) return "—";
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return String(n);
}

function pct(n) {
  if (!n) return "0%";
  return `${Number(n).toFixed(1)}%`;
}

// ---------------------------------------------------------------------------
// Activity row helpers
// ---------------------------------------------------------------------------

function buildActivity(data) {
  if (!data) return [];

  const items = [];
  const leads  = data.leads?.total              ?? 0;
  const scans  = data.website?.completed_scans  ?? 0;
  const queued = data.email?.total_queued        ?? 0;
  const sent   = data.email?.sent               ?? 0;
  const issues = data.website?.total_issues     ?? 0;
  const opps   = data.qualification?.total      ?? 0;

  if (leads  > 0) items.push({ icon: Users,    color: "maroon", label: "Total leads discovered",  value: fmt(leads)  });
  if (scans  > 0) items.push({ icon: Globe2,   color: "blue",   label: "Website scans completed", value: fmt(scans)  });
  if (issues > 0) items.push({ icon: Target,   color: "sage",   label: "Website issues detected", value: fmt(issues) });
  if (opps   > 0) items.push({ icon: Sparkles, color: "indigo", label: "Leads qualified",          value: fmt(opps)   });
  if (queued > 0) items.push({ icon: Mail,     color: "blue",   label: "Emails in queue",          value: fmt(queued) });
  if (sent   > 0) items.push({ icon: Send,     color: "sage",   label: "Emails sent",              value: fmt(sent)   });

  return items;
}

// ---------------------------------------------------------------------------
// LiveBadge — SSE connected indicator
// ---------------------------------------------------------------------------

function LiveBadge({ isLive }) {
  return (
    <span className={`db-live-badge ${isLive ? "db-live-badge--on" : "db-live-badge--off"}`}>
      {isLive ? (
        <>
          <span className="db-live-dot" />
          <Wifi size={11} />
          Live
        </>
      ) : (
        <>
          <WifiOff size={11} />
          Polling
        </>
      )}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

function DashboardPage() {
  // Real-time hook — SSE primary, polling fallback
  const { data, loading, error, lastUpdated, isLive, refresh } =
    useRealtimeDashboard(30);

  // -------------------------------------------------------------------------
  // Derived values
  // -------------------------------------------------------------------------

  const leads      = data?.leads         ?? {};
  const website    = data?.website       ?? {};
  const email      = data?.email         ?? {};
  const rates      = data?.rates         ?? {};
  const industries = data?.industries    ?? [];
  const qualify    = data?.qualification ?? {};

  const stats = [
    {
      label:  "Total leads",
      value:  loading ? "—" : fmt(leads.total ?? 0),
      change: leads.total
        ? `${fmt(leads.new ?? 0)} new · ${fmt(leads.contacted ?? 0)} contacted`
        : "Ready to discover",
      icon: Users,
      tone: "maroon",
      href: "/leads",
    },
    {
      label:  "Websites scanned",
      value:  loading ? "—" : fmt(website.completed_scans ?? 0),
      change: website.total_issues
        ? `${fmt(website.total_issues)} issues found`
        : "No scans yet",
      icon: Globe2,
      tone: "blue",
      href: "/websites/scanner",
    },
    {
      label:  "Leads qualified",
      value:  loading ? "—" : fmt(qualify.total ?? 0),
      change: qualify.total
        ? `${fmt(qualify.high ?? 0)} high · ${fmt(qualify.medium ?? 0)} medium`
        : "Awaiting qualification",
      icon: Target,
      tone: "sage",
      href: "/leads",
    },
    {
      label:  "Emails sent",
      value:  loading ? "—" : fmt(email.sent ?? 0),
      change: email.sent
        ? `${fmt(email.scheduled ?? 0)} scheduled · ${pct(rates.open_rate)} opened`
        : "No emails sent yet",
      icon: Send,
      tone: "indigo",
      href: "/queue",
    },
  ];

  const quickActions = [
    {
      title:       "Discover leads",
      description: "Find businesses by location and industry.",
      icon:  Search,
      path:  "/leads/discover",
      tone:  "maroon",
    },
    {
      title:       "Analyze websites",
      description: "Identify real SEO, UX and performance issues.",
      icon:  Globe2,
      path:  "/websites/scanner",
      tone:  "blue",
    },
    {
      title:       "Create outreach",
      description: "Generate personalized business emails.",
      icon:  Mail,
      path:  "/email/editor",
      tone:  "sage",
    },
  ];

  const activityItems  = buildActivity(data);
  const topIndustries  = industries.slice(0, 5);

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------

  return (
    <main className="dashboard-page">
      <div className="dashboard-shell">

        {/* HEADER */}
        <header className="dashboard-header">
          <div>
            <p className="dashboard-eyebrow">AI lead generation</p>
            <h1>
              Your pipeline,
              <span> at a glance.</span>
            </h1>
            <p className="dashboard-description">
              Discover businesses, understand their digital presence, and turn
              real findings into personalized outreach.
            </p>
          </div>

          <div style={{ display: "flex", gap: 10, alignItems: "center", flexShrink: 0 }}>

            {/* Live / Polling badge */}
            <LiveBadge isLive={isLive} />

            {/* Last updated timestamp */}
            {lastUpdated && (
              <span style={{ fontSize: 11, color: "var(--color-muted)", whiteSpace: "nowrap" }}>
                Updated {lastUpdated.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
              </span>
            )}

            {/* Error notice */}
            {error && (
              <span style={{ fontSize: 11, color: "var(--color-maroon)", whiteSpace: "nowrap" }}>
                ⚠ {error}
              </span>
            )}

            {/* Manual refresh button */}
            <button
              type="button"
              className="dashboard-primary-action"
              style={{
                background:  "var(--color-ivory-deep)",
                color:       "var(--color-graphite)",
                border:      "1px solid var(--border-light)",
                boxShadow:   "none",
              }}
              onClick={refresh}
              disabled={loading}
              title="Refresh dashboard"
            >
              <RefreshCw size={15} className={loading ? "dashboard-spin" : ""} />
              {loading ? "Loading..." : "Refresh"}
            </button>

            <button
              type="button"
              className="dashboard-primary-action"
              onClick={() => (window.location.href = "/leads/discover")}
            >
              <Search size={17} />
              Discover leads
              <ArrowUpRight size={16} />
            </button>
          </div>
        </header>

        {/* STATS */}
        <section className="dashboard-stats">
          {stats.map((stat, index) => {
            const Icon = stat.icon;
            return (
              <a
                href={stat.href}
                className={`dashboard-stat-card ${stat.tone}`}
                key={stat.label}
                style={{ animationDelay: `${index * 70}ms`, textDecoration: "none" }}
              >
                <div className="dashboard-stat-top">
                  <span>{stat.label}</span>
                  <div className="dashboard-stat-icon">
                    <Icon size={18} />
                  </div>
                </div>

                <strong>
                  {loading ? (
                    <span
                      className="dashboard-skeleton"
                      style={{ width: 60, height: 32, display: "inline-block", borderRadius: 6 }}
                    />
                  ) : (
                    stat.value
                  )}
                </strong>

                <div className="dashboard-stat-bottom">
                  <span>{stat.change}</span>
                  <TrendingUp size={14} />
                </div>
              </a>
            );
          })}
        </section>

        {/* MAIN GRID */}
        <section className="dashboard-main-grid">

          {/* Quick actions */}
          <div className="dashboard-panel quick-actions-panel">
            <div className="dashboard-panel-header">
              <div>
                <p className="dashboard-panel-label">Start here</p>
                <h2>Build your pipeline</h2>
              </div>
              <Sparkles size={19} className="dashboard-panel-accent" />
            </div>

            <div className="quick-actions">
              {quickActions.map((action, index) => {
                const Icon = action.icon;
                return (
                  <a
                    href={action.path}
                    className={`quick-action ${action.tone}`}
                    key={action.title}
                    style={{ animationDelay: `${index * 90}ms` }}
                  >
                    <div className="quick-action-icon">
                      <Icon size={19} />
                    </div>
                    <div className="quick-action-content">
                      <h3>{action.title}</h3>
                      <p>{action.description}</p>
                    </div>
                    <ChevronRight size={17} className="quick-action-arrow" />
                  </a>
                );
              })}
            </div>

            {/* Email metrics row */}
            {(email.sent > 0 || email.total_queued > 0) && (
              <div className="db-metrics-row">
                <div className="db-metric">
                  <span>Queued</span>
                  <strong>{fmt(email.total_queued)}</strong>
                </div>
                <div className="db-metric">
                  <span>Sent</span>
                  <strong>{fmt(email.sent)}</strong>
                </div>
                <div className="db-metric">
                  <span>Scheduled</span>
                  <strong>{fmt(email.scheduled)}</strong>
                </div>
                <div className="db-metric">
                  <span>Failed</span>
                  <strong>{fmt(email.failed)}</strong>
                </div>
                <div className="db-metric">
                  <span>Open rate</span>
                  <strong>{pct(rates.open_rate)}</strong>
                </div>
                <div className="db-metric">
                  <span>Reply rate</span>
                  <strong>{pct(rates.reply_rate)}</strong>
                </div>
              </div>
            )}
          </div>

          {/* Activity / Industry */}
          <div className="dashboard-panel activity-panel">
            <div className="dashboard-panel-header">
              <div>
                <p className="dashboard-panel-label">Workspace</p>
                <h2>Overview</h2>
              </div>
              <Activity size={19} className="dashboard-panel-accent" />
            </div>

            {loading ? (
              <div className="dashboard-empty">
                <RefreshCw
                  size={22}
                  className="dashboard-spin"
                  style={{ color: "var(--color-blue)", marginBottom: 12 }}
                />
                <h3>Loading stats…</h3>
              </div>
            ) : activityItems.length === 0 ? (
              <div className="dashboard-empty">
                <div className="dashboard-empty-icon">
                  <BarChart3 size={22} />
                </div>
                <h3>Your activity will appear here</h3>
                <p>
                  Once you discover businesses and analyze websites, your
                  latest activity will be shown here.
                </p>
              </div>
            ) : (
              <div className="db-activity-list">
                {activityItems.map((item, i) => {
                  const Icon = item.icon;
                  return (
                    <div key={i} className="db-activity-item">
                      <div className={`db-activity-icon db-icon-${item.color}`}>
                        <Icon size={14} />
                      </div>
                      <span className="db-activity-label">{item.label}</span>
                      <strong className="db-activity-value">{item.value}</strong>
                    </div>
                  );
                })}

                {/* Top industries */}
                {topIndustries.length > 0 && (
                  <>
                    <div className="db-divider" />
                    <p className="db-section-label">Top industries</p>
                    {topIndustries.map((ind) => (
                      <div key={ind.industry} className="db-industry-row">
                        <span className="db-industry-name">
                          {ind.industry.charAt(0).toUpperCase() +
                            ind.industry.slice(1)}
                        </span>
                        <div className="db-industry-bar-wrap">
                          <div
                            className="db-industry-bar"
                            style={{
                              width: `${Math.round(
                                (ind.leads / (topIndustries[0]?.leads || 1)) * 100,
                              )}%`,
                            }}
                          />
                        </div>
                        <strong className="db-industry-count">
                          {fmt(ind.leads)}
                        </strong>
                      </div>
                    ))}
                  </>
                )}
              </div>
            )}
          </div>
        </section>

        {/* PIPELINE */}
        <section className="dashboard-panel pipeline-panel">
          <div className="dashboard-panel-header">
            <div>
              <p className="dashboard-panel-label">Lead pipeline</p>
              <h2>From discovery to outreach</h2>
            </div>
            <Building2 size={19} className="dashboard-panel-accent" />
          </div>

          <div className="pipeline">
            {[
              {
                n: "01", title: "Discover",
                desc: "Find businesses in your target market.",
                val: leads.total ?? 0,
              },
              {
                n: "02", title: "Analyze",
                desc: "Inspect websites and digital presence.",
                val: website.completed_scans ?? 0,
              },
              {
                n: "03", title: "Qualify",
                desc: "Prioritize opportunities using evidence.",
                val: qualify.total ?? 0,
              },
              {
                n: "04", title: "Outreach",
                desc: "Generate relevant personalized emails.",
                val: email.sent ?? 0,
              },
            ].map((step, i, arr) => (
              <>
                <div className="pipeline-step" key={step.n}>
                  <span>{step.n}</span>
                  <div>
                    <strong>{step.title}</strong>
                    <p>{step.desc}</p>
                    {!loading && step.val > 0 && (
                      <span className="pipeline-count">{fmt(step.val)}</span>
                    )}
                  </div>
                </div>
                {i < arr.length - 1 && (
                  <div className="pipeline-connector" key={`c${i}`} />
                )}
              </>
            ))}
          </div>
        </section>

      </div>
    </main>
  );
}

export default DashboardPage;
