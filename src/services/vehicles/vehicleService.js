import BaseService from '../base/BaseService';

/**
 * Vehicle service.
 */
class VehicleService extends BaseService {
  constructor() {
    super('/vehicles');
  }

  /**
   * Get all vehicles.
   * @returns {Promise<Array>}
   */
  async getAll() {
    // TODO: Implement in Phase 4B
    return this.get('/');
  }

  /**
   * Get vehicle by ID.
   * @param {number|string} id
   * @returns {Promise<Object>}
   */
  async getById(id) {
    // TODO: Implement in Phase 4B
    return this.get(`/${id}`);
  }
}

export default new VehicleService();
