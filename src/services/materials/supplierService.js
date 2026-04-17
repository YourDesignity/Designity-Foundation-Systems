import BaseService from '../base/BaseService';

/**
 * Supplier service.
 */
class SupplierService extends BaseService {
  constructor() {
    super('/suppliers');
  }

  /**
   * Get all suppliers.
   * @returns {Promise<Array>}
   */
  async getAll() {
    // TODO: Implement in Phase 4B
    return this.get('/');
  }

  /**
   * Create supplier.
   * @param {Object} payload
   * @returns {Promise<Object>}
   */
  async create(payload) {
    // TODO: Implement in Phase 4B
    return this.post('/', payload);
  }
}

export default new SupplierService();
