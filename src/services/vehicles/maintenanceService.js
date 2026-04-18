import BaseService from '../base/BaseService';

/**
 * Vehicle maintenance service.
 */
class MaintenanceService extends BaseService {
  constructor() {
    super('/vehicles');
  }

  /**
   * Get maintenance logs.
   * @returns {Promise<Array>}
   */
  async getAll() {
    // TODO: Implement in Phase 4B
    return this.get('/maintenance');
  }

  /**
   * Create maintenance log.
   * @param {Object} payload
   * @returns {Promise<Object>}
   */
  async create(payload) {
    // TODO: Implement in Phase 4B
    return this.post('/maintenance', payload);
  }
}

export default new MaintenanceService();
