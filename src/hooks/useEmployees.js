import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-toastify';
import { employeeService } from '../services';

/**
 * Fetch all employees with optional filters.
 * @param {Object} filters
 */
export const useEmployees = (filters = {}) => {
  return useQuery({
    queryKey: ['employees', filters],
    queryFn: () => employeeService.getAll(filters),
  });
};

/**
 * Fetch a single employee by ID.
 * @param {number|string} id
 */
export const useEmployee = (id) => {
  return useQuery({
    queryKey: ['employee', id],
    queryFn: () => employeeService.getById(id),
    enabled: !!id,
  });
};

/**
 * Fetch employees filtered by designation.
 * @param {string} designation
 */
export const useEmployeesByDesignation = (designation) => {
  return useQuery({
    queryKey: ['employees', { designation }],
    queryFn: () => employeeService.getAll({ designation }),
    enabled: !!designation,
  });
};

/**
 * Fetch employees assigned to a specific site.
 * @param {number|string} siteId
 */
export const useEmployeesAtSite = (siteId) => {
  return useQuery({
    queryKey: ['employees', { siteId }],
    queryFn: () => employeeService.getAll({ site_id: siteId }),
    enabled: !!siteId,
  });
};

/**
 * Create a new employee.
 */
export const useCreateEmployee = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data) => employeeService.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['employees'] });
      toast.success('Employee created successfully!');
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Failed to create employee');
    },
  });
};

/**
 * Update an existing employee.
 */
export const useUpdateEmployee = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }) => employeeService.update(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['employees'] });
      queryClient.invalidateQueries({ queryKey: ['employee', variables.id] });
      toast.success('Employee updated successfully!');
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Failed to update employee');
    },
  });
};

/**
 * Delete an employee.
 */
export const useDeleteEmployee = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id) => employeeService.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['employees'] });
      toast.success('Employee deleted successfully!');
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Failed to delete employee');
    },
  });
};

/**
 * Upload an employee photo.
 */
export const useUploadEmployeePhoto = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, file }) => employeeService.uploadPhoto(id, file),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['employee', variables.id] });
      toast.success('Photo uploaded successfully!');
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Failed to upload photo');
    },
  });
};

/**
 * Upload an employee document.
 */
export const useUploadEmployeeDocument = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, documentType, file }) =>
      employeeService.uploadDocument(id, documentType, file),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['employee', variables.id] });
      toast.success('Document uploaded successfully!');
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Failed to upload document');
    },
  });
};
