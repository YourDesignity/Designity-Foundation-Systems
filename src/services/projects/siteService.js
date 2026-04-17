import BaseService from '../base/BaseService';

/**
 * Site service.
 */
class SiteService extends BaseService {
  constructor() {
    super('/sites');
  }

  /**
   * Get all sites.
   * @returns {Promise<Array>}
   */
  async getAll() {
    // TODO: Implement in Phase 4B
    return this.get('/');
  }

  /**
   * Get site by ID.
   * @param {number|string} id
   * @returns {Promise<Object>}
   */
  async getById(id) {
    // TODO: Implement in Phase 4B
    return this.get(`/${id}`);
  }
}

export default new SiteService();
