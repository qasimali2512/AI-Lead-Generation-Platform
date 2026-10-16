
import { lazy, Suspense, useContext, useState } from "react";
import {
  BrowserRouter,
  Navigate,
  Outlet,
  Route,
  Routes,
} from "react-router-dom";
import { Menu } from "lucide-react";

import { AuthContext } from "../context/AuthContext";
import Sidebar from "../components/layout/Sidebar";

// Lazy-loaded pages — each page becomes its own JS chunk.
// Only the current page is downloaded on first visit.
const LoginPage           = lazy(() => import("../pages/auth/LoginPage"));
const RegisterPage        = lazy(() => import("../pages/auth/RegisterPage"));
const DashboardPage       = lazy(() => import("../pages/dashboard/DashboardPage"));
const LeadDiscoveryPage   = lazy(() => import("../pages/leads/LeadDiscoveryPage"));
const AutoDiscoveryPage   = lazy(() => import("../pages/leads/AutoDiscoveryPage"));
const LeadsPage           = lazy(() => import("../pages/leads/LeadsPage"));
const WebsiteScannerPage  = lazy(() => import("../pages/websites/WebsiteScannerPage"));
const OpportunitiesPage   = lazy(() => import("../pages/opportunities/OpportunitiesPage"));
const AIEmailEditorPage   = lazy(() => import("../pages/email/AIEmailEditorPage"));
const EmailAccountsPage   = lazy(() => import("../pages/email/EmailAccountsPage"));
const CampaignsListPage   = lazy(() => import("../pages/campaigns/CampaignsListPage"));
const CampaignBuilderPage = lazy(() => import("../pages/campaigns/CampaignBuilderPage"));
const CampaignDetailPage  = lazy(() => import("../pages/campaigns/CampaignDetailPage"));
const QueueMonitorPage    = lazy(() => import("../pages/queue/QueueMonitorPage"));
const DeliveryMonitorPage = lazy(() => import("../pages/delivery/DeliveryMonitorPage"));
const RepliesInboxPage    = lazy(() => import("../pages/replies/RepliesInboxPage"));
const AnalyticsPage       = lazy(() => import("../pages/analytics/AnalyticsPage"));
const SettingsPage        = lazy(() => import("../pages/settings/SettingsPage"));
const NotFoundPage        = lazy(() => import("../pages/NotFoundPage"));

// Shown while any lazy page chunk is downloading
function PageLoader() {
  return (
    <div className="router-loading">
      <div className="router-spinner" />
      <p>Loading...</p>

      <style>{`
        .router-loading {
          min-height: 100vh;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          gap: 14px;
          color: #29394a;
          background: #f7f5ef;
          font-family: Inter, Arial, sans-serif;
        }
        .router-spinner {
          width: 32px;
          height: 32px;
          border: 3px solid #e5e0d8;
          border-top-color: #7f3035;
          border-radius: 50%;
          animation: router-spin .8s linear infinite;
        }
        @keyframes router-spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}

function ProtectedRoute() {
  const { user, loading, isAuthenticated } =
    useContext(AuthContext);

  if (loading) {
    return (
      <div className="router-loading">
        <div className="router-spinner" />
        <p>Loading your workspace...</p>

        <style>{`
          .router-loading {
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 14px;
            color: #29394a;
            background: #f7f5ef;
            font-family: Inter, Arial, sans-serif;
          }
          .router-spinner {
            width: 32px;
            height: 32px;
            border: 3px solid #e5e0d8;
            border-top-color: #7f3035;
            border-radius: 50%;
            animation: router-spin .8s linear infinite;
          }
          @keyframes router-spin {
            to { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    );
  }

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}

function PublicRoute() {
  const { loading, isAuthenticated } =
    useContext(AuthContext);

  if (loading) {
    return (
      <div style={{ padding: 40, textAlign: "center" }}>
        Loading...
      </div>
    );
  }

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return <Outlet />;
}

function AppLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="workspace-layout">
      <Sidebar
        collapsed={collapsed}
        mobileOpen={mobileOpen}
        onToggle={() => setCollapsed((value) => !value)}
        onCloseMobile={() => setMobileOpen(false)}
      />

      <div
        className={`workspace-content ${
          collapsed ? "sidebar-collapsed" : ""
        }`}
      >
        <button
          type="button"
          className="workspace-mobile-menu"
          onClick={() => setMobileOpen(true)}
          aria-label="Open navigation"
        >
          <Menu size={21} />
        </button>

        <Outlet />
      </div>

      <style>{`
        .workspace-layout {
          min-height: 100vh;
          background: #f7f5ef;
        }

        .workspace-content {
          min-height: 100vh;
          margin-left: 252px;
          transition: margin-left .25s ease;
        }

        .workspace-content.sidebar-collapsed {
          margin-left: 76px;
        }

        .workspace-mobile-menu {
          display: none;
          align-items: center;
          justify-content: center;
          width: 40px;
          height: 40px;
          margin: 12px 0 0 14px;
          border: 1px solid #e5e0d8;
          border-radius: 10px;
          background: #fff;
          color: #29394a;
          cursor: pointer;
        }

        @media (max-width: 768px) {
          .workspace-content,
          .workspace-content.sidebar-collapsed {
            margin-left: 0;
          }

          .workspace-mobile-menu {
            display: flex;
          }
        }
      `}</style>
    </div>
  );
}

function AppRouter() {
  const { isAuthenticated } = useContext(AuthContext);

  return (
    <Suspense fallback={<PageLoader />}>
      <Routes>
        <Route element={<PublicRoute />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
        </Route>

        <Route element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>
            <Route
              path="/"
              element={
                <Navigate
                  to={isAuthenticated ? "/dashboard" : "/login"}
                  replace
                />
              }
            />

            <Route path="/dashboard" element={<DashboardPage />} />

            <Route
              path="/leads/discover"
              element={<LeadDiscoveryPage />}
            />
            <Route
              path="/leads/auto"
              element={<AutoDiscoveryPage />}
            />
            <Route path="/leads" element={<LeadsPage />} />

            <Route
              path="/websites/scanner"
              element={<WebsiteScannerPage />}
            />
            <Route
              path="/opportunities"
              element={<OpportunitiesPage />}
            />

            <Route
              path="/email/editor"
              element={<AIEmailEditorPage />}
            />
            <Route
              path="/email/accounts"
              element={<EmailAccountsPage />}
            />

            <Route
              path="/campaigns"
              element={<CampaignsListPage />}
            />
            <Route
              path="/campaigns/new"
              element={<CampaignBuilderPage />}
            />
            <Route
              path="/campaigns/:campaignId"
              element={<CampaignDetailPage />}
            />
            <Route
              path="/campaigns/:campaignId/edit"
              element={<CampaignBuilderPage />}
            />

            <Route path="/queue" element={<QueueMonitorPage />} />
            <Route
              path="/delivery"
              element={<DeliveryMonitorPage />}
            />
            <Route
              path="/replies"
              element={<RepliesInboxPage />}
            />
            <Route
              path="/analytics"
              element={<AnalyticsPage />}
            />
            <Route path="/settings" element={<SettingsPage />} />

            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Route>
      </Routes>
    </Suspense>
  );
}

export default AppRouter;
