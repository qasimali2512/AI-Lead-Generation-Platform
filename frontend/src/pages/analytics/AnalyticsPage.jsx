import {
  Activity,
  AlertTriangle,
  ArrowDownLeft,
  ArrowUpRight,
  BarChart3,
  CheckCircle2,
  ChevronDown,
  Globe,
  Mail,
  MessageSquare,
  MousePointerClick,
  RefreshCw,
  Send,
  TrendingUp,
  Users,
  XCircle,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { toast } from "react-toastify";

import analyticsService from "../../services/analyticsService";
import "./AnalyticsPage.css";

function formatNumber(value) {
  return Number(value || 0).toLocaleString();
}

function formatPercent(value) {
  return `${Number(value || 0).toFixed(2)}%`;
}

function formatDate(value) {
  if (!value) {
    return "";
  }

  const date = new Date(`${value}T00:00:00`);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleDateString(undefined, {
    day: "2-digit",
    month: "short",
  });
}

function AnalyticsPage() {
  const [data, setData] = useState(null);
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  async function loadAnalytics(showRefresh = false) {
    try {
      if (showRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      const result = await analyticsService.getSummary(days);

      setData(result);
    } catch (error) {
      console.error(error);

      toast.error(
        error?.response?.data?.detail ||
          "Unable to load analytics.",
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    loadAnalytics();
  }, [days]);

  const dailyMaximum = useMemo(() => {
    if (!data?.daily?.length) {
      return 1;
    }

    return Math.max(
      1,
      ...data.daily.map((item) =>
        Math.max(
          Number(item.leads || 0),
          Number(item.emails_sent || 0),
          Number(item.replies || 0),
        ),
      ),
    );
  }, [data]);

  const topIndustries = useMemo(() => {
    if (!data?.industries) {
      return [];
    }

    return [...data.industries]
      .sort(
        (a, b) =>
          Number(b.leads || 0) -
          Number(a.leads || 0),
      )
      .slice(0, 8);
  }, [data]);

  const leadConversionRate = useMemo(() => {
    const total = Number(data?.leads?.total || 0);
    const converted = Number(
      data?.leads?.converted || 0,
    );

    if (!total) {
      return 0;
    }

    return (converted / total) * 100;
  }, [data]);

  const websiteIssueRate = useMemo(() => {
    const scans = Number(
      data?.website?.completed_scans || 0,
    );

    const issues = Number(
      data?.website?.total_issues || 0,
    );

    if (!scans) {
      return 0;
    }

    return issues / scans;
  }, [data]);

  if (loading && !data) {
    return (
      <section className="analytics-page">
        <div className="analytics-loading-screen">
          <RefreshCw
            size={25}
            className="analytics-spinner"
          />

          <span>Loading analytics...</span>
        </div>
      </section>
    );
  }

  const leads = data?.leads || {};
  const qualification = data?.qualification || {};
  const website = data?.website || {};
  const email = data?.email || {};
  const rates = data?.rates || {};

  return (
    <section className="analytics-page">
      <div className="analytics-header">
        <div>
          <span className="analytics-eyebrow">
            Performance
          </span>

          <h1>Analytics</h1>

          <p>
            Understand your lead pipeline, website
            opportunities and outreach performance.
          </p>
        </div>

        <div className="analytics-header-actions">
          <div className="analytics-period">
            <BarChart3 size={16} />

            <select
              value={days}
              onChange={(event) =>
                setDays(Number(event.target.value))
              }
            >
              <option value={7}>Last 7 days</option>
              <option value={14}>Last 14 days</option>
              <option value={30}>Last 30 days</option>
              <option value={60}>Last 60 days</option>
              <option value={90}>Last 90 days</option>
              <option value={180}>Last 180 days</option>
              <option value={365}>Last year</option>
            </select>

            <ChevronDown size={14} />
          </div>

          <button
            type="button"
            className="analytics-refresh"
            onClick={() => loadAnalytics(true)}
            disabled={refreshing}
          >
            <RefreshCw
              size={16}
              className={
                refreshing
                  ? "analytics-spinner"
                  : ""
              }
            />

            {refreshing
              ? "Refreshing..."
              : "Refresh"}
          </button>
        </div>
      </div>

      <div className="analytics-overview-grid">
        <div className="analytics-overview-card">
          <div className="analytics-card-icon analytics-icon-blue">
            <Users size={19} />
          </div>

          <div className="analytics-overview-content">
            <span>Total Leads</span>
            <strong>{formatNumber(leads.total)}</strong>
            <small>
              {formatNumber(leads.new)} new
            </small>
          </div>
        </div>

        <div className="analytics-overview-card">
          <div className="analytics-card-icon analytics-icon-sage">
            <CheckCircle2 size={19} />
          </div>

          <div className="analytics-overview-content">
            <span>Qualified</span>
            <strong>
              {formatNumber(leads.qualified)}
            </strong>
            <small>
              {formatNumber(qualification.high)} high
              priority
            </small>
          </div>
        </div>

        <div className="analytics-overview-card">
          <div className="analytics-card-icon analytics-icon-maroon">
            <Send size={19} />
          </div>

          <div className="analytics-overview-content">
            <span>Emails Sent</span>
            <strong>
              {formatNumber(email.sent)}
            </strong>
            <small>
              {formatNumber(email.total_deliveries)} deliveries
            </small>
          </div>
        </div>

        <div className="analytics-overview-card">
          <div className="analytics-card-icon analytics-icon-indigo">
            <MessageSquare size={19} />
          </div>

          <div className="analytics-overview-content">
            <span>Replies</span>
            <strong>
              {formatNumber(email.replies)}
            </strong>
            <small>
              {formatPercent(rates.reply_rate)} reply rate
            </small>
          </div>
        </div>
      </div>

      <div className="analytics-main-grid">
        <div className="analytics-panel analytics-chart-panel">
          <div className="analytics-panel-header">
            <div>
              <h2>Activity Overview</h2>
              <span>
                Leads, emails and replies by day
              </span>
            </div>

            <div className="analytics-chart-legend">
              <span>
                <i className="legend-dot legend-leads" />
                Leads
              </span>

              <span>
                <i className="legend-dot legend-emails" />
                Emails
              </span>

              <span>
                <i className="legend-dot legend-replies" />
                Replies
              </span>
            </div>
          </div>

          <div className="analytics-chart">
            {!data?.daily?.length ? (
              <div className="analytics-chart-empty">
                No activity data available for this period.
              </div>
            ) : (
              <div className="analytics-bars">
                {data.daily.map((item) => {
                  const leadsHeight =
                    (Number(item.leads || 0) /
                      dailyMaximum) *
                    100;

                  const emailsHeight =
                    (Number(item.emails_sent || 0) /
                      dailyMaximum) *
                    100;

                  const repliesHeight =
                    (Number(item.replies || 0) /
                      dailyMaximum) *
                    100;

                  return (
                    <div
                      className="analytics-day"
                      key={item.date}
                      title={`${item.date}: ${item.leads || 0} leads, ${item.emails_sent || 0} emails, ${item.replies || 0} replies`}
                    >
                      <div className="analytics-bar-area">
                        <div className="analytics-bar-group">
                          <div
                            className="analytics-bar analytics-bar-leads"
                            style={{
                              height: `${Math.max(
                                leadsHeight,
                                item.leads
                                  ? 4
                                  : 0,
                              )}%`,
                            }}
                          />

                          <div
                            className="analytics-bar analytics-bar-emails"
                            style={{
                              height: `${Math.max(
                                emailsHeight,
                                item.emails_sent
                                  ? 4
                                  : 0,
                              )}%`,
                            }}
                          />

                          <div
                            className="analytics-bar analytics-bar-replies"
                            style={{
                              height: `${Math.max(
                                repliesHeight,
                                item.replies
                                  ? 4
                                  : 0,
                              )}%`,
                            }}
                          />
                        </div>
                      </div>

                      <span>
                        {formatDate(item.date)}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        <div className="analytics-panel analytics-rates-panel">
          <div className="analytics-panel-header">
            <div>
              <h2>Outreach Rates</h2>
              <span>Email performance</span>
            </div>
          </div>

          <div className="analytics-rate-list">
            <RateRow
              label="Delivery rate"
              value={rates.delivery_rate}
              icon={CheckCircle2}
              modifier="sage"
            />

            <RateRow
              label="Open rate"
              value={rates.open_rate}
              icon={Mail}
              modifier="blue"
            />

            <RateRow
              label="Click rate"
              value={rates.click_rate}
              icon={MousePointerClick}
              modifier="indigo"
            />

            <RateRow
              label="Reply rate"
              value={rates.reply_rate}
              icon={MessageSquare}
              modifier="maroon"
            />

            <RateRow
              label="Bounce rate"
              value={rates.bounce_rate}
              icon={AlertTriangle}
              modifier="warning"
            />

            <RateRow
              label="Complaint rate"
              value={rates.complaint_rate}
              icon={XCircle}
              modifier="danger"
            />

            <RateRow
              label="Unsubscribe rate"
              value={rates.unsubscribe_rate}
              icon={ArrowDownLeft}
              modifier="muted"
            />
          </div>
        </div>
      </div>

      <div className="analytics-section-grid">
        <div className="analytics-panel">
          <div className="analytics-panel-header">
            <div>
              <h2>Lead Pipeline</h2>
              <span>
                Current lead status distribution
              </span>
            </div>
          </div>

          <div className="analytics-pipeline">
            <PipelineRow
              label="New"
              value={leads.new}
              total={leads.total}
              modifier="blue"
            />

            <PipelineRow
              label="Contacted"
              value={leads.contacted}
              total={leads.total}
              modifier="indigo"
            />

            <PipelineRow
              label="Qualified"
              value={leads.qualified}
              total={leads.total}
              modifier="sage"
            />

            <PipelineRow
              label="Converted"
              value={leads.converted}
              total={leads.total}
              modifier="maroon"
            />

            <PipelineRow
              label="Closed"
              value={leads.closed}
              total={leads.total}
              modifier="graphite"
            />
          </div>

          <div className="analytics-mini-metrics">
            <div>
              <span>Conversion</span>
              <strong>
                {formatPercent(leadConversionRate)}
              </strong>
            </div>

            <div>
              <span>With website</span>
              <strong>
                {formatNumber(leads.with_website)}
              </strong>
            </div>

            <div>
              <span>No website</span>
              <strong>
                {formatNumber(leads.without_website)}
              </strong>
            </div>

            <div>
              <span>Unreachable</span>
              <strong>
                {formatNumber(
                  leads.unreachable_website,
                )}
              </strong>
            </div>
          </div>
        </div>

        <div className="analytics-panel">
          <div className="analytics-panel-header">
            <div>
              <h2>Qualification</h2>
              <span>
                Lead quality and outreach readiness
              </span>
            </div>
          </div>

          <div className="analytics-qualification-grid">
            <MetricCard
              label="High"
              value={qualification.high}
              icon={TrendingUp}
              modifier="sage"
            />

            <MetricCard
              label="Medium"
              value={qualification.medium}
              icon={Activity}
              modifier="blue"
            />

            <MetricCard
              label="Low"
              value={qualification.low}
              icon={ArrowDownLeft}
              modifier="warning"
            />

            <MetricCard
              label="Unqualified"
              value={qualification.unqualified}
              icon={XCircle}
              modifier="muted"
            />
          </div>

          <div className="analytics-readiness">
            <div>
              <span>Ready</span>
              <strong>{formatNumber(qualification.ready)}</strong>
            </div>

            <div>
              <span>Review</span>
              <strong>{formatNumber(qualification.review)}</strong>
            </div>

            <div>
              <span>Not ready</span>
              <strong>
                {formatNumber(
                  qualification.not_ready,
                )}
              </strong>
            </div>

            <div>
              <span>Missing contact</span>
              <strong>
                {formatNumber(
                  qualification.missing_contact,
                )}
              </strong>
            </div>
          </div>
        </div>
      </div>

      <div className="analytics-section-grid">
        <div className="analytics-panel">
          <div className="analytics-panel-header">
            <div>
              <h2>Website Analysis</h2>
              <span>
                Scans and detected website issues
              </span>
            </div>

            <Globe size={19} />
          </div>

          <div className="analytics-website-summary">
            <div className="analytics-website-total">
              <span>Total scans</span>
              <strong>
                {formatNumber(website.total_scans)}
              </strong>
            </div>

            <div>
              <span>Completed</span>
              <strong>
                {formatNumber(
                  website.completed_scans,
                )}
              </strong>
            </div>

            <div>
              <span>Failed</span>
              <strong>
                {formatNumber(
                  website.failed_scans,
                )}
              </strong>
            </div>

            <div>
              <span>Issues</span>
              <strong>
                {formatNumber(
                  website.total_issues,
                )}
              </strong>
            </div>
          </div>

          <div className="analytics-issues">
            <IssueCount
              label="Critical"
              value={website.critical_issues}
              modifier="critical"
            />

            <IssueCount
              label="High"
              value={website.high_issues}
              modifier="high"
            />

            <IssueCount
              label="Medium"
              value={website.medium_issues}
              modifier="medium"
            />

            <IssueCount
              label="Low"
              value={website.low_issues}
              modifier="low"
            />
          </div>

          <div className="analytics-issue-average">
            <span>Average issues per completed scan</span>

            <strong>
              {websiteIssueRate.toFixed(1)}
            </strong>
          </div>
        </div>

        <div className="analytics-panel">
          <div className="analytics-panel-header">
            <div>
              <h2>Email Queue</h2>
              <span>
                Current outreach queue status
              </span>
            </div>

            <Send size={19} />
          </div>

          <div className="analytics-queue-grid">
            <QueueMetric
              label="Pending"
              value={email.pending}
            />

            <QueueMetric
              label="Scheduled"
              value={email.scheduled}
            />

            <QueueMetric
              label="Processing"
              value={email.processing}
            />

            <QueueMetric
              label="Sent"
              value={email.sent}
            />

            <QueueMetric
              label="Failed"
              value={email.failed}
            />

            <QueueMetric
              label="Cancelled"
              value={email.cancelled}
            />
          </div>

          <div className="analytics-delivery-summary">
            <div>
              <span>Delivered</span>
              <strong>
                {formatNumber(email.delivered)}
              </strong>
            </div>

            <div>
              <span>Opened</span>
              <strong>
                {formatNumber(email.opened)}
              </strong>
            </div>

            <div>
              <span>Clicked</span>
              <strong>
                {formatNumber(email.clicked)}
              </strong>
            </div>

            <div>
              <span>Bounced</span>
              <strong>
                {formatNumber(email.bounced)}
              </strong>
            </div>
          </div>
        </div>
      </div>

      <div className="analytics-panel analytics-industry-panel">
        <div className="analytics-panel-header">
          <div>
            <h2>Industry Performance</h2>
            <span>
              Lead distribution and website opportunity
            </span>
          </div>
        </div>

        {topIndustries.length === 0 ? (
          <div className="analytics-table-empty">
            No industry data available.
          </div>
        ) : (
          <div className="analytics-table-wrapper">
            <table className="analytics-table">
              <thead>
                <tr>
                  <th>Industry</th>
                  <th>Leads</th>
                  <th>Qualified</th>
                  <th>With website</th>
                  <th>Without website</th>
                  <th>Qualification</th>
                </tr>
              </thead>

              <tbody>
                {topIndustries.map((industry) => {
                  const leadCount = Number(
                    industry.leads || 0,
                  );

                  const qualifiedCount = Number(
                    industry.qualified || 0,
                  );

                  const qualificationRate =
                    leadCount > 0
                      ? (qualifiedCount /
                          leadCount) *
                        100
                      : 0;

                  return (
                    <tr key={industry.industry}>
                      <td>
                        <strong>
                          {industry.industry}
                        </strong>
                      </td>

                      <td>
                        {formatNumber(leadCount)}
                      </td>

                      <td>
                        {formatNumber(
                          qualifiedCount,
                        )}
                      </td>

                      <td>
                        {formatNumber(
                          industry.with_website,
                        )}
                      </td>

                      <td>
                        {formatNumber(
                          industry.without_website,
                        )}
                      </td>

                      <td>
                        <div className="analytics-table-rate">
                          <div>
                            <span
                              style={{
                                width: `${Math.min(
                                  100,
                                  qualificationRate,
                                )}%`,
                              }}
                            />
                          </div>

                          <strong>
                            {formatPercent(
                              qualificationRate,
                            )}
                          </strong>
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

      <div className="analytics-footer">
        <span>
          Analytics period: {days} days
        </span>

        {data?.generated_at && (
          <span>
            Generated{" "}
            {new Date(
              data.generated_at,
            ).toLocaleString()}
          </span>
        )}
      </div>
    </section>
  );
}

function RateRow({
  label,
  value,
  icon: Icon,
  modifier,
}) {
  return (
    <div className="analytics-rate-row">
      <div className={`analytics-rate-icon ${modifier}`}>
        <Icon size={15} />
      </div>

      <div className="analytics-rate-info">
        <div>
          <span>{label}</span>
          <strong>
            {formatPercent(value)}
          </strong>
        </div>

        <div className="analytics-rate-track">
          <span
            className={modifier}
            style={{
              width: `${Math.min(
                100,
                Math.max(0, Number(value || 0)),
              )}%`,
            }}
          />
        </div>
      </div>
    </div>
  );
}

function PipelineRow({
  label,
  value,
  total,
  modifier,
}) {
  const percentage =
    Number(total || 0) > 0
      ? (Number(value || 0) / Number(total)) * 100
      : 0;

  return (
    <div className="analytics-pipeline-row">
      <div className="analytics-pipeline-label">
        <span>{label}</span>
        <strong>
          {formatNumber(value)}
        </strong>
      </div>

      <div className="analytics-pipeline-track">
        <span
          className={modifier}
          style={{
            width: `${Math.min(
              100,
              Math.max(0, percentage),
            )}%`,
          }}
        />
      </div>
    </div>
  );
}

function MetricCard({
  label,
  value,
  icon: Icon,
  modifier,
}) {
  return (
    <div className="analytics-metric-card">
      <div className={`analytics-metric-icon ${modifier}`}>
        <Icon size={16} />
      </div>

      <span>{label}</span>

      <strong>{formatNumber(value)}</strong>
    </div>
  );
}

function IssueCount({
  label,
  value,
  modifier,
}) {
  return (
    <div className="analytics-issue-count">
      <div className={`analytics-issue-dot ${modifier}`} />

      <span>{label}</span>

      <strong>
        {formatNumber(value)}
      </strong>
    </div>
  );
}

function QueueMetric({ label, value }) {
  return (
    <div className="analytics-queue-metric">
      <span>{label}</span>

      <strong>
        {formatNumber(value)}
      </strong>
    </div>
  );
}

export default AnalyticsPage;