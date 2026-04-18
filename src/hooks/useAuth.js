import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-toastify';
import authService from '../services/auth/authService';

/**
 * Login mutation hook.
 */
export const useLogin = () => {
  return useMutation({
    mutationFn: ({ email, password }) => authService.login(email, password),
    onSuccess: () => {
      toast.success('Login successful!');
      window.location.href = '/#/';
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Login failed');
    },
  });
};

/**
 * Logout mutation hook.
 */
export const useLogout = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => {
      authService.logout();
    },
    onSuccess: () => {
      queryClient.clear();
    },
  });
};

/**
 * Get current user decoded from stored JWT token.
 */
export const useCurrentUser = () => {
  return useQuery({
    queryKey: ['currentUser'],
    queryFn: () => authService.getCurrentUser(),
    staleTime: Infinity,
  });
};
