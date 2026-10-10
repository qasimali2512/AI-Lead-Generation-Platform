from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.website_issue import WebsiteIssue
from app.models.website_scan import WebsiteScan


# ---------------------------------------------------------
# Issue definition
# ---------------------------------------------------------

@dataclass(frozen=True)
class IssueDefinition:
    category: str
    issue_code: str
    title: str
    severity: str
    evidence: str
    recommendation: str
    current_value: str | None = None
    expected_value: str | None = None


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def text_or_none(
    value: str | None,
) -> str | None:

    if value is None:
        return None

    value = str(value).strip()

    return value or None


# ---------------------------------------------------------
# Build issues
# ---------------------------------------------------------

def analyze_scan(
    scan: WebsiteScan,
) -> list[IssueDefinition]:

    issues: list[IssueDefinition] = []

    # -----------------------------------------------------
    # HTTP / availability
    # -----------------------------------------------------

    if (
        scan.http_status is not None
        and scan.http_status >= 400
    ):
        issues.append(
            IssueDefinition(
                category="technical",
                issue_code="HTTP_ERROR",
                title="Website returns an HTTP error",
                severity="critical",
                evidence=(
                    f"The scanned page returned "
                    f"HTTP {scan.http_status}."
                ),
                recommendation=(
                    "Investigate the server response and "
                    "make sure the main website page "
                    "returns a successful HTTP response."
                ),
                current_value=str(
                    scan.http_status
                ),
                expected_value="2xx successful response",
            )
        )

    # -----------------------------------------------------
    # HTTPS
    # -----------------------------------------------------

    if not scan.is_https:
        issues.append(
            IssueDefinition(
                category="security",
                issue_code="NO_HTTPS",
                title="Website is not using HTTPS",
                severity="critical",
                evidence=(
                    f"The final scanned URL is "
                    f"{scan.final_url or scan.url} "
                    "and does not use HTTPS."
                ),
                recommendation=(
                    "Enable HTTPS with a valid TLS certificate "
                    "and redirect HTTP traffic to HTTPS."
                ),
                current_value="HTTP",
                expected_value="HTTPS",
            )
        )

    # -----------------------------------------------------
    # Page title
    # -----------------------------------------------------

    title = text_or_none(
        scan.title
    )

    if not title:
        issues.append(
            IssueDefinition(
                category="seo",
                issue_code="MISSING_TITLE",
                title="Missing page title",
                severity="high",
                evidence=(
                    "No usable HTML <title> element "
                    "was found on the scanned page."
                ),
                recommendation=(
                    "Add a unique, descriptive page title "
                    "that clearly explains the page and "
                    "matches the business/service intent."
                ),
                current_value="Missing",
                expected_value="One descriptive title",
            )
        )

    elif len(title) > 70:
        issues.append(
            IssueDefinition(
                category="seo",
                issue_code="TITLE_TOO_LONG",
                title="Page title may be too long",
                severity="medium",
                evidence=(
                    f"The detected title contains "
                    f"{len(title)} characters."
                ),
                recommendation=(
                    "Review the title and shorten it where "
                    "appropriate while preserving the primary "
                    "topic and business intent."
                ),
                current_value=f"{len(title)} characters",
                expected_value="Concise descriptive title",
            )
        )

    # -----------------------------------------------------
    # Meta description
    # -----------------------------------------------------

    description = text_or_none(
        scan.meta_description
    )

    if not description:
        issues.append(
            IssueDefinition(
                category="seo",
                issue_code="MISSING_META_DESCRIPTION",
                title="Missing meta description",
                severity="medium",
                evidence=(
                    "No usable meta description was "
                    "detected on the scanned page."
                ),
                recommendation=(
                    "Add a concise, page-specific meta "
                    "description explaining the business "
                    "or page offering."
                ),
                current_value="Missing",
                expected_value="Descriptive meta description",
            )
        )

    elif len(description) > 180:
        issues.append(
            IssueDefinition(
                category="seo",
                issue_code="META_DESCRIPTION_LONG",
                title="Meta description may be too long",
                severity="low",
                evidence=(
                    f"The detected meta description "
                    f"contains {len(description)} characters."
                ),
                recommendation=(
                    "Review the description and remove "
                    "unnecessary text while keeping the "
                    "main value proposition."
                ),
                current_value=(
                    f"{len(description)} characters"
                ),
                expected_value=(
                    "Concise descriptive summary"
                ),
            )
        )

    # -----------------------------------------------------
    # H1
    # -----------------------------------------------------

    if scan.h1_count == 0:
        issues.append(
            IssueDefinition(
                category="seo",
                issue_code="MISSING_H1",
                title="Missing H1 heading",
                severity="high",
                evidence=(
                    "The scanner found zero H1 headings "
                    "on the page."
                ),
                recommendation=(
                    "Add one clear primary H1 heading that "
                    "describes the page's main purpose."
                ),
                current_value="0 H1 headings",
                expected_value="1 primary H1",
            )
        )

    elif scan.h1_count > 1:
        issues.append(
            IssueDefinition(
                category="seo",
                issue_code="MULTIPLE_H1",
                title="Multiple H1 headings detected",
                severity="medium",
                evidence=(
                    f"The scanner found "
                    f"{scan.h1_count} H1 headings."
                ),
                recommendation=(
                    "Review the heading hierarchy and ensure "
                    "the page has a clear primary heading. "
                    "Additional headings should normally use "
                    "appropriate lower-level heading elements."
                ),
                current_value=(
                    f"{scan.h1_count} H1 headings"
                ),
                expected_value="One clear primary H1",
            )
        )

    # -----------------------------------------------------
    # H2
    # -----------------------------------------------------

    if scan.h2_count == 0:
        issues.append(
            IssueDefinition(
                category="content",
                issue_code="NO_H2_HEADINGS",
                title="No H2 headings detected",
                severity="low",
                evidence=(
                    "The scanner found no H2 headings "
                    "on the scanned page."
                ),
                recommendation=(
                    "For content-heavy pages, consider using "
                    "meaningful H2 headings to organize major "
                    "sections."
                ),
                current_value="0 H2 headings",
                expected_value="Meaningful section headings where appropriate",
            )
        )

    # -----------------------------------------------------
    # Viewport
    # -----------------------------------------------------

    if not scan.has_viewport:
        issues.append(
            IssueDefinition(
                category="mobile",
                issue_code="MISSING_VIEWPORT",
                title="Missing mobile viewport configuration",
                severity="high",
                evidence=(
                    "No viewport meta tag was detected."
                ),
                recommendation=(
                    "Add a responsive viewport meta tag so "
                    "the page can scale correctly on mobile devices."
                ),
                current_value="Missing",
                expected_value="Viewport meta configuration",
            )
        )

    # -----------------------------------------------------
    # Images / alt
    # -----------------------------------------------------

    if (
        scan.image_count > 0
        and scan.images_without_alt > 0
    ):
        issues.append(
            IssueDefinition(
                category="accessibility",
                issue_code="IMAGES_MISSING_ALT",
                title="Images without alt text detected",
                severity="medium",
                evidence=(
                    f"{scan.images_without_alt} of "
                    f"{scan.image_count} detected images "
                    "do not have usable alt attributes."
                ),
                recommendation=(
                    "Add meaningful alternative text to "
                    "informative images. Use empty alt text "
                    "for purely decorative images where appropriate."
                ),
                current_value=(
                    f"{scan.images_without_alt} missing alt"
                ),
                expected_value="Relevant images have appropriate alt text",
            )
        )

    # -----------------------------------------------------
    # Canonical
    # -----------------------------------------------------

    if not scan.has_canonical:
        issues.append(
            IssueDefinition(
                category="seo",
                issue_code="MISSING_CANONICAL",
                title="Canonical URL not detected",
                severity="low",
                evidence=(
                    "No canonical link element was detected "
                    "on the scanned page."
                ),
                recommendation=(
                    "Consider adding a canonical URL where "
                    "canonicalization is relevant to the page."
                ),
                current_value="Missing",
                expected_value="Canonical URL where appropriate",
            )
        )

    # -----------------------------------------------------
    # Robots
    # -----------------------------------------------------

    if not scan.robots_txt_found:
        issues.append(
            IssueDefinition(
                category="seo",
                issue_code="ROBOTS_TXT_NOT_FOUND",
                title="robots.txt was not detected",
                severity="low",
                evidence=(
                    "A robots.txt file was not successfully "
                    "retrieved at the site's root."
                ),
                recommendation=(
                    "Review whether the site should publish "
                    "a robots.txt file with appropriate crawler "
                    "directives."
                ),
                current_value="Not detected",
                expected_value="robots.txt where appropriate",
            )
        )

    # -----------------------------------------------------
    # Sitemap
    # -----------------------------------------------------

    if not scan.sitemap_found:
        issues.append(
            IssueDefinition(
                category="seo",
                issue_code="SITEMAP_NOT_FOUND",
                title="XML sitemap was not detected",
                severity="low",
                evidence=(
                    "An XML sitemap was not successfully "
                    "retrieved from the expected sitemap.xml path."
                ),
                recommendation=(
                    "Review the site's XML sitemap setup and "
                    "make sure important indexable pages can "
                    "be discovered by search engines."
                ),
                current_value="Not detected",
                expected_value="XML sitemap where appropriate",
            )
        )

    # -----------------------------------------------------
    # Language
    # -----------------------------------------------------

    if not scan.html_language:
        issues.append(
            IssueDefinition(
                category="accessibility",
                issue_code="MISSING_HTML_LANGUAGE",
                title="HTML language attribute not detected",
                severity="low",
                evidence=(
                    "The root HTML element does not appear "
                    "to define a language attribute."
                ),
                recommendation=(
                    "Set an appropriate lang attribute on the "
                    "HTML element to help browsers and assistive "
                    "technologies interpret the page language."
                ),
                current_value="Missing",
                expected_value="Appropriate HTML lang attribute",
            )
        )

    # -----------------------------------------------------
    # Response time
    # -----------------------------------------------------

    if (
        scan.response_time_ms is not None
        and scan.response_time_ms > 3000
    ):
        issues.append(
            IssueDefinition(
                category="performance",
                issue_code="SLOW_SERVER_RESPONSE",
                title="Slow initial server response",
                severity="medium",
                evidence=(
                    f"The scanner measured an initial response "
                    f"time of approximately "
                    f"{scan.response_time_ms} ms."
                ),
                recommendation=(
                    "Investigate server response performance, "
                    "backend processing, hosting configuration, "
                    "caching and database queries."
                ),
                current_value=(
                    f"{scan.response_time_ms} ms"
                ),
                expected_value=(
                    "Lower server response time"
                ),
            )
        )

    # -----------------------------------------------------
    # Page size
    # -----------------------------------------------------

    if (
        scan.page_size_bytes is not None
        and scan.page_size_bytes > 2_000_000
    ):
        size_mb = (
            scan.page_size_bytes
            / 1_000_000
        )

        issues.append(
            IssueDefinition(
                category="performance",
                issue_code="LARGE_HTML_DOCUMENT",
                title="Large HTML document detected",
                severity="medium",
                evidence=(
                    f"The downloaded HTML document is "
                    f"approximately {size_mb:.2f} MB."
                ),
                recommendation=(
                    "Review unnecessary HTML, embedded content, "
                    "repeated markup and page-generation overhead. "
                    "Use appropriate caching and compression."
                ),
                current_value=(
                    f"{size_mb:.2f} MB"
                ),
                expected_value=(
                    "Reasonably sized HTML document"
                ),
            )
        )

    return issues


# ---------------------------------------------------------
# Persist issues
# ---------------------------------------------------------

def save_issues(
    db: Session,
    scan: WebsiteScan,
    definitions: list[IssueDefinition],
) -> list[WebsiteIssue]:

    # Remove previous issues for this scan so rerunning
    # the issue engine always produces a clean result.
    db.execute(
        delete(WebsiteIssue).where(
            WebsiteIssue.scan_id == scan.id
        )
    )

    issues: list[WebsiteIssue] = []

    for definition in definitions:

        issue = WebsiteIssue(
            user_id=scan.user_id,
            lead_id=scan.lead_id,
            scan_id=scan.id,

            category=definition.category,
            issue_code=definition.issue_code,

            title=definition.title,
            severity=definition.severity,

            evidence=definition.evidence,
            recommendation=definition.recommendation,

            current_value=definition.current_value,
            expected_value=definition.expected_value,

            status="open",
        )

        db.add(issue)

        issues.append(issue)

    try:
        db.commit()

        for issue in issues:
            db.refresh(issue)

    except Exception:
        db.rollback()
        raise

    return issues


# ---------------------------------------------------------
# Analyze one scan
# ---------------------------------------------------------

def analyze_and_save_scan(
    db: Session,
    user_id: UUID,
    lead_id: UUID,
    scan_id: UUID,
) -> list[WebsiteIssue]:

    scan = db.scalar(
        select(WebsiteScan).where(
            WebsiteScan.id == scan_id,
            WebsiteScan.user_id == user_id,
            WebsiteScan.lead_id == lead_id,
        )
    )

    if scan is None:
        raise ValueError(
            "Website scan not found."
        )

    definitions = analyze_scan(
        scan
    )

    return save_issues(
        db=db,
        scan=scan,
        definitions=definitions,
    )


# ---------------------------------------------------------
# Latest scan issue analysis
# ---------------------------------------------------------

def analyze_latest_scan(
    db: Session,
    user_id: UUID,
    lead_id: UUID,
) -> tuple[WebsiteScan, list[WebsiteIssue]]:

    scan = db.scalar(
        select(WebsiteScan)
        .where(
            WebsiteScan.user_id == user_id,
            WebsiteScan.lead_id == lead_id,
            WebsiteScan.scan_status == "completed",
        )
        .order_by(
            WebsiteScan.scanned_at.desc()
        )
        .limit(1)
    )

    if scan is None:
        raise ValueError(
            "No completed website scan found."
        )

    definitions = analyze_scan(
        scan
    )

    issues = save_issues(
        db=db,
        scan=scan,
        definitions=definitions,
    )

    return scan, issues