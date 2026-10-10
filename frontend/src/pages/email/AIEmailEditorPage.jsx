import {
  ArrowLeft,
  Check,
  Clipboard,
  Copy,
  Mail,
  RefreshCw,
  Save,
  Search,
  Send,
  Sparkles,
  UserRound,
  X,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "react-toastify";
import { useSearchParams } from "react-router-dom";

import aiEmailService from "../../services/aiEmailService";
import emailAccountService from "../../services/emailAccountService";
import leadsService from "../../services/leadsService";
import "./AIEmailEditorPage.css";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getValue(object, keys, fallback = "") {
  for (const key of keys) {
    if (
      object?.[key] !== undefined &&
      object?.[key] !== null &&
      object?.[key] !== ""
    ) {
      return object[key];
    }
  }

  return fallback;
}

function normalizeGeneratedEmail(response) {
  const source =
    response?.draft ||
    response?.email ||
    response?.data ||
    response ||
    {};

  return {
    id: getValue(source, ["id", "draft_id"], null),
    subject: getValue(source, ["subject", "email_subject"], ""),
    body: getValue(source, ["body_text", "body", "email_body"], ""),
    emailType: getValue(source, ["email_type", "type"], "initial_outreach"),
    personalizationPoints:
      getValue(source, ["personalization_points", "personalization"], []) || [],
    sourceEvidence:
      getValue(source, ["source_evidence", "evidence"], []) || [],
    callToAction: getValue(source, ["call_to_action", "cta"], ""),
  };
}

function normalizeLead(response) {
  if (response?.lead) return response.lead;
  if (response?.data?.lead) return response.data.lead;
  if (response?.data) return response.data;
  return response;
}

function normalizeAccounts(response) {
  if (Array.isArray(response)) return response;
  if (Array.isArray(response?.items)) return response.items;
  if (Array.isArray(response?.accounts)) return response.accounts;
  if (Array.isArray(response?.data)) return response.data;
  return [];
}

function normalizeLeadsList(response) {
  if (Array.isArray(response)) return response;
  if (Array.isArray(response?.leads)) return response.leads;
  if (Array.isArray(response?.data)) return response.data;
  return [];
}

// ---------------------------------------------------------------------------
// Lead picker modal
// ---------------------------------------------------------------------------

function LeadPickerModal({ onSelect, onClose }) {
  const [search, setSearch] = useState("");
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const inputRef = useRef(null);

  useEffect(() => {
    inputRef.current?.focus();

    const load = async () => {
      try {
        // Load leads that have an email (email filter)
        const data = await leadsService.getLeads({
          page_size: 100,
        });

        const all = normalizeLeadsList(data);

        // Prioritize leads with email
        const withEmail = all.filter((l) => l.email);
        const withoutEmail = all.filter((l) => !l.email);

        setLeads([...withEmail, ...withoutEmail]);
      } catch (err) {
        console.error("Unable to load leads:", err);
        toast.error("Unable to load leads.");
      } finally {
        setLoading(false);
      }
    };

    load();
  }, []);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return leads;

    return leads.filter((l) => {
      const name = (l.name || l.business_name || "").toLowerCase();
      const industry = (l.industry || "").toLowerCase();
      const city = (l.city || "").toLowerCase();
      const email = (l.email || "").toLowerCase();
      return (
        name.includes(q) ||
        industry.includes(q) ||
        city.includes(q) ||
        email.includes(q)
      );
    });
  }, [leads, search]);

  return (
    <div
      className="lead-picker-backdrop"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="lead-picker-modal">
        <div className="lead-picker-header">
          <h3>Select a lead</h3>
          <button type="button" onClick={onClose} aria-label="Close">
            <X size={18} />
          </button>
        </div>

        <div className="lead-picker-search">
          <Search size={16} />
          <input
            ref={inputRef}
            type="text"
            placeholder="Search by name, industry, city or email..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          {search && (
            <button type="button" onClick={() => setSearch("")} aria-label="Clear">
              <X size={14} />
            </button>
          )}
        </div>

        <div className="lead-picker-list">
          {loading ? (
            <div className="lead-picker-empty">Loading leads...</div>
          ) : filtered.length === 0 ? (
            <div className="lead-picker-empty">No leads found.</div>
          ) : (
            filtered.map((lead) => {
              const name = lead.name || lead.business_name || "Unnamed";
              const email = lead.email || "";
              const city = lead.city || "";
              const industry = lead.industry || "";
              const hasEmail = Boolean(email);

              return (
                <button
                  key={lead.id}
                  type="button"
                  className={`lead-picker-item ${!hasEmail ? "lead-picker-item-no-email" : ""}`}
                  onClick={() => {
                    if (!hasEmail) {
                      toast.warning(
                        `${name} has no email address — email can't be sent.`,
                      );
                    }
                    onSelect(lead);
                    onClose();
                  }}
                >
                  <div className="lead-picker-avatar">
                    {name.charAt(0).toUpperCase()}
                  </div>
                  <div className="lead-picker-info">
                    <strong>{name}</strong>
                    <span>
                      {[industry, city].filter(Boolean).join(" · ")}
                    </span>
                    {email ? (
                      <span className="lead-picker-email">{email}</span>
                    ) : (
                      <span className="lead-picker-no-email">No email</span>
                    )}
                  </div>
                </button>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

function AIEmailEditorPage() {
  const [searchParams] = useSearchParams();

  const initialLeadId = searchParams.get("lead_id");
  const initialDraftId = searchParams.get("draft_id");

  // Lead
  const [lead, setLead] = useState(null);
  const [selectedLeadId, setSelectedLeadId] = useState(initialLeadId || "");
  const [showLeadPicker, setShowLeadPicker] = useState(false);
  const [loadingLead, setLoadingLead] = useState(Boolean(initialLeadId));

  // Email accounts
  const [accounts, setAccounts] = useState([]);
  const [selectedAccountId, setSelectedAccountId] = useState("");
  const [loadingAccounts, setLoadingAccounts] = useState(true);

  // Generation settings
  const [emailType, setEmailType] = useState("initial_outreach");
  const [tone, setTone] = useState("professional");
  const [length, setLength] = useState("concise");

  // Draft content
  const [currentDraftId, setCurrentDraftId] = useState(initialDraftId || null);
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [personalizationPoints, setPersonalizationPoints] = useState([]);
  const [sourceEvidence, setSourceEvidence] = useState([]);
  const [callToAction, setCallToAction] = useState("");

  // UI states
  const [generating, setGenerating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [sending, setSending] = useState(false);
  const [saved, setSaved] = useState(false);
  const [scheduledAt, setScheduledAt] = useState(""); // ISO datetime-local string
  const [copiedSubject, setCopiedSubject] = useState(false);
  const [copiedBody, setCopiedBody] = useState(false);

  // -------------------------------------------------------------------------
  // Load connected email accounts on mount
  // -------------------------------------------------------------------------

  useEffect(() => {
    const loadAccounts = async () => {
      try {
        const data = await emailAccountService.getAccounts();
        const list = normalizeAccounts(data).filter(
          (a) => a.status === "active",
        );
        setAccounts(list);

        if (list.length > 0 && !selectedAccountId) {
          setSelectedAccountId(list[0].id);
        }
      } catch (err) {
        console.error("Unable to load email accounts:", err);
      } finally {
        setLoadingAccounts(false);
      }
    };

    loadAccounts();
  }, []);

  // -------------------------------------------------------------------------
  // Load lead if lead_id in URL
  // -------------------------------------------------------------------------

  useEffect(() => {
    if (!initialLeadId) {
      setLoadingLead(false);
      return;
    }

    const load = async () => {
      try {
        setLoadingLead(true);
        const response = await leadsService.getLead(initialLeadId);
        const normalized = normalizeLead(response);
        setLead(normalized);
        setSelectedLeadId(initialLeadId);
      } catch (err) {
        console.error("Unable to load lead:", err);
        toast.error("Unable to load the selected lead.");
      } finally {
        setLoadingLead(false);
      }
    };

    load();
  }, [initialLeadId]);

  // -------------------------------------------------------------------------
  // Load existing draft if draft_id in URL
  // -------------------------------------------------------------------------

  useEffect(() => {
    if (!initialDraftId) return;

    const load = async () => {
      try {
        const response = await aiEmailService.getDraft(initialDraftId);
        const email = normalizeGeneratedEmail(response);

        setCurrentDraftId(initialDraftId);
        setSubject(email.subject);
        setBody(email.body);
        setEmailType(email.emailType);
        setPersonalizationPoints(
          Array.isArray(email.personalizationPoints)
            ? email.personalizationPoints
            : [],
        );
        setSourceEvidence(
          Array.isArray(email.sourceEvidence) ? email.sourceEvidence : [],
        );
        setCallToAction(email.callToAction);
        setSaved(true);
      } catch (err) {
        console.error("Unable to load draft:", err);
        toast.error("Unable to load this email draft.");
      }
    };

    load();
  }, [initialDraftId]);

  // -------------------------------------------------------------------------
  // Lead picker selection
  // -------------------------------------------------------------------------

  const handleLeadSelect = (selectedLead) => {
    setLead(selectedLead);
    setSelectedLeadId(selectedLead.id);
    // Reset draft when lead changes
    setCurrentDraftId(null);
    setSubject("");
    setBody("");
    setPersonalizationPoints([]);
    setSourceEvidence([]);
    setCallToAction("");
    setSaved(false);
  };

  // -------------------------------------------------------------------------
  // Derived lead values
  // -------------------------------------------------------------------------

  const leadName = useMemo(
    () =>
      getValue(lead, ["business_name", "company_name", "name"], "Selected business"),
    [lead],
  );
  const leadEmail = useMemo(
    () => getValue(lead, ["email", "contact_email"], ""),
    [lead],
  );
  const leadIndustry = useMemo(
    () => getValue(lead, ["industry", "business_type", "category"], ""),
    [lead],
  );
  const leadCity = useMemo(
    () => getValue(lead, ["city", "location"], ""),
    [lead],
  );

  // -------------------------------------------------------------------------
  // Generate email
  // -------------------------------------------------------------------------

  // Map frontend values to backend-accepted email types
  const EMAIL_TYPE_MAP = {
    initial_outreach: "initial_outreach",
    follow_up: "follow_up",
    website_opportunity: "website_offer",
    seo_audit: "seo_offer",
    general_business_outreach: "general_business_outreach",
  };

  const generateEmail = async () => {
    if (!selectedLeadId) {
      toast.error("Select a lead before generating an email.");
      return;
    }

    try {
      setGenerating(true);
      setSaved(false);

      const response = await aiEmailService.generateEmail(selectedLeadId, {
        email_type: EMAIL_TYPE_MAP[emailType] || emailType,
        tone,
        length,
      });

      const email = normalizeGeneratedEmail(response);

      // Store the draft ID returned by the backend for later save/send
      if (email.id) {
        setCurrentDraftId(email.id);
      }

      setSubject(email.subject);
      setBody(email.body);
      setPersonalizationPoints(
        Array.isArray(email.personalizationPoints)
          ? email.personalizationPoints
          : [],
      );
      setSourceEvidence(
        Array.isArray(email.sourceEvidence) ? email.sourceEvidence : [],
      );
      setCallToAction(email.callToAction);

      toast.success("Personalized email generated.");
    } catch (err) {
      console.error("Unable to generate AI email:", err);
      const timedOut =
        err?.code === "ECONNABORTED" || err?.code === "ERR_CANCELED";
      toast.error(
        err?.response?.data?.detail ||
          (timedOut
            ? "AI is taking too long to respond. Please try again."
            : "Unable to generate the email."),
      );
    } finally {
      setGenerating(false);
    }
  };

  // -------------------------------------------------------------------------
  // Save draft
  // -------------------------------------------------------------------------

  const saveDraft = async () => {
    if (!subject.trim() && !body.trim()) {
      toast.error("Add a subject or email body before saving.");
      return;
    }

    if (!currentDraftId) {
      toast.info("Generate an email first, then save the draft.");
      return;
    }

    try {
      setSaving(true);

      await aiEmailService.updateDraft(currentDraftId, {
        subject,
        body_text: body,
        status: "draft",
      });

      setSaved(true);
      toast.success("Draft saved.");
    } catch (err) {
      console.error("Unable to save email draft:", err);
      toast.error(err?.response?.data?.detail || "Unable to save the draft.");
    } finally {
      setSaving(false);
    }
  };

  // -------------------------------------------------------------------------
  // Send email
  // -------------------------------------------------------------------------

  const sendEmail = async () => {
    if (!selectedLeadId) {
      toast.error("Select a lead first.");
      return;
    }

    if (!leadEmail) {
      toast.error("This lead has no email address on file.");
      return;
    }

    if (!currentDraftId) {
      toast.error("Generate an email first before sending.");
      return;
    }

    if (!selectedAccountId) {
      toast.error("Select a sending account before sending.");
      return;
    }

    if (!subject.trim() || !body.trim()) {
      toast.error("Subject and body cannot be empty.");
      return;
    }

    try {
      setSending(true);

      // Step 1 — Save latest edits and mark approved
      await aiEmailService.updateDraft(currentDraftId, {
        subject,
        body_text: body,
        status: "approved",
      });

      // Step 2 — Queue for sending (retry once on network error)
      const queuePayload = {
        draft_id: currentDraftId,
        email_account_id: selectedAccountId,
        queue_type: "initial",
        priority: 100,
        ...(scheduledAt
          ? { scheduled_at: new Date(scheduledAt).toISOString() }
          : {}),
      };

      let queued = false;
      let lastErr = null;

      for (let attempt = 0; attempt < 2; attempt++) {
        try {
          await aiEmailService.queueEmail(queuePayload);
          queued = true;
          break;
        } catch (err) {
          lastErr = err;
          // Only retry on network/timeout errors, not 4xx
          const isNetErr =
            !err?.response ||
            err?.code === "ECONNABORTED" ||
            err?.code === "ERR_NETWORK";
          if (!isNetErr) break;
          // Wait 1.2s before retry
          await new Promise((r) => setTimeout(r, 1200));
        }
      }

      if (!queued) throw lastErr;

      setSaved(true);

      if (scheduledAt) {
        const formatted = new Date(scheduledAt).toLocaleString(undefined, {
          dateStyle: "medium",
          timeStyle: "short",
        });
        toast.success(`Email scheduled for ${formatted}.`);
      } else {
        toast.success(`Email queued to send to ${leadEmail}.`);
      }
    } catch (err) {
      console.error("Unable to send email:", err);
      const detail = err?.response?.data?.detail;
      const isNet =
        !err?.response ||
        err?.code === "ECONNABORTED" ||
        err?.code === "ERR_NETWORK";
      toast.error(
        detail ||
          (isNet
            ? "Network error — please try again."
            : "Unable to queue the email."),
      );
    } finally {
      setSending(false);
    }
  };

  // -------------------------------------------------------------------------
  // Copy helpers
  // -------------------------------------------------------------------------

  const copyText = async (text, type) => {
    if (!text) {
      toast.info("Nothing to copy.");
      return;
    }

    try {
      await navigator.clipboard.writeText(text);

      if (type === "subject") {
        setCopiedSubject(true);
        setTimeout(() => setCopiedSubject(false), 1500);
      } else {
        setCopiedBody(true);
        setTimeout(() => setCopiedBody(false), 1500);
      }

      toast.success(type === "subject" ? "Subject copied." : "Email body copied.");
    } catch {
      toast.error("Clipboard access was not available.");
    }
  };

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------

  const canGenerate = Boolean(selectedLeadId) && !generating && !loadingLead;
  const canSend =
    Boolean(currentDraftId) &&
    Boolean(selectedAccountId) &&
    Boolean(leadEmail) &&
    subject.trim().length > 0 &&
    body.trim().length > 0 &&
    !sending;

  return (
    <div className="ai-email-page">
      {/* Lead picker modal */}
      {showLeadPicker && (
        <LeadPickerModal
          onSelect={handleLeadSelect}
          onClose={() => setShowLeadPicker(false)}
        />
      )}

      {/* Header */}
      <header className="ai-email-header">
        <div className="ai-email-heading">
          <a href="/leads" className="ai-email-back">
            <ArrowLeft size={17} />
            Back to leads
          </a>

          <div className="ai-email-title-row">
            <div className="ai-email-title-icon">
              <Sparkles size={22} />
            </div>

            <div>
              <div className="ai-email-kicker">AI Outreach</div>
              <h1>AI Email Editor</h1>
              <p>
                Select a lead, choose settings, generate a personalized email,
                then send directly from a connected account.
              </p>
            </div>
          </div>
        </div>

        <div className="ai-email-header-actions">
          <button
            type="button"
            className="email-secondary-button"
            onClick={saveDraft}
            disabled={saving || !currentDraftId}
          >
            {saved ? <Check size={17} /> : <Save size={17} />}
            {saving ? "Saving..." : saved ? "Saved" : "Save draft"}
          </button>

          <button
            type="button"
            className="email-primary-button"
            onClick={generateEmail}
            disabled={!canGenerate}
          >
            <Sparkles size={17} />
            {generating ? "Generating..." : "Generate with AI"}
          </button>
        </div>
      </header>

      <div className="ai-email-layout">
        {/* Sidebar */}
        <aside className="ai-email-sidebar">

          {/* Lead selector */}
          <section className="email-panel lead-context-panel">
            <div className="panel-heading">
              <div>
                <span className="panel-kicker">Recipient</span>
                <h2>Lead context</h2>
              </div>
              <UserRound size={18} />
            </div>

            {loadingLead ? (
              <div className="lead-loading">Loading lead...</div>
            ) : lead ? (
              <div className="lead-context">
                <div className="lead-context-avatar">
                  <Building2Icon />
                </div>
                <div className="lead-context-main">
                  <strong>{leadName}</strong>
                  {leadIndustry && <span>{leadIndustry}</span>}
                  {leadCity && <span>{leadCity}</span>}
                  {leadEmail ? (
                    <a href={`mailto:${leadEmail}`}>{leadEmail}</a>
                  ) : (
                    <span className="lead-no-email-warn">No email on file</span>
                  )}
                </div>
              </div>
            ) : (
              <div className="no-lead-context">
                <Mail size={20} />
                <p>No lead selected.</p>
              </div>
            )}

            <button
              type="button"
              className="lead-picker-trigger"
              onClick={() => setShowLeadPicker(true)}
            >
              <Search size={14} />
              {lead ? "Change lead" : "Select a lead"}
            </button>
          </section>

          {/* Email controls */}
          <section className="email-panel">
            <div className="panel-heading">
              <div>
                <span className="panel-kicker">Generation settings</span>
                <h2>Email controls</h2>
              </div>
            </div>

            {/* Sending account */}
            <label className="email-field">
              <span>Send from account</span>

              {loadingAccounts ? (
                <select disabled>
                  <option>Loading accounts...</option>
                </select>
              ) : accounts.length === 0 ? (
                <div className="no-accounts-warn">
                  <span>No connected accounts.</span>
                  <a href="/email-accounts">Connect one →</a>
                </div>
              ) : (
                <select
                  value={selectedAccountId}
                  onChange={(e) => setSelectedAccountId(e.target.value)}
                >
                  {accounts.map((acc) => (
                    <option key={acc.id} value={acc.id}>
                      {acc.display_name
                        ? `${acc.display_name} (${acc.email})`
                        : acc.email}
                    </option>
                  ))}
                </select>
              )}
            </label>

            {/* Schedule send */}
            <label className="email-field">
              <span>Schedule send (optional)</span>
              <input
                type="datetime-local"
                value={scheduledAt}
                min={new Date(Date.now() + 60000).toISOString().slice(0, 16)}
                onChange={(e) => setScheduledAt(e.target.value)}
              />
              {scheduledAt && (
                <div className="schedule-preview">
                  <span>
                    Sends {new Date(scheduledAt).toLocaleString(undefined, {
                      weekday: "short",
                      month: "short",
                      day: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                  <button
                    type="button"
                    onClick={() => setScheduledAt("")}
                    aria-label="Clear schedule"
                  >
                    ✕
                  </button>
                </div>
              )}
            </label>

            <label className="email-field">
              <span>Email type</span>              <select
                value={emailType}
                onChange={(e) => setEmailType(e.target.value)}
              >
                <option value="initial_outreach">Initial outreach</option>
                <option value="follow_up">Follow-up</option>
                <option value="website_opportunity">Website opportunity</option>
                <option value="seo_audit">SEO audit</option>
                <option value="general_business_outreach">General business</option>
              </select>
            </label>

            <label className="email-field">
              <span>Tone</span>
              <select
                value={tone}
                onChange={(e) => setTone(e.target.value)}
              >
                <option value="professional">Professional</option>
                <option value="conversational">Conversational</option>
                <option value="friendly">Friendly</option>
                <option value="direct">Direct</option>
              </select>
            </label>

            <label className="email-field">
              <span>Length</span>
              <select
                value={length}
                onChange={(e) => setLength(e.target.value)}
              >
                <option value="concise">Concise</option>
                <option value="medium">Medium</option>
                <option value="detailed">Detailed</option>
              </select>
            </label>

            <button
              type="button"
              className="generate-side-button"
              onClick={generateEmail}
              disabled={!canGenerate}
            >
              <RefreshCw
                size={16}
                className={generating ? "email-spinning" : ""}
              />
              {generating ? "Generating..." : "Regenerate email"}
            </button>
          </section>

          {/* Personalization points */}
          {personalizationPoints.length > 0 && (
            <section className="email-panel">
              <div className="panel-heading">
                <div>
                  <span className="panel-kicker">AI context</span>
                  <h2>Personalization</h2>
                </div>
              </div>

              <div className="personalization-list">
                {personalizationPoints.map((point, i) => (
                  <div className="personalization-item" key={i}>
                    <Check size={14} />
                    <span>
                      {typeof point === "string"
                        ? point
                        : point?.point || JSON.stringify(point)}
                    </span>
                  </div>
                ))}
              </div>
            </section>
          )}
        </aside>

        {/* Editor */}
        <main className="ai-email-editor">
          <section className="email-editor-card">
            <div className="editor-card-header">
              <div>
                <span className="panel-kicker">Message</span>
                <h2>Review and personalize</h2>
              </div>

              <div className="editor-provider">
                <Sparkles size={14} />
                Cloudflare AI
              </div>
            </div>

            <div className="email-editor-fields">
              {/* To field (read-only) */}
              {leadEmail && (
                <div className="to-field-row">
                  <span>To:</span>
                  <strong>{leadEmail}</strong>
                </div>
              )}

              {/* Subject */}
              <div className="subject-editor">
                <label htmlFor="email-subject">Subject</label>
                <div className="subject-input-wrap">
                  <input
                    id="email-subject"
                    type="text"
                    value={subject}
                    onChange={(e) => {
                      setSubject(e.target.value);
                      setSaved(false);
                    }}
                    placeholder="Your personalized subject..."
                  />
                  <button
                    type="button"
                    onClick={() => copyText(subject, "subject")}
                    title="Copy subject"
                  >
                    {copiedSubject ? <Check size={16} /> : <Copy size={16} />}
                  </button>
                </div>
              </div>

              {/* Body */}
              <div className="body-editor">
                <div className="body-editor-label">
                  <label htmlFor="email-body">Email body</label>
                  <span>{body.length} characters</span>
                </div>

                <div className="body-textarea-wrap">
                  <textarea
                    id="email-body"
                    value={body}
                    onChange={(e) => {
                      setBody(e.target.value);
                      setSaved(false);
                    }}
                    placeholder="Your AI-generated email will appear here..."
                  />

                  <button
                    type="button"
                    className="body-copy-button"
                    onClick={() => copyText(body, "body")}
                    title="Copy email"
                  >
                    {copiedBody ? <Check size={16} /> : <Clipboard size={16} />}
                    {copiedBody ? "Copied" : "Copy"}
                  </button>
                </div>
              </div>

              {callToAction && (
                <div className="cta-preview">
                  <span>Suggested CTA</span>
                  <strong>{callToAction}</strong>
                </div>
              )}
            </div>

            {/* Footer actions */}
            <div className="editor-footer">
              <div className="editor-footer-info">
                <Mail size={15} />
                <span>Review AI-generated content before sending.</span>
              </div>

              <div className="editor-footer-actions">
                <button
                  type="button"
                  className="email-secondary-button"
                  onClick={saveDraft}
                  disabled={saving || !currentDraftId}
                >
                  <Save size={16} />
                  {saving ? "Saving..." : "Save draft"}
                </button>

                <button
                  type="button"
                  className="email-primary-button email-send-button"
                  onClick={sendEmail}
                  disabled={!canSend}
                  title={
                    !selectedAccountId
                      ? "Select a sending account first"
                      : !currentDraftId
                        ? "Generate an email first"
                        : !leadEmail
                          ? "This lead has no email address"
                          : "Send email"
                  }
                >
                  {sending ? (
                    <>
                      <span className="email-send-spinner" />
                      {scheduledAt ? "Scheduling..." : "Sending..."}
                    </>
                  ) : (
                    <>
                      <Send size={16} />
                      {scheduledAt ? "Schedule send" : "Send"}
                    </>
                  )}
                </button>
              </div>
            </div>
          </section>

          {/* Source evidence */}
          {sourceEvidence.length > 0 && (
            <section className="email-editor-card evidence-card">
              <div className="editor-card-header">
                <div>
                  <span className="panel-kicker">Verification</span>
                  <h2>Source evidence</h2>
                </div>
              </div>

              <div className="evidence-list">
                {sourceEvidence.map((evidence, i) => (
                  <div className="evidence-item" key={i}>
                    <div className="evidence-number">{i + 1}</div>
                    <div>
                      <strong>
                        {typeof evidence === "string"
                          ? evidence
                          : getValue(evidence, ["title", "label", "item", "name"], "Verified finding")}
                      </strong>
                      {typeof evidence !== "string" && (
                        <p>
                          {getValue(
                            evidence,
                            ["value", "description", "detail", "source", "evidence"],
                            JSON.stringify(evidence),
                          )}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}
        </main>
      </div>
    </div>
  );
}

function Building2Icon() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M3 21h18" />
      <path d="M6 21V5a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v16" />
      <path d="M9 7h2" />
      <path d="M13 7h2" />
      <path d="M9 11h2" />
      <path d="M13 11h2" />
      <path d="M9 15h2" />
      <path d="M13 15h2" />
    </svg>
  );
}

export default AIEmailEditorPage;