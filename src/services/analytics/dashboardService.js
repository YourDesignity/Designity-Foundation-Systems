import BaseService from '../base/BaseService';

/**
 * Dashboard analytics service.
 */
class DashboardService extends BaseService {
  constructor() {
    super('/dashboard');
  }

  /** Get dashboard metrics (headcount, financials, alerts). */
  async getMetrics() {
    return this.get('/summary');
  }

  /** Get dashboard trends. */
  async getTrends() {
    return this.get('/trends');
  }

  /** Get attendance trend for the last 30 days. */
  async getAttendanceTrend() {
    return this.get('/attendance-trend');
  }

  /** Get monthly revenue trend for the last 12 months. */
  async getRevenueTrend() {
    return this.get('/revenue-trend');
  }

  /** Get cost breakdown by category (labour, materials, vehicles). */
  async getCostBreakdown() {
    return this.get('/cost-breakdown');
  }

  /** Get workflow summary for the workflow overview page. */
  async getWorkflowSummary() {
    return this.get('/workflow-summary');
  }
}

export default new DashboardService();
