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
    // TODO: Implement in Phase 4B
    return this.get(`/config/${managerId}`);
  }

  /**
   * Get attendance overview.
   * @param {string} date
   * @returns {Promise<Array>}
   */
  async getAll(date) {
    // TODO: Implement in Phase 4B
    return this.get('/all', date ? { date } : {});
  }
}

export default new ManagerAttendanceService();
