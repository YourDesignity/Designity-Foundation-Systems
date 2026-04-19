import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-toastify';
import { roleContractsService, dailyFulfillmentService } from '../services';

/**
 * Fetch all role-enabled labour contracts.
 */
export const useRoleContracts = () => {
  return useQuery({
    queryKey: ['roleContracts'],
    queryFn: () => roleContractsService.getRoleContractsList(),
  });
};

/**
 * Fetch role slot configuration for a single contract.
 * @param {number|string} contractId
 */
export const useRoleContract = (contractId) => {
  return useQuery({
    queryKey: ['roleContract', contractId],
    queryFn: () => roleContractsService.getContractRoleConfiguration(contractId),
    enabled: !!contractId,
  });
};

/**
 * Fetch daily fulfillment record for a contract and date.
 * @param {number|string} contractId
 * @param {string} date  ISO date string (YYYY-MM-DD)
 */
export const useDailyFulfillment = (contractId, date) => {
  return useQuery({
    queryKey: ['dailyFulfillment', contractId, date],
    queryFn: () => dailyFulfillmentService.getDailyFulfillmentRecord(contractId, date),
    enabled: !!contractId && !!date,
  });
};

/**
 * Fetch monthly role cost report.
 * @param {number|string} contractId
 * @param {number|string} month
 * @param {number|string} year
 */
export const useMonthlyReport = (contractId, month, year) => {
  return useQuery({
    queryKey: ['monthlyReport', contractId, month, year],
    queryFn: () => dailyFulfillmentService.getMonthlyRoleCostReport(contractId, month, year),
    enabled: !!contractId && !!month && !!year,
  });
};

/**
 * Fetch all contracts with unfilled slots.
 */
export const useUnfilledSlots = () => {
  return useQuery({
    queryKey: ['unfilledSlots'],
    queryFn: () => dailyFulfillmentService.getUnfilledRoleSlots(),
  });
};

/**
 * Configure role slots for a contract.
 */
export const useConfigureRoleSlots = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ contractId, payload }) =>
      roleContractsService.post(`/${contractId}/configure`, payload),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['roleContracts'] });
      queryClient.invalidateQueries({ queryKey: ['roleContract', variables.contractId] });
      toast.success('Role slots configured successfully!');
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Failed to configure role slots');
    },
  });
};

/**
 * Record daily fulfillment for a contract.
 */
export const useRecordDailyFulfillment = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload) => dailyFulfillmentService.recordDailyFulfillment(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dailyFulfillment'] });
      queryClient.invalidateQueries({ queryKey: ['unfilledSlots'] });
      toast.success('Daily fulfillment recorded successfully!');
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Failed to record daily fulfillment');
    },
  });
};

/**
 * Assign an employee to a role slot.
 */
export const useAssignEmployeeToSlot = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ fulfillmentId, payload }) =>
      dailyFulfillmentService.assignRoleSlotEmployee(fulfillmentId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dailyFulfillment'] });
      queryClient.invalidateQueries({ queryKey: ['unfilledSlots'] });
      toast.success('Employee assigned to slot successfully!');
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Failed to assign employee to slot');
    },
  });
};

/**
 * Swap employee in a role slot (with audit trail).
 */
export const useSwapEmployeeInSlot = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ fulfillmentId, payload }) =>
      dailyFulfillmentService.swapRoleSlotEmployee(fulfillmentId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dailyFulfillment'] });
      toast.success('Employee swapped successfully!');
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Failed to swap employee');
    },
  });
};
