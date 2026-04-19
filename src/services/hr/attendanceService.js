import BaseService from '../base/BaseService';
import apiClient, { API_BASE_URL } from '../base/apiClient';

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
    return this.get(`/by-date/${date}`);
  }

  /**
   * Get attendance for an entire month.
   * @param {number} year
   * @param {number} month
   * @returns {Promise<Array>}
   */
  async getByMonth(year, month) {
    return this.get(`/by-month/${year}/${month}/`);
  }

  /**
   * Update attendance in batch.
   * @param {Object} payload
   * @returns {Promise<Object>}
   */
  async updateBatch(payload) {
    return this.post('/update/', payload);
  }

  /**
   * Get manager attendance for all managers on a date.
   * @param {string} date
   * @returns {Promise<Array>}
   */
  async getManagerAttendance(date) {
    return apiClient.get('/managers/attendance/all', { params: { date } });
  }

  /**
   * Download attendance PDF for a given date.
   * @param {string} date
   * @returns {Promise<void>}
   */
  async downloadPDF(date) {
    const token = localStorage.getItem('access_token');
    const response = await fetch(`${API_BASE_URL}/attendance/export-pdf/${date}`, {
      method: 'GET',
      headers: { Authorization: `Bearer ${token}` },
    });
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Attendance_${date}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
  }
}

export default new AttendanceService();
