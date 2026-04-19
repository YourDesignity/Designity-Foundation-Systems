import roleContractsService from './roleContracts/roleContractsService';
import dailyFulfillmentService from './roleContracts/dailyFulfillmentService';

export const getRoleContractsList = () => roleContractsService.getRoleContractsList();
export const getContractRoleConfiguration = (contractId) =>
  roleContractsService.getContractRoleConfiguration(contractId);
export const getUnfilledRoleSlots = () => dailyFulfillmentService.getUnfilledRoleSlots();
export const getDailyFulfillmentRecord = (contractId, date) =>
  dailyFulfillmentService.getDailyFulfillmentRecord(contractId, date);
export const recordDailyFulfillment = (payload) =>
  dailyFulfillmentService.recordDailyFulfillment(payload);
export const getMonthlyRoleCostReport = (contractId, month, year) =>
  dailyFulfillmentService.getMonthlyRoleCostReport(contractId, month, year);
export const assignRoleSlotEmployee = (fulfillmentId, payload) =>
  dailyFulfillmentService.assignRoleSlotEmployee(fulfillmentId, payload);
export const swapRoleSlotEmployee = (fulfillmentId, payload) =>
  dailyFulfillmentService.swapRoleSlotEmployee(fulfillmentId, payload);

export default {
  getRoleContractsList,
  getContractRoleConfiguration,
  getUnfilledRoleSlots,
  getDailyFulfillmentRecord,
  recordDailyFulfillment,
  getMonthlyRoleCostReport,
  assignRoleSlotEmployee,
  swapRoleSlotEmployee,
};
