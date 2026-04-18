import BaseService from '../base/BaseService';

/**
 * Duty list assignment service.
 */
class DutyListService extends BaseService {
  constructor() {
    super('/duty_list');
  }

  /**
   * Get duty assignments for a specific date.
   * @param {string} date - ISO date string (YYYY-MM-DD)
   * @returns {Promise<Array>}
   */
  async getByDate(date) {
    return this.get(`/${date}`);
  }

  /**
   * Save duty assignments.
   * @param {Array} payload
   * @returns {Promise<Object>}
   */
  async save(payload) {
    return this.post('/', payload);
  }

  /**
   * Delete a duty assignment by ID.
   * @param {number|string} id
   * @returns {Promise<void>}
   */
  async deleteById(id) {
    return this.delete(`/${id}`);
  }
}

export default new DutyListService();
