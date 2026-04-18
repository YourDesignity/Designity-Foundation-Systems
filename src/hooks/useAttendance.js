import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-toastify';
import { attendanceService } from '../services';

/**
 * Fetch attendance records for a specific date.
 * @param {string} date  ISO date string (YYYY-MM-DD)
 */
export const useAttendanceByDate = (date) => {
  return useQuery({
    queryKey: ['attendance', date],
    queryFn: () => attendanceService.getByDate(date),
    enabled: !!date,
  });
};

/**
 * Batch update attendance records.
 * @returns {UseMutationResult}
 */
export const useUpdateAttendanceBatch = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload) => attendanceService.updateBatch(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['attendance'] });
      toast.success('Attendance updated successfully!');
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Failed to update attendance');
    },
  });
};

// TODO: Phase 4C - implement remaining attendance hooks
// (useAttendanceSummary, useEmployeeAttendanceHistory, useAttendanceReport)
