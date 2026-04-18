import BaseService from '../base/BaseService';
import apiClient from '../base/apiClient';

/**
 * Contract service.
 */
class ContractService extends BaseService {
  constructor() {
    super('/contracts');
  }

  /**
   * Get all contracts.
   * @returns {Promise<Array>}
   */
  async getAll() {
    return this.get('/');
  }

  /**
   * Get contract by ID.
   * @param {number|string} id
   * @returns {Promise<Object>}
   */
  async getById(id) {
    return this.get(`/${id}`);
  }

  /**
   * Get workflow contracts (optionally filtered by project).
   * @param {number|string} [projectId]
   * @returns {Promise<Array>}
   */
  async getWorkflowContracts(projectId) {
    return apiClient.get(projectId ? `/workflow/contracts/?project_id=${projectId}` : '/workflow/contracts/');
  }
}

export default new ContractService();
