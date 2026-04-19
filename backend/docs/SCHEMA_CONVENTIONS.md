# Schema & ID Mapping Conventions

## Overview

This codebase uses **two intentional ID mapping patterns** for different entity types.

---

## Pattern 1: Core Entities (Admin, Employee, Site, Attendance, Schedule, Designation)

### Database Layer
- **Primary Key:** `uid` (integer, auto-incremented via `Counter` collection)
- **Foreign Keys:** `employee_uid`, `manager_uid`, `site_uid`

### Pydantic Schemas
- **Input (`validation_alias`):** Reads `uid` from the database model
- **Output (serialized):** Exposes the field as `id` in JSON responses

### Example

```python
# Database Model (models.py)
class Employee(Document, MemoryNode):
    uid: Optional[int] = None  # Auto-assigned from Counter
    name: str

# Pydantic Schema (schemas.py)
class EmployeePublic(BaseModel):
    id: int = Field(..., validation_alias="uid")  # Reads 'uid', outputs 'id'
    name: str
    model_config = ConfigDict(from_attributes=True)

# ✅ CORRECT – return model directly; FastAPI/Pydantic converts uid → id
employee = await Employee.find_one(Employee.uid == 3)
return employee  # Response: {"id": 3, "name": "John"}

# ✅ CORRECT – explicit conversion for WebSocket or manual serialization
emp_dict = schemas.EmployeeFull.model_validate(employee).model_dump(mode='json')

# ❌ WRONG – breaks response_model validation (schema expects 'uid' as input field)
return {"id": employee.uid, "name": employee.name}
```

---

## Pattern 2: DutyAssignment (Join Table)

### Database Layer
- Uses `employee_id`, `site_id`, `manager_id` (no `_uid` suffix)
- References: `employee_id` → `Employee.uid`, `site_id` → `Site.uid`, `manager_id` → `Admin.uid`

### Why Different?
- Semantic clarity: The join table uses `*_id` for its foreign key columns to distinguish
  them from the primary `uid` of the entity itself.
- The frontend handles both patterns defensively: `emp.id || emp.uid`.

### Do NOT Change
Do **not** rename `DutyAssignment` fields to `*_uid` — this would break the frontend
assignment logic without providing any benefit.

---

## Rules for Developers

### ✅ DO
1. Return database model objects directly when an endpoint uses `response_model`.
2. Use `schemas.MySchema.model_validate(obj).model_dump(mode='json')` when manually
   building data for WebSocket broadcasts or other non-FastAPI serialization paths.
3. Let Pydantic handle the `uid → id` conversion automatically via `validation_alias`.

### ❌ DON'T
1. Manually build dicts with `"id": obj.uid` when a `response_model` schema is active —
   this bypasses Pydantic and causes `ResponseValidationError` ("Field 'uid' required").
2. Add `obj_dict['id'] = obj.uid` after calling `model_dump()` — this creates duplicate
   or conflicting fields in the serialized output.
3. Change `DutyAssignment` to use the `*_uid` naming pattern.

---

## Quick Reference: Serialization Methods

| Context | Method | Result |
|---|---|---|
| FastAPI endpoint with `response_model` | `return model_instance` | ✅ Pydantic auto-converts |
| WebSocket broadcast / manual dict | `schemas.X.model_validate(obj).model_dump(mode='json')` | ✅ Correct, JSON-safe |
| Debug logging | `obj.model_dump(mode='json')` | ⚠️ Contains raw `uid`, not `id` |

---

## Testing

```bash
# Should return 200 with {"id": 3, "email": "..."}
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/admins/managers

# WebSocket employee_update messages should contain {"id": 3, ...} (integer, not ObjectId)
# Check browser DevTools > Network > WS after creating or updating an employee.
```
