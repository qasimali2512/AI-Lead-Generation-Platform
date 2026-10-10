from html import escape
from typing import Any


def _safe(value: str | None) -> str:
    return escape(str(value or ""))


def _paragraphs(body_text: str) -> str:
    return "".join(
        '<p style="margin:0 0 16px;font-size:15px;line-height:1.7;color:#30343b;">'
        f"{_safe(paragraph.strip()).replace(chr(10), '<br>')}</p>"
        for paragraph in body_text.split("\n\n") if paragraph.strip()
    )


def _contact_line(phone: str | None, website: str | None) -> str:
    items: list[str] = []
    if phone:
        items.append(_safe(phone))
    if website:
        safe_website = _safe(website)
        items.append(f'<a href="{safe_website}" style="color:#52606d;text-decoration:none;">{safe_website}</a>')
    return " &nbsp;|&nbsp; ".join(items)


def render_initial_email(
    *, body_text: str, sender_name: str | None, sender_role: str | None,
    agency_name: str, logo_url: str | None, primary_color: str = "#1264a3",
    secondary_color: str = "#36c5f0", phone: str | None = None,
    website: str | None = None, unsubscribe_url: str | None = None,
    issues: list[dict[str, Any]] | None = None, address: str | None = None,
) -> str:
    """Gmail-compatible outreach email with matching header and signature logos."""
    del primary_color, secondary_color, issues
    logo_html = (
        f'<img src="{_safe(logo_url)}" alt="{_safe(agency_name)}" style="display:block;max-width:165px;max-height:58px;width:auto;height:auto;border:0;" />'
        if logo_url else ""
    )
    unsubscribe_html = (
        f'<a href="{_safe(unsubscribe_url)}" style="color:#7a869a;text-decoration:underline;">Unsubscribe</a>'
        if unsubscribe_url else "To opt out, reply to this email with “unsubscribe”."
    )
    return f"""<!doctype html>
<html><body style="margin:0;padding:0;background:#ffffff;font-family:Arial,Helvetica,sans-serif;">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"><tr><td align="center" style="padding:24px 12px;">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width:640px;background:#ffffff;border-top:4px solid #1f6b4f;">
<tr><td style="padding:28px 28px 16px;">{logo_html}</td></tr>
<tr><td style="padding:14px 28px 0;">{_paragraphs(body_text)}</td></tr>
<tr><td style="padding:18px 28px 24px;"><div style="border-top:1px solid #e6eaf0;padding-top:18px;">
<div style="margin-top:12px;font-size:14px;font-weight:700;color:#172b4d;">{_safe(sender_name) or _safe(agency_name)}</div>
<div style="margin-top:3px;font-size:12px;color:#667085;">{_safe(sender_role)}</div>
<div style="margin-top:5px;font-size:12px;color:#52606d;">{_safe(agency_name)}</div>
<div style="margin-top:9px;font-size:12px;color:#52606d;line-height:1.6;">{_contact_line(phone, website)}</div>
<div style="margin-top:7px;font-size:11px;color:#7a869a;line-height:1.55;">{_safe(address)}</div>
<div style="margin-top:14px;font-size:11px;color:#7a869a;line-height:1.55;">{unsubscribe_html}</div>
<div style="margin-top:16px;">{logo_html}</div>
</div></td></tr></table></td></tr></table></body></html>"""


def render_follow_up_email(**kwargs: Any) -> str:
    return render_initial_email(**kwargs)
