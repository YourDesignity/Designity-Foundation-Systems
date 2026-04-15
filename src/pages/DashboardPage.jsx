import React from 'react';
import { useAuth } from '../context/AuthContext';
import Dashboard from './Dashboard';
import ManagerDashboardPage from './ManagerDashboard';

/**
 * Role-Based Dashboard Router
 *
 * Routes users to the appropriate dashboard based on their role:
 * - SuperAdmin & Admin → Full company dashboard (Dashboard.jsx)
 * - Site Manager → Team-focused dashboard (ManagerDashboard.jsx)
 */
export default function DashboardPage() {
  const { user } = useAuth();

  if (user?.role === 'SuperAdmin' || user?.role === 'Admin') {
    return <Dashboard />;
  }

  if (user?.role === 'Site Manager') {
    return <ManagerDashboardPage />;
  }

  // Default fallback
  return <Dashboard />;
}
