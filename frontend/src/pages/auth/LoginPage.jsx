import { useContext, useState } from "react";
import {
  ArrowRight,
  Eye,
  EyeOff,
  LockKeyhole,
  Mail,
  Sparkles,
} from "lucide-react";
import {
  Link,
  useLocation,
  useNavigate,
} from "react-router-dom";
import { toast } from "react-toastify";

import { AuthContext } from "../../context/AuthContext";

import "./LoginPage.css";

function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();

  const {
    login,
    isAuthenticated,
  } = useContext(AuthContext);

  const [form, setForm] = useState({
    email: "",
    password: "",
  });

  const [showPassword, setShowPassword] =
    useState(false);

  const [submitting, setSubmitting] =
    useState(false);

  if (isAuthenticated) {
    navigate("/dashboard", {
      replace: true,
    });

    return null;
  }

  function handleChange(event) {
    const {
      name,
      value,
    } = event.target;

    setForm((current) => ({
      ...current,
      [name]: value,
    }));
  }

  async function handleSubmit(event) {
    event.preventDefault();

    if (!form.email.trim()) {
      toast.error("Please enter your email.");
      return;
    }

    if (!form.password) {
      toast.error("Please enter your password.");
      return;
    }

    setSubmitting(true);

    try {
      await login({
        email: form.email.trim(),
        password: form.password,
      });

      toast.success("Welcome back.");

      const destination =
        location.state?.from ||
        "/dashboard";

      navigate(destination, {
        replace: true,
      });
    } catch (error) {
      const message =
        error.response?.data?.detail ||
        "Unable to sign in. Please check your credentials.";

      toast.error(
        typeof message === "string"
          ? message
          : "Unable to sign in.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-visual">
        <div className="auth-visual-glow auth-glow-one" />
        <div className="auth-visual-glow auth-glow-two" />

        <div className="auth-brand">
          <div className="auth-brand-mark">
            <Sparkles size={19} />
          </div>

          <span>
            LeadFlow AI
          </span>
        </div>

        <div className="auth-visual-content">
          <p className="auth-eyebrow">
            AI-powered prospecting
          </p>

          <h1>
            Turn local businesses
            <span> into real opportunities.</span>
          </h1>

          <p className="auth-visual-description">
            Discover businesses, understand their
            digital presence, and build personalized
            outreach from one intelligent workspace.
          </p>

          <div className="auth-visual-line">
            <span />
            <span />
            <span />
          </div>
        </div>
      </section>

      <section className="auth-form-side">
        <div className="auth-form-wrapper">
          <div className="auth-mobile-brand">
            <div className="auth-brand-mark">
              <Sparkles size={18} />
            </div>

            <span>
              LeadFlow AI
            </span>
          </div>

          <div className="auth-heading">
            <p className="auth-form-eyebrow">
              Welcome back
            </p>

            <h2>
              Sign in to your workspace
            </h2>

            <p>
              Continue where you left off and
              manage your lead generation workflow.
            </p>
          </div>

          <form
            className="auth-form"
            onSubmit={handleSubmit}
          >
            <label className="auth-field">
              <span>Email address</span>

              <div className="auth-input-wrap">
                <Mail size={18} />

                <input
                  type="email"
                  name="email"
                  value={form.email}
                  onChange={handleChange}
                  placeholder="you@company.com"
                  autoComplete="email"
                  disabled={submitting}
                />
              </div>
            </label>

            <label className="auth-field">
              <span>Password</span>

              <div className="auth-input-wrap">
                <LockKeyhole size={18} />

                <input
                  type={
                    showPassword
                      ? "text"
                      : "password"
                  }
                  name="password"
                  value={form.password}
                  onChange={handleChange}
                  placeholder="Enter your password"
                  autoComplete="current-password"
                  disabled={submitting}
                />

                <button
                  type="button"
                  className="password-toggle"
                  onClick={() =>
                    setShowPassword(
                      (current) => !current,
                    )
                  }
                  aria-label={
                    showPassword
                      ? "Hide password"
                      : "Show password"
                  }
                >
                  {showPassword ? (
                    <EyeOff size={17} />
                  ) : (
                    <Eye size={17} />
                  )}
                </button>
              </div>
            </label>

            <button
              type="submit"
              className="auth-submit"
              disabled={submitting}
            >
              {submitting ? (
                <>
                  <span className="auth-spinner" />
                  Signing in...
                </>
              ) : (
                <>
                  Sign in
                  <ArrowRight size={18} />
                </>
              )}
            </button>
          </form>

          <div className="auth-footer">
            <span>
              Don't have an account?
            </span>

            <Link to="/register">
              Create one
              <ArrowRight size={15} />
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}

export default LoginPage;