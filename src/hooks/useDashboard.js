import { useQuery } from '@tanstack/react-query';
import { dashboardService } from '../services';

const DASHBOARD_STALE_TIME = 5 * 60 * 1000; // 5 minutes

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
    staleTime: DASHBOARD_STALE_TIME,
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
    staleTime: DASHBOARD_STALE_TIME,
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
    staleTime: DASHBOARD_STALE_TIME,
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
    staleTime: DASHBOARD_STALE_TIME,
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
    staleTime: DASHBOARD_STALE_TIME,
  });
};
