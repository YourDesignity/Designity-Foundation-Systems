import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  LuLayoutDashboard,
  LuChartBar,
  LuUsers,
  LuUserCog,
  LuCalendar,
  LuClipboardList,
  LuDollarSign,
  LuFolderKanban,
  LuBuilding2,
  LuGitBranch,
  LuTruck,
  LuWrench,
  LuWallet,
  LuPackage,
  LuMessageSquare,
  LuSettings,
  LuShield,
  LuChartPie,
  LuChartBarBig,
  LuUsersRound,
} from 'react-icons/lu';
import { useAuth } from '../context/AuthContext';
import NavSection from './Sidebar/NavSection';
import NavItem from './Sidebar/NavItem';
import './Sidebar.css';

const Sidebar = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  if (!user) {
    return null;
  }

  const hasPerm = (perm) => {
    if (user?.role === 'SuperAdmin' || user?.role === 'Admin') {
      return true;
    }
    return !perm || (user?.perms && user.perms.includes(perm));
  };
  const isActive = (path) => location.pathname === path;
  const isSiteManager = user?.role === 'Site Manager';

  const messagesPath = isSiteManager ? '/manager-messages' : '/messages';

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h1 className="sidebar-title">Montreal Intl.</h1>
      </div>

      <nav className="sidebar-nav">
        {/* Dashboard - Always visible */}
        <button
          onClick={() => navigate('/dashboard')}
          className={`nav-item-standalone ${isActive('/dashboard') ? 'active' : ''}`}
        >
          <LuLayoutDashboard size={20} />
          <span>Dashboard</span>
        </button>

        {/* OVERVIEW Section */}
        {hasPerm('admin:view_all') && (
          <NavSection title="ANALYTICS" icon={LuChartBar} defaultOpen={true}>
            <NavItem to="/analytics" icon={LuChartPie} label="Analytics" />
            <NavItem to="/dashboard" icon={LuChartBar} label="Overview" />
            <NavItem to="/workforce-allocation" icon={LuUsersRound} label="Workforce Alloc." />
          </NavSection>
        )}

        {/* WORKFORCE Section */}
        <NavSection title="WORKFORCE" icon={LuUsers} defaultOpen={true}>
          {hasPerm(null) && <NavItem to="/employees" icon={LuUsers} label="Employees" />}
          {hasPerm('admin:view_all') && <NavItem to="/managers" icon={LuUserCog} label="Managers" />}
          {hasPerm('attendance:update') && <NavItem to="/attendance" icon={LuCalendar} label="Attendance" />}
          {isSiteManager && <NavItem to="/my-attendance" icon={LuCalendar} label="My Attendance" />}
          {hasPerm('admin:view_all') && <NavItem to="/manager-attendance" icon={LuCalendar} label="Manager Attendance" />}
          {hasPerm('schedule:edit') && <NavItem to="/duty-list" icon={LuClipboardList} label="Duty List" />}
          {hasPerm('payslip:view_all') && <NavItem to="/payslips" icon={LuDollarSign} label="Payslips" />}
        </NavSection>

        {/* PROJECTS Section */}
        {hasPerm('employee:view_all') && (
          <NavSection title="PROJECTS" icon={LuFolderKanban} defaultOpen={false}>
            <NavItem to="/projects" icon={LuFolderKanban} label="All Projects" />
            <NavItem to="/site-management" icon={LuBuilding2} label="Sites" />
            <NavItem to="/project-workflow" icon={LuGitBranch} label="Workflow" />
            <NavItem to="/project-workflow/overview" icon={LuGitBranch} label="Workflow Overview" />
          </NavSection>
        )}

        {/* FLEET Section */}
        <NavSection title="FLEET" icon={LuTruck} defaultOpen={false}>
          {hasPerm(null) && <NavItem to="/vehicles" icon={LuTruck} label="Vehicles" />}
        </NavSection>

        {/* FINANCE Section */}
        {hasPerm('admin:view_all') && (
          <NavSection title="FINANCE" icon={LuWallet} defaultOpen={false}>
            <NavItem to="/finance" icon={LuChartBarBig} label="Finance Dashboard" />
          </NavSection>
        )}

        {/* INVENTORY - Standalone */}
        {hasPerm('employee:view_all') && (
          <button
            onClick={() => navigate('/inventory')}
            className={`nav-item-standalone ${isActive('/inventory') ? 'active' : ''}`}
          >
            <LuPackage size={20} />
            <span>Inventory</span>
          </button>
        )}

        {/* MESSAGES - Always visible */}
        <button
          onClick={() => navigate(messagesPath)}
          className={`nav-item-standalone ${isActive(messagesPath) ? 'active' : ''}`}
        >
          <LuMessageSquare size={20} />
          <span>Messages</span>
        </button>

        {/* SETTINGS Section */}
        {hasPerm('admin:view_all') && (
          <NavSection title="SETTINGS" icon={LuSettings} defaultOpen={false}>
            <NavItem to="/admins" icon={LuShield} label="Admins" />
            <NavItem to="/settings" icon={LuSettings} label="Company Settings" />
          </NavSection>
        )}
      </nav>
    </aside>
  );
};

export default Sidebar;