import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';

// Import New Layout
import Main from './components/layout/Main';

// Import Pages
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage'; // The new one
import EmployeesPage from './pages/EmployeesPage';
import AttendancePage from './pages/AttendancePage';
import DutyListPage from './pages/DutyList';
import AddEmployeePage from './pages/AddEmployee';
import SiteManagement from './components/SiteManagement';
import DesignationManagement from './pages/DesignationManagement';
// ... import other pages

// Import CSS
import "antd/dist/reset.css"; // or 'antd/dist/antd.css' depending on version
import "./assets/styles/main.css";
import "./assets/styles/responsive.css";

const App = () => {
  return (
    <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />

          {/* Wrap authenticated routes in Main Layout */}
          <Route element={<Main />}>
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="employees" element={<EmployeesPage />} />
            <Route path="attendance" element={<AttendancePage />} />
            <Route path="duty-list" element={<DutyListPage />} />
            <Route path="site-management" element={<SiteManagement />} />
            <Route path="designations" element={<DesignationManagement />} />
            <Route path="add-employee" element={<AddEmployeePage />} />
            {/* Add other routes here */}
          </Route>

          <Route path="/" element={<Navigate to="/dashboard" replace />} />
        </Routes>
    </AuthProvider>
  );
};

export default App;