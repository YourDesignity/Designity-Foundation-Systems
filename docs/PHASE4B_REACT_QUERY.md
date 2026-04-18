# Phase 4B: React Query State Management Integration

## Overview

Phase 4B integrates **@tanstack/react-query** for server state management across the frontend. This replaces manual `useState`/`useEffect` data-fetching patterns with automatic caching, background refetching, loading/error states, and mutation hooks with toast notifications.

---

## Setup

### Dependencies Added

```bash
npm install @tanstack/react-query @tanstack/react-query-devtools
```

### QueryClient Configuration (`src/main.jsx`)

```javascript
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

// Wrap the app:
<QueryClientProvider client={queryClient}>
  <HashRouter>
    <App />
  </HashRouter>
  <ReactQueryDevtools initialIsOpen={false} />
</QueryClientProvider>
```

### Toast Notifications (`src/App.jsx`)

```javascript
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

// Inside the App component's JSX:
<ToastContainer
  position="top-right"
  autoClose={3000}
  hideProgressBar={false}
  newestOnTop
  closeOnClick
  pauseOnHover
  theme="light"
/>
```

---

## Custom Hooks

All hooks are available as named exports from `src/hooks/index.js`:

```javascript
import { useEmployees, useCreateEmployee, useLogin } from '../hooks';
```

---

### Employee Hooks (`src/hooks/useEmployees.js`)

| Hook | Type | Description |
|------|------|-------------|
| `useEmployees(filters?)` | Query | List all employees |
| `useEmployee(id)` | Query | Get single employee by ID |
| `useEmployeesByDesignation(designation)` | Query | Filter employees by designation |
| `useEmployeesAtSite(siteId)` | Query | Get employees assigned to a site |
| `useCreateEmployee()` | Mutation | Create new employee |
| `useUpdateEmployee()` | Mutation | Update existing employee |
| `useDeleteEmployee()` | Mutation | Delete employee |
| `useUploadEmployeePhoto()` | Mutation | Upload employee photo |
| `useUploadEmployeeDocument()` | Mutation | Upload employee document |

**Usage example:**

```javascript
import { useEmployees, useDeleteEmployee } from '../hooks';

function EmployeesPage() {
  const { data: employees = [], isLoading, error } = useEmployees();
  const deleteEmployee = useDeleteEmployee();

  const handleDelete = (id) => {
    if (confirm('Are you sure?')) {
      deleteEmployee.mutate(id);
    }
  };

  if (isLoading) return <Spin />;
  if (error) return <Alert type="error" message={error.message} />;

  return <Table dataSource={employees} /* ... */ />;
}
```

---

### Role Contracts Hooks (`src/hooks/useRoleContracts.js`)

| Hook | Type | Description |
|------|------|-------------|
| `useRoleContracts()` | Query | List all labour contracts |
| `useRoleContract(contractId)` | Query | Get contract role configuration |
| `useDailyFulfillment(contractId, date)` | Query | Get fulfillment for a specific date |
| `useMonthlyReport(contractId, month, year)` | Query | Get monthly cost report |
| `useUnfilledSlots()` | Query | Get unfilled slots alerts |
| `useConfigureRoleSlots()` | Mutation | Configure role slots for contract |
| `useRecordDailyFulfillment()` | Mutation | Record daily fulfillment |
| `useAssignEmployeeToSlot()` | Mutation | Assign employee to slot |
| `useSwapEmployeeInSlot()` | Mutation | Swap employee with audit trail |

**Usage example:**

```javascript
import { useRoleContracts, useAssignEmployeeToSlot } from '../hooks';

function SlotManagement() {
  const { data: contracts = [], isLoading } = useRoleContracts();
  const assignMutation = useAssignEmployeeToSlot();

  const handleAssign = (fulfillmentId, payload) => {
    assignMutation.mutate({ fulfillmentId, payload });
  };

  return (
    <Button
      loading={assignMutation.isPending}
      onClick={() => handleAssign(id, payload)}
    >
      Assign
    </Button>
  );
}
```

---

### Auth Hooks (`src/hooks/useAuth.js`)

| Hook | Type | Description |
|------|------|-------------|
| `useLogin()` | Mutation | Login and store token |
| `useLogout()` | Mutation | Logout and clear cache |
| `useCurrentUser()` | Query | Get decoded user from JWT |

**Usage example:**

```javascript
import { useLogin } from '../hooks';

function LoginPage() {
  const loginMutation = useLogin();

  const handleSubmit = (e) => {
    e.preventDefault();
    loginMutation.mutate({ email, password });
  };

  return (
    <form onSubmit={handleSubmit}>
      <button disabled={loginMutation.isPending}>
        {loginMutation.isPending ? 'Logging in...' : 'Login'}
      </button>
    </form>
  );
}
```

---

### Other Service Hooks

These hooks have basic implementations with stubs for Phase 4C:

| File | Implemented Hooks | Stubs (Phase 4C) |
|------|------------------|-----------------|
| `useContracts.js` | `useContracts`, `useContract`, `useCreateContract`, `useDeleteContract` | update, details |
| `useProjects.js` | `useProjects`, `useProject`, `useCreateProject` | update, delete, stats, team |
| `useSites.js` | `useSites`, `useSite`, `useCreateSite` | update, delete, employees, contracts |
| `useAttendance.js` | `useAttendanceByDate`, `useUpdateAttendanceBatch` | summary, history, report |
| `useVehicles.js` | `useVehicles`, `useVehicle`, `useCreateVehicle` | trips, maintenance, update |
| `useMaterials.js` | `useMaterials`, `useMaterial`, `useCreateMaterial` | suppliers, purchase orders, update |
| `useInvoices.js` | `useInvoices`, `useCreateInvoice` | single invoice, update, delete, PDF |
| `useDashboard.js` | `useDashboardMetrics`, `useDashboardTrends` | workforce, analytics, financial |

---

## Query Key Conventions

```
['employees']             // All employees
['employees', filters]    // Employees with filters
['employee', id]          // Single employee

['roleContracts']         // All role contracts
['roleContract', id]      // Single contract config
['dailyFulfillment', contractId, date]  // Daily record
['monthlyReport', contractId, month, year]
['unfilledSlots']

['contracts']
['contract', id]
['projects', filters]
['project', id]
['sites']
['site', id]

['attendance', date]
['vehicles']
['vehicle', id]
['materials']
['invoices']

['dashboardMetrics']
['dashboardTrends']
['currentUser']
```

---

## Mutation Patterns

All mutations follow this pattern:

1. Call `useQueryClient()` for cache invalidation
2. `onSuccess` – invalidate related queries + show success toast
3. `onError` – show error toast with backend detail message

```javascript
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
```

---

## Error Handling

Errors from backend FastAPI are formatted as:

```json
{ "detail": "Error message here" }
```

Hooks extract this via `error.response?.data?.detail` with a fallback generic message.

---

## Optimistic Updates (Future Enhancement)

For Phase 4C, optimistic updates can be added to mutations:

```javascript
export const useUpdateEmployee = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }) => employeeService.update(id, data),
    onMutate: async ({ id, data }) => {
      await queryClient.cancelQueries({ queryKey: ['employee', id] });
      const previous = queryClient.getQueryData(['employee', id]);
      queryClient.setQueryData(['employee', id], (old) => ({ ...old, ...data }));
      return { previous };
    },
    onError: (error, variables, context) => {
      queryClient.setQueryData(['employee', variables.id], context.previous);
      toast.error('Failed to update employee');
    },
    onSettled: (_, __, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['employee', id] });
    },
  });
};
```

---

## Migrated Components

| Component | Status | Hooks Used |
|-----------|--------|-----------|
| `EmployeesPage.jsx` | ✅ Migrated | `useEmployees`, `useDeleteEmployee`, `useUpdateEmployee`, `useUploadEmployeePhoto` |
| `role-contracts/index.jsx` | ✅ Migrated | `useRoleContracts`, `useUnfilledSlots`, `useSites` |
| `role-contracts/DailyFulfillmentRecord.jsx` | ✅ Migrated | `useRoleContracts`, `useRoleContract`, `useEmployees`, `useRecordDailyFulfillment` |
| `role-contracts/SlotManagement.jsx` | ✅ Migrated | `useRoleContracts`, `useEmployees`, `useAssignEmployeeToSlot`, `useSwapEmployeeInSlot` |
| `LoginPage.jsx` | ✅ Migrated | `useMutation` wrapping `useAuth().login` |

---

## Migration Guide for Developers

### Before (manual state management)

```javascript
const [employees, setEmployees] = useState([]);
const [loading, setLoading] = useState(true);

useEffect(() => {
  employeeService.getAll()
    .then(setEmployees)
    .finally(() => setLoading(false));
}, []);
```

### After (React Query)

```javascript
import { useEmployees } from '../hooks';

const { data: employees = [], isLoading } = useEmployees();
```

### For create/update/delete

```javascript
// Before
const handleDelete = async (id) => {
  setLoading(true);
  try {
    await employeeService.remove(id);
    message.success('Deleted!');
    await loadData(); // manual refetch
  } catch (err) {
    message.error('Failed');
  } finally {
    setLoading(false);
  }
};

// After
const deleteEmployee = useDeleteEmployee(); // includes cache invalidation + toast

const handleDelete = (id) => {
  deleteEmployee.mutate(id);
};

// Button
<Button loading={deleteEmployee.isPending} onClick={() => handleDelete(id)}>
  Delete
</Button>
```

---

## DevTools

React Query DevTools appear in the bottom-left corner in development mode. Open them to:
- Inspect all active/inactive queries
- See cache state and stale times
- Trigger manual refetches
- Monitor mutation states

---

## Testing Checklist

After implementing Phase 4B:

1. ✅ React Query DevTools appears in bottom corner (dev mode)
2. ✅ Employee CRUD operations confirm cache invalidation works
3. ✅ Role contract fulfillment confirms auto-refetch after mutations
4. ✅ Login flow confirms token storage and redirect
5. ✅ Toast notifications appear on success/error
6. ✅ Browser Network tab confirms requests are cached (no duplicate calls)
7. ✅ Component unmount/remount confirms data persists from cache
