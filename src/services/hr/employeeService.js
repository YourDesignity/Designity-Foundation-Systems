import BaseService from '../base/BaseService';
import apiClient, { API_BASE_URL } from '../base/apiClient';

/**
 * Employee domain service.
 */
class EmployeeService extends BaseService {
  constructor() {
    super('/employees');
  }

  /**
   * Get all employees with optional filters.
   * @param {Object} filters
   * @returns {Promise<Array>}
   */
  async getAll(filters = {}) {
    return this.get('/', filters);
  }

  /**
   * Get employee by ID.
   * @param {number|string} id
   * @returns {Promise<Object>}
   */
  async getById(id) {
    return this.get(`/${id}/`);
  }

  /**
   * Create a new employee.
   * @param {Object|FormData} employeeData
   * @returns {Promise<Object>}
   */
  async create(employeeData) {
    return this.post('/', employeeData);
  }

  /**
   * Update employee details.
   * @param {number|string} id
   * @param {Object} employeeData
   * @returns {Promise<Object>}
   */
  async update(id, employeeData) {
    return this.put(`/${id}/`, employeeData);
  }

  /**
   * Delete an employee.
   * @param {number|string} id
   * @returns {Promise<any>}
   */
  async remove(id) {
    return this.delete(`/${id}/`);
  }

  /**
   * Upload employee photo.
   * @param {number|string} id
   * @param {File} file
   * @returns {Promise<Object>}
   */
  async uploadPhoto(id, file) {
    const formData = new FormData();
    formData.append('file', file);
    return this.upload(`/${id}/upload-photo`, formData);
  }

  /**
   * Upload employee document.
   * @param {number|string} id
   * @param {string} documentType
   * @param {File} file
   * @returns {Promise<Object>}
   */
  async uploadDocument(id, documentType, file) {
    const formData = new FormData();
    formData.append('file', file);
    return this.upload(`/${id}/upload-document?document_type=${encodeURIComponent(documentType)}`, formData);
  }

  /**
   * Download employee document.
   * @param {number|string} id
   * @param {string} documentType
   * @returns {Promise<Blob>}
   */
  async downloadDocument(id, documentType) {
    return apiClient.get(`/employees/${id}/download/${encodeURIComponent(documentType)}`, {
      responseType: 'blob',
    });
  }

  /**
   * Get employee photo URL with token query parameter.
   * @param {number|string} id
   * @returns {string}
   */
  getPhotoUrl(id) {
    const token = localStorage.getItem('access_token') || localStorage.getItem('accessToken') || '';
    return `${API_BASE_URL}/employees/${id}/download/photo?token=${token}`;
  }
}

export default new EmployeeService();
