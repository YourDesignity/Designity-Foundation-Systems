import BaseService from '../base/BaseService';

/**
 * Temporary worker assignment service.
 */
class TempWorkerService extends BaseService {
  constructor() {
    super('/temp-assignments');
  }

  /**
   * Bulk assign workers to a site.
   * @param {number} siteId
   * @param {Array} workers
   * @param {string|null} replacementReason
   * @returns {Promise<Object>}
   */
  async assignTempWorkers(siteId, workers, replacementReason = null) {
    return this.post('/assign-workers', {
      site_id: siteId,
      workers,
      replacement_reason: replacementReason,
    });
  }

  /**
   * Get all available workers.
   * @returns {Promise<Array>}
   */
  async getAvailableTempWorkers() {
    return this.get('/available');
  }

  /**
   * Register temporary worker.
   * @param {Object} data
   * @returns {Promise<Object>}
   */
  async registerTempWorker(data) {
    return this.post('/register-worker', data);
  }

  /**
   * Get temporary workers assigned at a site.
   * @param {number|string} siteId
   * @returns {Promise<Object>}
   */
  async getTempWorkersAtSite(siteId) {
    return this.get(`/site/${siteId}`);
  }

  /**
   * End temporary assignment.
   * @param {number|string} assignmentId
   * @returns {Promise<any>}
   */
  async endTempAssignment(assignmentId) {
    return this.delete(`/${assignmentId}`);
  }

  /**
   * Get cost summary with optional filters.
   * @param {Object} filters
   * @returns {Promise<Object>}
   */
  async getCostSummary(filters = {}) {
    return this.get('/cost-summary', filters);
  }

  /**
   * Get all temporary workers.
   * @param {boolean|null} availableOnly
   * @returns {Promise<Array>}
   */
  async getAllTempWorkers(availableOnly = null) {
    const params = {};
    if (availableOnly !== null) {
      params.available_only = availableOnly;
    }
    return this.get('/workers', params);
  }

  /**
   * Get worker assignment history.
   * @param {number|string} workerId
   * @returns {Promise<Array>}
   */
  async getWorkerHistory(workerId) {
    return this.get(`/worker/${workerId}/history`);
  }

  /**
   * Get all temporary assignments with filters.
   * @param {Object} filters
   * @returns {Promise<Array>}
   */
  async getTempAssignments(filters = {}) {
    return this.get('/', filters);
  }
}

export default new TempWorkerService();
