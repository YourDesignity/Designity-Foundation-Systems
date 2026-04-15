import { usePermission } from '../hooks/usePermission';

/**
 * Conditionally renders children based on a single required permission.
 *
 * @param {string}          permission - Required permission string (e.g. "finance:view")
 * @param {React.ReactNode} children   - Content to render when permitted
 * @param {React.ReactNode} fallback   - Content to render when not permitted (default: null)
 */
export const PermissionGate = ({ permission, children, fallback = null }) => {
  const { hasPermission } = usePermission();
  return hasPermission(permission) ? children : fallback;
};

/**
 * Renders children when the user has ANY of the listed permissions.
 *
 * @param {string[]}        permissions - Array of permission strings
 * @param {React.ReactNode} children
 * @param {React.ReactNode} fallback
 */
export const PermissionGateAny = ({ permissions, children, fallback = null }) => {
  const { hasAnyPermission } = usePermission();
  return hasAnyPermission(permissions) ? children : fallback;
};

/**
 * Renders children only when the user has ALL of the listed permissions.
 *
 * @param {string[]}        permissions - Array of permission strings
 * @param {React.ReactNode} children
 * @param {React.ReactNode} fallback
 */
export const PermissionGateAll = ({ permissions, children, fallback = null }) => {
  const { hasAllPermissions } = usePermission();
  return hasAllPermissions(permissions) ? children : fallback;
};
