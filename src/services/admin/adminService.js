import BaseService from '../base/BaseService';

/**
 * Admin user management service.
 */
class AdminService extends BaseService {
  constructor() {
    super('/admins');
  }

  /**
   * Get all admins.
   * @returns {Promise<Array>}
   */
  async getAll() {
    // TODO: Implement in Phase 4B
    return this.get('/');
  }

  /**
   * Get admin by ID.
   * @param {number|string} id
   * @returns {Promise<Object>}
   */
  async getById(id) {
    // TODO: Implement in Phase 4B
    return this.get(`/${id}`);
  }
}

export default new AdminService();
