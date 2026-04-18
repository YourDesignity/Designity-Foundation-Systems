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

// TODO: Phase 4C - implement remaining dashboard hooks
// (useWorkforceSummary, useProjectAnalytics, useFinancialOverview)
