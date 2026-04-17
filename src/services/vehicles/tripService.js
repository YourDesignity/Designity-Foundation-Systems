import BaseService from '../base/BaseService';

/**
 * Trip log service.
 */
class TripService extends BaseService {
  constructor() {
    super('/vehicles');
  }

  /**
   * Get all trips.
   * @returns {Promise<Array>}
   */
  async getAll() {
    // TODO: Implement in Phase 4B
    return this.get('/trips');
  }

  /**
   * Start trip.
   * @param {Object} payload
   * @returns {Promise<Object>}
   */
  async start(payload) {
    // TODO: Implement in Phase 4B
    return this.post('/trip/start', payload);
  }
}

export default new TripService();
