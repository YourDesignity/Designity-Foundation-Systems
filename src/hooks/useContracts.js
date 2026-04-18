import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-toastify';
import { contractService } from '../services';

/**
 * Fetch all contracts.
 */
export const useContracts = () => {
  return useQuery({
    queryKey: ['contracts'],
    queryFn: () => contractService.getAll(),
  });
};

/**
 * Fetch a single contract by ID.
 * @param {number|string} id
 */
export const useContract = (id) => {
  return useQuery({
    queryKey: ['contract', id],
    queryFn: () => contractService.getById(id),
    enabled: !!id,
  });
};

// TODO: Phase 4C - implement remaining contract hooks

/**
 * Create a contract.
 * @returns {UseMutationResult}
 */
export const useCreateContract = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data) => contractService.post('/', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contracts'] });
      toast.success('Contract created successfully!');
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Failed to create contract');
    },
  });
};

/**
 * Delete a contract.
 * @returns {UseMutationResult}
 */
export const useDeleteContract = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id) => contractService.delete(`/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contracts'] });
      toast.success('Contract deleted successfully!');
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Failed to delete contract');
    },
  });
};
