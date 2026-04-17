import BaseService from '../base/BaseService';

/**
 * Financial analytics service.
 */
class FinanceService extends BaseService {
  constructor() {
    super('/finance');
  }

  /**
   * Get finance summary.
   * @returns {Promise<Object>}
   */
  async getSummary() {
    // TODO: Implement in Phase 4B
    return this.get('/summary');
  }

  /**
   * Get advanced summary.
   * @returns {Promise<Object>}
   */
  async getAdvancedSummary() {
    // TODO: Implement in Phase 4B
    return this.get('/advanced-summary');
  }
}

export default new FinanceService();
