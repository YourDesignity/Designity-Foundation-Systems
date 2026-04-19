// src/components/Sidebar.jsx
//
// FIXES APPLIED (see audit report):
//  1. Removed duplicate Dashboard link ("Overview" inside ANALYTICS)
//  2. Replaced hasPerm() raw-string checks with usePermission() + PERMISSIONS constants
//  3. Removed orphaned isSiteManager inline check — now from useAuth()
//  4. Removed redundant "Workflow Overview" entry (adjacent duplicate in PROJECTS)
//  5. Promoted Vehicles and Finance to standalone links (single-item sections removed)
//  6. Expanded Inventory to a proper NavSection with all 4 sub-pages
//  7. Added missing routes: Overtime, Deductions, Designations, Audit Trail
//  8. Added Site Manager-specific routes: Site Attendance, Inventory Tasks
//  9. Messages route derived from isSiteManager (single place)
// 10. Active-state detection consolidated into NavItem (startsWith — parent-aware)
// NOTE: Only icons already proven to work in this codebase are used.

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
  LuWallet,
  LuPackage,
  LuMessageSquare,
  LuSettings,
  LuShield,
  LuChartPie,
  LuChartBarBig,
  LuUsersRound,
  LuFileText,
  LuFilePlus,
  LuSquareCheck,
  LuSlidersHorizontal,
  LuWrench,
} from 'react-icons/lu';

import { useAuth } from '../context/AuthContext';
import { usePermission } from '../hooks/usePermission';
import { PERMISSIONS } from '../constants/permissions';
import NavSection from './Sidebar/NavSection';
import NavItem from './Sidebar/NavItem';
import './Sidebar.css';

const Sidebar = () => {
  const { user, isAdmin, isSuperAdmin, isSiteManager } = useAuth();
  const { hasPermission } = usePermission();
  const navigate    = useNavigate();
  const { pathname } = useLocation();

  if (!user) return null;

  // Standalone active check (exact match) — for flat top-level buttons only
  const isActive = (path) => pathname === path;

  // Messages route — derived from role, single source of truth
  const messagesPath = isSiteManager ? '/manager-messages' : '/messages';

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h1 className="sidebar-title">Montreal Intl.</h1>
      </div>

      <nav className="sidebar-nav">

        {/* ── Dashboard ─────────────────────────────────────────────── */}
        <button
          onClick={() => navigate('/dashboard')}
          className={`nav-item-standalone ${isActive('/dashboard') ? 'active' : ''}`}
        >
          <LuLayoutDashboard size={20} />
          <span>Dashboard</span>
        </button>

        {/* ── ANALYTICS ─────────────────────────────────────────────── */}
        {isAdmin && (
          <NavSection title="ANALYTICS" icon={LuChartBar} defaultOpen={false}>
            <NavItem to="/analytics"            icon={LuChartPie}    label="Analytics" />
            <NavItem to="/workforce-allocation" icon={LuUsersRound}  label="Workforce" />
          </NavSection>
        )}

        {/* ── WORKFORCE ─────────────────────────────────────────────── */}
        <NavSection title="PEOPLE" icon={LuUsers} defaultOpen={true}>

          {hasPermission(PERMISSIONS.EMPLOYEES_VIEW) && (
            <NavItem to="/employees"         icon={LuUsers}         label="Employees" />
          )}
          {hasPermission(PERMISSIONS.MANAGERS_VIEW) && (
            <NavItem to="/managers"          icon={LuUserCog}       label="Managers" />
          )}
          {isAdmin && (
            <NavItem to="/designations"      icon={LuWrench}        label="Designations" />
          )}
          {hasPermission(PERMISSIONS.ATTENDANCE_VIEW) && (
            <NavItem to="/attendance"        icon={LuCalendar}      label="Attendance" />
          )}
          {isAdmin && (
            <NavItem to="/manager-attendance" icon={LuCalendar}     label="Manager Attendance" />
          )}
          {isSiteManager && (
            <NavItem to="/site-attendance"   icon={LuCalendar}      label="Site Attendance" />
          )}
          {isSiteManager && (
            <NavItem to="/my-attendance"     icon={LuCalendar}      label="My Attendance" />
          )}
          {hasPermission(PERMISSIONS.DUTY_LIST_VIEW) && (
            <NavItem to="/duty-list"         icon={LuClipboardList} label="Duty List" />
          )}
          {hasPermission(PERMISSIONS.PAYSLIPS_VIEW) && (
            <NavItem to="/payslips"          icon={LuDollarSign}    label="Payslips" />
          )}
          {hasPermission(PERMISSIONS.OVERTIME_VIEW) && (
            <NavItem to="/overtime"          icon={LuDollarSign}    label="Overtime" />
          )}
          {hasPermission(PERMISSIONS.DEDUCTIONS_VIEW) && (
            <NavItem to="/deductions"        icon={LuWallet}        label="Deductions" />
          )}

        </NavSection>

        {/* ── PROJECTS ──────────────────────────────────────────────── */}
        {hasPermission(PERMISSIONS.PROJECTS_VIEW) && (
          <NavSection title="OPERATIONS" icon={LuFolderKanban} defaultOpen={false}>
            <NavItem to="/projects"                   icon={LuFolderKanban}  label="All Projects" />
            <NavItem to="/site-management"            icon={LuBuilding2}     label="Sites" />
            <NavItem to="/project-workflow"           icon={LuGitBranch}     label="Workflow" />
            <NavItem to="/role-contracts/fulfillment" icon={LuClipboardList} label="Role Contracts" />
          </NavSection>
        )}

        {/* ── CONTRACTS ─────────────────────────────────────────────── */}
        {hasPermission(PERMISSIONS.CONTRACTS_VIEW) && (
          <NavSection title="CONTRACTS" icon={LuFileText} defaultOpen={false}>
            <NavItem to="/contracts"                          icon={LuFileText}          label="All Contracts" />
            <NavItem to="/contracts?status=PENDING_APPROVAL" icon={LuSquareCheck}       label="Pending Approvals" exact={true} />
            {isSuperAdmin && (
              <NavItem to="/contracts/modules/settings"       icon={LuSlidersHorizontal} label="Module Settings" />
            )}
          </NavSection>
        )}

        {/* ── INVENTORY ─────────────────────────────────────────────── */}
        {hasPermission(PERMISSIONS.INVENTORY_VIEW) && (
          <NavSection title="INVENTORY" icon={LuPackage} defaultOpen={false}>
            <NavItem to="/inventory"                 icon={LuPackage}       label="Overview"        exact={true} />
            <NavItem to="/inventory/materials"       icon={LuClipboardList} label="Materials" />
            <NavItem to="/inventory/suppliers"       icon={LuUsers}         label="Suppliers" />
            <NavItem to="/inventory/purchase-orders" icon={LuFileText}      label="Purchase Orders" />
            {isAdmin && (
              <NavItem to="/inventory/catalogue"       icon={LuClipboardList} label="Item Catalogue" />
            )}
          </NavSection>
        )}

        {/* Inventory Tasks — site manager only */}
        {isSiteManager && (
          <button
            onClick={() => navigate('/manager-inventory-tasks')}
            className={`nav-item-standalone ${isActive('/manager-inventory-tasks') ? 'active' : ''}`}
          >
            <LuClipboardList size={20} />
            <span>Inventory Tasks</span>
          </button>
        )}

        {/* ── VEHICLES — standalone (was a single-item section) ────── */}
        {hasPermission(PERMISSIONS.VEHICLES_VIEW) && (
          <button
            onClick={() => navigate('/vehicles')}
            className={`nav-item-standalone ${isActive('/vehicles') ? 'active' : ''}`}
          >
            <LuTruck size={20} />
            <span>Vehicles</span>
          </button>
        )}

        {/* ── FINANCE — standalone (was a single-item section) ─────── */}
        {hasPermission(PERMISSIONS.FINANCE_VIEW) && (
          <button
            onClick={() => navigate('/finance')}
            className={`nav-item-standalone ${isActive('/finance') ? 'active' : ''}`}
          >
            <LuWallet size={20} />
            <span>Finance</span>
          </button>
        )}

        {/* ── MESSAGES ──────────────────────────────────────────────── */}
        {hasPermission(PERMISSIONS.MESSAGES_VIEW) && (
          <button
            onClick={() => navigate(messagesPath)}
            className={`nav-item-standalone ${isActive(messagesPath) ? 'active' : ''}`}
          >
            <LuMessageSquare size={20} />
            <span>Messages</span>
          </button>
        )}

        {/* ── SETTINGS ──────────────────────────────────────────────── */}
        {isAdmin && (
          <NavSection title="SETTINGS" icon={LuSettings} defaultOpen={false}>
            <NavItem to="/admins"       icon={LuShield}       label="Admins" />
            <NavItem to="/audit-trail"  icon={LuClipboardList} label="Audit Trail" />
            <NavItem to="/settings"     icon={LuSettings}     label="Company Settings" />
          </NavSection>
        )}

      </nav>
    </aside>
  );
};

export default Sidebar;
