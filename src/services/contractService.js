/**
 * contractService.js
 *
 * API service for the Modular Contract Workflow System (Phase 5C–5F).
 * Provides full CRUD, module management, assignment, workflow, and
 * scheduling operations against the backend REST API.
 */

import apiClient from './base/apiClient';

const BASE = '/api/contracts';

// ─── Contract CRUD ────────────────────────────────────────────────────────────

/**
 * Fetch all contracts with optional filters and pagination.
 * @param {Object} [params] - Query params (status, type, project_id, search, page, page_size)
 */
export const getContracts = (params = {}) =>
  apiClient.get(BASE + '/', { params });

/**
 * Fetch a single contract by ID.
 * @param {string|number} id
 */
export const getContractById = (id) =>
  apiClient.get(`${BASE}/${id}`);

/**
 * Create a new contract.
 * @param {Object} data
 */
export const createContract = (data) =>
  apiClient.post(BASE + '/', data);

/**
 * Update an existing contract.
 * @param {string|number} id
 * @param {Object} data
 */
export const updateContract = (id, data) =>
  apiClient.put(`${BASE}/${id}`, data);

/**
 * Delete a contract.
 * @param {string|number} id
 */
export const deleteContract = (id) =>
  apiClient.delete(`${BASE}/${id}`);

/**
 * Clone an existing contract.
 * @param {string|number} id
 */
export const cloneContract = (id) =>
  apiClient.post(`${BASE}/${id}/clone`);

// ─── Module operations ────────────────────────────────────────────────────────

/**
 * Get all available module definitions.
 */
export const getModules = () =>
  apiClient.get('/api/modules/');

/**
 * Enable a module on a contract.
 * @param {string|number} contractId
 * @param {string} moduleType - 'employee' | 'inventory' | 'vehicle'
 * @param {Object} config
 */
export const enableModule = (contractId, moduleType, config = {}) =>
  apiClient.post(`${BASE}/${contractId}/modules/${moduleType}`, config);

/**
 * Disable a module on a contract.
 * @param {string|number} contractId
 * @param {string} moduleType
 */
export const disableModule = (contractId, moduleType) =>
  apiClient.delete(`${BASE}/${contractId}/modules/${moduleType}`);

/**
 * Update module configuration.
 * @param {string|number} contractId
 * @param {string} moduleType
 * @param {Object} config
 */
export const updateModuleConfig = (contractId, moduleType, config) =>
  apiClient.put(`${BASE}/${contractId}/modules/${moduleType}`, config);

// ─── Assignment operations ────────────────────────────────────────────────────

/**
 * Get assignments for a contract, optionally filtered by module type.
 * @param {string|number} contractId
 * @param {string} [moduleType] - 'employee' | 'inventory' | 'vehicle'
 */
export const getAssignments = (contractId, moduleType) => {
  const url = moduleType
    ? `${BASE}/${contractId}/assignments/${moduleType}`
    : `${BASE}/${contractId}/assignments/`;
  return apiClient.get(url);
};

/**
 * Assign employees to a contract.
 * @param {string|number} contractId
 * @param {number[]} employeeIds
 * @param {Object} details - { start_date, end_date, role, permissions }
 */
export const assignEmployee = (contractId, employeeIds, details = {}) =>
  apiClient.post(`${BASE}/${contractId}/assignments/employee`, {
    employee_ids: employeeIds,
    ...details,
  });

/**
 * Assign inventory items to a contract.
 * @param {string|number} contractId
 * @param {number[]} inventoryIds
 * @param {Object} details
 */
export const assignInventory = (contractId, inventoryIds, details = {}) =>
  apiClient.post(`${BASE}/${contractId}/assignments/inventory`, {
    inventory_ids: inventoryIds,
    ...details,
  });

/**
 * Assign vehicles to a contract.
 * @param {string|number} contractId
 * @param {number[]} vehicleIds
 * @param {Object} details
 */
export const assignVehicle = (contractId, vehicleIds, details = {}) =>
  apiClient.post(`${BASE}/${contractId}/assignments/vehicle`, {
    vehicle_ids: vehicleIds,
    ...details,
  });

// ─── Workflow operations ──────────────────────────────────────────────────────

/**
 * Get current workflow state for a contract.
 * @param {string|number} contractId
 */
export const getWorkflowState = (contractId) =>
  apiClient.get(`${BASE}/${contractId}/workflow/`);

/**
 * Transition the workflow to a new state.
 * @param {string|number} contractId
 * @param {string} action - 'submit' | 'approve' | 'reject' | 'activate' | 'complete' | 'cancel' | 'suspend'
 * @param {Object} [data] - { comment, reason }
 */
export const transitionWorkflow = (contractId, action, data = {}) =>
  apiClient.post(`${BASE}/${contractId}/workflow/${action}`, data);

/**
 * Get approval history for a contract.
 * @param {string|number} contractId
 */
export const getApprovalHistory = (contractId) =>
  apiClient.get(`${BASE}/${contractId}/history`);

/**
 * Approve a contract.
 * @param {string|number} contractId
 * @param {string} [comment]
 */
export const approveContract = (contractId, comment = '') =>
  transitionWorkflow(contractId, 'approve', { comment });

/**
 * Reject a contract.
 * @param {string|number} contractId
 * @param {string} [comment]
 */
export const rejectContract = (contractId, comment = '') =>
  transitionWorkflow(contractId, 'reject', { comment });

// ─── Scheduling operations ────────────────────────────────────────────────────

/**
 * Get all scheduled tasks for a contract.
 * @param {string|number} contractId
 */
export const getScheduledTasks = (contractId) =>
  apiClient.get(`${BASE}/${contractId}/schedule/`);

/**
 * Create a scheduled task for a contract.
 * @param {string|number} contractId
 * @param {Object} task
 */
export const createScheduledTask = (contractId, task) =>
  apiClient.post(`${BASE}/${contractId}/schedule/`, task);

/**
 * Update a scheduled task.
 * @param {string|number} taskId
 * @param {Object} task
 */
export const updateScheduledTask = (taskId, task) =>
  apiClient.put(`/api/schedule/${taskId}`, task);

/**
 * Delete a scheduled task.
 * @param {string|number} taskId
 */
export const deleteScheduledTask = (taskId) =>
  apiClient.delete(`/api/schedule/${taskId}`);

/**
 * Get automations for a contract.
 * @param {string|number} contractId
 */
export const getAutomations = (contractId) =>
  apiClient.get(`${BASE}/${contractId}/schedule/automations`);

/**
 * Create an automation rule.
 * @param {string|number} contractId
 * @param {Object} automation
 */
export const createAutomation = (contractId, automation) =>
  apiClient.post(`${BASE}/${contractId}/schedule/automations`, automation);

// ─── Global module settings ───────────────────────────────────────────────────

/**
 * Get global module settings.
 */
export const getGlobalModuleSettings = () =>
  apiClient.get('/api/modules/settings');

/**
 * Update global module settings.
 * @param {Object} settings
 */
export const updateGlobalModuleSettings = (settings) =>
  apiClient.put('/api/modules/settings', settings);

// ─── Notification & activity log ─────────────────────────────────────────────

/**
 * Get activity log / notification history for a contract.
 * @param {string|number} contractId
 */
export const getActivityLog = (contractId) =>
  apiClient.get(`${BASE}/${contractId}/activity`);

export default {
  getContracts,
  getContractById,
  createContract,
  updateContract,
  deleteContract,
  cloneContract,
  getModules,
  enableModule,
  disableModule,
  updateModuleConfig,
  getAssignments,
  assignEmployee,
  assignInventory,
  assignVehicle,
  getWorkflowState,
  transitionWorkflow,
  getApprovalHistory,
  approveContract,
  rejectContract,
  getScheduledTasks,
  createScheduledTask,
  updateScheduledTask,
  deleteScheduledTask,
  getAutomations,
  createAutomation,
  getGlobalModuleSettings,
  updateGlobalModuleSettings,
  getActivityLog,
};
