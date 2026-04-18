import BaseService from '../base/BaseService';

/**
 * Manager profile service.
 */
class ManagerService extends BaseService {
  constructor() {
    super('');
  }

  /**
   * Get all managers (lightweight list for dropdowns).
   * @returns {Promise<Array>}
   */
  async getAll() {
    return this.get('/admins/managers');
  }

  /**
   * Get full manager profiles.
   * @returns {Promise<Array>}
   */
  async getProfiles() {
    return this.get('/managers/profiles');
  }

  /**
   * Get manager profile by ID.
   * @param {number|string} id
   * @returns {Promise<Object>}
   */
  async getById(id) {
    return this.get(`/managers/profiles/${id}`);
  }

  /**
   * Delete a manager profile by ID.
   * @param {number|string} id
   * @returns {Promise<void>}
   */
  async deleteProfile(id) {
    return this.delete(`/managers/profiles/${id}`);
  }
}

export default new ManagerService();
