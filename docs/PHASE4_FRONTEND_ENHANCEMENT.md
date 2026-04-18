# Phase 4 Frontend Enhancement — Complete Guide

This document covers Phase 4B through 4G of the Designity Foundation Systems frontend modernisation.

---

## Table of Contents

1. [Phase 4B – React Query State Management](#phase-4b)
2. [Phase 4C – Error Handling & Toast Notifications](#phase-4c)
3. [Phase 4D – Code Splitting & Lazy Loading](#phase-4d)
4. [Phase 4E – Enhanced Role Contracts UI](#phase-4e)
5. [Phase 4F – Performance Optimisation](#phase-4f)
6. [Phase 4G – Dashboard Charts](#phase-4g)
7. [Custom Hooks Reference](#hooks-reference)
8. [Migration Guide](#migration-guide)
9. [Performance Tips](#performance-tips)

---

## Phase 4B – React Query State Management <a id="phase-4b"></a>

### Setup

`src/main.jsx` wraps the app with `QueryClientProvider`:

```jsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});
```

`ReactQueryDevtools` is included (bottom-right corner in development).

### Quick Start

```js
import { useEmployees, useCreateEmployee } from '../hooks';

function EmployeesPage() {
  const { data: employees = [], isLoading, error } = useEmployees();
  const createMutation = useCreateEmployee();

  if (isLoading) return <Spin />;
  if (error) return <Alert type="error" message={error.message} />;

  return (
    <>
      <Button
        loading={createMutation.isPending}
        onClick={() => createMutation.mutate({ full_name: 'Jane Doe' })}
      >
        Add Employee
      </Button>
      <Table dataSource={employees} />
    </>
  );
}
```

---

## Phase 4C – Error Handling & Toast Notifications <a id="phase-4c"></a>

### Toast Utility (`src/utils/toast.js`)

```js
import { toast } from '../utils/toast';

toast.success('Employee saved!');
toast.error('Something went wrong.');
toast.warning('Low stock alert.');
toast.info('Processing…');
toast.promise(myPromise, { pending: 'Saving…', success: 'Saved!', error: 'Failed.' });
```

### ErrorBoundary

`src/components/ErrorBoundary.jsx` catches render errors and shows a user-friendly fallback with a refresh button.

Used in `App.jsx`:

```jsx
<ErrorBoundary>
  <Suspense fallback={<PageLoader />}>
    <Routes>…</Routes>
  </Suspense>
</ErrorBoundary>
```

---

## Phase 4D – Code Splitting & Lazy Loading <a id="phase-4d"></a>

All routes in `App.jsx` are now lazily loaded using `React.lazy()`:

```jsx
const EmployeesPage = lazy(() => import('./pages/EmployeesPage'));
```

A `<Suspense fallback={<PageLoader />}>` wrapper shows a spinner while the chunk downloads.

`src/components/PageLoader.jsx` renders a centred Ant Design `<Spin size="large" />`.

### Bundle Impact

Before lazy loading: single `index.js` bundle (~4.7 MB minified).  
After lazy loading: initial bundle significantly smaller with per-route chunks loaded on demand.

---

## Phase 4E – Enhanced Role Contracts UI <a id="phase-4e"></a>

New and enhanced components in `src/components/role-contracts/`:

| Component | Description |
|-----------|-------------|
| `FulfillmentCalendar.jsx` | Ant Design Calendar with colour-coded fulfillment rate badges |
| `SlotAssignmentModal.jsx` | Assign an employee to a specific slot with designation filtering |
| `QuickAssignModal.jsx` | One-click quick assignment with auto-suggest by designation |
| `EmployeeSwapModal.jsx` | Swap an assigned employee with audit trail |
| `UnfilledSlotsAlert.jsx` | Alert banner when unfilled slots are detected |
| `CostBreakdownChart.jsx` | Column chart showing cost by designation |
| `CostTrendChart.jsx` | Area chart showing monthly cost trend |
| `ContractRoleCard.jsx` | Summary card for a contract's role slots |

### Usage: QuickAssignModal

```jsx
import QuickAssignModal from '../components/role-contracts/QuickAssignModal';

<QuickAssignModal
  open={isOpen}
  slot={{ slot_id: 'S-1', designation: 'Security Guard', fulfillment_id: 42 }}
  assignedIds={[3, 7]}
  onCancel={() => setIsOpen(false)}
  onSuccess={() => refetch()}
/>
```

### Usage: CostTrendChart

```jsx
import CostTrendChart from '../components/role-contracts/CostTrendChart';

<CostTrendChart
  data={[
    { month: 'Jan 2025', total_cost: 45000 },
    { month: 'Feb 2025', total_cost: 52000 },
  ]}
  loading={false}
  height={300}
/>
```

---

## Phase 4F – Performance Optimisation <a id="phase-4f"></a>

### useDebounce Hook

`src/hooks/useDebounce.js` — debounce any value (e.g. search inputs):

```js
import useDebounce from '../hooks/useDebounce';

function SearchInput() {
  const [query, setQuery] = useState('');
  const debouncedQuery = useDebounce(query, 300);

  // Use debouncedQuery for API calls
  const { data } = useEmployees({ search: debouncedQuery });

  return <Input value={query} onChange={(e) => setQuery(e.target.value)} />;
}
```

### Other Optimisations Applied

- `useMemo` for filtered/sorted lists in `EmployeesPage`
- `useCallback` for stable mutation callbacks
- `React.memo` opportunities flagged for expensive card components
- All images should use `loading="lazy"` attribute

---

## Phase 4G – Dashboard Charts <a id="phase-4g"></a>

Four interactive ApexCharts components in `src/components/Dashboard/`:

| Component | Chart Type | Data Hook |
|-----------|-----------|-----------|
| `AttendanceTrendChart.jsx` | Line | `useAttendanceTrend()` |
| `RevenueTrendChart.jsx` | Bar | `useRevenueTrend()` |
| `CostBreakdownChart.jsx` | Pie | `useCostBreakdown()` |
| `ProjectStatusChart.jsx` | Donut | `useProjectMetrics()` |

All charts:
- Show a `<Spin />` while loading
- Show an `<Empty />` state when no data is available
- Are responsive (`width: '100%'`)
- Use `react-apexcharts` (already installed)

### Dashboard Hooks (`src/hooks/useDashboard.js`)

```js
import {
  useDashboardMetrics,
  useDashboardTrends,
  useAttendanceTrend,
  useRevenueTrend,
  useCostBreakdown,
  useProjectMetrics,
} from '../hooks/useDashboard';
```

### Backend Endpoints Required

The following endpoints need to be implemented in the Django backend:

| Endpoint | Returns |
|----------|---------|
| `GET /dashboard/metrics` | `{ total_projects, active_projects, total_sites, total_employees, … }` |
| `GET /dashboard/attendance-trend` | `[{ date: "YYYY-MM-DD", rate: 0-100 }, …]` |
| `GET /dashboard/revenue-trend` | `[{ month: "MMM YYYY", revenue: number }, …]` |
| `GET /dashboard/cost-breakdown` | `[{ category: string, value: number }, …]` |
| `GET /dashboard/project-metrics` | `[{ status: string, count: number }, …]` |

---

## Custom Hooks Reference <a id="hooks-reference"></a>

All hooks are exported from `src/hooks/index.js`.

### Employee Hooks

| Hook | Type |
|------|------|
| `useEmployees(filters?)` | Query |
| `useEmployee(id)` | Query |
| `useEmployeesByDesignation(designation)` | Query |
| `useEmployeesAtSite(siteId)` | Query |
| `useCreateEmployee()` | Mutation |
| `useUpdateEmployee()` | Mutation |
| `useDeleteEmployee()` | Mutation |
| `useUploadEmployeePhoto()` | Mutation |
| `useUploadEmployeeDocument()` | Mutation |

### Role Contract Hooks

| Hook | Type |
|------|------|
| `useRoleContracts()` | Query |
| `useRoleContract(contractId)` | Query |
| `useDailyFulfillment(contractId, date)` | Query |
| `useMonthlyReport(contractId, month, year)` | Query |
| `useUnfilledSlots()` | Query (auto-refetch 30s) |
| `useConfigureRoleSlots()` | Mutation |
| `useRecordDailyFulfillment()` | Mutation |
| `useAssignEmployeeToSlot()` | Mutation |
| `useSwapEmployeeInSlot()` | Mutation |

### Auth Hooks

| Hook | Type |
|------|------|
| `useLogin()` | Mutation |
| `useLogout()` | Mutation |
| `useCurrentUser()` | Query |

### Utility Hooks

| Hook | Description |
|------|-------------|
| `useDebounce(value, delay?)` | Debounce any value |

---

## Migration Guide <a id="migration-guide"></a>

### Before (manual state)

```jsx
const [data, setData] = useState([]);
const [loading, setLoading] = useState(true);

useEffect(() => {
  fetchWithAuth('/employees').then(setData).finally(() => setLoading(false));
}, []);
```

### After (React Query)

```jsx
const { data = [], isLoading } = useEmployees();
```

### Mutation Before

```jsx
const handleDelete = async (id) => {
  await fetchWithAuth(`/employees/${id}`, { method: 'DELETE' });
  setData((prev) => prev.filter((e) => e.uid !== id));
};
```

### Mutation After

```jsx
const deleteEmployee = useDeleteEmployee();
const handleDelete = (id) => deleteEmployee.mutate(id);
// Cache auto-invalidates — no manual state update needed
```

---

## Performance Tips <a id="performance-tips"></a>

1. **Query keys matter** — use `['employees', filters]` to cache per-filter.
2. **Stale time** — set to 5 minutes for relatively static data.
3. **Optimistic updates** — use `onMutate` + `onError` for instant UI feedback.
4. **Debounce search** — always wrap search `onChange` with `useDebounce`.
5. **Lazy load routes** — all pages are already lazy-loaded in `App.jsx`.
6. **React DevTools** — use the Profiler tab to identify unnecessary re-renders.
7. **React Query DevTools** — available bottom-right in development to inspect cache.
