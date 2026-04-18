import BaseService from '../base/BaseService';

/**
 * Reporting service.
 */
class ReportingService extends BaseService {
  constructor() {
    super('/reports');
  }

  /**
   * Get available reports.
   * @returns {Promise<Array>}
   */
  async getAll() {
    // TODO: Implement in Phase 4B
    return this.get('/');
  }

  /**
   * Generate report.
   * @param {Object} payload
   * @returns {Promise<Object>}
   */
  async generate(payload) {
    // TODO: Implement in Phase 4B
    return this.post('/generate', payload);
  }
}

export default new ReportingService();
