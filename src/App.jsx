// src/App.js

import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';

// --- Layout ---
import Main from './components/layout/Main';

// --- Pages ---
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import EmployeesPage from './pages/EmployeesPage';
import EmployeeProfilePage from './pages/EmployeeProfilePage';
import AttendancePage from './pages/AttendancePage';
import DutyListPage from './pages/DutyList';
import AddEmployeePage from './pages/AddEmployee';
import MessagePage from './pages/MessagePage';
import ManagerMessagesPage from './pages/ManagerMessagesPage';
import ProjectsPage from './pages/ProjectsPage'; 
import InventoryPage from './pages/InventoryPage';
import SiteManagement from './components/SiteManagement'; 
import DesignationManagement from './pages/DesignationManagement';
import AdminManagementPage from './pages/AdminManagementPage';
import ManagersPage from './pages/ManagersPage';
import CreateManagerPage from './pages/CreateManagerPage';
import EditManagerPage from './pages/EditManagerPage';
import ManagerAttendanceAdminPage from './pages/ManagerAttendanceAdminPage';
import ManagerMyAttendancePage from './pages/ManagerMyAttendancePage';
import PayslipPage from './pages/PayslipPage';
import OvertimePage from './pages/OvertimePage';
import DeductionsPage from './pages/DeductionsPage';
import VehicleManagementPage from './pages/VehicleManagement'; 

// --- NEW FINANCIAL PAGES ---
import FinancePage from './pages/FinancePage'; // <--- NEW: Profit & Loss Page
import CompanySettingsPage from './pages/CompanySettingsPage';

// --- PROJECT WORKFLOW PAGES ---
import ProjectDashboard from './pages/ProjectWorkflow/ProjectDashboard';
import ContractManagementPage from './pages/ProjectWorkflow/ContractManagementPage';
import SiteManagementPage from './pages/ProjectWorkflow/SiteManagementPage';
import EmployeeAssignment from './pages/ProjectWorkflow/EmployeeAssignment';
import TempWorkerManagement from './pages/ProjectWorkflow/TempWorkerManagement';
import WorkflowPage from './pages/WorkflowPage';
import ProjectDetailsPage from './pages/ProjectWorkflow/ProjectDetailsPage';
import ContractDetailsPage from './pages/ProjectWorkflow/ContractDetailsPage';
import SiteDetailsPage from './pages/ProjectWorkflow/SiteDetailsPage';
import WorkflowOverview from './pages/ProjectWorkflow/WorkflowOverview';

// --- PHASE 6: ANALYTICS & DASHBOARD PAGES ---
import Dashboard from './pages/Dashboard';
import WorkforceDashboard from './pages/WorkforceDashboard';
import ProjectAnalytics from './pages/ProjectAnalytics';
import MyProfile from './pages/MyProfile';
import RoleContractFulfillmentOverview from './pages/role-contracts';
import DailyFulfillmentRecord from './pages/role-contracts/DailyFulfillmentRecord';
import MonthlyReportDashboard from './pages/role-contracts/MonthlyReportDashboard';
import SlotManagement from './pages/role-contracts/SlotManagement';

// --- DOCUMENT MANAGEMENT & INVENTORY SYSTEM ---
import EmployeeDocuments from './pages/Employees/EmployeeDocuments';
import MaterialsList from './pages/Inventory/MaterialsList';
import SuppliersList from './pages/Inventory/SuppliersList';
import PurchaseOrders from './pages/Inventory/PurchaseOrders';

// --- Styles ---
import "antd/dist/reset.css"; 
import "./assets/styles/main.css";
import "./assets/styles/responsive.css";

// Error Boundary to catch crashes
class ErrorBoundary extends React.Component {
  constructor(props) { super(props); this.state = { hasError: false }; }
  static getDerivedStateFromError(error) { return { hasError: true }; }
  render() { 
    if (this.state.hasError) { 
      return (
        <div style={{padding: 50, textAlign: 'center'}}>
          <h1 style={{color: '#ff4d4f'}}>Financial System Error</h1>
          <p>The dashboard encountered a crash while fetching data. Please refresh.</p>
          <button onClick={() => window.location.reload()} style={{padding: '10px 20px', cursor: 'pointer'}}>Refresh Dashboard</button>
        </div>
      ); 
    } 
    return this.props.children; 
  }
}

const App = () => {
  return (
    <AuthProvider>
      <ErrorBoundary>
        <Routes>
          {/* Public Route */}
          <Route path="/login" element={<LoginPage />} />

          {/* Protected Routes (Wrapped in Main Layout) */}
          <Route element={<Main />}>
            <Route path="dashboard" element={<DashboardPage />} />
            
            {/* Analytics & Workforce */}
            <Route path="workforce-allocation" element={<WorkforceDashboard />} />
            <Route path="analytics" element={<ProjectAnalytics />} />
            
            {/* HR & Workforce */}
            <Route path="employees" element={<EmployeesPage />} />
            <Route path="employees/:employeeId" element={<EmployeeProfilePage />} />
            <Route path="add-employee" element={<AddEmployeePage />} />
            <Route path="attendance" element={<AttendancePage />} />
            <Route path="duty-list" element={<DutyListPage />} />
            <Route path="payslips" element={<PayslipPage />} />
            <Route path="overtime" element={<OvertimePage />} />
            <Route path="deductions" element={ <DeductionsPage />} />
            
            {/* Operations */}
            <Route path="vehicles" element={<VehicleManagementPage />} />
            <Route path="projects" element={<ProjectsPage />} />
            <Route path="inventory" element={<InventoryPage />} />
            <Route path="inventory/materials" element={<MaterialsList />} />
            <Route path="inventory/suppliers" element={<SuppliersList />} />
            <Route path="inventory/purchase-orders" element={<PurchaseOrders />} />
            <Route path="site-management" element={<SiteManagement />} />
            <Route path="designations" element={<DesignationManagement />} />

            {/* Employee Documents */}
            <Route path="employees/:employeeId/documents" element={<EmployeeDocuments />} />

            {/* Project Workflow System */}
            <Route path="project-workflow" element={<ProjectDashboard />} />
            <Route path="project-workflow/overview" element={<WorkflowOverview />} />
            <Route path="project-workflow/:projectId/details" element={<ProjectDetailsPage />} />
            <Route path="project-workflow/contracts/:contractId/details" element={<ContractDetailsPage />} />
            <Route path="project-workflow/sites/:siteId/details" element={<SiteDetailsPage />} />
            <Route path="project-workflow/:projectId/contracts" element={<ContractManagementPage />} />
            <Route path="project-workflow/:projectId/sites" element={<SiteManagementPage />} />
            <Route path="sites/:siteId/assign-employees" element={<EmployeeAssignment />} />
            <Route path="sites/:siteId/workforce" element={<TempWorkerManagement />} />
            <Route path="workflow" element={<WorkflowPage />} />
            <Route path="role-contracts/fulfillment" element={<RoleContractFulfillmentOverview />} />
            <Route path="role-contracts/record-daily" element={<DailyFulfillmentRecord />} />
            <Route path="role-contracts/monthly-report" element={<MonthlyReportDashboard />} />
            <Route path="role-contracts/manage-slots" element={<SlotManagement />} />
            
            {/* --- NEW FINANCIAL INTEL ROUTE --- */}
            <Route path="finance" element={<FinancePage />} /> {/* <--- ADDED THIS */}
            
            {/* Administration */}
            <Route path="admins" element={<AdminManagementPage />} />
            <Route path="managers" element={<ManagersPage />} />
            <Route path="managers/create" element={<CreateManagerPage />} />
            <Route path="managers/edit/:id" element={<EditManagerPage />} />
            <Route path="manager-attendance" element={<ManagerAttendanceAdminPage />} />
            <Route path="my-attendance" element={<ManagerMyAttendancePage />} />
            <Route path="messages" element={<MessagePage />} />
            <Route path="manager-messages" element={<ManagerMessagesPage />} />
            <Route path="settings" element={<CompanySettingsPage />} />
            <Route path="my-profile" element={<MyProfile />} />
          </Route>

          {/* Redirects */}
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </ErrorBoundary>
    </AuthProvider>
  );
};

export default App;
