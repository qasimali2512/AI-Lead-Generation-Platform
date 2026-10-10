import {
  ArrowLeft,
  Calendar,
  Check,
  ChevronDown,
  Clock,
  Clock3,
  LoaderCircle,
  Mail,
  Play,
  Plus,
  Send,
  Settings2,
  ShieldCheck,
  Sparkles,
  Users,
  X,
} from "lucide-react";

import {
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  useLocation,
  useNavigate,
} from "react-router-dom";

import { toast } from "react-toastify";

import api from "../../api/client";
import campaignService from "../../services/campaignService";

import "./CampaignBuilderPage.css";


const defaultFollowUps = [
  {
    id: 1,
    delay: 3,
    unit: "days",
    enabled: true,
    label: "First follow-up",
  },
  {
    id: 2,
    delay: 5,
    unit: "days",
    enabled: false,
    label: "Second follow-up",
  },
];


function getSelectedLeadIds(locationState) {
  const stateIds =
    locationState?.selectedLeadIds;

  if (
    Array.isArray(stateIds) &&
    stateIds.length > 0
  ) {
    return stateIds.map(String);
  }


  try {
    const stored =
      localStorage.getItem(
        "leadflow_selected_lead_ids",
      );

    if (!stored) {
      return [];
    }

    const parsed =
      JSON.parse(stored);

    if (
      Array.isArray(parsed)
    ) {
      return parsed.map(String);
    }
  } catch (error) {
    console.error(
      "Unable to read selected leads:",
      error,
    );
  }


  return [];
}


function CampaignBuilderPage() {
  const location = useLocation();
  const navigate = useNavigate();


  /*
   * -----------------------------------------------------------
   * SELECTED LEADS
   * -----------------------------------------------------------
   */

  const [
    selectedLeadIds,
    setSelectedLeadIds,
  ] = useState(() =>
    getSelectedLeadIds(
      location.state,
    ),
  );


  /*
   * -----------------------------------------------------------
   * CAMPAIGN
   * -----------------------------------------------------------
   */

  const [
    campaignName,
    setCampaignName,
  ] = useState("");


  /*
   * -----------------------------------------------------------
   * EMAIL ACCOUNTS
   * -----------------------------------------------------------
   */

  const [
    emailAccounts,
    setEmailAccounts,
  ] = useState([]);

  const [
    loadingAccounts,
    setLoadingAccounts,
  ] = useState(true);

  const [
    selectedAccounts,
    setSelectedAccounts,
  ] = useState([]);

  const [
    showAccountSelector,
    setShowAccountSelector,
  ] = useState(false);


  /*
   * -----------------------------------------------------------
   * SENDING
   * -----------------------------------------------------------
   */

  const [
    dailyLimit,
    setDailyLimit,
  ] = useState("30");

  const [
    startTime,
    setStartTime,
  ] = useState("09:00");

  const [
    endTime,
    setEndTime,
  ] = useState("17:00");

  const [
    delayMin,
    setDelayMin,
  ] = useState("5");

  const [
    delayMax,
    setDelayMax,
  ] = useState("15");

  const [
    businessDaysOnly,
    setBusinessDaysOnly,
  ] = useState(true);

  // ── Scheduling ──────────────────────────────────────────────
  // "now" = start immediately, "later" = pick a future date/time
  const [scheduleMode, setScheduleMode] = useState("now");

  // Minimum date = today (local)
  const todayDate = new Date().toISOString().slice(0, 10);

  const [scheduleDate, setScheduleDate] = useState(todayDate);

  // Default launch time = current start_time setting (09:00)
  const [scheduleTime, setScheduleTime] = useState("09:00");


  /*
   * -----------------------------------------------------------
   * FOLLOW UPS
   * -----------------------------------------------------------
   */

  const [
    followUps,
    setFollowUps,
  ] = useState(
    defaultFollowUps,
  );


  /*
   * -----------------------------------------------------------
   * UI STATE
   * -----------------------------------------------------------
   */

  const [
    saving,
    setSaving,
  ] = useState(false);

  const [
    started,
    setStarted,
  ] = useState(false);

  const [campaignId, setCampaignId] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [processResult, setProcessResult] = useState(null);


  /*
   * -----------------------------------------------------------
   * LOAD SELECTED LEADS
   * -----------------------------------------------------------
   */

  useEffect(() => {
    const ids =
      getSelectedLeadIds(
        location.state,
      );

    setSelectedLeadIds(ids);
  }, [location.state]);


  /*
   * -----------------------------------------------------------
   * LOAD CONNECTED EMAIL ACCOUNTS
   * -----------------------------------------------------------
   *
   * Real accounts come from:
   *
   * GET /api/v1/email-accounts
   *
   * We do NOT hardcode Gmail accounts here.
   */

  useEffect(() => {
    loadEmailAccounts();
  }, []);


  const loadEmailAccounts =
    async () => {
      setLoadingAccounts(
        true,
      );

      try {
        const response =
          await api.get(
            "/email-accounts",
          );

        const items =
          Array.isArray(
            response.data,
          )
            ? response.data
            : Array.isArray(
                response.data?.items,
              )
              ? response.data.items
              : [];


        const activeAccounts =
          items.filter(
            (account) =>
              account.status ===
                "active" ||
              account.status ===
                undefined,
          );


        setEmailAccounts(
          activeAccounts,
        );


        /*
         * Automatically select the first
         * connected active account.
         */
        if (
          activeAccounts.length >
            0
        ) {
          setSelectedAccounts(
            [activeAccounts[0].id],
          );
        }
      } catch (error) {
        console.error(
          "Unable to load email accounts:",
          error,
        );

        toast.error(
          "Unable to load connected email accounts.",
        );

        setEmailAccounts(
          [],
        );
      } finally {
        setLoadingAccounts(
          false,
        );
      }
    };


  /*
   * -----------------------------------------------------------
   * ACCOUNT SELECTION
   * -----------------------------------------------------------
   */

  const toggleAccount = (
    accountId,
  ) => {
    setSelectedAccounts(
      (current) => {
        if (
          current.includes(
            accountId,
          )
        ) {
          return current.filter(
            (id) =>
              id !== accountId,
          );
        }

        return [
          ...current,
          accountId,
        ];
      },
    );
  };


  /*
   * -----------------------------------------------------------
   * FOLLOW UP CONTROLS
   * -----------------------------------------------------------
   */

  const toggleFollowUp = (
    id,
  ) => {
    setFollowUps(
      (current) =>
        current.map(
          (item) =>
            item.id === id
              ? {
                  ...item,
                  enabled:
                    !item.enabled,
                }
              : item,
        ),
    );
  };


  const updateFollowUp = (
    id,
    field,
    value,
  ) => {
    setFollowUps(
      (current) =>
        current.map(
          (item) =>
            item.id === id
              ? {
                  ...item,
                  [field]:
                    value,
                }
              : item,
        ),
    );
  };


  const addFollowUp = () => {
    setFollowUps(
      (current) => [
        ...current,
        {
          id: Date.now(),
          delay: 7,
          unit: "days",
          enabled: true,
          label: `Follow-up ${
            current.length + 1
          }`,
        },
      ],
    );
  };


  const removeFollowUp = (
    id,
  ) => {
    setFollowUps(
      (current) =>
        current.filter(
          (item) =>
            item.id !== id,
        ),
    );
  };


  /*
   * -----------------------------------------------------------
   * ACCOUNT CAPACITY
   * -----------------------------------------------------------
   */

  const selectedAccountObjects =
    useMemo(() => {
      return emailAccounts.filter(
        (account) =>
          selectedAccounts.includes(
            account.id,
          ),
      );
    }, [
      emailAccounts,
      selectedAccounts,
    ]);


  const totalAccountCapacity =
    selectedAccountObjects.reduce(
      (sum, account) =>
        sum +
        Number(
          account.daily_send_limit ||
            account.dailyLimit ||
            0,
        ),
      0,
    );


  const effectiveDailyLimit =
    Math.min(
      Number(dailyLimit) ||
        0,
      totalAccountCapacity,
    );


  /*
   * -----------------------------------------------------------
   * START CAMPAIGN
   * -----------------------------------------------------------
   */

  const handleStartCampaign =
    async () => {
      if (
        !campaignName.trim()
      ) {
        toast.error(
          "Enter a campaign name first.",
        );

        return;
      }


      if (
        selectedLeadIds.length ===
        0
      ) {
        toast.error(
          "No leads are selected. Go back to Leads and select leads first.",
        );

        return;
      }


      if (
        selectedAccounts.length ===
        0
      ) {
        toast.error(
          "Select at least one email account.",
        );

        return;
      }


      if (
        !Number(dailyLimit) ||
        Number(dailyLimit) < 1
      ) {
        toast.error(
          "Daily sending limit must be greater than zero.",
        );

        return;
      }


      if (
        totalAccountCapacity > 0 &&
        Number(dailyLimit) >
          totalAccountCapacity
      ) {
        toast.error(
          `Daily limit cannot exceed the selected accounts' configured capacity of ${totalAccountCapacity}.`,
        );

        return;
      }


      if (
        Number(delayMin) < 0 ||
        Number(delayMax) <
          Number(delayMin)
      ) {
        toast.error(
          "Check the sending delay range.",
        );

        return;
      }


      try {
        setSaving(true);

        // Build scheduled_start_at if user chose "later"
        let scheduledStartAt = null;
        if (scheduleMode === "later") {
          if (!scheduleDate) {
            toast.error("Pick a start date for the campaign.");
            setSaving(false);
            return;
          }
          // Combine date + time into a local ISO string
          const combined = new Date(`${scheduleDate}T${scheduleTime || "09:00"}:00`);
          if (isNaN(combined.getTime()) || combined <= new Date()) {
            toast.error("Scheduled start must be a future date and time.");
            setSaving(false);
            return;
          }
          scheduledStartAt = combined.toISOString();
        }

        const payload = {
          name: campaignName.trim(),
          selected_lead_ids: selectedLeadIds,
          email_account_ids: selectedAccounts,
          daily_limit: Number(dailyLimit),
          start_time: startTime,
          end_time: endTime,
          delay_min_minutes: Number(delayMin),
          delay_max_minutes: Number(delayMax),
          business_days_only: businessDaysOnly,
          follow_ups: followUps.filter((item) => item.enabled),
          ...(scheduledStartAt ? { scheduled_start_at: scheduledStartAt } : {}),
        };

        // Step 1: Create the campaign (status = draft)
        const created = await campaignService.createCampaign(payload);
        const newCampaignId = created.id;
        setCampaignId(newCampaignId);

        // Step 2: Start / schedule it
        const started_campaign = await campaignService.startCampaign(newCampaignId);
        const isScheduled = started_campaign?.status === "scheduled";

        setStarted(true);

        if (isScheduled) {
          const formatted = new Date(scheduledStartAt).toLocaleString(undefined, {
            dateStyle: "medium",
            timeStyle: "short",
          });
          toast.success(`Campaign scheduled for ${formatted}. Emails will be generated and queued automatically when the time arrives.`);

          // Clear localStorage and navigate after short delay
          localStorage.removeItem("leadflow_selected_lead_ids");
          localStorage.removeItem("leadflow_campaign_draft");
          setTimeout(() => navigate("/campaigns"), 2500);
          return;
        }

        toast.success("Campaign started! Generating AI emails now...");

        // Step 3: Process — AI generates + queues all lead emails (only for immediate campaigns)
        setProcessing(true);

        try {
          const result = await campaignService.processCampaign(newCampaignId);
          setProcessResult(result);

          const { queued = 0, skipped = 0, failed = 0 } = result;

          if (queued > 0) {
            toast.success(
              `${queued} email${queued !== 1 ? "s" : ""} generated and queued.${
                skipped > 0 ? ` ${skipped} skipped (no email).` : ""
              }${failed > 0 ? ` ${failed} failed.` : ""}`,
            );
          } else if (skipped > 0 && failed === 0) {
            toast.warning("All leads were skipped — no email addresses found.");
          } else {
            toast.error("No emails were queued. Check lead emails and account status.");
          }

          localStorage.removeItem("leadflow_selected_lead_ids");
          localStorage.removeItem("leadflow_campaign_draft");

          setTimeout(() => navigate("/campaigns"), 2000);
        } catch (processError) {
          console.error("Campaign processing error:", processError);
          toast.error(
            processError?.response?.data?.detail ||
              "Campaign started but email generation failed. You can retry from the campaigns page.",
          );
        } finally {
          setProcessing(false);
        }
      } catch (error) {
        console.error("Campaign creation error:", error);
        toast.error(
          error?.response?.data?.detail ||
            "Unable to start the campaign. Please try again.",
        );
      } finally {
        setSaving(false);
      }
    };


  /*
   * -----------------------------------------------------------
   * REMOVE ALL SELECTED LEADS
   * -----------------------------------------------------------
   */

  const clearSelectedLeads =
    () => {
      localStorage.removeItem(
        "leadflow_selected_lead_ids",
      );

      setSelectedLeadIds([]);

      toast.info(
        "Selected leads removed from this campaign.",
      );
    };


  /*
   * -----------------------------------------------------------
   * NO LEADS
   * -----------------------------------------------------------
   */

  if (
    selectedLeadIds.length ===
    0
  ) {
    return (
      <div className="campaign-builder-page">

        <div className="campaign-no-leads">

          <div className="campaign-no-leads-icon">
            <Users size={24} />
          </div>

          <span className="campaign-section-kicker">
            Campaign setup
          </span>

          <h1>
            No leads selected
          </h1>

          <p>
            Go back to the Leads page,
            select the businesses you want
            to contact, and then click
            <strong>
              {" "}
              Create Campaign
            </strong>.
          </p>

          <button
            type="button"
            className="campaign-primary-action"
            onClick={() =>
              navigate(
                "/leads",
              )
            }
          >
            <ArrowLeft
              size={16}
            />
            Back to Leads
          </button>

        </div>

      </div>
    );
  }


  return (
    <div className="campaign-builder-page">

      {/* =====================================================
          HEADER
      ===================================================== */}

      <header className="campaign-builder-header">

        <div>

          <button
            type="button"
            className="campaign-back-link"
            onClick={() =>
              navigate(
                "/leads",
              )
            }
          >
            <ArrowLeft
              size={16}
            />
            Back to leads
          </button>


          <div className="campaign-title-row">

            <div className="campaign-title-icon">
              <Send size={21} />
            </div>


            <div>

              <span className="campaign-kicker">
                Outreach automation
              </span>

              <h1>
                Campaign Builder
              </h1>

              <p>
                Your selected leads are already
                attached. Configure the outreach
                settings below.
              </p>

            </div>

          </div>

        </div>


        <div className="campaign-header-actions">

          <div
            className={`campaign-state ${
              started
                ? "campaign-state-ready"
                : ""
            }`}
          >

            {started ? (
              <Check size={14} />
            ) : (
              <Settings2
                size={14}
              />
            )}

            {started
              ? "Configuration ready"
              : "Draft campaign"}

          </div>

        </div>

      </header>


      <div className="campaign-builder-layout">

        <main className="campaign-builder-main">


          {/* =================================================
              01 CAMPAIGN DETAILS
          ================================================= */}

          <section className="campaign-card">

            <div className="campaign-card-header">

              <div>

                <span className="campaign-section-kicker">
                  01
                </span>

                <h2>
                  Campaign details
                </h2>

                <p>
                  Give your campaign a clear
                  internal name.
                </p>

              </div>

            </div>


            <div className="campaign-form-grid">

              <label className="campaign-field full">

                <span>
                  Campaign name
                </span>

                <input
                  type="text"
                  value={
                    campaignName
                  }
                  onChange={(
                    event,
                  ) =>
                    setCampaignName(
                      event.target
                        .value,
                    )
                  }
                  placeholder="e.g. US Hotel Website Outreach"
                />

              </label>

            </div>

          </section>


          {/* =================================================
              02 SELECTED LEADS
          ================================================= */}

          <section className="campaign-card">

            <div className="campaign-card-header">

              <div>

                <span className="campaign-section-kicker">
                  02
                </span>

                <h2>
                  Selected leads
                </h2>

                <p>
                  These leads came directly from
                  your Leads page. No targeting
                  information needs to be entered
                  again.
                </p>

              </div>

              <Users size={19} />

            </div>


            <div className="selected-leads-box">

              <div className="selected-leads-icon">
                <Users size={21} />
              </div>


              <div className="selected-leads-copy">

                <strong>
                  {
                    selectedLeadIds.length
                  }{" "}
                  leads selected
                </strong>

                <span>
                  These exact leads will be used
                  for this campaign.
                </span>

              </div>


              <button
                type="button"
                className="selected-leads-clear"
                onClick={
                  clearSelectedLeads
                }
              >
                <X size={14} />
                Clear
              </button>

            </div>


            <div className="selected-lead-id-preview">

              <span>
                Selected lead IDs
              </span>

              <div>
                {selectedLeadIds
                  .slice(0, 8)
                  .map(
                    (
                      id,
                    ) => (
                      <span
                        key={id}
                      >
                        {id}
                      </span>
                    ),
                  )}

                {selectedLeadIds.length >
                  8 && (
                  <span>
                    +
                    {selectedLeadIds.length -
                      8}{" "}
                    more
                  </span>
                )}

              </div>

            </div>

          </section>


          {/* =================================================
              03 EMAIL ACCOUNTS
          ================================================= */}

          <section className="campaign-card">

            <div className="campaign-card-header">

              <div>

                <span className="campaign-section-kicker">
                  03
                </span>

                <h2>
                  Email account
                </h2>

                <p>
                  Select the authorized email
                  account that can participate
                  in this campaign.
                </p>

              </div>

              <Mail size={19} />

            </div>


            <div className="account-selector">

              <button
                type="button"
                className="account-selector-trigger"
                onClick={() =>
                  setShowAccountSelector(
                    (
                      current,
                    ) =>
                      !current,
                  )
                }
              >

                <div>

                  <strong>

                    {loadingAccounts
                      ? "Loading accounts..."
                      : selectedAccounts.length ===
                          0
                        ? "No account selected"
                        : `${selectedAccounts.length} account${
                            selectedAccounts.length >
                            1
                              ? "s"
                              : ""
                          } selected`}

                  </strong>


                  <span>

                    {totalAccountCapacity >
                    0
                      ? `${totalAccountCapacity} configured emails/day capacity`
                      : "Connect an email account"}

                  </span>

                </div>


                {loadingAccounts ? (
                  <LoaderCircle
                    size={17}
                    className="campaign-spin"
                  />
                ) : (
                  <ChevronDown
                    size={17}
                    className={
                      showAccountSelector
                        ? "selector-open"
                        : ""
                    }
                  />
                )}

              </button>


              {showAccountSelector &&
                !loadingAccounts && (
                  <div className="account-selector-menu">

                    {emailAccounts.length ===
                    0 ? (

                      <div className="account-empty">

                        <Mail
                          size={20}
                        />

                        <strong>
                          No connected accounts
                        </strong>

                        <span>
                          Connect Gmail first from
                          Email Accounts.
                        </span>

                        <a
                          href="/email/accounts"
                          className="manage-accounts-link"
                        >
                          Manage email accounts
                        </a>

                      </div>

                    ) : (

                      emailAccounts.map(
                        (
                          account,
                        ) => {

                          const selected =
                            selectedAccounts.includes(
                              account.id,
                            );


                          return (
                            <button
                              type="button"
                              key={
                                account.id
                              }
                              className={`account-selector-option ${
                                selected
                                  ? "selected"
                                  : ""
                              }`}
                              onClick={() =>
                                toggleAccount(
                                  account.id,
                                )
                              }
                            >

                              <div className="account-option-icon">
                                <Mail
                                  size={16}
                                />
                              </div>


                              <div className="account-option-copy">

                                <strong>
                                  {account.display_name ||
                                    account.name ||
                                    "Email account"}
                                </strong>

                                <span>
                                  {account.email}
                                </span>

                              </div>


                              <div
                                className={`account-checkbox ${
                                  selected
                                    ? "checked"
                                    : ""
                                }`}
                              >

                                {selected && (
                                  <Check
                                    size={
                                      13
                                    }
                                  />
                                )}

                              </div>

                            </button>
                          );
                        },
                      )

                    )}


                    <a
                      href="/email/accounts"
                      className="manage-accounts-link"
                    >
                      Manage email accounts
                    </a>

                  </div>
                )}

            </div>

          </section>


          {/* =================================================
              04 SENDING SCHEDULE
          ================================================= */}

          <section className="campaign-card">

            <div className="campaign-card-header">

              <div>

                <span className="campaign-section-kicker">
                  04
                </span>

                <h2>
                  Sending schedule
                </h2>

                <p>
                  Control daily volume, sending
                  hours and spacing between emails.
                </p>

              </div>

              <Clock3 size={19} />

            </div>


            <div className="campaign-form-grid">

              <label className="campaign-field">

                <span>
                  Daily email limit
                </span>

                <input
                  type="number"
                  min="1"
                  max={
                    totalAccountCapacity ||
                    10000
                  }
                  value={
                    dailyLimit
                  }
                  onChange={(
                    event,
                  ) =>
                    setDailyLimit(
                      event.target
                        .value,
                    )
                  }
                />

                <small>
                  Effective capacity:{" "}
                  {
                    effectiveDailyLimit
                  }{" "}
                  emails/day
                </small>

              </label>


              <div className="campaign-field">

                <span>
                  Sending days
                </span>

                <button
                  type="button"
                  className={`toggle-field ${
                    businessDaysOnly
                      ? "enabled"
                      : ""
                  }`}
                  onClick={() =>
                    setBusinessDaysOnly(
                      (
                        current,
                      ) =>
                        !current,
                    )
                  }
                >

                  <span className="toggle-switch">
                    <span />
                  </span>

                  <span>
                    Business days only
                  </span>

                </button>

              </div>


              <label className="campaign-field">

                <span>
                  Start time
                </span>

                <input
                  type="time"
                  value={
                    startTime
                  }
                  onChange={(
                    event,
                  ) =>
                    setStartTime(
                      event.target
                        .value,
                    )
                  }
                />

              </label>


              <label className="campaign-field">

                <span>
                  End time
                </span>

                <input
                  type="time"
                  value={
                    endTime
                  }
                  onChange={(
                    event,
                  ) =>
                    setEndTime(
                      event.target
                        .value,
                    )
                  }
                />

              </label>


              <label className="campaign-field">

                <span>
                  Minimum delay
                </span>

                <div className="input-with-suffix">

                  <input
                    type="number"
                    min="0"
                    value={
                      delayMin
                    }
                    onChange={(
                      event,
                    ) =>
                      setDelayMin(
                        event.target
                          .value,
                      )
                    }
                  />

                  <span>
                    min
                  </span>

                </div>

              </label>


              <label className="campaign-field">

                <span>
                  Maximum delay
                </span>

                <div className="input-with-suffix">

                  <input
                    type="number"
                    min="0"
                    value={
                      delayMax
                    }
                    onChange={(
                      event,
                    ) =>
                      setDelayMax(
                        event.target
                          .value,
                      )
                    }
                  />

                  <span>
                    min
                  </span>

                </div>

              </label>

            </div>


            <div className="sending-safety-note">

              <ShieldCheck
                size={16}
              />

              <div>

                <strong>
                  Provider limits remain authoritative
                </strong>

                <p>
                  Campaign limits should never be
                  used to bypass provider sending
                  restrictions. Bounce, complaint,
                  unsubscribe and suppression rules
                  remain enforced by the delivery system.
                </p>

              </div>

            </div>


            {/* ── Campaign start scheduling ── */}
            <div className="schedule-launch-box">

              <div className="schedule-launch-header">
                <Calendar size={16} />
                <strong>Campaign start</strong>
                <span>When should this campaign begin sending?</span>
              </div>

              {/* Toggle: Start now / Schedule */}
              <div className="schedule-mode-toggle">
                <button
                  type="button"
                  className={`schedule-mode-btn ${scheduleMode === "now" ? "active" : ""}`}
                  onClick={() => setScheduleMode("now")}
                >
                  <Play size={13} />
                  Start now
                </button>
                <button
                  type="button"
                  className={`schedule-mode-btn ${scheduleMode === "later" ? "active" : ""}`}
                  onClick={() => setScheduleMode("later")}
                >
                  <Clock size={13} />
                  Schedule for later
                </button>
              </div>

              {/* Date + time pickers (only when "later") */}
              {scheduleMode === "later" && (
                <div className="schedule-datetime-row">

                  <label className="campaign-field">
                    <span>Start date</span>
                    <div className="schedule-input-wrap">
                      <Calendar size={15} />
                      <input
                        type="date"
                        value={scheduleDate}
                        min={todayDate}
                        onChange={(e) => setScheduleDate(e.target.value)}
                      />
                    </div>
                  </label>

                  <label className="campaign-field">
                    <span>Start time</span>
                    <div className="schedule-input-wrap">
                      <Clock size={15} />
                      <input
                        type="time"
                        value={scheduleTime}
                        onChange={(e) => setScheduleTime(e.target.value)}
                      />
                    </div>
                  </label>

                </div>
              )}

              {scheduleMode === "now" && (
                <p className="schedule-hint">
                  Emails will be generated and queued immediately after you click <strong>Start Campaign</strong>.
                </p>
              )}

              {scheduleMode === "later" && scheduleDate && (
                <p className="schedule-hint">
                  Campaign will activate on <strong>{new Date(`${scheduleDate}T${scheduleTime}:00`).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" })}</strong>. The scheduler checks every 30 seconds.
                </p>
              )}

            </div>

          </section>


          {/* =================================================
              05 FOLLOW UPS
          ================================================= */}

          <section className="campaign-card">

            <div className="campaign-card-header">

              <div>

                <span className="campaign-section-kicker">
                  05
                </span>

                <h2>
                  Follow-up sequence
                </h2>

                <p>
                  Define optional follow-ups for
                  leads that do not reply.
                </p>

              </div>

              <Sparkles size={19} />

            </div>


            <div className="follow-up-list">

              {followUps.map(
                (
                  followUp,
                  index,
                ) => (

                  <div
                    className={`follow-up-row ${
                      followUp.enabled
                        ? "enabled"
                        : "disabled"
                    }`}
                    key={
                      followUp.id
                    }
                  >

                    <div className="follow-up-number">
                      {index + 1}
                    </div>


                    <div className="follow-up-main">

                      <strong>
                        {
                          followUp.label
                        }
                      </strong>


                      <div className="follow-up-controls">

                        <span>
                          Send after
                        </span>


                        <input
                          type="number"
                          min="1"
                          value={
                            followUp.delay
                          }
                          disabled={
                            !followUp.enabled
                          }
                          onChange={(
                            event,
                          ) =>
                            updateFollowUp(
                              followUp.id,
                              "delay",
                              event.target
                                .value,
                            )
                          }
                        />


                        <select
                          value={
                            followUp.unit
                          }
                          disabled={
                            !followUp.enabled
                          }
                          onChange={(
                            event,
                          ) =>
                            updateFollowUp(
                              followUp.id,
                              "unit",
                              event.target
                                .value,
                            )
                          }
                        >

                          <option value="days">
                            days
                          </option>

                          <option value="hours">
                            hours
                          </option>

                        </select>

                      </div>

                    </div>


                    <button
                      type="button"
                      className={`follow-up-toggle ${
                        followUp.enabled
                          ? "active"
                          : ""
                      }`}
                      onClick={() =>
                        toggleFollowUp(
                          followUp.id,
                        )
                      }
                    >
                      {followUp.enabled
                        ? "Enabled"
                        : "Disabled"}
                    </button>


                    {followUps.length >
                      1 && (
                      <button
                        type="button"
                        className="follow-up-remove"
                        onClick={() =>
                          removeFollowUp(
                            followUp.id,
                          )
                        }
                        aria-label="Remove follow-up"
                      >
                        <X
                          size={15}
                        />
                      </button>
                    )}

                  </div>

                ),
              )}

            </div>


            <button
              type="button"
              className="add-follow-up-button"
              onClick={
                addFollowUp
              }
            >
              <Plus size={15} />
              Add follow-up
            </button>

          </section>

        </main>


        {/* ===================================================
            SUMMARY
        =================================================== */}

        <aside className="campaign-summary">

          <div className="campaign-summary-card">

            <div className="summary-header">

              <div>

                <span className="campaign-section-kicker">
                  Campaign summary
                </span>

                <h2>
                  {campaignName.trim() ||
                    "Untitled campaign"}
                </h2>

              </div>


              <div className="summary-icon">
                <Send size={18} />
              </div>

            </div>


            <div className="summary-stat">

              <span>
                Selected leads
              </span>

              <strong>
                {
                  selectedLeadIds.length
                }
              </strong>

            </div>


            <div className="summary-stat">

              <span>
                Email accounts
              </span>

              <strong>
                {
                  selectedAccounts.length
                }
              </strong>

            </div>


            <div className="summary-stat">

              <span>
                Daily limit
              </span>

              <strong>
                {
                  effectiveDailyLimit
                }
              </strong>

            </div>


            <div className="summary-stat">

              <span>
                Sending window
              </span>

              <strong>
                {startTime} –{" "}
                {endTime}
              </strong>

            </div>


            <div className="summary-stat">

              <span>
                Follow-ups
              </span>

              <strong>
                {
                  followUps.filter(
                    (item) =>
                      item.enabled,
                  ).length
                }
              </strong>

            </div>


            <div className="summary-stat">
              <span>Campaign start</span>
              <strong>
                {scheduleMode === "later" && scheduleDate
                  ? (() => {
                      try {
                        return new Date(`${scheduleDate}T${scheduleTime}:00`).toLocaleString(undefined, {
                          dateStyle: "medium",
                          timeStyle: "short",
                        });
                      } catch {
                        return `${scheduleDate} ${scheduleTime}`;
                      }
                    })()
                  : "Immediately"}
              </strong>
            </div>


            <div className="summary-divider" />


            <button
              type="button"
              className="start-campaign-button"
              onClick={
                handleStartCampaign
              }
              disabled={
                saving ||
                loadingAccounts ||
                started
              }
            >

              {processing ? (
                <>
                  <LoaderCircle
                    size={17}
                    className="campaign-spin"
                  />
                  Generating emails...
                </>
              ) : started ? (
                <>
                  <Check
                    size={17}
                  />
                  {scheduleMode === "later" ? "Campaign scheduled" : "Campaign running"}
                </>
              ) : (
                <>
                  {scheduleMode === "later" ? (
                    <Calendar size={17} />
                  ) : (
                    <Play size={17} />
                  )}

                  {saving
                    ? "Saving..."
                    : scheduleMode === "later"
                    ? "Schedule Campaign"
                    : "Start Campaign"}
                </>
              )}

            </button>


            <p className="summary-disclaimer">
              {started
                ? scheduleMode === "later"
                  ? "Campaign is scheduled. It will activate automatically at the chosen time."
                  : "Campaign is live. Emails are being generated and queued for each lead."
                : scheduleMode === "later"
                ? "Campaign will be scheduled. Emails will be generated automatically when it activates."
                : "Leads are attached. Click Start Campaign to generate personalized emails and queue them for sending."}
            </p>

            {processResult && (
              <div className="process-result">
                <div className="process-result-row">
                  <span>Queued</span>
                  <strong className="result-queued">{processResult.queued ?? 0}</strong>
                </div>
                <div className="process-result-row">
                  <span>Skipped</span>
                  <strong>{processResult.skipped ?? 0}</strong>
                </div>
                {(processResult.failed ?? 0) > 0 && (
                  <div className="process-result-row">
                    <span>Failed</span>
                    <strong className="result-failed">{processResult.failed}</strong>
                  </div>
                )}
              </div>
            )}

          </div>


          <div className="campaign-summary-info">

            <ShieldCheck
              size={17}
            />

            <div>

              <strong>
                Outreach safeguards
              </strong>

              <p>
                Respect provider limits, bounces,
                complaints, unsubscribe requests
                and suppression rules.
              </p>

            </div>

          </div>

          {started && (
            <button
              type="button"
              className="view-campaigns-link"
              onClick={() => navigate("/campaigns")}
            >
              View all campaigns →
            </button>
          )}

        </aside>

      </div>

    </div>
  );
}


export default CampaignBuilderPage;