import BaseService from '../base/BaseService';

/**
 * Assignment service.
 */
class AssignmentService extends BaseService {
  constructor() {
    super('/assignments');
  }

  /**
   * Get assignments.
   * @param {Object} filters
   * @returns {Promise<Array>}
   */
  async getAll(filters = {}) {
    // TODO: Implement in Phase 4B
    return this.get('/', filters);
  }

  /**
   * Assign employee to site.
   * @param {Object} payload
   * @returns {Promise<Object>}
   */
  async assign(payload) {
    // TODO: Implement in Phase 4B
    return this.post('/', payload);
  }
}

export default new AssignmentService();
