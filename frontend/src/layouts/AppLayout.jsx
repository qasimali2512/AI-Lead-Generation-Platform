import { Menu } from "lucide-react";
import { useState } from "react";
import { Outlet } from "react-router-dom";

import Sidebar from "../components/layout/Sidebar";
import NotificationCenter from "../components/notifications/NotificationCenter";

import "./AppLayout.css";


function AppLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);


  const handleOpenMobile = () => {
    setMobileOpen(true);
  };


  const handleCloseMobile = () => {
    setMobileOpen(false);
  };


  const handleToggleSidebar = () => {
    setCollapsed((current) => !current);
  };


  return (
    <div
      className={`app-layout ${
        collapsed
          ? "sidebar-collapsed"
          : ""
      }`}
    >

      {/* ================================================== */}
      {/* Sidebar                                            */}
      {/* ================================================== */}

      <Sidebar
        collapsed={collapsed}
        mobileOpen={mobileOpen}
        onToggle={handleToggleSidebar}
        onCloseMobile={handleCloseMobile}
      />


      {/* ================================================== */}
      {/* Main Application                                   */}
      {/* ================================================== */}

      <div className="app-layout-main">

        {/* ============================================== */}
        {/* Mobile Header                                  */}
        {/* ============================================== */}

        <header className="app-mobile-header">

          <button
            type="button"
            className="app-mobile-menu"
            onClick={handleOpenMobile}
            aria-label="Open navigation"
          >
            <Menu size={20} />
          </button>


          <div className="app-mobile-brand">
            <div className="app-mobile-brand-mark">
              <span />
              <span />
              <span />
            </div>

            <span>
              LeadFlow
            </span>
          </div>


          <NotificationCenter />

        </header>


        {/* ============================================== */}
        {/* Desktop Topbar                                 */}
        {/* ============================================== */}

        <header className="app-desktop-header">

          <div className="app-desktop-header-spacer" />

          <NotificationCenter />

        </header>


        {/* ============================================== */}
        {/* Page Content                                    */}
        {/* ============================================== */}

        <main className="app-layout-content">
          <Outlet />
        </main>

      </div>

    </div>
  );
}


export default AppLayout;