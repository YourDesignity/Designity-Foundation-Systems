import { jwtDecode } from 'jwt-decode';
import apiClient from '../base/apiClient';

/**
 * Authentication service.
 */
class AuthService {
  /**
   * Login with credentials.
   * @param {string} email
   * @param {string} password
   * @returns {Promise<Object>}
   */
  async login(email, password) {
    const formData = new FormData();
    formData.append('username', email);
    formData.append('password', password);

    const response = await apiClient.post('/token', formData);

    if (response?.access_token) {
      localStorage.setItem('access_token', response.access_token);
      localStorage.setItem('accessToken', response.access_token);
    }

    return response;
  }

  /**
   * Logout and redirect.
   */
  logout() {
    localStorage.clear();
    window.location.href = '/login';
  }

  /**
   * Placeholder for refresh token support.
   * @returns {Promise<null>}
   */
  async refreshToken() {
    return null;
  }

  /**
   * Get decoded current user from token.
   * @returns {Object|null}
   */
  getCurrentUser() {
    const token = localStorage.getItem('access_token') || localStorage.getItem('accessToken');
    if (!token) return null;

    try {
      return jwtDecode(token);
    } catch {
      return null;
    }
  }
}

export default new AuthService();
