import BaseService from '../base/BaseService';

/**
 * Schedule service.
 */
class ScheduleService extends BaseService {
  constructor() {
    super('/schedules');
  }

  /**
   * Get all schedules.
   * @returns {Promise<Array>}
   */
  async getAll() {
    // TODO: Implement in Phase 4B
    return this.get('/');
  }

  /**
   * Get schedule by ID.
   * @param {number|string} id
   * @returns {Promise<Object>}
   */
  async getById(id) {
    // TODO: Implement in Phase 4B
    return this.get(`/${id}`);
  }
}

export default new ScheduleService();
