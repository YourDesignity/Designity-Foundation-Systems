import apiClient from './apiClient';

/**
 * Base service with common HTTP helper methods.
 */
class BaseService {
  /**
   * @param {string} baseUrl
   */
  constructor(baseUrl) {
    this.baseUrl = baseUrl;
  }

  /**
   * @param {string} endpoint
   * @param {Object} [params]
   * @returns {Promise<any>}
   */
  async get(endpoint = '/', params = {}) {
    return apiClient.get(`${this.baseUrl}${endpoint}`, { params });
  }

  /**
   * @param {string} endpoint
   * @param {Object} data
   * @returns {Promise<any>}
   */
  async post(endpoint = '/', data = {}) {
    return apiClient.post(`${this.baseUrl}${endpoint}`, data);
  }

  /**
   * @param {string} endpoint
   * @param {Object} data
   * @returns {Promise<any>}
   */
  async put(endpoint = '/', data = {}) {
    return apiClient.put(`${this.baseUrl}${endpoint}`, data);
  }

  /**
   * @param {string} endpoint
   * @returns {Promise<any>}
   */
  async delete(endpoint = '/') {
    return apiClient.delete(`${this.baseUrl}${endpoint}`);
  }

  /**
   * @param {string} endpoint
   * @param {FormData} formData
   * @returns {Promise<any>}
   */
  async upload(endpoint = '/', formData) {
    return apiClient.post(`${this.baseUrl}${endpoint}`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  }
}

export default BaseService;
