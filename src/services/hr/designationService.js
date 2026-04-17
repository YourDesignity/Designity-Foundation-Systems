import BaseService from '../base/BaseService';

/**
 * Designation service.
 */
class DesignationService extends BaseService {
  constructor() {
    super('/designations');
  }

  /**
   * Get all designations.
   * @returns {Promise<Array>}
   */
  async getAll() {
    // TODO: Implement in Phase 4B
    return this.get('/');
  }

  /**
   * Create designation.
   * @param {Object} payload
   * @returns {Promise<Object>}
   */
  async create(payload) {
    // TODO: Implement in Phase 4B
    return this.post('/', payload);
  }
}

export default new DesignationService();
