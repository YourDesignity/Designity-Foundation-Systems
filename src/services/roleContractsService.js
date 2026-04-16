import { fetchWithAuth } from './apiService';

export const getRoleContractsList = async () => {
  try {
    const response = await fetchWithAuth('/contract-roles/list');
    return Array.isArray(response?.contracts) ? response.contracts : [];
  } catch {
    const contracts = await fetchWithAuth('/workflow/contracts/').catch(() => fetchWithAuth('/contracts/'));
    const list = Array.isArray(contracts) ? contracts : [];
    return list
      .filter((contract) => contract.contract_type === 'Labour' || Array.isArray(contract.role_slots))
      .map((contract) => ({
        contract_id: contract.uid ?? contract.contract_id ?? contract.id,
        contract_code: contract.contract_code,
        contract_type: contract.contract_type || 'Labour',
        total_role_slots: contract.total_role_slots || contract.role_slots?.length || 0,
        total_daily_cost: contract.total_daily_cost || (contract.role_slots || []).reduce((sum, slot) => sum + Number(slot.daily_rate || 0), 0),
        roles_by_designation: contract.roles_by_designation || (contract.role_slots || []).reduce((acc, slot) => {
          acc[slot.designation] = (acc[slot.designation] || 0) + 1;
          return acc;
        }, {}),
        site_ids: contract.site_ids || [],
        project_name: contract.project_name,
      }));
  }
};

export const getContractRoleConfiguration = (contractId) => fetchWithAuth(`/contract-roles/${contractId}`);
export const getUnfilledRoleSlots = () => fetchWithAuth('/daily-fulfillment/unfilled');
export const getDailyFulfillmentRecord = (contractId, date) => fetchWithAuth(`/daily-fulfillment/${contractId}/date/${date}`);
export const recordDailyFulfillment = (payload) => fetchWithAuth('/daily-fulfillment/record', { method: 'POST', body: JSON.stringify(payload) });
export const getMonthlyRoleCostReport = (contractId, month, year) => fetchWithAuth(`/daily-fulfillment/${contractId}/month/${month}/year/${year}`);
export const assignRoleSlotEmployee = (fulfillmentId, payload) => fetchWithAuth(`/daily-fulfillment/${fulfillmentId}/assign`, { method: 'PUT', body: JSON.stringify(payload) });
export const swapRoleSlotEmployee = (fulfillmentId, payload) => fetchWithAuth(`/daily-fulfillment/${fulfillmentId}/swap`, { method: 'PUT', body: JSON.stringify(payload) });
