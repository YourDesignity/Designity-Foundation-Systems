import BaseService from '../base/BaseService';

/**
 * Workforce allocation service.
 */
class WorkforceService extends BaseService {
  constructor() {
    super('/workforce');
  }

  /**
   * Get workforce allocation data.
   * @returns {Promise<Object>}
   */
  async getAllocation() {
    return this.get('/allocation');
  }
}

export default new WorkforceService();
