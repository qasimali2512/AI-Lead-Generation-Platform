import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  ArrowLeft,
  Check,
  Clock3,
  ExternalLink,
  FileText,
  Globe,
  Image,
  Info,
  Link2,
  LoaderCircle,
  Lock,
  Mail,
  Phone as PhoneIcon,
  RefreshCw,
  Search,
  ShieldCheck,
  Smartphone,
  Sparkles,
  X,
  XCircle,
  Zap,
} from "lucide-react";
import { toast } from "react-toastify";
import { useLocation, useNavigate } from "react-router-dom";

import websiteService from "../../services/websiteService";
import leadsService from "../../services/leadsService";
import "./WebsiteScannerPage.css";

function getLeadFromLocation(location) {
  return location.state?.lead || null;
}

function getLeadIdFromLocation(location) {
  return (
    location.state?.leadId ||
    location.state?.lead?.id ||
    location.state?.lead?.lead_id ||
    null
  );
}

function normalizeScan(data) {
  if (!data) {
    return null;
  }

  if (data.scan) {
    return data.scan;
  }

  if (data.data) {
    return data.data;
  }

  return data;
}

function normalizeIssues(data) {
  if (Array.isArray(data)) {
    return data;
  }

  if (Array.isArray(data?.issues)) {
    return data.issues;
  }

  if (Array.isArray(data?.data)) {
    return data.data;
  }

  return [];
}

function getScanId(scan) {
  return (
    scan?.scan_id ||
    scan?.id ||
    null
  );
}

function getScanStatus(scan) {
  return (
    scan?.scan_status ||
    scan?.status ||
    "unknown"
  );
}

function getWebsiteUrl(scan, lead) {
  return (
    scan?.final_url ||
    scan?.url ||
    lead?.website ||
    lead?.website_url ||
    null
  );
}

function formatBytes(bytes) {
  if (!bytes || Number(bytes) <= 0) {
    return "—";
  }

  const value = Number(bytes);

  if (value < 1024) {
    return `${value} B`;
  }

  if (value < 1024 * 1024) {
    return `${(value / 1024).toFixed(1)} KB`;
  }

  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDuration(value) {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return "—";
  }

  const number = Number(value);

  if (Number.isNaN(number)) {
    return "—";
  }

  return `${number} ms`;
}

function formatDate(value) {
  if (!value) {
    return "Not available";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "Not available";
  }

  return date.toLocaleString();
}

function booleanLabel(value) {
  return value ? "Yes" : "No";
}

function getIssueSeverity(issue) {
  return (
    issue?.severity ||
    issue?.level ||
    "medium"
  )
    .toString()
    .toLowerCase();
}

function getIssueCategory(issue) {
  return (
    issue?.category ||
    issue?.issue_category ||
    "General"
  );
}

function getIssueTitle(issue) {
  return (
    issue?.title ||
    issue?.name ||
    "Website issue"
  );
}

function getIssueDescription(issue) {
  return (
    issue?.description ||
    issue?.details ||
    issue?.message ||
    "No additional details available."
  );
}

function getIssueSolution(issue) {
  return (
    issue?.recommendation ||
    issue?.solution ||
    issue?.fix ||
    "No solution suggested yet."
  );
}

function getLeadBusinessName(lead) {
  return (
    lead?.business_name ||
    lead?.name ||
    lead?.company_name ||
    "Unnamed business"
  );
}

function getLeadEmail(lead) {
  return (
    lead?.email ||
    lead?.email_address ||
    null
  );
}

function getLeadPhone(lead) {
  return (
    lead?.phone ||
    lead?.phone_number ||
    null
  );
}

function normalizeLeadRecord(data) {
  if (!data) {
    return null;
  }

  if (data.lead) {
    return data.lead;
  }

  if (data.data) {
    return data.data;
  }

  return data;
}

function isUuidLike(value) {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(
    value,
  );
}

function normalizeLeadsList(data) {
  if (Array.isArray(data)) {
    return data;
  }

  if (Array.isArray(data?.leads)) {
    return data.leads;
  }

  if (Array.isArray(data?.results)) {
    return data.results;
  }

  if (Array.isArray(data?.data)) {
    return data.data;
  }

  return [];
}

const LEAD_LOOKUP_PAGE_SIZE = 100;

function WebsiteScannerPage() {
  const navigate = useNavigate();
  const location = useLocation();

  const leadFromLocation =
    getLeadFromLocation(location);

  const leadIdFromLocation =
    getLeadIdFromLocation(location);

  const [leadId, setLeadId] = useState(
    leadIdFromLocation || "",
  );

  const [leadDisplayId, setLeadDisplayId] =
    useState(
      leadIdFromLocation || "",
    );

  const [lead, setLead] = useState(
    leadFromLocation,
  );

  const [manualLeadId, setManualLeadId] =
    useState(
      leadIdFromLocation || "",
    );

  const [scan, setScan] = useState(null);
  const [issues, setIssues] = useState([]);

  const [loading, setLoading] =
    useState(false);

  const [loadingIssues, setLoadingIssues] =
    useState(false);

  const [analyzingIssues, setAnalyzingIssues] =
    useState(false);

  const [history, setHistory] =
    useState([]);

  const [showHistory, setShowHistory] =
    useState(false);

  const [hasLoaded, setHasLoaded] =
    useState(false);

  const [scannedRows, setScannedRows] =
    useState([]);

  const upsertScannedRow = (
    targetLeadId,
    displayId,
    rowLead,
    rowScan,
    rowIssues,
  ) => {
    setScannedRows((previousRows) => {
      const remainingRows =
        previousRows.filter(
          (row) =>
            row.leadId !== targetLeadId,
        );

      return [
        {
          leadId: targetLeadId,
          displayId:
            displayId || targetLeadId,
          lead: rowLead,
          scan: rowScan,
          issues: rowIssues,
        },
        ...remainingRows,
      ];
    });
  };

  useEffect(() => {
    if (!leadIdFromLocation) {
      return;
    }

    loadLatestScan(
      leadIdFromLocation,
      true,
    );
  }, [leadIdFromLocation]);

  const loadLatestScan = async (
    targetLeadId,
    showToast = false,
  ) => {
    if (!targetLeadId) {
      return;
    }

    setLoading(true);

    try {
      const data =
        await websiteService.getLatestScan(
          targetLeadId,
        );

      const latestScan =
        normalizeScan(data);

      setScan(latestScan);
      setHasLoaded(true);

      if (showToast && latestScan) {
        toast.success(
          "Latest website scan loaded.",
        );
      }

      let latestIssues = [];

      if (latestScan) {
        latestIssues = await loadIssues(
          targetLeadId,
        );
      }

      let currentLead = lead;

      if (
        !currentLead ||
        getLeadIdFromLocation(location) !==
          targetLeadId
      ) {
        currentLead =
          await loadLeadDetails(
            targetLeadId,
          );

        if (currentLead) {
          setLead(currentLead);
        }
      }

      upsertScannedRow(
        targetLeadId,
        leadDisplayId || targetLeadId,
        currentLead,
        latestScan,
        latestIssues,
      );
    } catch (error) {
      if (
        error?.response?.status === 404
      ) {
        setScan(null);
        setHasLoaded(true);
        return;
      }

      console.error(
        "Unable to load website scan:",
        error,
      );

      const detail =
        error?.response?.data?.detail;

      toast.error(
        typeof detail === "string"
          ? detail
          : "Unable to load the website scan.",
      );
    } finally {
      setLoading(false);
    }
  };

  const loadIssues = async (
    targetLeadId,
  ) => {
    setLoadingIssues(true);

    try {
      const data =
        await websiteService.getIssues(
          targetLeadId,
        );

      const normalizedIssues =
        normalizeIssues(data);

      setIssues(normalizedIssues);

      return normalizedIssues;
    } catch (error) {
      if (
        error?.response?.status === 404
      ) {
        setIssues([]);
        return [];
      }

      console.error(
        "Unable to load website issues:",
        error,
      );

      return [];
    } finally {
      setLoadingIssues(false);
    }
  };

  const loadLeadDetails = async (
    targetLeadId,
  ) => {
    try {
      const data =
        await leadsService.getLead(
          targetLeadId,
        );

      return normalizeLeadRecord(data);
    } catch (error) {
      console.error(
        "Unable to load lead details:",
        error,
      );

      return null;
    }
  };

  const fetchAllLeadsSortedLikeLeadsPage =
    async () => {
      const firstPage =
        await leadsService.getLeads({
          page: 1,
          page_size:
            LEAD_LOOKUP_PAGE_SIZE,
        });

      let combined =
        normalizeLeadsList(firstPage);

      const total =
        firstPage?.total ??
        combined.length;

      let page = 2;

      while (
        combined.length < total &&
        page <= 10
      ) {
        const nextPage =
          await leadsService.getLeads({
            page,
            page_size:
              LEAD_LOOKUP_PAGE_SIZE,
          });

        const nextList =
          normalizeLeadsList(nextPage);

        if (nextList.length === 0) {
          break;
        }

        combined =
          combined.concat(nextList);

        page += 1;
      }

      return [...combined].sort(
        (first, second) =>
          getLeadBusinessName(
            first,
          ).localeCompare(
            getLeadBusinessName(second),
          ),
      );
    };

  const resolveLeadIdentifier = async (
    rawValue,
  ) => {
    const cleanValue = rawValue.trim();

    if (isUuidLike(cleanValue)) {
      return {
        apiLeadId: cleanValue,
        displayId: cleanValue,
      };
    }

    const position = Number(cleanValue);

    if (
      !Number.isInteger(position) ||
      position < 1
    ) {
      throw new Error(
        "Enter a valid lead number (1, 2, 3...) or a full lead ID.",
      );
    }

    const sortedLeads =
      await fetchAllLeadsSortedLikeLeadsPage();

    const match =
      sortedLeads[position - 1];

    if (!match?.id) {
      throw new Error(
        sortedLeads.length
          ? `No lead found at number ${position}. You have ${sortedLeads.length} lead(s).`
          : `No lead found at number ${position}.`,
      );
    }

    return {
      apiLeadId: match.id,
      displayId: String(position),
    };
  };

  const handleLoadLead = async (
    event,
  ) => {
    event.preventDefault();

    const rawValue =
      manualLeadId.trim();

    if (!rawValue) {
      toast.error(
        "Enter a lead number first.",
      );
      return;
    }

    setLoading(true);

    let resolved;

    try {
      resolved =
        await resolveLeadIdentifier(
          rawValue,
        );
    } catch (error) {
      console.error(
        "Unable to resolve lead number:",
        error,
      );

      toast.error(
        error?.message ||
          "Unable to find that lead.",
      );

      setLoading(false);
      return;
    }

    setLeadId(resolved.apiLeadId);
    setLeadDisplayId(resolved.displayId);
    setLead(null);
    setScan(null);
    setIssues([]);

    await runScanForLead(
      resolved.apiLeadId,
      resolved.displayId,
    );
  };

  const runScanForLead = async (
    targetLeadId,
    targetDisplayId = targetLeadId,
  ) => {
    if (!targetLeadId) {
      return;
    }

    setLoading(true);

    let fetchedLead = null;

    try {
      fetchedLead =
        await loadLeadDetails(
          targetLeadId,
        );

      setLead(fetchedLead);

      if (!fetchedLead?.website) {
        toast.error(
          "This lead does not have a website on file, so it can't be scanned.",
        );

        setScan(null);
        setIssues([]);
        setHasLoaded(true);

        upsertScannedRow(
          targetLeadId,
          targetDisplayId,
          fetchedLead,
          null,
          [],
        );

        return;
      }

      const data =
        await websiteService.scanWebsite(
          targetLeadId,
          false,
        );

      const newScan =
        normalizeScan(data);

      setScan(newScan);
      setHasLoaded(true);

      toast.success(
        "Website scanned successfully.",
      );

      const newIssues = await loadIssues(
        targetLeadId,
      );

      upsertScannedRow(
        targetLeadId,
        targetDisplayId,
        fetchedLead,
        newScan,
        newIssues,
      );
    } catch (error) {
      console.error(
        "Website scan failed:",
        error,
      );

      const detail =
        error?.response?.data?.detail;

      toast.error(
        typeof detail === "string"
          ? detail
          : "Website scan failed for this lead.",
      );

      setScan(null);
      setIssues([]);
      setHasLoaded(true);

      upsertScannedRow(
        targetLeadId,
        targetDisplayId,
        fetchedLead,
        null,
        [],
      );
    } finally {
      setLoading(false);
    }
  };

  const selectScannedRow = (row) => {
    setLeadId(row.leadId);
    setLeadDisplayId(
      row.displayId || row.leadId,
    );
    setManualLeadId(
      row.displayId || row.leadId,
    );
    setLead(row.lead);
    setScan(row.scan);
    setIssues(row.issues || []);
    setHasLoaded(true);
  };

  const handleScan = async (
    forceRescan = false,
  ) => {
    if (!leadId) {
      toast.error(
        "No lead has been selected.",
      );
      return;
    }

    if (!lead?.website) {
      toast.error(
        "This lead does not have a website on file, so it can't be scanned.",
      );
      return;
    }

    setLoading(true);

    try {
      const data =
        await websiteService.scanWebsite(
          leadId,
          forceRescan,
        );

      const newScan =
        normalizeScan(data);

      setScan(newScan);
      setHasLoaded(true);

      toast.success(
        forceRescan
          ? "Website re-scanned successfully."
          : "Website scan completed.",
      );

      await loadIssues(leadId);
    } catch (error) {
      console.error(
        "Website scan failed:",
        error,
      );

      const detail =
        error?.response?.data?.detail;

      toast.error(
        typeof detail === "string"
          ? detail
          : "Website scan failed.",
      );
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyzeIssues = async () => {
    if (!leadId) {
      toast.error(
        "No lead has been selected.",
      );
      return;
    }

    setAnalyzingIssues(true);

    try {
      const scanId =
        getScanId(scan);

      await websiteService.analyzeIssues(
        leadId,
        scanId,
      );

      await loadIssues(leadId);

      toast.success(
        "Website issues analyzed successfully.",
      );
    } catch (error) {
      console.error(
        "Issue analysis failed:",
        error,
      );

      const detail =
        error?.response?.data?.detail;

      toast.error(
        typeof detail === "string"
          ? detail
          : "Unable to analyze website issues.",
      );
    } finally {
      setAnalyzingIssues(false);
    }
  };

  const loadHistory = async () => {
    if (!leadId) {
      return;
    }

    try {
      const data =
        await websiteService.getScanHistory(
          leadId,
          10,
        );

      const historyData =
        Array.isArray(data)
          ? data
          : Array.isArray(data?.scans)
            ? data.scans
            : Array.isArray(data?.data)
              ? data.data
              : [];

      setHistory(historyData);
      setShowHistory(true);
    } catch (error) {
      console.error(
        "Unable to load scan history:",
        error,
      );

      toast.error(
        "Unable to load scan history.",
      );
    }
  };

  const websiteUrl =
    getWebsiteUrl(scan, lead);

  const scanStatus =
    getScanStatus(scan);

  const scanSuccessful =
    scanStatus === "completed" ||
    scanStatus === "success" ||
    scanStatus === "complete";

  const criticalIssues = useMemo(
    () =>
      issues.filter(
        (issue) =>
          getIssueSeverity(issue) ===
          "critical",
      ).length,
    [issues],
  );

  const highIssues = useMemo(
    () =>
      issues.filter(
        (issue) =>
          getIssueSeverity(issue) ===
          "high",
      ).length,
    [issues],
  );

  const mediumIssues = useMemo(
    () =>
      issues.filter(
        (issue) =>
          getIssueSeverity(issue) ===
          "medium",
      ).length,
    [issues],
  );

  const lowIssues = useMemo(
    () =>
      issues.filter(
        (issue) =>
          getIssueSeverity(issue) ===
          "low",
      ).length,
    [issues],
  );

  return (
    <main className="website-scanner-page">
      <div className="website-scanner-shell">

        {/* HEADER */}
        <header className="website-scanner-header">
          <div>
            <button
              type="button"
              className="website-back-button"
              onClick={() =>
                navigate("/leads")
              }
            >
              <ArrowLeft size={16} />
              Back to Leads
            </button>

            <div className="website-eyebrow">
              WEBSITE INTELLIGENCE
            </div>

            <h1>
              Website
              <span> scanner.</span>
            </h1>

            <p className="website-description">
              Scan a lead's website and inspect
              technical, SEO, mobile, performance,
              and content signals before outreach.
            </p>
          </div>

          {scan && (
            <div className="website-header-actions">
              <button
                type="button"
                className="website-secondary-button"
                onClick={loadHistory}
              >
                <Clock3 size={15} />
                Scan history
              </button>

              <button
                type="button"
                className="website-primary-button"
                onClick={() =>
                  handleScan(true)
                }
                disabled={loading}
              >
                {loading ? (
                  <LoaderCircle
                    size={16}
                    className="website-spin"
                  />
                ) : (
                  <RefreshCw size={16} />
                )}

                Re-scan
              </button>
            </div>
          )}
        </header>

        {/* LEAD SCAN INPUT */}
        <section className="website-selector-panel">
          <div className="website-selector-icon">
            <Search size={21} />
          </div>

          <div className="website-selector-content">
            <span className="website-panel-label">
              SCAN A LEAD
            </span>

            <h2>
              Enter a lead number to scan
            </h2>

            <p>
              Type a simple lead number (1, 2, 3...)
              to scan that lead's website, or paste
              a full lead ID. Every scan is added as
              a new row so you can select any of
              them afterwards.
            </p>

            <form
              className="website-lead-form"
              onSubmit={handleLoadLead}
            >
              <input
                type="text"
                value={manualLeadId}
                onChange={(event) =>
                  setManualLeadId(
                    event.target.value,
                  )
                }
                placeholder="Lead number"
              />

              <button
                type="submit"
                disabled={loading}
              >
                {loading ? (
                  <LoaderCircle
                    size={16}
                    className="website-spin"
                  />
                ) : (
                  <Search size={16} />
                )}
                Scan website
              </button>
            </form>
          </div>
        </section>

        {/* SCANNED LEADS TABLE */}
        {scannedRows.length > 0 && (
          <section className="scanned-rows-panel">
            <div className="scanned-rows-header">
              <span className="website-panel-label">
                SCAN RESULTS
              </span>

              <h2>
                Select a lead to view details
              </h2>
            </div>

            <div className="scanned-rows-table">
              <div className="scanned-rows-head">
                <span>Business</span>
                <span>Website</span>
                <span>Email</span>
                <span>Phone</span>
                <span>Issues</span>
              </div>

              <div className="scanned-rows-body">
                {scannedRows.map((row) => {
                  const rowWebsite =
                    getWebsiteUrl(
                      row.scan,
                      row.lead,
                    );

                  const rowEmail =
                    getLeadEmail(row.lead);

                  const rowPhone =
                    getLeadPhone(row.lead);

                  const rowIssueCount = (
                    row.issues || []
                  ).length;

                  const rowHasNoWebsite =
                    !rowWebsite;

                  const isActiveRow =
                    leadId === row.leadId;

                  return (
                    <button
                      type="button"
                      key={row.leadId}
                      className={`scanned-row ${
                        isActiveRow
                          ? "active"
                          : ""
                      }`}
                      onClick={() =>
                        selectScannedRow(row)
                      }
                    >
                      <span className="scanned-row-business">
                        <strong>
                          {getLeadBusinessName(
                            row.lead,
                          )}
                        </strong>
                        <span className="scanned-row-id">
                          #{row.displayId}
                        </span>
                      </span>

                      <span className="scanned-row-website">
                        {rowWebsite || "—"}
                      </span>

                      <span>
                        {rowEmail || "—"}
                      </span>

                      <span>
                        {rowPhone || "—"}
                      </span>

                      <span
                        className={`scanned-row-issues ${
                          rowHasNoWebsite
                            ? "no-issues"
                            : rowIssueCount > 0
                              ? "has-issues"
                              : "no-issues"
                        }`}
                      >
                        {rowHasNoWebsite
                          ? "—"
                          : rowIssueCount}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          </section>
        )}

        {/* LEAD / WEBSITE OVERVIEW */}
        {leadId && (
          <>
            <section className="website-overview">

              <div className="website-overview-main">
                <div className="website-main-icon">
                  <Globe size={22} />
                </div>

                <div>
                  <span className="website-panel-label">
                    LEAD #
                    {leadDisplayId ||
                      leadId}
                  </span>

                  <h2>
                    {getLeadBusinessName(lead)}
                  </h2>

                  <div className="website-url">
                    <Globe size={14} />

                    {websiteUrl ? (
                      <a
                        href={websiteUrl}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {websiteUrl}
                        <ExternalLink
                          size={12}
                        />
                      </a>
                    ) : (
                      <span>
                        Website URL will appear
                        after the scan.
                      </span>
                    )}
                  </div>

                  <div className="website-contact-row">
                    <span className="website-contact-item">
                      <Mail size={14} />
                      {getLeadEmail(lead) ||
                        "No email on file"}
                    </span>

                    <span className="website-contact-item">
                      <PhoneIcon size={14} />
                      {getLeadPhone(lead) ||
                        "No phone on file"}
                    </span>
                  </div>
                </div>
              </div>

              {!scan &&
                !loading &&
                lead &&
                !lead.website && (
                  <div className="website-no-url-state">
                    <AlertTriangle
                      size={16}
                    />
                    No website on file
                    for this lead.
                  </div>
                )}

              {!scan &&
                !loading &&
                (!lead ||
                  lead.website) && (
                  <button
                    type="button"
                    className="website-primary-button website-scan-button"
                    onClick={() =>
                      handleScan(false)
                    }
                  >
                    <Search size={17} />
                    Scan website
                  </button>
                )}

              {loading && (
                <div className="website-scanning-state">
                  <LoaderCircle
                    size={18}
                    className="website-spin"
                  />

                  <span>
                    Scanning website...
                  </span>
                </div>
              )}

            </section>

            {/* SCAN RESULTS */}
            {scan && (
              <>
                <section className="scan-status-bar">
                  <div className="scan-status-main">
                    <div
                      className={`scan-status-icon ${
                        scanSuccessful
                          ? "success"
                          : "warning"
                      }`}
                    >
                      {scanSuccessful ? (
                        <Check size={18} />
                      ) : (
                        <AlertTriangle
                          size={18}
                        />
                      )}
                    </div>

                    <div>
                      <strong>
                        {scanSuccessful
                          ? "Website scan completed"
                          : `Scan status: ${scanStatus}`}
                      </strong>

                      <span>
                        Scanned{" "}
                        {formatDate(
                          scan.scanned_at ||
                            scan.created_at,
                        )}
                      </span>
                    </div>
                  </div>

                  {scan.error && (
                    <div className="scan-error">
                      <XCircle size={15} />
                      {scan.error}
                    </div>
                  )}
                </section>

                {/* KEY METRICS */}
                <section className="scan-metrics">

                  <div className="scan-metric-card blue">
                    <div className="scan-metric-icon">
                      <Zap size={18} />
                    </div>

                    <span>
                      Response time
                    </span>

                    <strong>
                      {formatDuration(
                        scan.response_time_ms,
                      )}
                    </strong>
                  </div>

                  <div className="scan-metric-card maroon">
                    <div className="scan-metric-icon">
                      <FileText size={18} />
                    </div>

                    <span>
                      Page size
                    </span>

                    <strong>
                      {formatBytes(
                        scan.page_size_bytes,
                      )}
                    </strong>
                  </div>

                  <div className="scan-metric-card sage">
                    <div className="scan-metric-icon">
                      <Link2 size={18} />
                    </div>

                    <span>
                      Links
                    </span>

                    <strong>
                      {scan.link_count ??
                        scan.links_count ??
                        "—"}
                    </strong>
                  </div>

                  <div className="scan-metric-card indigo">
                    <div className="scan-metric-icon">
                      <Image size={18} />
                    </div>

                    <span>
                      Images
                    </span>

                    <strong>
                      {scan.image_count ??
                        scan.images_count ??
                        "—"}
                    </strong>
                  </div>

                </section>

                {/* CORE CHECKS */}
                <section className="scan-main-grid">

                  <div className="scan-panel">

                    <div className="scan-panel-header">
                      <div>
                        <span className="website-panel-label">
                          TECHNICAL CHECKS
                        </span>

                        <h2>
                          Website health
                        </h2>
                      </div>

                      <ShieldCheck
                        size={20}
                        className="scan-panel-accent"
                      />
                    </div>

                    <div className="health-check-grid">

                      <div className="health-check">
                        <div>
                          <Lock size={16} />
                          <span>
                            HTTPS
                          </span>
                        </div>

                        <strong
                          className={
                            scan.is_https
                              ? "yes"
                              : "no"
                          }
                        >
                          {booleanLabel(
                            scan.is_https,
                          )}
                        </strong>
                      </div>

                      <div className="health-check">
                        <div>
                          <Smartphone
                            size={16}
                          />
                          <span>
                            Mobile viewport
                          </span>
                        </div>

                        <strong
                          className={
                            scan.has_viewport
                              ? "yes"
                              : "no"
                          }
                        >
                          {booleanLabel(
                            scan.has_viewport,
                          )}
                        </strong>
                      </div>

                      <div className="health-check">
                        <div>
                          <Globe size={16} />
                          <span>
                            Canonical
                          </span>
                        </div>

                        <strong
                          className={
                            scan.has_canonical
                              ? "yes"
                              : "no"
                          }
                        >
                          {booleanLabel(
                            scan.has_canonical,
                          )}
                        </strong>
                      </div>

                      <div className="health-check">
                        <div>
                          <ShieldCheck
                            size={16}
                          />
                          <span>
                            Robots.txt
                          </span>
                        </div>

                        <strong
                          className={
                            scan.has_robots_txt
                              ? "yes"
                              : "no"
                          }
                        >
                          {booleanLabel(
                            scan.has_robots_txt,
                          )}
                        </strong>
                      </div>

                      <div className="health-check">
                        <div>
                          <Search size={16} />
                          <span>
                            Sitemap
                          </span>
                        </div>

                        <strong
                          className={
                            scan.has_sitemap
                              ? "yes"
                              : "no"
                          }
                        >
                          {booleanLabel(
                            scan.has_sitemap,
                          )}
                        </strong>
                      </div>

                      <div className="health-check">
                        <div>
                          <Globe size={16} />
                          <span>
                            HTTP status
                          </span>
                        </div>

                        <strong>
                          {scan.http_status ??
                            "—"}
                        </strong>
                      </div>

                    </div>
                  </div>

                  <div className="scan-panel">

                    <div className="scan-panel-header">
                      <div>
                        <span className="website-panel-label">
                          PAGE CONTENT
                        </span>

                        <h2>
                          SEO signals
                        </h2>
                      </div>

                      <Sparkles
                        size={20}
                        className="scan-panel-accent"
                      />
                    </div>

                    <div className="seo-content">

                      <div className="seo-item">
                        <span>
                          Page title
                        </span>

                        <strong>
                          {scan.title ||
                            "Not detected"}
                        </strong>
                      </div>

                      <div className="seo-item">
                        <span>
                          Meta description
                        </span>

                        <strong>
                          {scan.meta_description ||
                            "Not detected"}
                        </strong>
                      </div>

                      <div className="seo-item">
                        <span>
                          Language
                        </span>

                        <strong>
                          {scan.language ||
                            "Not detected"}
                        </strong>
                      </div>

                      <div className="seo-stats">
                        <div>
                          <span>
                            Headings
                          </span>

                          <strong>
                            {scan.heading_count ??
                              scan.headings_count ??
                              "—"}
                          </strong>
                        </div>

                        <div>
                          <span>
                            Content type
                          </span>

                          <strong>
                            {scan.content_type ||
                              "—"}
                          </strong>
                        </div>
                      </div>

                    </div>
                  </div>

                </section>

                {/* ISSUES */}
                <section className="issues-panel">

                  <div className="issues-header">
                    <div>
                      <span className="website-panel-label">
                        ISSUE ENGINE
                      </span>

                      <h2>
                        Website issues
                      </h2>

                      <p>
                        Evidence-backed issues detected
                        from the website scan.
                      </p>
                    </div>

                    <button
                      type="button"
                      className="website-primary-button"
                      onClick={
                        handleAnalyzeIssues
                      }
                      disabled={
                        analyzingIssues ||
                        loadingIssues
                      }
                    >
                      {analyzingIssues ? (
                        <LoaderCircle
                          size={16}
                          className="website-spin"
                        />
                      ) : (
                        <Sparkles size={16} />
                      )}

                      Analyze issues
                    </button>
                  </div>

                  <div className="issue-summary">

                    <div className="issue-count critical">
                      <span>
                        Critical
                      </span>

                      <strong>
                        {criticalIssues}
                      </strong>
                    </div>

                    <div className="issue-count high">
                      <span>
                        High
                      </span>

                      <strong>
                        {highIssues}
                      </strong>
                    </div>

                    <div className="issue-count medium">
                      <span>
                        Medium
                      </span>

                      <strong>
                        {mediumIssues}
                      </strong>
                    </div>

                    <div className="issue-count low">
                      <span>
                        Low
                      </span>

                      <strong>
                        {lowIssues}
                      </strong>
                    </div>

                  </div>

                  {loadingIssues ? (
                    <div className="issues-loading">
                      <LoaderCircle
                        size={20}
                        className="website-spin"
                      />

                      <span>
                        Loading website issues...
                      </span>
                    </div>
                  ) : issues.length === 0 ? (
                    <div className="issues-empty">
                      <div>
                        <Info size={21} />
                      </div>

                      <h3>
                        No analyzed issues yet
                      </h3>

                      <p>
                        Run the issue analysis to turn
                        scan signals into actionable
                        website findings.
                      </p>
                    </div>
                  ) : (
                    <div className="issues-list">
                      {issues.map(
                        (issue, index) => {
                          const severity =
                            getIssueSeverity(
                              issue,
                            );

                          return (
                            <article
                              key={
                                issue.id ||
                                `issue-${index}`
                              }
                              className="issue-card"
                            >
                              <div
                                className={`issue-severity ${severity}`}
                              >
                                {severity}
                              </div>

                              <div className="issue-content">
                                <div className="issue-card-top">
                                  <span>
                                    {getIssueCategory(
                                      issue,
                                    )}
                                  </span>

                                  <strong>
                                    {getIssueTitle(
                                      issue,
                                    )}
                                  </strong>
                                </div>

                                <p>
                                  {getIssueDescription(
                                    issue,
                                  )}
                                </p>

                                {issue.evidence && (
                                  <div className="issue-evidence">
                                    <span>
                                      Evidence
                                    </span>

                                    <p>
                                      {typeof issue.evidence ===
                                      "string"
                                        ? issue.evidence
                                        : JSON.stringify(
                                            issue.evidence,
                                          )}
                                    </p>
                                  </div>
                                )}

                                <div className="issue-recommendation">
                                  <span>
                                    Solution
                                  </span>

                                  <p>
                                    {getIssueSolution(
                                      issue,
                                    )}
                                  </p>
                                </div>
                              </div>
                            </article>
                          );
                        },
                      )}
                    </div>
                  )}

                </section>
              </>
            )}

            {/* NO SCAN */}
            {!scan &&
              !loading &&
              hasLoaded && (
                <section className="scanner-empty">
                  <div className="scanner-empty-icon">
                    <Globe size={24} />
                  </div>

                  <h2>
                    Ready to scan this website
                  </h2>

                  <p>
                    Start a website scan to collect
                    technical, SEO, mobile, and
                    performance signals.
                  </p>

                  <button
                    type="button"
                    className="website-primary-button"
                    onClick={() =>
                      handleScan(false)
                    }
                  >
                    <Search size={17} />
                    Start website scan
                  </button>
                </section>
              )}

          </>
        )}

        {/* HISTORY */}
        {showHistory && (
          <div className="history-overlay">
            <section className="history-modal">

              <div className="history-header">
                <div>
                  <span className="website-panel-label">
                    SCAN HISTORY
                  </span>

                  <h2>
                    Previous scans
                  </h2>
                </div>

                <button
                  type="button"
                  onClick={() =>
                    setShowHistory(false)
                  }
                  aria-label="Close scan history"
                >
                  <X size={18} />
                </button>
              </div>

              {history.length === 0 ? (
                <div className="history-empty">
                  <Clock3 size={20} />

                  <p>
                    No previous scans found.
                  </p>
                </div>
              ) : (
                <div className="history-list">
                  {history.map(
                    (historyItem, index) => (
                      <div
                        key={
                          historyItem.id ||
                          historyItem.scan_id ||
                          `history-${index}`
                        }
                        className="history-item"
                      >
                        <div>
                          <strong>
                            Scan{" "}
                            {history.length -
                              index}
                          </strong>

                          <span>
                            {formatDate(
                              historyItem.scanned_at ||
                                historyItem.created_at,
                            )}
                          </span>
                        </div>

                        <span
                          className={`history-status ${
                            getScanStatus(
                              historyItem,
                            ) ===
                            "completed"
                              ? "success"
                              : "neutral"
                          }`}
                        >
                          {getScanStatus(
                            historyItem,
                          )}
                        </span>
                      </div>
                    ),
                  )}
                </div>
              )}

            </section>
          </div>
        )}

      </div>
    </main>
  );
}

export default WebsiteScannerPage;