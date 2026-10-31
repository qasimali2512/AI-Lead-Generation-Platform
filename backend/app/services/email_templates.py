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


def _logo_block(agency_name: str, logo_url: str | None, primary_color: str = "#1f6b4f") -> str:
    """
    Logo render karo:
    - Agar logo_url ek valid HTTPS URL hai → <img> tag use karo (remote load, koi attachment nahi)
    - Warna → Pure HTML/CSS wordmark (professional styled text, koi image nahi)

    Inline CID images (cid:...) kabhi use nahi karta — wo attachment ban'ti hain aur
    Gmail/Outlook mein broken dikhti hain.
    """
    safe_name = _safe(agency_name)

    # Sirf external HTTPS URL pe hi real image use karo
    if logo_url and logo_url.startswith("https://"):
        return (
            f'<img src="{_safe(logo_url)}" alt="{safe_name}" '
            f'style="display:block;max-width:160px;max-height:55px;'
            f'width:auto;height:auto;border:0;" />'
        )

    # ─── Pure CSS Wordmark — koi image nahi, koi attachment nahi ───
    # Agency name ko 2 parts mein split karo (pehla word alag color)
    words = agency_name.strip().split()
    if len(words) >= 2:
        first = _safe(words[0])
        rest  = _safe(" ".join(words[1:]))
        wordmark = (
            f'<span style="color:{_safe(primary_color)};font-weight:800;">{first}</span>'
            f'<span style="color:#172b4d;font-weight:800;"> {rest}</span>'
        )
    else:
        wordmark = f'<span style="color:{_safe(primary_color)};font-weight:800;">{safe_name}</span>'

    return (
        f'<div style="display:inline-block;'
        f'font-family:Arial,Helvetica,sans-serif;'
        f'font-size:20px;letter-spacing:-0.3px;line-height:1;">'
        f'{wordmark}'
        f'</div>'
    )


def render_initial_email(
    *, body_text: str, sender_name: str | None, sender_role: str | None,
    agency_name: str, logo_url: str | None, primary_color: str = "#1f6b4f",
    secondary_color: str = "#c49a4a", phone: str | None = None,
    website: str | None = None, unsubscribe_url: str | None = None,
    issues: list[dict[str, Any]] | None = None, address: str | None = None,
    booking_url: str | None = None,
) -> str:
    """
    Gmail-compatible professional outreach email.
    Logo = CSS wordmark (no image attachment ever).
    Agar brand settings mein valid HTTPS logo URL ho to woh use hoga (remote load).
    """
    del secondary_color, issues, booking_url  # reserved for future use

    logo_html = _logo_block(agency_name, logo_url, primary_color)

    unsubscribe_html = (
        f'<a href="{_safe(unsubscribe_url)}" style="color:#7a869a;text-decoration:underline;">Unsubscribe</a>'
        if unsubscribe_url else "To opt out, reply to this email with \u201cunsubscribe\u201d."
    )

    border_color = _safe(primary_color) if primary_color else "#1f6b4f"

    return f"""<!doctype html>
<html><body style="margin:0;padding:0;background:#f5f5f5;font-family:Arial,Helvetica,sans-serif;">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"><tr><td align="center" style="padding:24px 12px;">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width:620px;background:#ffffff;border-top:4px solid {border_color};border-radius:4px;">
<tr><td style="padding:28px 32px 18px;">{logo_html}</td></tr>
<tr><td style="padding:8px 32px 0;">{_paragraphs(body_text)}</td></tr>
<tr><td style="padding:20px 32px 28px;"><div style="border-top:1px solid #e6eaf0;padding-top:18px;">
<div style="margin-top:12px;font-size:14px;font-weight:700;color:#172b4d;">{_safe(sender_name) or _safe(agency_name)}</div>
<div style="margin-top:3px;font-size:12px;color:#667085;">{_safe(sender_role)}</div>
<div style="margin-top:4px;font-size:12px;color:#52606d;">{_safe(agency_name)}</div>
<div style="margin-top:9px;font-size:12px;color:#52606d;line-height:1.6;">{_contact_line(phone, website)}</div>
<div style="margin-top:7px;font-size:11px;color:#7a869a;line-height:1.55;">{_safe(address)}</div>
<div style="margin-top:18px;">{logo_html}</div>
<div style="margin-top:14px;font-size:11px;color:#7a869a;line-height:1.55;">{unsubscribe_html}</div>
</div></td></tr></table></td></tr></table></body></html>"""


def render_follow_up_email(**kwargs: Any) -> str:
    return render_initial_email(**kwargs)
