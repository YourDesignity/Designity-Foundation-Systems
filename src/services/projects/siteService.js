import BaseService from '../base/BaseService';
import apiClient from '../base/apiClient';

/**
 * Site service.
 */
class SiteService extends BaseService {
  constructor() {
    super('/sites');
  }

  /**
   * Get all sites.
   * @returns {Promise<Array>}
   */
  async getAll() {
    return this.get('/');
  }

  /**
   * Get site by ID.
   * @param {number|string} id
   * @returns {Promise<Object>}
   */
  async getById(id) {
    return this.get(`/${id}`);
  }

  /**
   * Get workflow sites (optionally filtered by project).
   * @param {number|string} [projectId]
   * @returns {Promise<Array>}
   */
  async getWorkflowSites(projectId) {
    return apiClient.get(projectId ? `/workflow/sites/?project_id=${projectId}` : '/workflow/sites/');
  }
}

export default new SiteService();
