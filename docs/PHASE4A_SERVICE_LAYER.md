# Phase 4A Frontend Service Layer

## Overview

Phase 4A introduces a domain-based frontend service architecture that mirrors backend service domains.

```text
UI Components
   ↓
Domain Services (src/services/<domain>)
   ↓
BaseService / apiClient / errorHandler
   ↓
FastAPI Backend
```

## Structure

- `src/services/base/`
  - `apiClient.js` (Axios + JWT + response interceptors + toast handling)
  - `BaseService.js` (shared CRUD + upload)
  - `errorHandler.js` (FastAPI-friendly error extraction)
- `src/services/<domain>/...` (domain-specific service classes)
- `src/services/index.js` (central named exports)

## Migration Guide

### Old pattern

```javascript
import { getEmployees, updateEmployee } from '../services/apiService';
```

### New pattern

```javascript
import { employeeService } from '../services';

const employees = await employeeService.getAll();
await employeeService.update(id, payload);
```

## Pilot Migrations Included

- `src/pages/EmployeesPage.jsx` now uses `employeeService`
- `src/pages/role-contracts/SlotManagement.jsx` now uses:
  - `roleContractsService`
  - `dailyFulfillmentService`
  - `employeeService`

## Backward Compatibility

- `src/services/apiService.jsx` remains functional.
- It is marked deprecated and now logs console warnings to support gradual migration.
- Legacy files:
  - `src/services/roleContractsService.js`
  - `src/services/tempWorkerService.js`
  remain as compatibility wrappers over the new domain services.

## Error Handling Best Practices

- Let `apiClient` response interceptors handle status-based UX messaging.
- Keep service methods focused on API interactions.
- Use `errorHandler.extractErrorMessage()` for consistent FastAPI error parsing.

## Domain Export Examples

```javascript
import {
  employeeService,
  roleContractsService,
  dailyFulfillmentService,
  authService,
  tempWorkerService,
} from '../services';
```

## Next Step (Phase 4B)

- Replace remaining `apiService` imports with domain services.
- Fill TODO stubs in non-pilot domains.
- Add targeted unit tests for high-use services.
