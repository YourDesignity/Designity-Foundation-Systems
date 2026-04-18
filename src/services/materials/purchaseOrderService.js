import BaseService from '../base/BaseService';

/**
 * Purchase order service.
 */
class PurchaseOrderService extends BaseService {
  constructor() {
    super('/purchase-orders');
  }

  /**
   * Get all purchase orders.
   * @param {Object} filters
   * @returns {Promise<Array>}
   */
  async getAll(filters = {}) {
    // TODO: Implement in Phase 4B
    return this.get('/', filters);
  }

  /**
   * Get purchase order by ID.
   * @param {number|string} id
   * @returns {Promise<Object>}
   */
  async getById(id) {
    // TODO: Implement in Phase 4B
    return this.get(`/${id}`);
  }
}

export default new PurchaseOrderService();
