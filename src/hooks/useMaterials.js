import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-toastify';
import { materialService } from '../services';

/**
 * Fetch all materials.
 */
export const useMaterials = () => {
  return useQuery({
    queryKey: ['materials'],
    queryFn: () => materialService.getAll(),
  });
};

/**
 * Fetch a single material by ID.
 * @param {number|string} id
 */
export const useMaterial = (id) => {
  return useQuery({
    queryKey: ['material', id],
    queryFn: () => materialService.getById(id),
    enabled: !!id,
  });
};

/**
 * Create a new material record.
 * @returns {UseMutationResult}
 */
export const useCreateMaterial = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data) => materialService.post('/', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['materials'] });
      toast.success('Material created successfully!');
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Failed to create material');
    },
  });
};

// TODO: Phase 4C - implement remaining material hooks (useSuppliers, usePurchaseOrders, useMaterialUpdate)
