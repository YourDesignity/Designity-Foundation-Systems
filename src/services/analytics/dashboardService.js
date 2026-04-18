import BaseService from '../base/BaseService';

/**
 * Dashboard analytics service.
 */
class DashboardService extends BaseService {
  constructor() {
    super('/dashboard');
  }

  /**
   * Get dashboard metrics.
   * @returns {Promise<Object>}
   */
  async getMetrics() {
    // TODO: Implement in Phase 4B
    return this.get('/metrics');
  }

  /**
   * Get dashboard trends.
   * @returns {Promise<Object>}
   */
  async getTrends() {
    // TODO: Implement in Phase 4B
    return this.get('/trends');
  }
}

export default new DashboardService();
