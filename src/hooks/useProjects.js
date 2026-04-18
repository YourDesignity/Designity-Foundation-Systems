import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-toastify';
import { projectService } from '../services';

/**
 * Fetch all projects.
 * @param {Object} filters
 */
export const useProjects = (filters = {}) => {
  return useQuery({
    queryKey: ['projects', filters],
    queryFn: () => projectService.getAll(filters),
  });
};

/**
 * Fetch a single project by ID.
 * @param {number|string} id
 */
export const useProject = (id) => {
  return useQuery({
    queryKey: ['project', id],
    queryFn: () => projectService.getById(id),
    enabled: !!id,
  });
};

/**
 * Create a new project.
 * @returns {UseMutationResult}
 */
export const useCreateProject = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data) => projectService.post('/', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      toast.success('Project created successfully!');
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Failed to create project');
    },
  });
};

// TODO: Phase 4C - implement remaining project hooks (update, delete, getStats, getTeam)
