import { Link } from "react-router-dom";
import "./LegalPage.css";

const APP_NAME   = "LeadFlow AI";
const COMPANY    = "SoftPeak Technologies";
const CONTACT    = "technologiessoftpeak@gmail.com";
const SITE_URL   = "https://ai-lead-generation-platform-one.vercel.app";
const UPDATED_AT = "November 14, 2026";

function TermsPage() {
  return (
    <div className="legal-page">

      {/* ── Nav ─────────────────────────────────── */}
      <nav className="legal-nav">
        <Link to="/login" className="legal-logo">
          <span className="legal-logo-icon">⚡</span>
          {APP_NAME}
        </Link>
        <div className="legal-nav-links">
          <Link to="/privacy-policy">Privacy Policy</Link>
          <Link to="/terms" className="legal-nav-active">Terms of Service</Link>
          <Link to="/login" className="legal-nav-btn">Sign In</Link>
        </div>
      </nav>

      {/* ── Hero ────────────────────────────────── */}
      <header className="legal-hero">
        <div className="legal-hero-grid" />
        <div className="legal-hero-inner">
          <span className="legal-badge">Legal · Terms</span>
          <h1>Terms of Service</h1>
          <p className="legal-hero-sub">
            By using our platform, you agree to these terms. Please read them carefully —
            they govern your rights, responsibilities, and our commitment to you.
          </p>
          <div className="legal-hero-pills">
            <span className="legal-hero-pill">📋 Fair Use Policy</span>
            <span className="legal-hero-pill">⚖️ CAN-SPAM Compliant</span>
            <span className="legal-hero-pill">🌍 GDPR &amp; CASL</span>
            <span className="legal-hero-pill">🔑 OAuth 2.0 Integration</span>
          </div>
          <p className="legal-hero-date">Last updated: {UPDATED_AT}</p>
        </div>
      </header>

      {/* ── Body ────────────────────────────────── */}
      <main className="legal-body">

        <section className="legal-section">
          <h2>1. Acceptance of Terms</h2>
          <p>
            By accessing or using <strong>{APP_NAME}</strong> (the "Service"), operated by{" "}
            <strong>{COMPANY}</strong> ("we", "us", or "our"), you agree to be bound by these
            Terms of Service ("Terms"). If you do not agree, you may not use the Service.
          </p>
          <p>
            These Terms apply to all users, including registered account holders and visitors.
          </p>
        </section>

        <section className="legal-section">
          <h2>2. Description of Service</h2>
          <p>
            {APP_NAME} is an AI-powered B2B lead generation and cold email outreach platform
            that enables businesses to:
          </p>
          <ul>
            <li>Discover local business leads using Google Places and web scraping</li>
            <li>Qualify leads based on their online presence and website status</li>
            <li>Generate personalized outreach emails using AI</li>
            <li>Send cold emails via connected Gmail accounts (Google OAuth)</li>
            <li>Monitor email delivery, replies, and campaign analytics</li>
            <li>Manage automated follow-up sequences</li>
          </ul>
        </section>

        <section className="legal-section">
          <h2>3. Account Registration</h2>
          <p>
            To use the Service, you must create an account with a valid email address and
            password. You are responsible for:
          </p>
          <ul>
            <li>Maintaining the confidentiality of your account credentials</li>
            <li>All activity that occurs under your account</li>
            <li>Notifying us immediately of any unauthorized access at <a href={`mailto:${CONTACT}`}>{CONTACT}</a></li>
          </ul>
          <p>
            You must be at least 18 years old and have the legal authority to enter into these
            Terms on behalf of yourself or your organization.
          </p>
        </section>

        <section className="legal-section">
          <h2>4. Google OAuth &amp; Gmail Integration</h2>
          <p>
            The Service allows you to connect your Google/Gmail account via OAuth 2.0 to send
            outreach emails. By connecting your Gmail account:
          </p>
          <ul>
            <li>You authorize {APP_NAME} to send emails on your behalf through Gmail API</li>
            <li>You confirm you are the authorized owner of the connected Gmail account</li>
            <li>You understand that sent emails will appear in your Gmail "Sent" folder</li>
            <li>
              You may revoke access at any time via{" "}
              <a href="https://myaccount.google.com/permissions" target="_blank" rel="noreferrer">
                Google Account Permissions
              </a>
            </li>
          </ul>
          <p>
            We use Gmail data solely to send emails you explicitly instruct us to send.
            Our use complies with the{" "}
            <a
              href="https://developers.google.com/terms/api-services-user-data-policy"
              target="_blank"
              rel="noreferrer"
            >
              Google API Services User Data Policy
            </a>.
          </p>
        </section>

        <section className="legal-section">
          <h2>5. Acceptable Use Policy</h2>
          <p>You agree to use the Service only for lawful purposes. You must <strong>NOT</strong>:</p>
          <ul>
            <li>Send spam, unsolicited bulk emails, or violate CAN-SPAM, GDPR, CASL, or any applicable anti-spam law</li>
            <li>Send emails to recipients who have opted out or unsubscribed</li>
            <li>Use the Service for phishing, fraud, or deceptive practices</li>
            <li>Scrape, harvest, or collect data in violation of a website's Terms of Service</li>
            <li>Impersonate any person or organization</li>
            <li>Use the Service to send malware, viruses, or harmful content</li>
            <li>Attempt to reverse-engineer, hack, or disrupt the Service</li>
            <li>Use the Service in any way that violates applicable local, national, or international laws</li>
          </ul>
          <p>
            Violation of this policy may result in immediate account suspension or termination
            without refund.
          </p>
        </section>

        <section className="legal-section">
          <h2>6. Email Sending Limits &amp; Compliance</h2>
          <p>
            You are solely responsible for compliance with all applicable email marketing laws,
            including:
          </p>
          <ul>
            <li><strong>CAN-SPAM Act (USA)</strong> — Include your business address; honor unsubscribe requests within 10 days</li>
            <li><strong>GDPR (EU/UK)</strong> — Ensure a lawful basis for processing recipient data</li>
            <li><strong>CASL (Canada)</strong> — Obtain express or implied consent before sending commercial emails</li>
          </ul>
          <p>
            The platform enforces daily sending limits per Gmail account to protect your
            deliverability. Attempting to bypass these limits is prohibited.
          </p>
        </section>

        <section className="legal-section">
          <h2>7. AI-Generated Content</h2>
          <p>
            The Service uses AI to generate email drafts and lead qualification insights. You
            acknowledge that:
          </p>
          <ul>
            <li>AI-generated content may contain errors or inaccuracies</li>
            <li>You are responsible for reviewing all AI-generated emails before sending</li>
            <li>We do not guarantee the accuracy, completeness, or fitness of AI output</li>
            <li>AI-generated emails must comply with all applicable laws and this Terms of Service</li>
          </ul>
        </section>

        <section className="legal-section">
          <h2>8. Intellectual Property</h2>
          <p>
            The Service, including its software, design, algorithms, and content (excluding
            user-generated content), is owned by {COMPANY} and protected by intellectual
            property laws. You are granted a limited, non-exclusive, non-transferable license
            to use the Service for its intended purpose.
          </p>
          <p>
            You retain ownership of all lead data, email content, and campaign data you create
            using the Service.
          </p>
        </section>

        <section className="legal-section">
          <h2>9. Privacy</h2>
          <p>
            Your use of the Service is also governed by our{" "}
            <Link to="/privacy-policy">Privacy Policy</Link>, which is incorporated into these
            Terms by reference.
          </p>
        </section>

        <section className="legal-section">
          <h2>10. Disclaimers &amp; Limitation of Liability</h2>
          <p>
            THE SERVICE IS PROVIDED "AS IS" AND "AS AVAILABLE" WITHOUT WARRANTIES OF ANY KIND,
            EXPRESS OR IMPLIED, INCLUDING MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, OR
            NON-INFRINGEMENT.
          </p>
          <p>
            WE DO NOT WARRANT THAT THE SERVICE WILL BE UNINTERRUPTED, ERROR-FREE, OR THAT
            EMAILS WILL BE DELIVERED. RESULTS FROM LEAD GENERATION AND EMAIL OUTREACH VARY AND
            ARE NOT GUARANTEED.
          </p>
          <p>
            TO THE MAXIMUM EXTENT PERMITTED BY LAW, {COMPANY.toUpperCase()} SHALL NOT BE
            LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES
            ARISING FROM YOUR USE OF THE SERVICE.
          </p>
        </section>

        <section className="legal-section">
          <h2>11. Indemnification</h2>
          <p>
            You agree to indemnify and hold harmless {COMPANY}, its officers, employees, and
            agents from any claims, losses, damages, or expenses (including attorneys' fees)
            arising from your use of the Service, your violation of these Terms, or your
            violation of any third party's rights.
          </p>
        </section>

        <section className="legal-section">
          <h2>12. Termination</h2>
          <p>
            We reserve the right to suspend or terminate your account at any time for violation
            of these Terms or applicable law, with or without notice.
          </p>
          <p>
            You may terminate your account at any time by contacting us at{" "}
            <a href={`mailto:${CONTACT}`}>{CONTACT}</a>. Upon termination, your data will be
            deleted within 30 days per our Privacy Policy.
          </p>
        </section>

        <section className="legal-section">
          <h2>13. Changes to Terms</h2>
          <p>
            We may update these Terms from time to time. We will notify you of material changes
            via email. Continued use of the Service after changes take effect constitutes your
            acceptance of the revised Terms.
          </p>
        </section>

        <section className="legal-section">
          <h2>14. Governing Law</h2>
          <p>
            These Terms are governed by the laws applicable to {COMPANY}'s place of business.
            Any disputes shall be resolved through binding arbitration or the courts of that
            jurisdiction.
          </p>
        </section>

        <section className="legal-section">
          <h2>15. Contact Us</h2>
          <p>
            For questions about these Terms, please contact us:
          </p>
          <address>
            <strong>{COMPANY}</strong><br />
            Email: <a href={`mailto:${CONTACT}`}>{CONTACT}</a><br />
            Website: <a href={SITE_URL} target="_blank" rel="noreferrer">{SITE_URL}</a>
          </address>
        </section>

      </main>

      {/* ── Footer ──────────────────────────────── */}
      <footer className="legal-footer">
        <div className="legal-footer-inner">
          <div className="legal-footer-brand">
            <span className="legal-footer-logo">⚡</span>
            <div>
              <strong>AI Lead Generation &amp; Business Outreach Platform</strong>
              <span>by {COMPANY}</span>
            </div>
          </div>
          <p className="legal-footer-desc">
            Empowering businesses with AI-powered lead discovery and email outreach.
            Your data is always secure and private.
          </p>
          <div className="legal-footer-links">
            <Link to="/privacy-policy">Privacy Policy</Link>
            <Link to="/terms">Terms of Service</Link>
            <Link to="/login">Sign In</Link>
            <Link to="/register">Register</Link>
          </div>
          <p className="legal-footer-copy">
            © {new Date().getFullYear()} {COMPANY}. All rights reserved.
          </p>
        </div>
      </footer>

    </div>
  );
}

export default TermsPage;
