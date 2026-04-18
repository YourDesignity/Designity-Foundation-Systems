import { useQuery } from '@tanstack/react-query';
import { dashboardService } from '../services';

/**
 * Fetch dashboard metrics (headcount, financials, alerts).
 */
export const useDashboardMetrics = () => {
  return useQuery({
    queryKey: ['dashboardMetrics'],
    queryFn: () => dashboardService.getMetrics(),
    staleTime: 2 * 60 * 1000, // 2 minutes — metrics refresh more frequently
  });
};

/**
 * Fetch dashboard trend data for charts.
 */
export const useDashboardTrends = () => {
  return useQuery({
    queryKey: ['dashboardTrends'],
    queryFn: () => dashboardService.getTrends(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

/**
 * Fetch attendance trend data (last 30 days).
 * Returns Array<{ date: string, rate: number }>
 */
export const useAttendanceTrend = () => {
  return useQuery({
    queryKey: ['attendanceTrend'],
    queryFn: () => dashboardService.getAttendanceTrend(),
    staleTime: 5 * 60 * 1000,
  });
};

/**
 * Fetch monthly revenue trend (last 12 months).
 * Returns Array<{ month: string, revenue: number }>
 */
export const useRevenueTrend = () => {
  return useQuery({
    queryKey: ['revenueTrend'],
    queryFn: () => dashboardService.getRevenueTrend(),
    staleTime: 5 * 60 * 1000,
  });
};

/**
 * Fetch cost breakdown by category.
 * Returns Array<{ category: string, value: number }>
 */
export const useCostBreakdown = () => {
  return useQuery({
    queryKey: ['costBreakdown'],
    queryFn: () => dashboardService.getCostBreakdown(),
    staleTime: 5 * 60 * 1000,
  });
};

/**
 * Fetch project status distribution.
 * Returns Array<{ status: string, count: number }>
 */
export const useProjectMetrics = () => {
  return useQuery({
    queryKey: ['projectMetrics'],
    queryFn: () => dashboardService.getProjectMetrics(),
    staleTime: 5 * 60 * 1000,
  });
};
