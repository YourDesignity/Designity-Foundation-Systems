import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-toastify';
import { vehicleService } from '../services';

/**
 * Fetch all vehicles.
 */
export const useVehicles = () => {
  return useQuery({
    queryKey: ['vehicles'],
    queryFn: () => vehicleService.getAll(),
  });
};

/**
 * Fetch a single vehicle by ID.
 * @param {number|string} id
 */
export const useVehicle = (id) => {
  return useQuery({
    queryKey: ['vehicle', id],
    queryFn: () => vehicleService.getById(id),
    enabled: !!id,
  });
};

/**
 * Create a new vehicle record.
 * @returns {UseMutationResult}
 */
export const useCreateVehicle = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data) => vehicleService.post('/', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vehicles'] });
      toast.success('Vehicle added successfully!');
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Failed to add vehicle');
    },
  });
};

// TODO: Phase 4C - implement remaining vehicle hooks (useTrips, useMaintenanceRecords, useVehicleUpdate)
