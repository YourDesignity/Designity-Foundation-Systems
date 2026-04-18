import BaseService from '../base/BaseService';

/**
 * Material service.
 */
class MaterialService extends BaseService {
  constructor() {
    super('/materials');
  }

  /**
   * Get all materials.
   * @returns {Promise<Array>}
   */
  async getAll() {
    // TODO: Implement in Phase 4B
    return this.get('/');
  }

  /**
   * Get material by ID.
   * @param {number|string} id
   * @returns {Promise<Object>}
   */
  async getById(id) {
    // TODO: Implement in Phase 4B
    return this.get(`/${id}`);
  }
}

export default new MaterialService();
