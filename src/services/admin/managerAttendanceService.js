import BaseService from '../base/BaseService';

/**
 * Manager attendance service.
 */
class ManagerAttendanceService extends BaseService {
  constructor() {
    super('/managers/attendance');
  }

  /**
   * Get attendance config for manager.
   * @param {number|string} managerId
   * @returns {Promise<Object>}
   */
  async getConfig(managerId) {
    return this.get(`/config/${managerId}`);
  }

  /**
   * Get attendance overview for all managers on a date.
   * @param {string} date
   * @returns {Promise<Array>}
   */
  async getAll(date) {
    return this.get('/all', date ? { date } : {});
  }

  /**
   * Override manager attendance.
   * @param {Object} payload
   * @returns {Promise<Object>}
   */
  async override(payload) {
    return this.post('/override', payload);
  }
}

export default new ManagerAttendanceService();
