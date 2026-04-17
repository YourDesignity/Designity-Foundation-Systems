import BaseService from '../base/BaseService';

/**
 * Contract service.
 */
class ContractService extends BaseService {
  constructor() {
    super('/contracts');
  }

  /**
   * Get all contracts.
   * @returns {Promise<Array>}
   */
  async getAll() {
    // TODO: Implement in Phase 4B
    return this.get('/');
  }

  /**
   * Get contract by ID.
   * @param {number|string} id
   * @returns {Promise<Object>}
   */
  async getById(id) {
    // TODO: Implement in Phase 4B
    return this.get(`/${id}`);
  }
}

export default new ContractService();
