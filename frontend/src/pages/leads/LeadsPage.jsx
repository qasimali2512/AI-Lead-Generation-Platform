import { useEffect, useMemo, useState } from "react";
import {
  ChevronLeft,
  ChevronRight,
  Globe,
  LoaderCircle,
  Mail,
  MapPin,
  Phone,
  Search,
  SlidersHorizontal,
  Target,
  Users,
  X,
} from "lucide-react";
import { toast } from "react-toastify";
import { useNavigate, useSearchParams } from "react-router-dom";

import leadsService from "../../services/leadsService";
import "./LeadsPage.css";


function normalizeLeads(data) {
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


function getLeadId(lead) {
  return lead?.id || null;
}


function getLeadName(lead) {
  return (
    lead.business_name ||
    lead.name ||
    lead.company_name ||
    "Unnamed business"
  );
}


function getIndustry(lead) {
  return (
    lead.industry ||
    lead.category ||
    lead.business_type ||
    lead.type ||
    "Business"
  );
}


function getLocation(lead) {
  return (
    lead.location ||
    lead.address ||
    lead.city ||
    lead.display_name ||
    "Location unavailable"
  );
}


function getWebsite(lead) {
  return (
    lead.website ||
    lead.website_url ||
    lead.url ||
    null
  );
}


function getEmail(lead) {
  return (
    lead.email ||
    lead.email_address ||
    null
  );
}


function getPhone(lead) {
  return (
    lead.phone ||
    lead.phone_number ||
    null
  );
}


function getQualification(lead) {
  const qualification =
    lead.qualification_level ||
    lead.qualification ||
    lead.qualification_status;

  if (!qualification) {
    return "Not qualified";
  }

  return String(qualification);
}


function getQualificationClass(lead) {
  const value = getQualification(lead)
    .toLowerCase()
    .replaceAll("_", " ");

  if (
    value.includes("qualified") &&
    !value.includes("unqualified")
  ) {
    return "qualified";
  }

  if (
    value.includes("high") ||
    value.includes("ready")
  ) {
    return "high";
  }

  if (
    value.includes("low") ||
    value.includes("not")
  ) {
    return "low";
  }

  return "neutral";
}


function LeadsPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);

  // Pre-fill search from URL ?search= param (used by Opportunities "Open lead")
  const [search, setSearch] = useState(
    () => searchParams.get("search") || ""
  );
  const [websiteFilter, setWebsiteFilter] =
    useState("all");
  const [emailFilter, setEmailFilter] =
    useState("all");
  const [qualificationFilter, setQualificationFilter] =
    useState("all");

  const [selectedIds, setSelectedIds] = useState([]);
  const [sortBy, setSortBy] = useState("date");

  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);


  useEffect(() => {
    loadLeads();
  }, []);


  const loadLeads = async () => {
    setLoading(true);

    try {
      // Fetch all leads across all pages (max 100 per request)
      const PAGE_SIZE = 100;
      let allLeads = [];
      let currentFetchPage = 1;
      let total = null;

      do {
        const data = await leadsService.getLeads({
          page: currentFetchPage,
          page_size: PAGE_SIZE,
        });

        const pageLeads = normalizeLeads(data);
        allLeads = [...allLeads, ...pageLeads];

        if (total === null) {
          total = data?.total ?? pageLeads.length;
        }

        if (pageLeads.length < PAGE_SIZE) break;
        currentFetchPage += 1;
      } while (allLeads.length < total);

      setLeads(allLeads);
    } catch (error) {
      console.error(
        "Unable to load leads:",
        error,
      );

      const detail =
        error?.response?.data?.detail;

      if (
        error?.response?.status === 404
      ) {
        setLeads([]);
        return;
      }

      toast.error(
        typeof detail === "string"
          ? detail
          : "Unable to load leads right now.",
      );
    } finally {
      setLoading(false);
    }
  };


  const filteredLeads = useMemo(() => {
    const normalizedSearch =
      search.trim().toLowerCase();

    let filtered = [...leads];


    if (normalizedSearch) {
      filtered = filtered.filter((lead) => {
        const searchableText = [
          getLeadName(lead),
          getIndustry(lead),
          getLocation(lead),
          getEmail(lead),
          getWebsite(lead),
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();

        return searchableText.includes(
          normalizedSearch,
        );
      });
    }


    if (websiteFilter === "with") {
      filtered = filtered.filter((lead) =>
        Boolean(
          getWebsite(lead),
        ),
      );
    }


    if (websiteFilter === "without") {
      filtered = filtered.filter(
        (lead) =>
          !getWebsite(lead),
      );
    }


    if (emailFilter === "with") {
      filtered = filtered.filter((lead) =>
        Boolean(getEmail(lead)),
      );
    }

    if (emailFilter === "without") {
      filtered = filtered.filter((lead) =>
        !getEmail(lead),
      );
    }


    if (
      qualificationFilter !==
      "all"
    ) {
      filtered = filtered.filter(
        (lead) => {
          const qualification =
            getQualification(lead)
              .toLowerCase()
              .replaceAll(
                "_",
                " ",
              );


          if (
            qualificationFilter ===
            "qualified"
          ) {
            return (
              qualification.includes(
                "qualified",
              ) &&
              !qualification.includes(
                "unqualified",
              )
            );
          }


          if (
            qualificationFilter ===
            "ready"
          ) {
            return (
              qualification.includes(
                "ready",
              ) ||
              qualification.includes(
                "high",
              )
            );
          }


          if (
            qualificationFilter ===
            "unqualified"
          ) {
            return (
              qualification.includes(
                "unqualified",
              ) ||
              qualification.includes(
                "not qualified",
              )
            );
          }


          return true;
        },
      );
    }


    filtered.sort(
      (first, second) => {
        if (sortBy === "date") {
          return (
            new Date(second.created_at || 0) -
            new Date(first.created_at || 0)
          );
        }

        if (
          sortBy ===
          "industry"
        ) {
          return getIndustry(
            first,
          ).localeCompare(
            getIndustry(
              second,
            ),
          );
        }

        // name (default)
        return getLeadName(
          first,
        ).localeCompare(
          getLeadName(
            second,
          ),
        );
      },
    );


    return filtered;
  }, [
    leads,
    search,
    websiteFilter,
    emailFilter,
    qualificationFilter,
    sortBy,
  ]);


  const totalPages = Math.max(
    1,
    Math.ceil(
      filteredLeads.length /
        pageSize,
    ),
  );


  const currentPage = Math.min(
    page,
    totalPages,
  );


  const paginatedLeads =
    filteredLeads.slice(
      (currentPage - 1) *
        pageSize,
      currentPage *
        pageSize,
    );


  const selectedVisibleCount =
    paginatedLeads.filter(
      (lead, index) =>
        selectedIds.includes(
          getLeadId(lead)
        ),
    ).length;


  const totalWithWebsite =
    leads.filter(
      (lead) =>
        getWebsite(lead),
    ).length;


  const totalWithoutWebsite =
    leads.length -
    totalWithWebsite;


  const clearFilters = () => {
    setSearch("");
    setWebsiteFilter("all");
    setEmailFilter("all");
    setQualificationFilter(
      "all",
    );
    setPage(1);
  };


  const hasFilters =
    search.trim() ||
    websiteFilter !==
      "all" ||
    emailFilter !== "all" ||
    qualificationFilter !==
      "all";


  const toggleLead = (
    leadId,
  ) => {
    setSelectedIds(
      (current) => {
        if (
          current.includes(
            leadId,
          )
        ) {
          return current.filter(
            (id) =>
              id !== leadId,
          );
        }

        return [
          ...current,
          leadId,
        ];
      },
    );
  };


  const toggleVisibleLeads =
    () => {
      const visibleIds =
        paginatedLeads.map(
          (lead, index) =>
            getLeadId(
              lead,
              (currentPage - 1) *
                pageSize +
                index,
            ),
        );


      const allVisibleSelected =
        visibleIds.length >
          0 &&
        visibleIds.every(
          (id) =>
            selectedIds.includes(
              id,
            ),
        );


      if (
        allVisibleSelected
      ) {
        setSelectedIds(
          (current) =>
            current.filter(
              (id) =>
                !visibleIds.includes(
                  id,
                ),
            ),
        );

        return;
      }


      setSelectedIds(
        (current) => [
          ...new Set([
            ...current,
            ...visibleIds,
          ]),
        ],
      );
    };


  /*
   * -----------------------------------------------------------
   * SELECTED LEADS → CAMPAIGN
   * -----------------------------------------------------------
   *
   * Selected lead IDs are stored locally and also passed through
   * React Router state.
   *
   * This allows Campaign Builder to recover the selected leads
   * even after navigation/reload.
   */

  const createCampaignFromSelected =
    () => {
      if (
        selectedIds.length ===
        0
      ) {
        toast.info(
          "Select at least one lead first.",
        );

        return;
      }


      const selectedLeadIds =
        selectedIds.map(
          (id) =>
            String(id),
        );


      localStorage.setItem(
        "leadflow_selected_lead_ids",
        JSON.stringify(
          selectedLeadIds,
        ),
      );


      navigate(
        "/campaigns/new",
        {
          state: {
            selectedLeadIds,
            selectedCount:
              selectedLeadIds.length,
          },
        },
      );
    };


  const goToPage = (
    nextPage,
  ) => {
    setPage(
      Math.max(
        1,
        Math.min(
          nextPage,
          totalPages,
        ),
      ),
    );
  };


  return (
    <main className="leads-page">
      <div className="leads-shell">

        {/* HEADER */}

        <header className="leads-header">
          <div>

            <div className="leads-eyebrow">
              LEAD MANAGEMENT
            </div>


            <h1>
              Your business
              <span>
                {" "}
                pipeline.
              </span>
            </h1>


            <p className="leads-description">
              Review discovered businesses,
              filter opportunities, and
              prepare leads for website
              analysis and outreach.
            </p>

          </div>


          <button
            type="button"
            className="leads-refresh-button"
            onClick={
              loadLeads
            }
            disabled={
              loading
            }
          >

            <LoaderCircle
              size={16}
              className={
                loading
                  ? "leads-spin"
                  : ""
              }
            />

            Refresh

          </button>
        </header>


        {/* SUMMARY */}

        <section className="leads-summary">

          <div className="lead-summary-card maroon">

            <div className="lead-summary-icon">
              <Users size={18} />
            </div>

            <div>
              <span>
                Total leads
              </span>

              <strong>
                {leads.length}
              </strong>
            </div>

          </div>


          <div className="lead-summary-card blue">

            <div className="lead-summary-icon">
              <Globe size={18} />
            </div>

            <div>
              <span>
                With website
              </span>

              <strong>
                {totalWithWebsite}
              </strong>
            </div>

          </div>


          <div className="lead-summary-card sage">

            <div className="lead-summary-icon">
              <Target size={18} />
            </div>

            <div>
              <span>
                No website
              </span>

              <strong>
                {totalWithoutWebsite}
              </strong>
            </div>

          </div>

        </section>


        {/* FILTER PANEL */}

        <section className="leads-filter-panel">

          <div className="leads-filter-top">

            <div>

              <span className="leads-panel-label">
                LEAD DATABASE
              </span>

              <h2>
                Search and filter leads
              </h2>

            </div>


            <div className="leads-filter-icon">
              <SlidersHorizontal
                size={19}
              />
            </div>

          </div>


          <div className="leads-filters">

            <div className="leads-search">

              <Search size={17} />

              <input
                type="text"
                value={search}
                onChange={(
                  event,
                ) => {
                  setSearch(
                    event.target.value,
                  );

                  setPage(1);
                }}
                placeholder="Search business, industry, location..."
              />


              {search && (
                <button
                  type="button"
                  onClick={() => {
                    setSearch(
                      "",
                    );

                    setPage(1);
                  }}
                  aria-label="Clear search"
                >
                  <X size={15} />
                </button>
              )}

            </div>


            <select
              value={
                websiteFilter
              }
              onChange={(
                event,
              ) => {
                setWebsiteFilter(
                  event.target.value,
                );

                setPage(1);
              }}
            >

              <option value="all">
                All websites
              </option>

              <option value="with">
                With website
              </option>

              <option value="without">
                No website
              </option>

            </select>


            <select
              value={emailFilter}
              onChange={(event) => {
                setEmailFilter(
                  event.target.value,
                );
                setPage(1);
              }}
            >

              <option value="all">
                All emails
              </option>

              <option value="with">
                Has email
              </option>

              <option value="without">
                No email
              </option>

            </select>


            <select
              value={
                qualificationFilter
              }
              onChange={(
                event,
              ) => {
                setQualificationFilter(
                  event.target.value,
                );

                setPage(1);
              }}
            >

              <option value="all">
                All qualification
              </option>

              <option value="qualified">
                Qualified
              </option>

              <option value="ready">
                Outreach ready
              </option>

              <option value="unqualified">
                Unqualified
              </option>

            </select>


            <select
              value={sortBy}
              onChange={(event) => {
                setSortBy(event.target.value);
                setPage(1);
              }}
            >
              <option value="date">Sort: Newest</option>
              <option value="name">Sort: Name</option>
              <option value="industry">Sort: Industry</option>
            </select>


            {hasFilters && (
              <button
                type="button"
                className="leads-clear-button"
                onClick={
                  clearFilters
                }
              >
                Clear
              </button>
            )}

          </div>

        </section>


        {/* RESULTS */}

        <section className="leads-results-section">

          <div className="leads-results-header">

            <div>

              <span className="leads-panel-label">
                RESULTS
              </span>

              <h2>
                {
                  filteredLeads.length
                }{" "}
                {
                  filteredLeads.length ===
                  1
                    ? "lead"
                    : "leads"
                }
              </h2>

            </div>


            <div className="leads-selection-info">

              {selectedIds.length >
                0 && (
                <span>
                  {
                    selectedIds.length
                  }{" "}
                  selected
                </span>
              )}


              {/* NEW CREATE CAMPAIGN BUTTON */}

              {selectedIds.length >
                0 && (
                <button
                  type="button"
                  className="leads-create-campaign-button"
                  onClick={
                    createCampaignFromSelected
                  }
                >
                  Create Campaign
                </button>
              )}


              <button
                type="button"
                onClick={
                  toggleVisibleLeads
                }
                disabled={
                  paginatedLeads.length ===
                  0
                }
              >
                {selectedVisibleCount ===
                    paginatedLeads.length &&
                  paginatedLeads.length >
                    0
                  ? "Clear visible"
                  : "Select visible"}
              </button>

            </div>

          </div>


          {loading ? (

            <div className="leads-empty-state">

              <div className="leads-empty-icon">
                <LoaderCircle
                  size={24}
                  className="leads-spin"
                />
              </div>

              <h3>
                Loading your leads
              </h3>

              <p>
                Fetching the latest
                businesses from your
                lead database.
              </p>

            </div>

          ) : filteredLeads.length ===
            0 ? (

            <div className="leads-empty-state">

              <div className="leads-empty-icon">
                <Users size={23} />
              </div>

              <h3>
                {leads.length ===
                0
                  ? "No leads yet"
                  : "No leads match your filters"}
              </h3>

              <p>
                {leads.length ===
                0
                  ? "Discover businesses first and your leads will appear here."
                  : "Try changing your search or filters to see more leads."}
              </p>


              {hasFilters && (
                <button
                  type="button"
                  className="leads-empty-action"
                  onClick={
                    clearFilters
                  }
                >
                  Clear filters
                </button>
              )}

            </div>

          ) : (

            <div className="leads-table-wrapper">

              <div className="leads-table-head">

                <span className="lead-table-check">

                  <button
                    type="button"
                    onClick={
                      toggleVisibleLeads
                    }
                    aria-label="Select visible leads"
                  >

                    <span
                      className={
                        selectedVisibleCount ===
                          paginatedLeads.length
                          ? "checked"
                          : ""
                      }
                    >

                      {selectedVisibleCount ===
                        paginatedLeads.length &&
                        paginatedLeads.length >
                          0 && (
                          <span />
                        )}

                    </span>

                  </button>

                </span>


                <span>
                  Business
                </span>

                <span>
                  Location
                </span>

                <span>
                  Contact
                </span>

                <span>
                  Website
                </span>

                <span>
                  Email
                </span>

              </div>


              <div className="leads-table-body">

                {paginatedLeads.map(
                  (
                    lead,
                    index,
                  ) => {

                    const absoluteIndex =
                      (currentPage -
                        1) *
                        pageSize +
                      index;


                    const leadId =
                      getLeadId(
                        lead,
                        absoluteIndex,
                      );


                    const website =
                      getWebsite(
                        lead,
                      );


                    const email =
                      getEmail(
                        lead,
                      );


                    const phone =
                      getPhone(
                        lead,
                      );


                    const isSelected =
                      selectedIds.includes(
                        leadId,
                      );


                    return (
                      <article
                        key={
                          leadId
                        }
                        className={`lead-row ${
                          isSelected
                            ? "selected"
                            : ""
                        }`}
                      >

                        <div className="lead-row-check">

                          <button
                            type="button"
                            onClick={() =>
                              toggleLead(
                                leadId,
                              )
                            }
                            aria-label={`Select ${getLeadName(
                              lead,
                            )}`}
                          >

                            <span
                              className={
                                isSelected
                                  ? "checked"
                                  : ""
                              }
                            >

                              {isSelected && (
                                <span />
                              )}

                            </span>

                          </button>

                        </div>


                        <div className="lead-business-cell">

                          <div className="lead-business-avatar">
                            {getLeadName(
                              lead,
                            )
                              .charAt(
                                0,
                              )
                              .toUpperCase()}
                          </div>


                          <div>

                            <strong>
                              {getLeadName(
                                lead,
                              )}
                            </strong>

                            <span>
                              {getIndustry(
                                lead,
                              )}
                            </span>

                          </div>

                        </div>


                        <div className="lead-location-cell">

                          <MapPin
                            size={14}
                          />

                          <span>
                            {getLocation(
                              lead,
                            )}
                          </span>

                        </div>


                        <div className="lead-contact-cell">

                          {email && (
                            <div>

                              <Mail
                                size={13}
                              />

                              <span>
                                {email}
                              </span>

                            </div>
                          )}


                          {phone && (
                            <div>

                              <Phone
                                size={13}
                              />

                              <span>
                                {phone}
                              </span>

                            </div>
                          )}


                          {!email &&
                            !phone && (
                              <span className="lead-not-available">
                                No contact
                              </span>
                            )}

                        </div>


                        <div className="lead-website-cell">

                          {website ? (

                            <a
                              href={
                                website
                              }
                              target="_blank"
                              rel="noreferrer"
                            >

                              <Globe
                                size={14}
                              />

                              Website

                            </a>

                          ) : (

                            <span className="lead-no-website">
                              No website
                            </span>

                          )}

                        </div>


                        <div className="lead-email-col">

                          {email ? (
                            <a
                              href={`mailto:${email}`}
                              className="lead-email-link"
                            >
                              <Mail size={13} />
                              <span>{email}</span>
                            </a>
                          ) : (
                            <span className="lead-not-available">
                              No email
                            </span>
                          )}

                        </div>

                      </article>
                    );
                  },
                )}

              </div>

            </div>
          )}


          {/* PAGINATION */}

          {filteredLeads.length >
            0 && (

            <div className="leads-pagination">

              <span>

                Showing{" "}

                {Math.min(
                  (currentPage -
                    1) *
                    pageSize +
                    1,
                  filteredLeads.length,
                )}

                {" - "}

                {Math.min(
                  currentPage *
                    pageSize,
                  filteredLeads.length,
                )}{" "}

                of{" "}
                {
                  filteredLeads.length
                }

              </span>


              <div className="leads-pagination-controls">

                <button
                  type="button"
                  onClick={() =>
                    goToPage(
                      currentPage -
                        1,
                    )
                  }
                  disabled={
                    currentPage ===
                    1
                  }
                  aria-label="Previous page"
                >
                  <ChevronLeft
                    size={16}
                  />
                </button>


                <span>
                  {
                    currentPage
                  }{" "}
                  /{" "}
                  {
                    totalPages
                  }
                </span>


                <button
                  type="button"
                  onClick={() =>
                    goToPage(
                      currentPage +
                        1,
                    )
                  }
                  disabled={
                    currentPage ===
                    totalPages
                  }
                  aria-label="Next page"
                >
                  <ChevronRight
                    size={16}
                  />
                </button>

              </div>

            </div>
          )}

        </section>

      </div>
    </main>
  );
}


export default LeadsPage;