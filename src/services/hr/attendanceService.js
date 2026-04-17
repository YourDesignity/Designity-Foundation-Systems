import BaseService from '../base/BaseService';

/**
 * Attendance service.
 */
class AttendanceService extends BaseService {
  constructor() {
    super('/attendance');
  }

  /**
   * Get attendance by date.
   * @param {string} date
   * @returns {Promise<Array>}
   */
  async getByDate(date) {
    // TODO: Implement in Phase 4B
    return this.get(`/by-date/${date}`);
  }

  /**
   * Update attendance in batch.
   * @param {Object} payload
   * @returns {Promise<Object>}
   */
  async updateBatch(payload) {
    // TODO: Implement in Phase 4B
    return this.post('/update/', payload);
  }
}

export default new AttendanceService();
