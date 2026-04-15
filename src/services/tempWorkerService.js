// src/services/tempWorkerService.js
// API service helpers for Temporary Worker Management (Phase 5)

import { fetchWithAuth } from './apiService';

/**
 * Bulk assign multiple temp workers to a site.
 * @param {number} siteId
 * @param {Array} workers - Array of { employee_id, start_date, end_date, rate_type, daily_rate, hourly_rate }
 * @param {string} [replacementReason]
 */
export const assignTempWorkers = (siteId, workers, replacementReason = null) =>
    fetchWithAuth('/temp-assignments/assign-workers', {
        method: 'POST',
        body: JSON.stringify({
            site_id: siteId,
            workers,
            replacement_reason: replacementReason,
        }),
    });

/**
 * Get available (unassigned) temp workers.
 */
export const getAvailableTempWorkers = () =>
    fetchWithAuth('/temp-assignments/available');

/**
 * Register a new temporary/outsourced worker.
 * @param {Object} data - { name, phone_kuwait, designation, agency_name, rate_type, daily_rate, hourly_rate }
 */
export const registerTempWorker = (data) =>
    fetchWithAuth('/temp-assignments/register-worker', {
        method: 'POST',
        body: JSON.stringify(data),
    });

/**
 * Get temp workers at a specific site.
 * @param {number} siteId
 */
export const getTempWorkersAtSite = (siteId) =>
    fetchWithAuth(`/temp-assignments/site/${siteId}`);

/**
 * End a temporary assignment.
 * @param {number} assignmentId
 */
export const endTempAssignment = (assignmentId) =>
    fetchWithAuth(`/temp-assignments/${assignmentId}`, {
        method: 'DELETE',
    });

/**
 * Get cost summary analytics.
 * @param {Object} filters - { site_id, project_id, month, year }
 */
export const getCostSummary = (filters = {}) => {
    const params = new URLSearchParams();
    if (filters.site_id) params.append('site_id', filters.site_id);
    if (filters.project_id) params.append('project_id', filters.project_id);
    if (filters.month) params.append('month', filters.month);
    if (filters.year) params.append('year', filters.year);
    const query = params.toString();
    return fetchWithAuth(`/temp-assignments/cost-summary${query ? `?${query}` : ''}`);
};

/**
 * Get all temp workers (with optional availability filter).
 * @param {boolean|null} availableOnly
 */
export const getAllTempWorkers = (availableOnly = null) => {
    const params = availableOnly !== null ? `?available_only=${availableOnly}` : '';
    return fetchWithAuth(`/temp-assignments/workers${params}`);
};

/**
 * Get assignment history for a specific worker.
 * @param {number} workerId
 */
export const getWorkerHistory = (workerId) =>
    fetchWithAuth(`/temp-assignments/worker/${workerId}/history`);

/**
 * Get all temporary assignments with optional filters.
 * @param {Object} filters - { site_id, status, start_after, end_before }
 */
export const getTempAssignments = (filters = {}) => {
    const params = new URLSearchParams();
    if (filters.site_id) params.append('site_id', filters.site_id);
    if (filters.status) params.append('status', filters.status);
    if (filters.start_after) params.append('start_after', filters.start_after);
    if (filters.end_before) params.append('end_before', filters.end_before);
    const query = params.toString();
    return fetchWithAuth(`/temp-assignments/${query ? `?${query}` : ''}`);
};
