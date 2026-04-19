import { useMemo } from 'react';
import { useAuth } from '../context/AuthContext';
import { ROLE_PERMISSIONS } from '../constants/permissions';

/**
 * Custom hook for checking user permissions based on the centralised RBAC config.
 * Uses role → permission mapping defined in code (not the JWT perms array),
 * which prevents privilege escalation via token manipulation.
 *
 * @returns {Object} Permission checking functions and current user's permission list
 */
export const usePermission = () => {
  const { user } = useAuth();

  const userPermissions = useMemo(() => {
    if (!user?.role) return [];

    const perms = ROLE_PERMISSIONS[user.role] || [];

    // SuperAdmin has wildcard – return as-is so hasPermission can detect '*'
    return perms;
  }, [user?.role]);

  const hasPermission = (permission) => {
    if (!user?.role) return false;

    // Wildcard check (SuperAdmin)
    if (userPermissions.includes('*')) return true;

    return userPermissions.includes(permission);
  };

  const hasAnyPermission = (permissions) => {
    return permissions.some((perm) => hasPermission(perm));
  };

  const hasAllPermissions = (permissions) => {
    return permissions.every((perm) => hasPermission(perm));
  };

  return {
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
    userPermissions,
  };
};
