/**
 * Permission Constants
 *
 * IMPORTANT: This must match backend/config/permissions.py
 * Sync any changes between frontend and backend!
 */

export const PERMISSIONS = {
  // Dashboard & Analytics
  DASHBOARD_VIEW: 'dashboard:view',
  ANALYTICS_VIEW: 'analytics:view',
  WORKFORCE_VIEW: 'workforce:view',

  // Finance
  FINANCE_VIEW: 'finance:view',
  FINANCE_EXPORT: 'finance:export',

  // Employees
  EMPLOYEES_VIEW: 'employees:view',
  EMPLOYEES_CREATE: 'employees:create',
  EMPLOYEES_EDIT: 'employees:edit',
  EMPLOYEES_DELETE: 'employees:delete',
  EMPLOYEES_ASSIGN: 'employees:assign',

  // Managers
  MANAGERS_VIEW: 'managers:view',
  MANAGERS_CREATE: 'managers:create',
  MANAGERS_EDIT: 'managers:edit',
  MANAGERS_DELETE: 'managers:delete',

  // Admins
  ADMINS_VIEW: 'admins:view',
  ADMINS_CREATE: 'admins:create',
  ADMINS_EDIT: 'admins:edit',
  ADMINS_DELETE: 'admins:delete',

  // Projects & Contracts
  PROJECTS_VIEW: 'projects:view',
  PROJECTS_CREATE: 'projects:create',
  PROJECTS_EDIT: 'projects:edit',
  PROJECTS_DELETE: 'projects:delete',
  CONTRACTS_VIEW: 'contracts:view',
  CONTRACTS_CREATE: 'contracts:create',
  CONTRACTS_EDIT: 'contracts:edit',
  CONTRACTS_DELETE: 'contracts:delete',

  // Sites
  SITES_VIEW: 'sites:view',
  SITES_CREATE: 'sites:create',
  SITES_EDIT: 'sites:edit',
  SITES_DELETE: 'sites:delete',
  SITES_ASSIGN_WORKERS: 'sites:assign-workers',

  // Attendance & Payroll
  ATTENDANCE_VIEW: 'attendance:view',
  ATTENDANCE_EDIT: 'attendance:edit',
  PAYSLIPS_VIEW: 'payslips:view',
  PAYSLIPS_GENERATE: 'payslips:generate',
  OVERTIME_VIEW: 'overtime:view',
  OVERTIME_APPROVE: 'overtime:approve',
  DEDUCTIONS_VIEW: 'deductions:view',
  DEDUCTIONS_MANAGE: 'deductions:manage',

  // Operations
  INVENTORY_VIEW: 'inventory:view',
  INVENTORY_EDIT: 'inventory:edit',
  VEHICLES_VIEW: 'vehicles:view',
  VEHICLES_EDIT: 'vehicles:edit',
  VEHICLES_CREATE: 'vehicles:create',
  VEHICLES_DELETE: 'vehicles:delete',
  DUTY_LIST_VIEW: 'duty-list:view',
  DUTY_LIST_MANAGE: 'duty-list:manage',

  // Communication
  MESSAGES_VIEW: 'messages:view',
  MESSAGES_SEND: 'messages:send',
  MESSAGES_BROADCAST: 'messages:broadcast',
  MESSAGES_VIEW_ALL: 'messages:view-all',

  // Settings
  SETTINGS_VIEW: 'settings:view',
  SETTINGS_EDIT: 'settings:edit',

  // Audit Trail (Admin/SuperAdmin only)
  AUDIT_VIEW: 'audit:view',

  // Profile
  MY_PROFILE_VIEW: 'my-profile:view',
  MY_PROFILE_EDIT: 'my-profile:edit',
  MY_ATTENDANCE_VIEW: 'my-attendance:view',
  MY_ATTENDANCE_EDIT: 'my-attendance:edit',
};

// Role permission mappings (must match backend/config/permissions.py)
export const ROLE_PERMISSIONS = {
  SuperAdmin: ['*'],

  Admin: [
    PERMISSIONS.DASHBOARD_VIEW,
    PERMISSIONS.ANALYTICS_VIEW,
    PERMISSIONS.WORKFORCE_VIEW,
    PERMISSIONS.FINANCE_VIEW,
    PERMISSIONS.FINANCE_EXPORT,
    PERMISSIONS.EMPLOYEES_VIEW,
    PERMISSIONS.EMPLOYEES_CREATE,
    PERMISSIONS.EMPLOYEES_EDIT,
    PERMISSIONS.EMPLOYEES_ASSIGN,
    PERMISSIONS.MANAGERS_VIEW,
    PERMISSIONS.MANAGERS_CREATE,
    PERMISSIONS.MANAGERS_EDIT,
    PERMISSIONS.ADMINS_VIEW,
    PERMISSIONS.PROJECTS_VIEW,
    PERMISSIONS.PROJECTS_CREATE,
    PERMISSIONS.PROJECTS_EDIT,
    PERMISSIONS.PROJECTS_DELETE,
    PERMISSIONS.CONTRACTS_VIEW,
    PERMISSIONS.CONTRACTS_CREATE,
    PERMISSIONS.CONTRACTS_EDIT,
    PERMISSIONS.CONTRACTS_DELETE,
    PERMISSIONS.SITES_VIEW,
    PERMISSIONS.SITES_CREATE,
    PERMISSIONS.SITES_EDIT,
    PERMISSIONS.SITES_DELETE,
    PERMISSIONS.SITES_ASSIGN_WORKERS,
    PERMISSIONS.ATTENDANCE_VIEW,
    PERMISSIONS.ATTENDANCE_EDIT,
    PERMISSIONS.PAYSLIPS_VIEW,
    PERMISSIONS.PAYSLIPS_GENERATE,
    PERMISSIONS.OVERTIME_VIEW,
    PERMISSIONS.OVERTIME_APPROVE,
    PERMISSIONS.DEDUCTIONS_VIEW,
    PERMISSIONS.DEDUCTIONS_MANAGE,
    PERMISSIONS.INVENTORY_VIEW,
    PERMISSIONS.INVENTORY_EDIT,
    PERMISSIONS.VEHICLES_VIEW,
    PERMISSIONS.VEHICLES_EDIT,
    PERMISSIONS.VEHICLES_CREATE,
    PERMISSIONS.DUTY_LIST_VIEW,
    PERMISSIONS.DUTY_LIST_MANAGE,
    PERMISSIONS.MESSAGES_VIEW,
    PERMISSIONS.MESSAGES_SEND,
    PERMISSIONS.MESSAGES_BROADCAST,
    PERMISSIONS.MESSAGES_VIEW_ALL,
    PERMISSIONS.SETTINGS_VIEW,
    PERMISSIONS.AUDIT_VIEW,
    PERMISSIONS.MY_PROFILE_VIEW,
    PERMISSIONS.MY_PROFILE_EDIT,
    PERMISSIONS.MY_ATTENDANCE_VIEW,
  ],

  'Site Manager': [
    PERMISSIONS.DASHBOARD_VIEW,
    PERMISSIONS.EMPLOYEES_VIEW,
    PERMISSIONS.ATTENDANCE_VIEW,
    PERMISSIONS.ATTENDANCE_EDIT,
    PERMISSIONS.MESSAGES_VIEW,
    PERMISSIONS.MESSAGES_SEND,
    PERMISSIONS.MY_PROFILE_VIEW,
    PERMISSIONS.MY_PROFILE_EDIT,
    PERMISSIONS.MY_ATTENDANCE_VIEW,
    PERMISSIONS.MY_ATTENDANCE_EDIT,
    PERMISSIONS.SITES_VIEW,
    PERMISSIONS.INVENTORY_VIEW,
  ],
};
