import {
  BarChart3,
  ChevronLeft,
  ChevronRight,
  FileSearch,
  Gauge,
  Globe,
  Inbox,
  LayoutDashboard,
  LogOut,
  Mail,
  Megaphone,
  MessageCircle,
  Settings,
  Users,
  X,
  Zap,
} from "lucide-react";

import { NavLink } from "react-router-dom";
import { useContext } from "react";

import { AuthContext } from "../../context/AuthContext";
import "./Sidebar.css";


const mainNavigation = [
  {
    label: "Dashboard",
    path: "/dashboard",
    icon: LayoutDashboard,
    end: true,
  },
  {
    label: "Discover Leads",
    path: "/leads/discover",
    icon: FileSearch,
    end: true,
  },
  {
  label: "Auto Discovery",
  path: "/leads/auto",
  icon: Zap,
  end: true,
},
  {
    label: "Leads",
    path: "/leads",
    icon: Users,
    end: true,
  },
  {
    label: "Websites",
    path: "/websites/scanner",
    icon: Globe,
    end: true,
  },
  {
    label: "Opportunities",
    path: "/opportunities",
    icon: Gauge,
    end: true,
  },
];


const outreachNavigation = [
  {
    label: "AI Email Editor",
    path: "/email/editor",
    icon: Mail,
    end: true,
  },
  {
    label: "Email Accounts",
    path: "/email/accounts",
    icon: Mail,
    end: true,
  },
  {
    label: "Campaigns",
    path: "/campaigns",
    icon: Megaphone,
    end: false,
  },
  {
    label: "Email Queue",
    path: "/queue",
    icon: Inbox,
    end: true,
  },
  {
    label: "Delivery",
    path: "/delivery",
    icon: MessageCircle,
    end: true,
  },
  {
    label: "Replies",
    path: "/replies",
    icon: Mail,
    end: true,
  },
];


const insightNavigation = [
  {
    label: "Analytics",
    path: "/analytics",
    icon: BarChart3,
    end: true,
  },
];


function Sidebar({
  collapsed,
  mobileOpen,
  onToggle,
  onCloseMobile,
}) {
  const { user, logout } = useContext(AuthContext);


  const handleLogout = async () => {
    await logout();
  };


  const renderNavigation = (items) =>
    items.map((item) => {
      const Icon = item.icon;

      return (
        <NavLink
          key={item.path}
          to={item.path}
          end={item.end ?? false}
          onClick={onCloseMobile}
          className={({ isActive }) =>
            `sidebar-nav-item ${
              isActive ? "active" : ""
            }`
          }
        >
          <Icon
            size={18}
            strokeWidth={1.8}
          />

          <span className="sidebar-nav-label">
            {item.label}
          </span>
        </NavLink>
      );
    });


  /*
   * ------------------------------------------------------------
   * Real authenticated user information
   * ------------------------------------------------------------
   */

  const userEmail =
    user?.email ||
    "Workspace user";


  const userName =
    user?.full_name ||
    user?.user_metadata?.full_name ||
    user?.user_metadata?.name ||
    user?.name ||
    (
      userEmail !== "Workspace user"
        ? userEmail.split("@")[0]
        : "User"
    );


  const userInitial =
    userName?.charAt(0)?.toUpperCase() ||
    userEmail?.charAt(0)?.toUpperCase() ||
    "U";


  return (
    <>
      {mobileOpen && (
        <button
          type="button"
          className="sidebar-mobile-overlay"
          onClick={onCloseMobile}
          aria-label="Close navigation"
        />
      )}


      <aside
        className={`sidebar ${
          collapsed ? "collapsed" : ""
        } ${
          mobileOpen ? "mobile-open" : ""
        }`}
      >

        {/* ================================================== */}
        {/* Sidebar Header                                    */}
        {/* ================================================== */}

        <div className="sidebar-top">

          <div className="sidebar-brand">

            <div className="sidebar-brand-mark">
              <span />
              <span />
              <span />
            </div>

            <div className="sidebar-brand-text">
              <strong>
                LeadFlow
              </strong>

              <span>
                AI WORKSPACE
              </span>
            </div>

          </div>


          <button
            type="button"
            className="sidebar-mobile-close"
            onClick={onCloseMobile}
            aria-label="Close sidebar"
          >
            <X size={18} />
          </button>


          <button
            type="button"
            className="sidebar-collapse-button"
            onClick={onToggle}
            aria-label={
              collapsed
                ? "Expand sidebar"
                : "Collapse sidebar"
            }
          >
            {collapsed ? (
              <ChevronRight size={16} />
            ) : (
              <ChevronLeft size={16} />
            )}
          </button>

        </div>


        {/* ================================================== */}
        {/* Navigation                                        */}
        {/* ================================================== */}

        <nav className="sidebar-navigation">

          <div className="sidebar-section">

            <span className="sidebar-section-label">
              MAIN
            </span>

            <div className="sidebar-nav-list">
              {renderNavigation(
                mainNavigation,
              )}
            </div>

          </div>


          <div className="sidebar-section">

            <span className="sidebar-section-label">
              OUTREACH
            </span>

            <div className="sidebar-nav-list">
              {renderNavigation(
                outreachNavigation,
              )}
            </div>

          </div>


          <div className="sidebar-section">

            <span className="sidebar-section-label">
              INSIGHTS
            </span>

            <div className="sidebar-nav-list">
              {renderNavigation(
                insightNavigation,
              )}
            </div>

          </div>

        </nav>


        {/* ================================================== */}
        {/* Bottom / User                                    */}
        {/* ================================================== */}

        <div className="sidebar-bottom">

          <NavLink
            to="/settings"
            end
            onClick={onCloseMobile}
            className={({ isActive }) =>
              `sidebar-nav-item sidebar-settings ${
                isActive ? "active" : ""
              }`
            }
          >
            <Settings
              size={18}
              strokeWidth={1.8}
            />

            <span className="sidebar-nav-label">
              Settings
            </span>
          </NavLink>


          <div className="sidebar-divider" />


          {/* ================================================== */}
          {/* Real User Profile                                  */}
          {/* ================================================== */}

          <div className="sidebar-user">

            <div className="sidebar-user-avatar">
              {userInitial}
            </div>


            <div className="sidebar-user-info">

              <strong
                title={userName}
              >
                {userName}
              </strong>

              <span
                title={userEmail}
              >
                {userEmail}
              </span>

            </div>

          </div>


          {/* ================================================== */}
          {/* Logout                                            */}
          {/* ================================================== */}

          <button
            type="button"
            className="sidebar-logout"
            onClick={handleLogout}
          >
            <LogOut
              size={17}
              strokeWidth={1.8}
            />

            <span className="sidebar-nav-label">
              Sign out
            </span>
          </button>

        </div>

      </aside>
    </>
  );
}


export default Sidebar;