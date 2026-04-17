import BaseService from '../base/BaseService';

/**
 * Manager profile service.
 */
class ManagerService extends BaseService {
  constructor() {
    super('/managers/profiles');
  }

  /**
   * Get all managers.
   * @returns {Promise<Array>}
   */
  async getAll() {
    // TODO: Implement in Phase 4B
    return this.get('/');
  }

  /**
   * Get manager by ID.
   * @param {number|string} id
   * @returns {Promise<Object>}
   */
  async getById(id) {
    // TODO: Implement in Phase 4B
    return this.get(`/${id}`);
  }
}

export default new ManagerService();
