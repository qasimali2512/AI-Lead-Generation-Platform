import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
} from "react-router-dom";

import LoginPage from "../pages/auth/LoginPage";
import RegisterPage from "../pages/auth/RegisterPage";

import DashboardPage from "../pages/dashboard/DashboardPage";

import LeadDiscoveryPage from "../pages/leads/LeadDiscoveryPage";
import LeadsPage from "../pages/leads/LeadsPage";

import WebsiteScannerPage from "../pages/websites/WebsiteScannerPage";
import OpportunitiesPage from "../pages/opportunities/OpportunitiesPage";

import AIEmailEditorPage from "../pages/email/AIEmailEditorPage";
import EmailAccountsPage from "../pages/email/EmailAccountsPage";

import CampaignBuilderPage from "../pages/campaigns/CampaignBuilderPage";
import CampaignsListPage from "../pages/campaigns/CampaignsListPage";
import CampaignDetailPage from "../pages/campaigns/CampaignDetailPage";

import QueueMonitorPage from "../pages/queue/QueueMonitorPage";
import DeliveryMonitorPage from "../pages/delivery/DeliveryMonitorPage";

import RepliesInboxPage from "../pages/replies/RepliesInboxPage";
import AnalyticsPage from "../pages/analytics/AnalyticsPage";

import SettingsPage from "../pages/settings/SettingsPage";

import NotFoundPage from "../pages/NotFoundPage";

import AppLayout from "../layouts/AppLayout";
import ProtectedRoute from "./ProtectedRoute";


function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>

        {/* ====================================================== */}
        {/* Authentication                                         */}
        {/* ====================================================== */}

        <Route
          path="/login"
          element={<LoginPage />}
        />

        <Route
          path="/register"
          element={<RegisterPage />}
        />


        {/* ====================================================== */}
        {/* Protected Application                                  */}
        {/* ====================================================== */}

        <Route element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>

            {/* Dashboard */}
            <Route
              path="/dashboard"
              element={<DashboardPage />}
            />


            {/* ================================================== */}
            {/* Leads                                               */}
            {/* ================================================== */}

            <Route
              path="/leads/discover"
              element={<LeadDiscoveryPage />}
            />

            <Route
              path="/leads"
              element={<LeadsPage />}
            />


            {/* ================================================== */}
            {/* Websites                                            */}
            {/* ================================================== */}

            <Route
              path="/websites/scanner"
              element={<WebsiteScannerPage />}
            />


            {/* ================================================== */}
            {/* Opportunities                                       */}
            {/* ================================================== */}

            <Route
              path="/opportunities"
              element={<OpportunitiesPage />}
            />


            {/* ================================================== */}
            {/* Email                                               */}
            {/* ================================================== */}

            <Route
              path="/email/editor"
              element={<AIEmailEditorPage />}
            />

            <Route
              path="/email/accounts"
              element={<EmailAccountsPage />}
            />


            {/* ================================================== */}
            {/* Campaigns                                           */}
            {/* ================================================== */}

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


            {/* ================================================== */}
            {/* Queue                                               */}
            {/* ================================================== */}

            <Route
              path="/queue"
              element={<QueueMonitorPage />}
            />


            {/* ================================================== */}
            {/* Delivery                                            */}
            {/* ================================================== */}

            <Route
              path="/delivery"
              element={<DeliveryMonitorPage />}
            />


            {/* ================================================== */}
            {/* Replies                                             */}
            {/* ================================================== */}

            <Route
              path="/replies"
              element={<RepliesInboxPage />}
            />


            {/* ================================================== */}
            {/* Analytics                                           */}
            {/* ================================================== */}

            <Route
              path="/analytics"
              element={<AnalyticsPage />}
            />


            {/* ================================================== */}
            {/* Settings                                            */}
            {/* ================================================== */}

            <Route
              path="/settings"
              element={<SettingsPage />}
            />

          </Route>
        </Route>


        {/* ====================================================== */}
        {/* Root                                                   */}
        {/* ====================================================== */}

        <Route
          path="/"
          element={
            <Navigate
              to="/dashboard"
              replace
            />
          }
        />


        {/* ====================================================== */}
        {/* 404                                                    */}
        {/* ====================================================== */}

        <Route
          path="*"
          element={<NotFoundPage />}
        />

      </Routes>
    </BrowserRouter>
  );
}


export default AppRouter;