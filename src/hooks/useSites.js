import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-toastify';
import { siteService } from '../services';

/**
 * Fetch all sites.
 */
export const useSites = () => {
  return useQuery({
    queryKey: ['sites'],
    queryFn: () => siteService.getAll(),
  });
};

/**
 * Fetch a single site by ID.
 * @param {number|string} id
 */
export const useSite = (id) => {
  return useQuery({
    queryKey: ['site', id],
    queryFn: () => siteService.getById(id),
    enabled: !!id,
  });
};

/**
 * Create a new site.
 * @returns {UseMutationResult}
 */
export const useCreateSite = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data) => siteService.post('/', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sites'] });
      toast.success('Site created successfully!');
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Failed to create site');
    },
  });
};

// TODO: Phase 4C - implement remaining site hooks (update, delete, getEmployees, getContracts)
