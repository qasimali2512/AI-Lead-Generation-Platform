import { useEffect, useMemo, useState } from "react";
import {
  Building2,
  Check,
  Globe,
  Image,
  Link as LinkIcon,
  Mail,
  Palette,
  Phone,
  Save,
  User,
} from "lucide-react";

import {
  createBrandSettings,
  getBrandSettings,
  updateBrandSettings,
} from "../../services/settingsService";

import "./SettingsPage.css";


// Public URL — Vite serves /public/* as root static files
// The backend embeds its bundled default logo into outgoing email. Enter a
// public HTTPS URL here only when using a custom brand logo.
const DEFAULT_LOGO_URL = "";

const DEFAULT_SETTINGS = {
  agency_name: "SoftPeak Technologies",
  website: "",
  logo_url: DEFAULT_LOGO_URL,
  primary_color: "#1f6b4f",
  secondary_color: "#c49a4a",
  sender_name: "",
  sender_role: "",
  phone: "",
  address: "",
  booking_url: "",
  unsubscribe_url: "",
};


function SettingsPage() {
  const [form, setForm] = useState(DEFAULT_SETTINGS);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  const [activeSection, setActiveSection] =
    useState("brand");

  useEffect(() => {
    let mounted = true;

    async function loadSettings() {
      try {
        setLoading(true);
        setError("");

        const data = await getBrandSettings();

        if (!mounted) {
          return;
        }

        setForm({
          agency_name:
            data?.agency_name ||
            DEFAULT_SETTINGS.agency_name,

          website:
            data?.website || "",

          logo_url:
            data?.logo_url || "",

          primary_color:
            data?.primary_color ||
            DEFAULT_SETTINGS.primary_color,

          secondary_color:
            data?.secondary_color ||
            DEFAULT_SETTINGS.secondary_color,

          sender_name:
            data?.sender_name || "",

          sender_role:
            data?.sender_role || "",

          phone:
            data?.phone || "",

          address:
            data?.address || "",

          booking_url:
            data?.booking_url || "",

          unsubscribe_url:
            data?.unsubscribe_url || "",
        });
      } catch (err) {
        if (!mounted) {
          return;
        }

        setError(
          err?.response?.data?.detail ||
            "Unable to load brand settings.",
        );
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    loadSettings();

    return () => {
      mounted = false;
    };
  }, []);


  const updateField = (field, value) => {
    setForm((previous) => ({
      ...previous,
      [field]: value,
    }));

    setSaved(false);
  };


  const handleSubmit = async (event) => {
    event.preventDefault();

    try {
      setSaving(true);
      setError("");
      setSaved(false);

      let result;

      try {
        result = await updateBrandSettings(form);
      } catch (updateError) {
        if (
          updateError?.response?.status === 404 ||
          updateError?.response?.status === 405
        ) {
          result = await createBrandSettings(form);
        } else {
          throw updateError;
        }
      }

      setForm((previous) => ({
        ...previous,
        ...result,
      }));

      setSaved(true);

      window.setTimeout(() => {
        setSaved(false);
      }, 3000);
    } catch (err) {
      setError(
        err?.response?.data?.detail ||
          "Unable to save brand settings.",
      );
    } finally {
      setSaving(false);
    }
  };


  const previewStyles = useMemo(
    () => ({
      "--preview-primary":
        form.primary_color || "#1f6b4f",

      "--preview-secondary":
        form.secondary_color || "#c49a4a",
    }),
    [
      form.primary_color,
      form.secondary_color,
    ],
  );


  if (loading) {
    return (
      <div className="settings-page">
        <div className="settings-loading">
          <div className="settings-loading-spinner" />
          <span>Loading settings...</span>
        </div>
      </div>
    );
  }


  return (
    <div className="settings-page">

      <div className="settings-header">
        <div>
          <div className="settings-eyebrow">
            WORKSPACE
          </div>

          <h1>Settings</h1>

          <p>
            Manage your agency identity and email
            branding.
          </p>
        </div>
      </div>


      {error && (
        <div className="settings-alert settings-alert-error">
          {error}
        </div>
      )}


      <div className="settings-layout">

        <aside className="settings-sidebar">

          <button
            type="button"
            className={
              activeSection === "brand"
                ? "settings-nav-item active"
                : "settings-nav-item"
            }
            onClick={() => setActiveSection("brand")}
          >
            <Palette size={18} />
            <span>Brand Settings</span>
          </button>

          <button
            type="button"
            className={
              activeSection === "email"
                ? "settings-nav-item active"
                : "settings-nav-item"
            }
            onClick={() => setActiveSection("email")}
          >
            <Mail size={18} />
            <span>Email Identity</span>
          </button>

          <button
            type="button"
            className={
              activeSection === "links"
                ? "settings-nav-item active"
                : "settings-nav-item"
            }
            onClick={() => setActiveSection("links")}
          >
            <LinkIcon size={18} />
            <span>Links</span>
          </button>

        </aside>


        <main className="settings-content">

          <form onSubmit={handleSubmit}>

            {activeSection === "brand" && (
              <section className="settings-card">

                <div className="settings-card-header">
                  <div className="settings-card-icon">
                    <Building2 size={20} />
                  </div>

                  <div>
                    <h2>Agency Branding</h2>
                    <p>
                      These details are used across your
                      outreach emails.
                    </p>
                  </div>
                </div>


                <div className="settings-form-grid">

                  <div className="settings-field settings-field-full">

                    <label>
                      Agency Name
                    </label>

                    <input
                      value={form.agency_name}
                      onChange={(event) =>
                        updateField(
                          "agency_name",
                          event.target.value,
                        )
                      }
                      placeholder="SoftPeak Technologies"
                    />

                  </div>


                  <div className="settings-field">

                    <label>
                      Website
                    </label>

                    <div className="settings-input-icon">
                      <Globe size={16} />

                      <input
                        value={form.website}
                        onChange={(event) =>
                          updateField(
                            "website",
                            event.target.value,
                          )
                        }
                        placeholder="https://example.com"
                      />
                    </div>

                  </div>


                  <div className="settings-field">

                    <label>
                      Logo URL
                    </label>

                    <div className="settings-input-icon">
                      <Image size={16} />

                      <input
                        value={form.logo_url}
                        onChange={(event) =>
                          updateField(
                            "logo_url",
                            event.target.value,
                          )
                        }
                        placeholder="https://..."
                      />
                    </div>

                    <small className="settings-field-hint">
                      Optional. Use a public HTTPS image URL; the default
                      SoftPeak logo is embedded automatically in emails.
                    </small>

                    {/* Logo preview */}
                    {form.logo_url && (
                      <div className="settings-logo-preview">
                        <img
                          src={form.logo_url}
                          alt="Logo preview"
                          onError={(e) => {
                            e.target.style.display = "none";
                          }}
                          onLoad={(e) => {
                            e.target.style.display = "block";
                          }}
                        />
                      </div>
                    )}

                  </div>


                  <div className="settings-field">

                    <label>
                      Primary Color
                    </label>

                    <div className="settings-color-field">

                      <input
                        type="color"
                        value={
                          form.primary_color ||
                          "#1f6b4f"
                        }
                        onChange={(event) =>
                          updateField(
                            "primary_color",
                            event.target.value,
                          )
                        }
                      />

                      <input
                        value={form.primary_color}
                        onChange={(event) =>
                          updateField(
                            "primary_color",
                            event.target.value,
                          )
                        }
                      />

                    </div>

                  </div>


                  <div className="settings-field">

                    <label>
                      Secondary Color
                    </label>

                    <div className="settings-color-field">

                      <input
                        type="color"
                        value={
                          form.secondary_color ||
                          "#c49a4a"
                        }
                        onChange={(event) =>
                          updateField(
                            "secondary_color",
                            event.target.value,
                          )
                        }
                      />

                      <input
                        value={form.secondary_color}
                        onChange={(event) =>
                          updateField(
                            "secondary_color",
                            event.target.value,
                          )
                        }
                      />

                    </div>

                  </div>

                </div>

              </section>
            )}


            {activeSection === "email" && (
              <section className="settings-card">

                <div className="settings-card-header">
                  <div className="settings-card-icon">
                    <User size={20} />
                  </div>

                  <div>
                    <h2>Email Identity</h2>
                    <p>
                      Information shown in your email
                      signature.
                    </p>
                  </div>
                </div>


                <div className="settings-form-grid">

                  <div className="settings-field">

                    <label>
                      Sender Name
                    </label>

                    <input
                      value={form.sender_name}
                      onChange={(event) =>
                        updateField(
                          "sender_name",
                          event.target.value,
                        )
                      }
                      placeholder="Your Name"
                    />

                  </div>


                  <div className="settings-field">

                    <label>
                      Sender Role
                    </label>

                    <input
                      value={form.sender_role}
                      onChange={(event) =>
                        updateField(
                          "sender_role",
                          event.target.value,
                        )
                      }
                      placeholder="Founder / Director"
                    />

                  </div>


                  <div className="settings-field">

                    <label>
                      Phone
                    </label>

                    <div className="settings-input-icon">
                      <Phone size={16} />

                      <input
                        value={form.phone}
                        onChange={(event) =>
                          updateField(
                            "phone",
                            event.target.value,
                          )
                        }
                        placeholder="+92..."
                      />
                    </div>

                  </div>


                  <div className="settings-field settings-field-full">

                    <label>
                      Business Address
                    </label>

                    <textarea
                      value={form.address}
                      onChange={(event) =>
                        updateField(
                          "address",
                          event.target.value,
                        )
                      }
                      placeholder="Your business address"
                      rows={3}
                    />

                  </div>

                </div>

              </section>
            )}


            {activeSection === "links" && (
              <section className="settings-card">

                <div className="settings-card-header">
                  <div className="settings-card-icon">
                    <LinkIcon size={20} />
                  </div>

                  <div>
                    <h2>Important Links</h2>
                    <p>
                      Links used by your email templates.
                    </p>
                  </div>
                </div>


                <div className="settings-form-grid">

                  <div className="settings-field settings-field-full">

                    <label>
                      Booking / CTA URL
                    </label>

                    <input
                      value={form.booking_url}
                      onChange={(event) =>
                        updateField(
                          "booking_url",
                          event.target.value,
                        )
                      }
                      placeholder="https://cal.com/..."
                    />

                    <small>
                      Used by follow-up emails for the
                      booking button.
                    </small>

                  </div>


                  <div className="settings-field settings-field-full">

                    <label>
                      Unsubscribe URL
                    </label>

                    <input
                      value={form.unsubscribe_url}
                      onChange={(event) =>
                        updateField(
                          "unsubscribe_url",
                          event.target.value,
                        )
                      }
                      placeholder="https://..."
                    />

                    <small>
                      Used for the email unsubscribe link.
                    </small>

                  </div>

                </div>

              </section>
            )}


            <section
              className="settings-preview-card"
              style={previewStyles}
            >

              <div className="settings-preview-heading">
                <div>
                  <div className="settings-preview-label">
                    EMAIL PREVIEW
                  </div>

                  <h2>Signature Preview</h2>
                </div>
              </div>


              <div className="email-preview">

                <div className="email-preview-body">

                  <p>
                    Hi there,
                  </p>

                  <p>
                    I noticed a few opportunities that
                    could make your online presence
                    stronger. I thought I would reach
                    out with a quick idea.
                  </p>

                  <p>
                    If it is useful, I can share a few
                    specific recommendations.
                  </p>

                </div>


                <div className="email-preview-signature">

                  <img
                    src={form.logo_url || DEFAULT_LOGO_URL}
                    alt={form.agency_name}
                    className="email-preview-logo"
                    onError={(e) => { e.target.style.display = "none"; }}
                    onLoad={(e)  => { e.target.style.display = "block"; }}
                  />

                  <div className="email-preview-name">
                    {form.sender_name ||
                      "Your Name"}
                  </div>

                  <div className="email-preview-role">
                    {form.sender_role ||
                      "Founder / Director"}
                  </div>

                  <div className="email-preview-line" />

                  <div
                    className="email-preview-company"
                  >
                    {form.agency_name ||
                      "SoftPeak Technologies"}
                  </div>

                  {form.phone && (
                    <div className="email-preview-contact">
                      {form.phone}
                    </div>
                  )}

                  {form.website && (
                    <div className="email-preview-contact">
                      {form.website}
                    </div>
                  )}

                </div>

              </div>

            </section>


            <div className="settings-actions">

              {saved && (
                <div className="settings-saved">
                  <Check size={16} />
                  Settings saved
                </div>
              )}

              <button
                type="submit"
                className="settings-save-button"
                disabled={saving}
              >
                {saving ? (
                  <>
                    <span className="settings-button-spinner" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save size={17} />
                    Save Settings
                  </>
                )}
              </button>

            </div>

          </form>

        </main>

      </div>

    </div>
  );
}

export default SettingsPage;
