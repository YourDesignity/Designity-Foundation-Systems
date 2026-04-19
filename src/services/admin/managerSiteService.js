import BaseService from '../base/BaseService';

/**
 * Service for manager-site attendance and employee management.
 * Wraps the /manager-sites API endpoints.
 */
class ManagerSiteService extends BaseService {
  constructor() {
    super('/manager-sites');
  }

  /**
   * Get all sites managed by a specific manager.
   * @param {number|string} managerId
   * @returns {Promise<Object>} { manager_id, manager_name, total_sites, sites: [] }
   */
  async getManagerSites(managerId) {
    return this.get(`/${managerId}/sites`);
  }

  /**
   * Get all employees at a site managed by this manager.
   * @param {number|string} managerId
   * @param {number|string} siteId
   * @returns {Promise<Object>}
   */
  async getSiteEmployees(managerId, siteId) {
    return this.get(`/${managerId}/sites/${siteId}/employees`);
  }

  /**
   * Record bulk attendance for a site.
   * @param {number|string} managerId
   * @param {number|string} siteId
   * @param {Object} payload - { site_id, date, records: [] }
   * @returns {Promise<Object>}
   */
  async recordAttendance(managerId, siteId, payload) {
    return this.post(`/${managerId}/sites/${siteId}/attendance`, payload);
  }

  /**
   * Get attendance records for a managed site.
   * @param {number|string} managerId
   * @param {number|string} siteId
   * @param {string} [attendanceDate] - YYYY-MM-DD
   * @returns {Promise<Object>}
   */
  async getAttendance(managerId, siteId, attendanceDate) {
    const query = attendanceDate ? `?attendance_date=${attendanceDate}` : '';
    return this.get(`/${managerId}/sites/${siteId}/attendance${query}`);
  }
}

export default new ManagerSiteService();
