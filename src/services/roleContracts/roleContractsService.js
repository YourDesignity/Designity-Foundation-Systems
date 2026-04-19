import BaseService from '../base/BaseService';
import apiClient from '../base/apiClient';

/**
 * Contract role configuration service.
 */
class RoleContractsService extends BaseService {
  constructor() {
    super('/contract-roles');
  }

  /**
   * Get list of role-enabled contracts.
   * @returns {Promise<Array>}
   */
  async getRoleContractsList() {
    try {
      const response = await this.get('/list');
      return Array.isArray(response?.contracts) ? response.contracts : [];
    } catch {
      const contracts = await apiClient
        .get('/workflow/contracts/')
        .catch(() => apiClient.get('/contracts/'));
      const list = Array.isArray(contracts) ? contracts : [];
      return list
        .filter((contract) => ['SHIFT_BASED', 'DEDICATED_STAFF'].includes(contract.contract_type) || Array.isArray(contract.role_slots))
        .map((contract) => ({
          contract_id: contract.uid ?? contract.id ?? contract.contract_id,
          contract_code: contract.contract_code,
          contract_type: contract.contract_type || 'DEDICATED_STAFF',
          total_role_slots: contract.total_role_slots || contract.role_slots?.length || 0,
          total_daily_cost:
            contract.total_daily_cost ||
            (contract.role_slots || []).reduce((sum, slot) => sum + Number(slot.daily_rate || 0), 0),
          roles_by_designation:
            contract.roles_by_designation ||
            (contract.role_slots || []).reduce((acc, slot) => {
              acc[slot.designation] = (acc[slot.designation] || 0) + 1;
              return acc;
            }, {}),
          site_ids: contract.site_ids || [],
          project_name: contract.project_name,
        }));
    }
  }

  /**
   * Get role slot configuration for one contract.
   * @param {number|string} contractId
   * @returns {Promise<Object>}
   */
  async getContractRoleConfiguration(contractId) {
    return this.get(`/${contractId}`);
  }
}

export default new RoleContractsService();
