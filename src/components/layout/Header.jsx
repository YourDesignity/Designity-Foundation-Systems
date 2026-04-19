// src/components/layout/Header.jsx
// Fixed: Notification panel now polls /messaging/unread-count and shows real unread messages.

import { useEffect, useState, useCallback } from "react";
import {
  Row, Col, Breadcrumb, Badge, Input, Avatar, Dropdown, Typography,
  Tag, theme, Tooltip, Popover, Button, Empty, List,
} from "antd";
import {
  SearchOutlined, BellFilled, UserOutlined, LogoutOutlined,
  ProfileOutlined, MessageOutlined,
} from "@ant-design/icons";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";

const { Text, Title } = Typography;
const { useToken } = theme;

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

function Header({ name, subName, onPress }) {
  const { user, logout, isSiteManager } = useAuth();
  const { token } = useToken();
  const navigate = useNavigate();
  const [unreadCount, setUnreadCount]       = useState(0);
  const [conversations, setConversations]   = useState([]);
  const [openNotif, setOpenNotif]           = useState(false);

  const messagesPath = isSiteManager ? '/manager-messages' : '/messages';

  // ── Poll unread count every 30 seconds ─────────────────────────────
  const fetchUnread = useCallback(async () => {
    try {
      const authToken = localStorage.getItem('access_token');
      if (!authToken) return;

      const [countRes, convRes] = await Promise.all([
        fetch(`${API_BASE_URL}/messages/unread-count`, {
          headers: { Authorization: `Bearer ${authToken}` },
        }),
        fetch(`${API_BASE_URL}/messages/conversations?limit=5`, {
          headers: { Authorization: `Bearer ${authToken}` },
        }),
      ]);

      if (countRes.ok) {
        const countData = await countRes.json();
        setUnreadCount(countData.unread_count || 0);
      }

      if (convRes.ok) {
        const convData = await convRes.json();
        const list = Array.isArray(convData) ? convData : convData?.conversations || [];
        // Only show conversations with unread messages
        setConversations(list.filter(c => (c.unread_count || 0) > 0).slice(0, 5));
      }
    } catch {
      // Silently ignore — network may not be ready
    }
  }, []);

  useEffect(() => {
    fetchUnread();
    const interval = setInterval(fetchUnread, 30_000);
    return () => clearInterval(interval);
  }, [fetchUnread]);

  // ── Notification panel content ──────────────────────────────────────
  const notifContent = (
    <div style={{ width: 320 }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #f0f0f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Text strong>Notifications</Text>
        {unreadCount > 0 && (
          <Button size="small" type="link" onClick={() => { navigate(messagesPath); setOpenNotif(false); }}>
            View all
          </Button>
        )}
      </div>

      {conversations.length === 0 ? (
        <div style={{ padding: 24, textAlign: 'center' }}>
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="No new messages" />
        </div>
      ) : (
        <List
          dataSource={conversations}
          renderItem={(conv) => (
            <List.Item
              style={{ padding: '10px 16px', cursor: 'pointer' }}
              onClick={() => { navigate(messagesPath); setOpenNotif(false); }}
            >
              <List.Item.Meta
                avatar={
                  <Badge count={conv.unread_count || 0} size="small">
                    <Avatar size={36} icon={<MessageOutlined />} style={{ background: '#1677ff' }} />
                  </Badge>
                }
                title={<Text style={{ fontSize: 13 }}>{conv.title || 'Message'}</Text>}
                description={
                  <Text type="secondary" style={{ fontSize: 12 }} ellipsis>
                    {conv.last_message || 'New message'}
                  </Text>
                }
              />
            </List.Item>
          )}
        />
      )}
    </div>
  );

  const photoSrc = user?.profile_photo ? `${API_BASE_URL}${user.profile_photo}` : undefined;

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
      borderRadius: '12px', marginBottom: '8px', cursor: 'default',
    },
    gradientAvatar: {
      background: 'linear-gradient(135deg, #1890ff 0%, #0050b3 100%)',
      verticalAlign: 'middle', boxShadow: '0 2px 8px rgba(24, 144, 255, 0.35)',
    },
  };

  const menuItems = [
    {
      key: 'header',
      label: (
        <div style={styles.headerCard}>
          <Badge dot status="success" offset={[-6, 58]}>
            <Avatar size={64} style={styles.gradientAvatar} src={photoSrc} icon={<UserOutlined />} />
          </Badge>
          <Title level={5} style={{ margin: '12px 0 2px 0' }}>
            {user?.full_name || user?.sub?.split('@')[0] || "Guest"}
          </Title>
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
        <Breadcrumb items={[
          { title: <NavLink to="/">Pages</NavLink> },
          { title: <span style={{ textTransform: "capitalize" }}>{name?.replace("/", "")}</span> },
        ]} />
      </Col>
      <Col span={24} md={18} className="header-control">
        <Dropdown
          menu={{ items: menuItems }}
          trigger={['click']}
          placement="bottomRight"
          popupRender={(menu) => <div style={styles.dropdownContent}>{menu}</div>}
        >
          <div className="admin-profile-trigger" style={{ display: 'flex', alignItems: 'center', cursor: 'pointer', gap: '12px' }}>
            <Badge dot offset={[-5, 35]} status="success">
              <Avatar size={40} style={styles.gradientAvatar} src={photoSrc} icon={<UserOutlined />} />
            </Badge>
            <div style={{ display: 'flex', flexDirection: 'column', lineHeight: '1.2' }}>
              <span style={{ fontWeight: 600 }}>{user?.full_name || user?.sub?.split('@')[0] || "Guest"}</span>
              <span style={{ fontSize: '10px', color: '#8c8c8c' }}>{user?.role || "Admin"}</span>
            </div>
          </div>
        </Dropdown>

        <Popover
          content={notifContent}
          trigger="click"
          placement="bottomRight"
          arrow={false}
          open={openNotif}
          onOpenChange={(v) => { setOpenNotif(v); if (v) fetchUnread(); }}
          styles={{ body: { padding: 0, borderRadius: '8px' } }}
        >
          <Badge count={unreadCount} size="small" offset={[-5, 5]} style={{ marginRight: '25px' }}>
            <BellFilled style={{ fontSize: 20, color: "#8c8c8c", cursor: 'pointer', marginRight: '20px' }} />
          </Badge>
        </Popover>

        <Input
          className="custom-search-input"
          placeholder="Search..."
          prefix={<SearchOutlined style={{ color: '#bfbfbf' }} />}
          style={{ borderRadius: '8px', maxWidth: '200px', marginRight: '10px', backgroundColor: '#f5f5f5' }}
          variant="borderless"
        />
      </Col>
    </Row>
  );
}

export default Header;
