import BaseService from '../base/BaseService';

/**
 * Inventory service.
 */
class InventoryService extends BaseService {
  constructor() {
    super('/inventory');
  }

  /**
   * Get all inventory items.
   * @returns {Promise<Array>}
   */
  async getAll() {
    return this.get('/');
  }

  /**
   * Create a new inventory item.
   * @param {Object} data
   * @returns {Promise<Object>}
   */
  async create(data) {
    return this.post('/', data);
  }

  /**
   * Delete an inventory item by ID.
   * @param {number|string} id
   * @returns {Promise<void>}
   */
  async deleteById(id) {
    return this.delete(`/${id}`);
  }
}

export default new InventoryService();
