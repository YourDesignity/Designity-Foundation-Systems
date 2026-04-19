import BaseService from '../base/BaseService';

/**
 * Company settings service.
 */
class SettingsService extends BaseService {
  constructor() {
    super('/settings');
  }

  /**
   * Get all company settings.
   * @returns {Promise<Object>}
   */
  async getAll() {
    return this.get('/');
  }

  /**
   * Update company settings.
   * @param {Object} data
   * @returns {Promise<Object>}
   */
  async update(data) {
    return this.put('/', data);
  }
}

export default new SettingsService();
