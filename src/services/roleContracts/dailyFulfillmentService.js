import BaseService from '../base/BaseService';

/**
 * Daily role fulfillment service.
 */
class DailyFulfillmentService extends BaseService {
  constructor() {
    super('/daily-fulfillment');
  }

  /**
   * Get all contracts with unfilled slots.
   * @returns {Promise<Array>}
   */
  async getUnfilledRoleSlots() {
    return this.get('/unfilled');
  }

  /**
   * Get daily fulfillment record for contract/date.
   * @param {number|string} contractId
   * @param {string} date
   * @returns {Promise<Object>}
   */
  async getDailyFulfillmentRecord(contractId, date) {
    return this.get(`/${contractId}/date/${date}`);
  }

  /**
   * Record daily fulfillment payload.
   * @param {Object} payload
   * @returns {Promise<Object>}
   */
  async recordDailyFulfillment(payload) {
    return this.post('/record', payload);
  }

  /**
   * Get monthly role fulfillment/cost report.
   * @param {number|string} contractId
   * @param {number|string} month
   * @param {number|string} year
   * @returns {Promise<Object>}
   */
  async getMonthlyRoleCostReport(contractId, month, year) {
    return this.get(`/${contractId}/month/${month}/year/${year}`);
  }

  /**
   * Assign employee to a role slot.
   * @param {number|string} fulfillmentId
   * @param {Object} payload
   * @returns {Promise<Object>}
   */
  async assignRoleSlotEmployee(fulfillmentId, payload) {
    return this.put(`/${fulfillmentId}/assign`, payload);
  }

  /**
   * Swap employee for a role slot.
   * @param {number|string} fulfillmentId
   * @param {Object} payload
   * @returns {Promise<Object>}
   */
  async swapRoleSlotEmployee(fulfillmentId, payload) {
    return this.put(`/${fulfillmentId}/swap`, payload);
  }
}

export default new DailyFulfillmentService();
