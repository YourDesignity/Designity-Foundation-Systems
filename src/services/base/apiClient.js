import axios from 'axios';
import { toast } from 'react-toastify';
import { extractErrorMessage } from './errorHandler';

const API_BASE_URL = 'http://127.0.0.1:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token') || localStorage.getItem('accessToken');

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error) => Promise.reject(error)
);

apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const status = error?.response?.status;
    const message = extractErrorMessage(error);

    if (!status) {
      toast.error('Network error. Please check your connection and backend status.');
      return Promise.reject(error);
    }

    if (status === 401) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('accessToken');
      localStorage.removeItem('currentUser');
      toast.error('Session expired. Please log in again.');
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
      return Promise.reject(error);
    }

    if (status === 403) {
      toast.error(message || 'You are not allowed to perform this action.');
      return Promise.reject(error);
    }

    if (status === 404) {
      toast.error(message || 'Requested resource not found.');
      return Promise.reject(error);
    }

    if (status >= 500) {
      toast.error(message || 'Server error. Please try again later.');
      return Promise.reject(error);
    }

    toast.error(message || `Request failed with status ${status}.`);
    return Promise.reject(error);
  }
);

export { API_BASE_URL };
export default apiClient;
