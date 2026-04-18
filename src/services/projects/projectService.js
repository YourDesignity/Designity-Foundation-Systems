import BaseService from '../base/BaseService';

/**
 * Project service.
 */
class ProjectService extends BaseService {
  constructor() {
    super('/projects');
  }

  /**
   * Get all projects.
   * @param {Object} filters
   * @returns {Promise<Array>}
   */
  async getAll(filters = {}) {
    // TODO: Implement in Phase 4B
    return this.get('/', filters);
  }

  /**
   * Get project by ID.
   * @param {number|string} id
   * @returns {Promise<Object>}
   */
  async getById(id) {
    // TODO: Implement in Phase 4B
    return this.get(`/${id}`);
  }
}

export default new ProjectService();
