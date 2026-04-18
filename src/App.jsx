// src/App.js

import React, { lazy, Suspense } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

// --- Layout (eager – always needed) ---
import Main from './components/layout/Main';
import PageLoader from './components/PageLoader';
import ErrorBoundary from './components/ErrorBoundary';

// --- Pages (lazy-loaded for code splitting) ---
const LoginPage = lazy(() => import('./pages/LoginPage'));
const DashboardPage = lazy(() => import('./pages/DashboardPage'));
const EmployeesPage = lazy(() => import('./pages/EmployeesPage'));
const EmployeeProfilePage = lazy(() => import('./pages/EmployeeProfilePage'));
const AttendancePage = lazy(() => import('./pages/AttendancePage'));
const DutyListPage = lazy(() => import('./pages/DutyList'));
const AddEmployeePage = lazy(() => import('./pages/AddEmployee'));
const MessagePage = lazy(() => import('./pages/MessagePage'));
const ManagerMessagesPage = lazy(() => import('./pages/ManagerMessagesPage'));
const ProjectsPage = lazy(() => import('./pages/ProjectsPage'));
const InventoryPage = lazy(() => import('./pages/InventoryPage'));
const SiteManagement = lazy(() => import('./components/SiteManagement'));
const DesignationManagement = lazy(() => import('./pages/DesignationManagement'));
const AdminManagementPage = lazy(() => import('./pages/AdminManagementPage'));
const ManagersPage = lazy(() => import('./pages/ManagersPage'));
const CreateManagerPage = lazy(() => import('./pages/CreateManagerPage'));
const EditManagerPage = lazy(() => import('./pages/EditManagerPage'));
const ManagerAttendanceAdminPage = lazy(() => import('./pages/ManagerAttendanceAdminPage'));
const ManagerMyAttendancePage = lazy(() => import('./pages/ManagerMyAttendancePage'));
const PayslipPage = lazy(() => import('./pages/PayslipPage'));
const OvertimePage = lazy(() => import('./pages/OvertimePage'));
const DeductionsPage = lazy(() => import('./pages/DeductionsPage'));
const VehicleManagementPage = lazy(() => import('./pages/VehicleManagement'));

// --- Financial pages ---
const FinancePage = lazy(() => import('./pages/FinancePage'));
const CompanySettingsPage = lazy(() => import('./pages/CompanySettingsPage'));

// --- Project Workflow pages ---
const ProjectDashboard = lazy(() => import('./pages/ProjectWorkflow/ProjectDashboard'));
const ContractManagementPage = lazy(() => import('./pages/ProjectWorkflow/ContractManagementPage'));
const SiteManagementPage = lazy(() => import('./pages/ProjectWorkflow/SiteManagementPage'));
const EmployeeAssignment = lazy(() => import('./pages/ProjectWorkflow/EmployeeAssignment'));
const TempWorkerManagement = lazy(() => import('./pages/ProjectWorkflow/TempWorkerManagement'));
const WorkflowPage = lazy(() => import('./pages/WorkflowPage'));
const ProjectDetailsPage = lazy(() => import('./pages/ProjectWorkflow/ProjectDetailsPage'));
const ContractDetailsPage = lazy(() => import('./pages/ProjectWorkflow/ContractDetailsPage'));
const SiteDetailsPage = lazy(() => import('./pages/ProjectWorkflow/SiteDetailsPage'));
const WorkflowOverview = lazy(() => import('./pages/ProjectWorkflow/WorkflowOverview'));

// --- Analytics & Dashboard pages ---
const Dashboard = lazy(() => import('./pages/Dashboard'));
const WorkforceDashboard = lazy(() => import('./pages/WorkforceDashboard'));
const ProjectAnalytics = lazy(() => import('./pages/ProjectAnalytics'));
const MyProfile = lazy(() => import('./pages/MyProfile'));

// --- Role contracts pages ---
const RoleContractFulfillmentOverview = lazy(() => import('./pages/role-contracts'));
const DailyFulfillmentRecord = lazy(() => import('./pages/role-contracts/DailyFulfillmentRecord'));
const MonthlyReportDashboard = lazy(() => import('./pages/role-contracts/MonthlyReportDashboard'));
const SlotManagement = lazy(() => import('./pages/role-contracts/SlotManagement'));

// --- Document Management & Inventory ---
const EmployeeDocuments = lazy(() => import('./pages/Employees/EmployeeDocuments'));
const MaterialsList = lazy(() => import('./pages/Inventory/MaterialsList'));
const SuppliersList = lazy(() => import('./pages/Inventory/SuppliersList'));
const PurchaseOrders = lazy(() => import('./pages/Inventory/PurchaseOrders'));

// --- Styles ---
import "antd/dist/reset.css"; 
import "./assets/styles/main.css";
import "./assets/styles/responsive.css";

const App = () => {
  return (
    <AuthProvider>
      <ErrorBoundary>
        <Suspense fallback={<PageLoader />}>
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
              
              {/* Financial */}
              <Route path="finance" element={<FinancePage />} />
              
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

              {/* Overview Dashboard (project workflow analytics) */}
              <Route path="overview" element={<Dashboard />} />
            </Route>

            {/* Redirects */}
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </Suspense>
        <ToastContainer
          position="top-right"
          autoClose={3000}
          hideProgressBar={false}
          newestOnTop
          closeOnClick
          rtl={false}
          pauseOnFocusLoss
          draggable
          pauseOnHover
          theme="light"
        />
      </ErrorBoundary>
    </AuthProvider>
  );
};

export default App;

