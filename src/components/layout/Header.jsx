import { useEffect, useState } from "react";
import { 
  Row, Col, Breadcrumb, Badge, Input, Avatar, Dropdown, Typography, 
  Tag, theme, Tooltip, Popover, List, Button, Empty
} from "antd";
import { 
  SearchOutlined, BellFilled, UserOutlined, LogoutOutlined, 
  ProfileOutlined
} from "@ant-design/icons";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";

const { Text, Title } = Typography;
const { useToken } = theme;

const initialNotifications = [];

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

function Header({ name, subName }) {
  const { user, logout } = useAuth();
  const { token } = useToken(); 
  const navigate = useNavigate();
  const [notifications, setNotifications] = useState(initialNotifications);
  const [openNotif, setOpenNotif] = useState(false);

  useEffect(() => window.scrollTo(0, 0));

  const styles = {
    dropdownContent: {
      backgroundColor: token.colorBgElevated,
      borderRadius: token.borderRadiusLG,
      boxShadow: '0 6px 16px -8px rgba(0,0,0,0.08), 0 9px 28px 0 rgba(0,0,0,0.05)',
      padding: '8px', minWidth: '260px',
    },
    headerCard: {
      display: 'flex', flexDirection: 'column', alignItems: 'center', 
      padding: '24px 12px 20px',
      background: 'linear-gradient(180deg, #f0f5ff 0%, rgba(255,255,255,0) 100%)', 
      borderRadius: '12px', marginBottom: '8px', cursor: 'default'
    },
    gradientAvatar: {
      background: 'linear-gradient(135deg, #1890ff 0%, #0050b3 100%)', 
      verticalAlign: 'middle', boxShadow: '0 2px 8px rgba(24, 144, 255, 0.35)'
    },
    notifPopover: { width: 350, padding: 0 }
  };

  const notificationContent = (
    <div style={styles.notifPopover}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #f0f0f0', display: 'flex', justifyContent: 'space-between' }}>
        <Text strong>Notifications</Text>
      </div>
      <List dataSource={notifications} locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="No Notifications" /> }} renderItem={(item) => <List.Item>{item.title}</List.Item>} />
    </div>
  );

  const photoSrc = user?.profile_photo ? `${API_BASE_URL}${user.profile_photo}` : undefined;

  const menuItems = [
    {
      key: 'header',
      label: (
        <div style={styles.headerCard}>
          <Badge dot status="success" offset={[-6, 58]}>
            <Avatar size={64} style={styles.gradientAvatar} src={photoSrc} icon={<UserOutlined />} />
          </Badge>
          <Title level={5} style={{ margin: '12px 0 2px 0' }}>{user?.full_name || user?.sub?.split('@')[0] || "Guest"}</Title>
          <Text type="secondary" style={{ fontSize: '12px', marginBottom: '12px' }}>{user?.sub}</Text>
          <Tag color="blue">{user?.role || "ADMIN"}</Tag>
        </div>
      ),
    },
    { type: 'divider' },
    { key: 'profile', icon: <ProfileOutlined />, label: 'My Profile', onClick: () => navigate('/my-profile') },
    { type: 'divider' },
    { key: 'logout', danger: true, icon: <LogoutOutlined />, label: 'Logout', onClick: logout },
  ];

  return (
    <Row gutter={[24, 0]}>
      <Col span={24} md={6}>
        <Breadcrumb items={[{ title: <NavLink to="/">Pages</NavLink> }, { title: <span style={{ textTransform: "capitalize" }}>{name.replace("/", "")}</span> }]} />
      </Col>
      <Col span={24} md={18} className="header-control">
        {/* FIX: popupRender */}
        <Dropdown menu={{ items: menuItems }} trigger={['click']} placement="bottomRight" popupRender={(menu) => <div style={styles.dropdownContent}>{menu}</div>}>
          <div className="admin-profile-trigger" style={{ display: 'flex', alignItems: 'center', cursor: 'pointer', gap: '12px' }}>
            <Badge dot offset={[-5, 35]} status="success"><Avatar size={40} style={styles.gradientAvatar} src={photoSrc} icon={<UserOutlined />} /></Badge>
            <div style={{ display: 'flex', flexDirection: 'column', lineHeight: '1.2' }}>
              <span style={{ fontWeight: 600 }}>{user?.full_name || user?.sub?.split('@')[0] || "Guest"}</span>
              <span style={{ fontSize: '10px', color: '#8c8c8c' }}>{user?.role || "Admin"}</span>
            </div>
          </div>
        </Dropdown>
        {/* FIX: styles.body */}
        <Popover content={notificationContent} trigger="click" placement="bottomRight" arrow={false} open={openNotif} onOpenChange={setOpenNotif} styles={{ body: { padding: 0, borderRadius: '8px' } }}>
          <Badge count={notifications.length} size="small" offset={[-5, 5]} style={{ marginRight: '25px' }}>
             <BellFilled style={{ fontSize: 20, color: "#8c8c8c", cursor: 'pointer', marginRight: '20px' }} />
          </Badge>
        </Popover>
        {/* FIX: variant="borderless" */}
        <Input className="custom-search-input" placeholder="Search..." prefix={<SearchOutlined style={{ color: '#bfbfbf' }} />} style={{ borderRadius: '8px', maxWidth: '200px', marginRight: '10px', backgroundColor: '#f5f5f5' }} variant="borderless" />
      </Col>
    </Row>
  );
}

export default Header;