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
    return this.get('/');
  }

  /**
   * Get admin by ID.
   * @param {number|string} id
   * @returns {Promise<Object>}
   */
  async getById(id) {
    return this.get(`/${id}`);
  }

  /**
   * Create a new admin.
   * @param {Object} data
   * @returns {Promise<Object>}
   */
  async create(data) {
    return this.post('/', data);
  }

  /**
   * Delete an admin by ID.
   * @param {number|string} id
   * @returns {Promise<void>}
   */
  async deleteById(id) {
    return this.delete(`/${id}`);
  }
}

export default new AdminService();
