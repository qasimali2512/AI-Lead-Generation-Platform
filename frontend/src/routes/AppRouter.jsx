
import { useContext, useState } from "react";
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

import LoginPage from "../pages/auth/LoginPage";
import RegisterPage from "../pages/auth/RegisterPage";
import DashboardPage from "../pages/dashboard/DashboardPage";
import LeadDiscoveryPage from "../pages/leads/LeadDiscoveryPage";
import AutoDiscoveryPage from "../pages/leads/AutoDiscoveryPage";
import LeadsPage from "../pages/leads/LeadsPage";
import WebsiteScannerPage from "../pages/websites/WebsiteScannerPage";
import OpportunitiesPage from "../pages/opportunities/OpportunitiesPage";
import AIEmailEditorPage from "../pages/email/AIEmailEditorPage";
import EmailAccountsPage from "../pages/email/EmailAccountsPage";
import CampaignsListPage from "../pages/campaigns/CampaignsListPage";
import CampaignBuilderPage from "../pages/campaigns/CampaignBuilderPage";
import CampaignDetailPage from "../pages/campaigns/CampaignDetailPage";
import QueueMonitorPage from "../pages/queue/QueueMonitorPage";
import DeliveryMonitorPage from "../pages/delivery/DeliveryMonitorPage";
import RepliesInboxPage from "../pages/replies/RepliesInboxPage";
import AnalyticsPage from "../pages/analytics/AnalyticsPage";
import SettingsPage from "../pages/settings/SettingsPage";
import NotFoundPage from "../pages/NotFoundPage";

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
  );
}

export default AppRouter;
