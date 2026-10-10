import { useContext, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  Eye,
  EyeOff,
  LockKeyhole,
  Mail,
  Sparkles,
  UserRound,
} from "lucide-react";
import {
  Link,
  Navigate,
  useNavigate,
} from "react-router-dom";
import { toast } from "react-toastify";

import { AuthContext } from "../../context/AuthContext";

import "./RegisterPage.css";

function RegisterPage() {
  const navigate = useNavigate();

  const {
    register,
    isAuthenticated,
  } = useContext(AuthContext);

  const [form, setForm] = useState({
    full_name: "",
    email: "",
    password: "",
    confirm_password: "",
  });

  const [showPassword, setShowPassword] =
    useState(false);

  const [showConfirmPassword, setShowConfirmPassword] =
    useState(false);

  const [submitting, setSubmitting] =
    useState(false);

  const [verificationRequired, setVerificationRequired] =
    useState(false);

  const [registeredEmail, setRegisteredEmail] =
    useState("");

  if (isAuthenticated) {
    return (
      <Navigate
        to="/dashboard"
        replace
      />
    );
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

    if (!form.full_name.trim()) {
      toast.error(
        "Please enter your full name.",
      );
      return;
    }

    if (!form.email.trim()) {
      toast.error(
        "Please enter your email.",
      );
      return;
    }

    if (form.password.length < 8) {
      toast.error(
        "Password must be at least 8 characters.",
      );
      return;
    }

    if (
      form.password !==
      form.confirm_password
    ) {
      toast.error(
        "Passwords do not match.",
      );
      return;
    }

    setSubmitting(true);

    try {
      const result = await register({
        full_name: form.full_name.trim(),
        email: form.email.trim(),
        password: form.password,
      });

      /*
       * Supabase email confirmation flow:
       *
       * If email confirmation is enabled,
       * backend creates the account but does
       * not return an access token.
       *
       * In that case we show the verification
       * screen instead of sending the user
       * directly to login.
       */

      const accessToken =
        result?.access_token ||
        result?.accessToken ||
        "";

      const email =
        result?.user?.email ||
        form.email.trim();

      if (!accessToken) {
        setRegisteredEmail(email);
        setVerificationRequired(true);

        return;
      }

      toast.success(
        "Account created successfully.",
      );

      navigate("/dashboard", {
        replace: true,
      });
    } catch (error) {
      const message =
        error?.response?.data?.detail ||
        error?.message ||
        "Unable to create your account.";

      toast.error(
        typeof message === "string"
          ? message
          : "Unable to create your account.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  /*
   * ---------------------------------------------------------
   * EMAIL VERIFICATION SCREEN
   * ---------------------------------------------------------
   */

  if (verificationRequired) {
    return (
      <main className="register-page">
        <section className="register-intro">
          <div className="register-brand">
            <div className="register-brand-mark">
              <Sparkles size={19} />
            </div>
            <span>LeadFlow AI</span>
          </div>

          <div className="register-intro-content">
            <p className="register-eyebrow">One more step</p>
            <h1>
              Verify your email.
              <span> Then start building.</span>
            </h1>
            <p>
              Your account has been created. Verify your email
              address before signing in to your LeadFlow workspace.
            </p>
            <div className="register-points">
              <div>
                <span>01</span>
                <p>Open the verification email sent to your inbox.</p>
              </div>
              <div>
                <span>02</span>
                <p>Click the verification link inside the email.</p>
              </div>
              <div>
                <span>03</span>
                <p>Return to LeadFlow and sign in to your workspace.</p>
              </div>
            </div>
          </div>
        </section>

        <section className="register-form-side">
          <div className="register-form-wrapper">
            <div className="register-mobile-brand">
              <div className="register-brand-mark">
                <Sparkles size={18} />
              </div>
              <span>LeadFlow AI</span>
            </div>

            <div className="register-verification">
              <div className="register-verification-icon">
                <CheckCircle2 size={32} />
              </div>

              <div className="register-heading">
                <p>Account created</p>
                <h2>Verify your email</h2>
                <span>We sent a verification link to</span>
              </div>

              <div className="register-verification-email">
                <Mail size={17} />
                <strong>{registeredEmail}</strong>
              </div>

              <p className="register-verification-text">
                Please open your email and click the verification
                link. Once your email is confirmed, you can return
                here and sign in to your account.
              </p>

              <div className="register-verification-note">
                <Mail size={16} />
                <span>
                  Check your spam or promotions folder if you
                  don't see the email.
                </span>
              </div>

              {/* Primary CTA — Go to Login */}
              <button
                type="button"
                className="register-goto-login"
                onClick={() => navigate("/login", { replace: true })}
              >
                Go to Login
                <ArrowRight size={17} />
              </button>

              {/* Secondary — Use a different email */}
              <button
                type="button"
                className="register-back-button"
                onClick={() => {
                  setVerificationRequired(false);
                  setRegisteredEmail("");
                }}
              >
                <ArrowLeft size={15} />
                Use a different email
              </button>
            </div>

            <div className="register-footer">
              <span>Already verified?</span>
              <Link to="/login">
                Sign in
                <ArrowRight size={15} />
              </Link>
            </div>
          </div>
        </section>
      </main>
    );
  }

  /*
   * ---------------------------------------------------------
   * NORMAL REGISTRATION SCREEN
   * ---------------------------------------------------------
   */

  return (
    <main className="register-page">
      <section className="register-intro">
        <div className="register-brand">
          <div className="register-brand-mark">
            <Sparkles size={19} />
          </div>

          <span>
            LeadFlow AI
          </span>
        </div>

        <div className="register-intro-content">
          <p className="register-eyebrow">
            Build your pipeline
          </p>

          <h1>
            Find better leads.
            <span>
              {" "}
              Reach them personally.
            </span>
          </h1>

          <p>
            Your workspace brings discovery,
            website analysis, qualification and
            personalized outreach together.
          </p>

          <div className="register-points">
            <div>
              <span>01</span>

              <p>
                Discover businesses by market
                and industry.
              </p>
            </div>

            <div>
              <span>02</span>

              <p>
                Understand real website and
                digital presence issues.
              </p>
            </div>

            <div>
              <span>03</span>

              <p>
                Create outreach based on actual
                business findings.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="register-form-side">
        <div className="register-form-wrapper">
          <div className="register-mobile-brand">
            <div className="register-brand-mark">
              <Sparkles size={18} />
            </div>

            <span>
              LeadFlow AI
            </span>
          </div>

          <div className="register-heading">
            <p>
              Get started
            </p>

            <h2>
              Create your workspace
            </h2>

            <span>
              Start building your lead generation
              workflow in minutes.
            </span>
          </div>

          <form
            className="register-form"
            onSubmit={handleSubmit}
          >
            <label className="register-field">
              <span>
                Full name
              </span>

              <div className="register-input-wrap">
                <UserRound size={18} />

                <input
                  type="text"
                  name="full_name"
                  value={form.full_name}
                  onChange={handleChange}
                  placeholder="Your full name"
                  autoComplete="name"
                  disabled={submitting}
                />
              </div>
            </label>

            <label className="register-field">
              <span>
                Email address
              </span>

              <div className="register-input-wrap">
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

            <label className="register-field">
              <span>
                Password
              </span>

              <div className="register-input-wrap">
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
                  placeholder="At least 8 characters"
                  autoComplete="new-password"
                  disabled={submitting}
                />

                <button
                  type="button"
                  className="register-password-toggle"
                  onClick={() =>
                    setShowPassword(
                      (current) => !current,
                    )
                  }
                  disabled={submitting}
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

            <label className="register-field">
              <span>
                Confirm password
              </span>

              <div className="register-input-wrap">
                <LockKeyhole size={18} />

                <input
                  type={
                    showConfirmPassword
                      ? "text"
                      : "password"
                  }
                  name="confirm_password"
                  value={
                    form.confirm_password
                  }
                  onChange={handleChange}
                  placeholder="Repeat your password"
                  autoComplete="new-password"
                  disabled={submitting}
                />

                <button
                  type="button"
                  className="register-password-toggle"
                  onClick={() =>
                    setShowConfirmPassword(
                      (current) => !current,
                    )
                  }
                  disabled={submitting}
                  aria-label={
                    showConfirmPassword
                      ? "Hide password"
                      : "Show password"
                  }
                >
                  {showConfirmPassword ? (
                    <EyeOff size={17} />
                  ) : (
                    <Eye size={17} />
                  )}
                </button>
              </div>
            </label>

            <button
              type="submit"
              className="register-submit"
              disabled={submitting}
            >
              {submitting ? (
                <>
                  <span className="register-spinner" />

                  Creating account...
                </>
              ) : (
                <>
                  Create account

                  <ArrowRight size={18} />
                </>
              )}
            </button>
          </form>

          <div className="register-footer">
            <span>
              Already have an account?
            </span>

            <Link to="/login">
              Sign in
              <ArrowRight size={15} />
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}

export default RegisterPage;