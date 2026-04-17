import BaseService from '../base/BaseService';

/**
 * Invoice service.
 */
class InvoiceService extends BaseService {
  constructor() {
    super('/invoices');
  }

  /**
   * Get all invoices.
   * @returns {Promise<Array>}
   */
  async getAll() {
    // TODO: Implement in Phase 4B
    return this.get('/');
  }

  /**
   * Create invoice.
   * @param {Object} payload
   * @returns {Promise<Object>}
   */
  async create(payload) {
    // TODO: Implement in Phase 4B
    return this.post('/', payload);
  }
}

export default new InvoiceService();
