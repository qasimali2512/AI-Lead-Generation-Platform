import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import "./HomePage.css";

/* ── Animated counter hook ──────────────────────────────── */
function useCounter(target, duration = 2000, start = false) {
  const [count, setCount] = useState(0);
  useEffect(() => {
    if (!start) return;
    let startTime = null;
    const step = (timestamp) => {
      if (!startTime) startTime = timestamp;
      const progress = Math.min((timestamp - startTime) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setCount(Math.floor(eased * target));
      if (progress < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [target, duration, start]);
  return count;
}

/* ── Intersection observer hook ─────────────────────────── */
function useInView(threshold = 0.15) {
  const ref = useRef(null);
  const [inView, setInView] = useState(false);
  useEffect(() => {
    const obs = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) setInView(true); },
      { threshold }
    );
    if (ref.current) obs.observe(ref.current);
    return () => obs.disconnect();
  }, [threshold]);
  return [ref, inView];
}

/* ── Feature cards data ─────────────────────────────────── */
const FEATURES = [
  {
    icon: "🔍",
    title: "AI Lead Discovery",
    desc: "Google Places + web scraping se automatically hazaron local businesses discover karo. Smart filters se sirf best leads rakho.",
    color: "blue",
  },
  {
    icon: "🤖",
    title: "AI Email Generation",
    desc: "Har lead ke liye personalized outreach email AI se generate karo. Business ka naam, location aur issues automatically include hote hain.",
    color: "maroon",
  },
  {
    icon: "📧",
    title: "Gmail Outreach",
    desc: "Apne Gmail account se directly emails bhejo. Automated scheduling, follow-ups aur reply tracking sab ek jagah.",
    color: "sage",
  },
  {
    icon: "📊",
    title: "Campaign Analytics",
    desc: "Delivery rate, open rate, reply rate aur conversion sab track karo. Real-time dashboard se apni performance monitor karo.",
    color: "indigo",
  },
  {
    icon: "🌐",
    title: "Website Scanner",
    desc: "Leads ki websites automatically scan karo. Missing SSL, slow speed, no mobile aur other issues detect karo.",
    color: "gold",
  },
  {
    icon: "⚡",
    title: "Auto Follow-ups",
    desc: "Reply na aane par automatically follow-up emails schedule hoti hain. Conversion rate dramatically improve hota hai.",
    color: "maroon",
  },
];

/* ── How it works steps ─────────────────────────────────── */
const STEPS = [
  { num: "01", title: "Connect Gmail", desc: "Apna Gmail account securely connect karo. OAuth 2.0 se safe aur instant." },
  { num: "02", title: "Discover Leads", desc: "City aur industry select karo — AI hazaron businesses dhund laata hai." },
  { num: "03", title: "AI Emails Generate", desc: "Platform har lead ke liye personalized email draft karta hai automatically." },
  { num: "04", title: "Send & Track", desc: "Emails send karo aur real-time delivery, opens aur replies track karo." },
];

/* ── Stats ──────────────────────────────────────────────── */
const STATS = [
  { value: 10000, suffix: "+", label: "Leads Discovered" },
  { value: 95,    suffix: "%", label: "Email Deliverability" },
  { value: 3,     suffix: "x", label: "More Replies" },
  { value: 80,    suffix: "%", label: "Time Saved" },
];

/* ═══════════════════════════════════════════════════════════
   HomePage Component
═══════════════════════════════════════════════════════════ */
export default function HomePage() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  /* Navbar scroll effect */
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  /* Stats section inview */
  const [statsRef, statsInView] = useInView(0.3);
  const [featuresRef, featuresInView] = useInView(0.1);
  const [stepsRef, stepsInView] = useInView(0.1);

  /* Counters */
  const c0 = useCounter(STATS[0].value, 2200, statsInView);
  const c1 = useCounter(STATS[1].value, 1600, statsInView);
  const c2 = useCounter(STATS[2].value, 1400, statsInView);
  const c3 = useCounter(STATS[3].value, 1800, statsInView);
  const counts = [c0, c1, c2, c3];

  return (
    <div className="hp-root">

      {/* ══════════════════════════════════════════
          NAVBAR
      ══════════════════════════════════════════ */}
      <nav className={`hp-nav ${scrolled ? "hp-nav--scrolled" : ""}`}>
        <div className="hp-nav-inner">

          <Link to="/" className="hp-logo">
            <span className="hp-logo-mark">⚡</span>
            <span className="hp-logo-text">
              AI Lead Generation
              <span className="hp-logo-amp"> & </span>
              Business Outreach
            </span>
          </Link>

          {/* Desktop links */}
          <div className="hp-nav-links">
            <a href="#features" className="hp-nav-link">Features</a>
            <a href="#how-it-works" className="hp-nav-link">How it Works</a>
            <a href="#stats" className="hp-nav-link">Results</a>
          </div>

          <div className="hp-nav-actions">
            <Link to="/login" className="hp-btn-ghost">Sign In</Link>
            <Link to="/register" className="hp-btn-primary">Get Started Free</Link>
          </div>

          {/* Mobile hamburger */}
          <button
            className="hp-hamburger"
            onClick={() => setMenuOpen((v) => !v)}
            aria-label="Toggle menu"
          >
            <span className={menuOpen ? "hp-ham-open" : ""} />
            <span className={menuOpen ? "hp-ham-open" : ""} />
            <span className={menuOpen ? "hp-ham-open" : ""} />
          </button>
        </div>

        {/* Mobile menu */}
        <div className={`hp-mobile-menu ${menuOpen ? "hp-mobile-menu--open" : ""}`}>
          <a href="#features"    onClick={() => setMenuOpen(false)}>Features</a>
          <a href="#how-it-works" onClick={() => setMenuOpen(false)}>How it Works</a>
          <a href="#stats"       onClick={() => setMenuOpen(false)}>Results</a>
          <Link to="/login"    onClick={() => setMenuOpen(false)}>Sign In</Link>
          <Link to="/register" onClick={() => setMenuOpen(false)} className="hp-mobile-cta">Get Started Free</Link>
        </div>
      </nav>


      {/* ══════════════════════════════════════════
          HERO
      ══════════════════════════════════════════ */}
      <section className="hp-hero">
        {/* Animated background blobs */}
        <div className="hp-blob hp-blob-1" />
        <div className="hp-blob hp-blob-2" />
        <div className="hp-blob hp-blob-3" />

        {/* Grid overlay */}
        <div className="hp-grid-overlay" />

        <div className="hp-hero-inner">
          <div className="hp-hero-badge">
            <span className="hp-badge-dot" />
            AI-Powered • Automated • Scalable
          </div>

          <h1 className="hp-hero-title">
            <span className="hp-hero-line">AI Lead Generation</span>
            <span className="hp-hero-line hp-hero-line--accent">& Business Outreach</span>
            <span className="hp-hero-line">Platform</span>
          </h1>

          <p className="hp-hero-sub">
            Local businesses discover karo, personalized emails AI se generate karo
            aur Gmail se directly outreach karo — sab kuch ek platform par.
          </p>

          <div className="hp-hero-actions">
            <Link to="/register" className="hp-cta-primary">
              <span>Start Free Today</span>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            </Link>
            <Link to="/login" className="hp-cta-secondary">
              Sign In to Dashboard
            </Link>
          </div>

          <div className="hp-hero-trust">
            <span className="hp-trust-item">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
              No credit card required
            </span>
            <span className="hp-trust-item">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
              Gmail OAuth 2.0 secure
            </span>
            <span className="hp-trust-item">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
              Setup in 5 minutes
            </span>
          </div>
        </div>

        {/* Floating dashboard preview */}
        <div className="hp-hero-visual">
          <div className="hp-dashboard-card">
            <div className="hp-dc-header">
              <div className="hp-dc-dots">
                <span /><span /><span />
              </div>
              <span className="hp-dc-title">LeadFlow Dashboard</span>
            </div>
            <div className="hp-dc-body">
              <div className="hp-dc-stat-row">
                <div className="hp-dc-stat">
                  <span className="hp-dc-num">2,847</span>
                  <span className="hp-dc-lbl">Leads Found</span>
                  <span className="hp-dc-trend hp-dc-trend--up">↑ 24%</span>
                </div>
                <div className="hp-dc-stat">
                  <span className="hp-dc-num">143</span>
                  <span className="hp-dc-lbl">Emails Sent</span>
                  <span className="hp-dc-trend hp-dc-trend--up">↑ 18%</span>
                </div>
                <div className="hp-dc-stat">
                  <span className="hp-dc-num">31</span>
                  <span className="hp-dc-lbl">Replies</span>
                  <span className="hp-dc-trend hp-dc-trend--up">↑ 42%</span>
                </div>
              </div>
              <div className="hp-dc-bar-chart">
                {[65, 80, 55, 90, 75, 95, 70].map((h, i) => (
                  <div key={i} className="hp-dc-bar" style={{ "--h": `${h}%`, "--delay": `${i * 0.1}s` }} />
                ))}
              </div>
              <div className="hp-dc-leads">
                {["Pilot Cafe Budapest", "Tech Studio Berlin", "Green Market Vienna"].map((name, i) => (
                  <div key={i} className="hp-dc-lead-row" style={{ "--delay": `${i * 0.15 + 0.3}s` }}>
                    <span className="hp-dc-lead-dot" />
                    <span className="hp-dc-lead-name">{name}</span>
                    <span className="hp-dc-lead-badge">AI Email Ready</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Floating mini cards */}
          <div className="hp-float-card hp-float-card-1">
            <span>🎯</span>
            <div>
              <strong>Lead Qualified</strong>
              <span>Score: 94/100</span>
            </div>
          </div>
          <div className="hp-float-card hp-float-card-2">
            <span>📬</span>
            <div>
              <strong>Reply Received</strong>
              <span>Interested!</span>
            </div>
          </div>
        </div>
      </section>


      {/* ══════════════════════════════════════════
          STATS
      ══════════════════════════════════════════ */}
      <section className="hp-stats" id="stats" ref={statsRef}>
        <div className="hp-stats-inner">
          {STATS.map((s, i) => (
            <div key={i} className={`hp-stat-item ${statsInView ? "hp-stat-item--visible" : ""}`} style={{ "--delay": `${i * 0.1}s` }}>
              <span className="hp-stat-num">
                {counts[i].toLocaleString()}{s.suffix}
              </span>
              <span className="hp-stat-lbl">{s.label}</span>
            </div>
          ))}
        </div>
      </section>


      {/* ══════════════════════════════════════════
          FEATURES
      ══════════════════════════════════════════ */}
      <section className="hp-features" id="features" ref={featuresRef}>
        <div className="hp-section-inner">
          <div className={`hp-section-head ${featuresInView ? "hp-section-head--visible" : ""}`}>
            <span className="hp-section-badge">Platform Features</span>
            <h2>Sab kuch ek jagah</h2>
            <p>Lead discovery se leke email reply tak — poora outreach workflow automate karo</p>
          </div>

          <div className="hp-features-grid">
            {FEATURES.map((f, i) => (
              <div
                key={i}
                className={`hp-feature-card hp-feature-card--${f.color} ${featuresInView ? "hp-feature-card--visible" : ""}`}
                style={{ "--delay": `${i * 0.1}s` }}
              >
                <div className="hp-feature-icon">{f.icon}</div>
                <h3>{f.title}</h3>
                <p>{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>


      {/* ══════════════════════════════════════════
          HOW IT WORKS
      ══════════════════════════════════════════ */}
      <section className="hp-how" id="how-it-works" ref={stepsRef}>
        <div className="hp-section-inner">
          <div className={`hp-section-head ${stepsInView ? "hp-section-head--visible" : ""}`}>
            <span className="hp-section-badge">Process</span>
            <h2>Sirf 4 Steps mein shuru karo</h2>
            <p>5 minute mein setup complete — aur pehle din se leads milna shuru</p>
          </div>

          <div className="hp-steps">
            {STEPS.map((s, i) => (
              <div
                key={i}
                className={`hp-step ${stepsInView ? "hp-step--visible" : ""}`}
                style={{ "--delay": `${i * 0.15}s` }}
              >
                <div className="hp-step-num">{s.num}</div>
                <div className="hp-step-line" />
                <div className="hp-step-content">
                  <h3>{s.title}</h3>
                  <p>{s.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>


      {/* ══════════════════════════════════════════
          CTA BANNER
      ══════════════════════════════════════════ */}
      <section className="hp-cta-banner">
        <div className="hp-cta-blob-1" />
        <div className="hp-cta-blob-2" />
        <div className="hp-cta-inner">
          <h2>Aaj hi shuru karo — free mein</h2>
          <p>
            AI Lead Generation & Business Outreach Platform ke saath apni
            outreach game ko next level par le jao.
          </p>
          <div className="hp-cta-btns">
            <Link to="/register" className="hp-cta-primary hp-cta-primary--lg">
              Create Free Account
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            </Link>
            <Link to="/login" className="hp-cta-outline">
              Already have account? Sign In
            </Link>
          </div>
        </div>
      </section>


      {/* ══════════════════════════════════════════
          FOOTER
      ══════════════════════════════════════════ */}
      <footer className="hp-footer">
        <div className="hp-footer-inner">
          <div className="hp-footer-brand">
            <span className="hp-logo-mark">⚡</span>
            <div>
              <strong>AI Lead Generation & Business Outreach Platform</strong>
              <span>by SoftPeak Technologies</span>
            </div>
          </div>
          <div className="hp-footer-links">
            <Link to="/privacy-policy">Privacy Policy</Link>
            <Link to="/terms">Terms of Service</Link>
            <Link to="/login">Sign In</Link>
            <Link to="/register">Register</Link>
          </div>
          <p className="hp-footer-copy">
            © {new Date().getFullYear()} SoftPeak Technologies. All rights reserved.
          </p>
        </div>
      </footer>

    </div>
  );
}
