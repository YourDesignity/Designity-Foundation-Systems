import { useMemo } from "react";
import { Menu } from "antd";
import { NavLink, useLocation } from "react-router-dom";
import {
  HomeOutlined, UserOutlined, CalendarOutlined, ProfileOutlined,
  MessageOutlined, ProjectOutlined, SafetyCertificateOutlined,
  DatabaseOutlined, GoldOutlined, DollarOutlined,
  CarOutlined,
  PieChartOutlined,
  TeamOutlined,
  ClockCircleOutlined,
  SettingOutlined,
  ApartmentOutlined,
  BarChartOutlined,
  UsergroupAddOutlined,
  ContactsOutlined,
  ShopOutlined,
  ShoppingCartOutlined,
  BoxPlotOutlined,
} from "@ant-design/icons";
import { useAuth } from "../../context/AuthContext";
import { usePermission } from "../../hooks/usePermission";
import { PERMISSIONS } from "../../constants/permissions";

function Sidenav({ color }) {
  const { pathname } = useLocation();
  const { user } = useAuth();
  const { hasPermission } = usePermission();

  const items = useMemo(() => {
    const rawMenuItems = [
      { path: "/dashboard", name: "Dashboard", icon: <HomeOutlined />, perm: PERMISSIONS.DASHBOARD_VIEW },
      // My Attendance is shown prominently for Site Managers
      ...(user?.role === 'Site Manager' ? [{ path: "/my-attendance", name: "My Attendance", icon: <ClockCircleOutlined />, perm: PERMISSIONS.MY_ATTENDANCE_VIEW }] : []),
      { path: "/workforce-allocation", name: "Workforce Alloc.", icon: <UsergroupAddOutlined />, perm: PERMISSIONS.WORKFORCE_VIEW },
      { path: "/analytics", name: "Analytics", icon: <PieChartOutlined />, perm: PERMISSIONS.ANALYTICS_VIEW },
      { path: "/employees", name: "Employees", icon: <UserOutlined />, perm: PERMISSIONS.EMPLOYEES_VIEW },
      { path: "/managers", name: "Managers", icon: <TeamOutlined />, perm: PERMISSIONS.MANAGERS_VIEW },
      { path: "/manager-attendance", name: "Manager Attendance", icon: <CalendarOutlined />, perm: PERMISSIONS.ATTENDANCE_VIEW },
      { path: "/vehicles", name: "Vehicles", icon: <CarOutlined />, perm: PERMISSIONS.VEHICLES_VIEW },
      { path: "/attendance", name: "Attendance", icon: <CalendarOutlined />, perm: PERMISSIONS.ATTENDANCE_VIEW },
      { path: "/duty-list", name: "Duty List", icon: <ProfileOutlined />, perm: PERMISSIONS.DUTY_LIST_VIEW },
      { path: "/payslips", name: "Payslips", icon: <DollarOutlined />, perm: PERMISSIONS.PAYSLIPS_VIEW },
      { path: "/inventory", name: "Inventory", icon: <DatabaseOutlined />, perm: PERMISSIONS.INVENTORY_VIEW },
      { path: "/inventory/materials", name: "Materials", icon: <BoxPlotOutlined />, perm: PERMISSIONS.INVENTORY_VIEW },
      { path: "/inventory/suppliers", name: "Suppliers", icon: <ShopOutlined />, perm: PERMISSIONS.INVENTORY_VIEW },
      { path: "/inventory/purchase-orders", name: "Purchase Orders", icon: <ShoppingCartOutlined />, perm: PERMISSIONS.INVENTORY_VIEW },
      { path: "/projects", name: "Projects", icon: <ProjectOutlined />, perm: PERMISSIONS.PROJECTS_VIEW },
      { path: "/project-workflow", name: "Project Workflow", icon: <ApartmentOutlined />, perm: PERMISSIONS.PROJECTS_VIEW },
      { path: "/workflow", name: "Workflow Overview", icon: <ApartmentOutlined />, perm: PERMISSIONS.PROJECTS_VIEW },

      // --- RESTRICTED FINANCE ITEM (Admin + SuperAdmin only via RBAC) ---
      {
        path: "/finance",
        name: "Finance (P&L)",
        icon: <PieChartOutlined />,
        perm: PERMISSIONS.FINANCE_VIEW,
      },

      {
        path: user?.role === 'Site Manager' ? "/manager-messages" : "/messages",
        name: user?.role === 'Site Manager' ? "My Messages" : "Messages",
        icon: <MessageOutlined />,
        perm: PERMISSIONS.MESSAGES_VIEW,
      },
      { path: "/admins", name: "Admins", icon: <SafetyCertificateOutlined />, perm: PERMISSIONS.ADMINS_VIEW },
      { path: "/site-management", name: "Site Mgmt", icon: <GoldOutlined />, perm: PERMISSIONS.SITES_VIEW },
      { path: "/my-profile", name: "My Profile", icon: <ContactsOutlined />, perm: PERMISSIONS.MY_PROFILE_VIEW },
      { path: "/settings", name: "Settings", icon: <SettingOutlined />, perm: PERMISSIONS.SETTINGS_VIEW },
    ];

    // Filter menu items using the centralised RBAC permission hook
    const visibleItems = rawMenuItems.filter(item =>
      !item.perm || hasPermission(item.perm)
    );

    return visibleItems.map((item) => ({
      key: item.path,
      label: (
        <NavLink to={item.path} style={{ display: 'flex', alignItems: 'center', width: '100%', gap: '12px' }}>
          <span className="icon" style={{
              background: pathname === item.path ? color : "#fff",
              display: 'flex', justifyContent: 'center', alignItems: 'center',
              minWidth: '32px', height: '32px', borderRadius: '8px',
              color: pathname === item.path ? "#fff" : color,
              boxShadow: pathname === item.path ? "0 4px 6px rgba(0,0,0,0.12)" : "0 2px 4px rgba(0,0,0,0.05)",
            }}>
            {item.icon}
          </span>
          <span className="label" style={{ fontWeight: pathname === item.path ? 600 : 500 }}>{item.name}</span>
        </NavLink>
      ),
    }));
  }, [user, pathname, color, hasPermission]);

  return (
    <>
      <div className="brand" style={{ padding: '20px', fontSize: '18px', fontWeight: 800 }}>Montreal Intl.</div>
      <hr style={{ margin: '0 20px 15px', border: '0', borderTop: '1px solid #f0f0f0' }} />
      <Menu
        theme="light"
        mode="inline"
        selectedKeys={[pathname]}
        items={items}
        style={{ borderRight: 0, background: 'transparent' }}
      />
    </>
  );
}

export default Sidenav;