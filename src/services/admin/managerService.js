import BaseService from '../base/BaseService';

/**
 * Manager profile service.
 * Uses an empty base path because this service spans two different
 * API prefixes: /admins/managers (list) and /managers/profiles (CRUD).
 */
class ManagerService extends BaseService {
  constructor() {
    // Empty base path: methods use absolute paths to span two API prefixes
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
