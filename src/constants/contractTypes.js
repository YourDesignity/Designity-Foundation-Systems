/**
 * Contract Type Constants
 * Single source of truth for contract types across the entire frontend.
 * Must stay in sync with backend/models/contracts/base_contract.py ContractType class.
 */

export const CONTRACT_TYPES = {
  DEDICATED_STAFF: 'DEDICATED_STAFF',
  SHIFT_BASED:     'SHIFT_BASED',
  GOODS_STORAGE:   'GOODS_STORAGE',
  TRANSPORTATION:  'TRANSPORTATION',
  HYBRID:          'HYBRID',
};

// Human-readable labels shown in UI
export const CONTRACT_TYPE_LABELS = {
  [CONTRACT_TYPES.DEDICATED_STAFF]: 'Dedicated Staff',
  [CONTRACT_TYPES.SHIFT_BASED]:     'Shift-Based',
  [CONTRACT_TYPES.GOODS_STORAGE]:   'Goods & Storage',
  [CONTRACT_TYPES.TRANSPORTATION]:  'Transportation',
  [CONTRACT_TYPES.HYBRID]:          'Hybrid',
};

// Ant Design tag colours per type
export const CONTRACT_TYPE_COLORS = {
  [CONTRACT_TYPES.DEDICATED_STAFF]: 'blue',
  [CONTRACT_TYPES.SHIFT_BASED]:     'cyan',
  [CONTRACT_TYPES.GOODS_STORAGE]:   'orange',
  [CONTRACT_TYPES.TRANSPORTATION]:  'purple',
  [CONTRACT_TYPES.HYBRID]:          'magenta',
};

// Array for dropdowns / selects
export const CONTRACT_TYPE_OPTIONS = Object.entries(CONTRACT_TYPE_LABELS).map(
  ([value, label]) => ({ value, label })
);

// Legacy map — old values that may still be in local state or cached API responses
export const LEGACY_CONTRACT_TYPE_MAP = {
  'Labour':           CONTRACT_TYPES.DEDICATED_STAFF,
  'Role-Based':       CONTRACT_TYPES.SHIFT_BASED,
  'Goods Supply':     CONTRACT_TYPES.GOODS_STORAGE,
  'Equipment Rental': CONTRACT_TYPES.TRANSPORTATION,
  'Hybrid':           CONTRACT_TYPES.HYBRID,
};

/**
 * Normalise a contract_type value — handles legacy strings from old API responses.
 * Always returns a CONTRACT_TYPES constant.
 */
export const normaliseContractType = (value) => {
  if (!value) return CONTRACT_TYPES.DEDICATED_STAFF;
  return LEGACY_CONTRACT_TYPE_MAP[value] ?? value;
};

/**
 * Get the display label for a contract type (handles legacy values too).
 */
export const getContractTypeLabel = (value) => {
  const normalised = normaliseContractType(value);
  return CONTRACT_TYPE_LABELS[normalised] ?? normalised;
};

/**
 * Get the Ant Design tag colour for a contract type.
 */
export const getContractTypeColor = (value) => {
  const normalised = normaliseContractType(value);
  return CONTRACT_TYPE_COLORS[normalised] ?? 'default';
};
