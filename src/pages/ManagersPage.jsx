import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Table, Card, Input, Button, Dropdown, Tag, Typography, Row, Col, Modal, Space, message,
} from 'antd';
import {
  SearchOutlined, PlusOutlined, EditOutlined, DeleteOutlined,
  CalendarOutlined, SettingOutlined, MoreOutlined, TeamOutlined, CloseCircleOutlined,
} from '@ant-design/icons';
import { getManagerProfiles, deleteManagerProfile } from '../services/apiService';

const { Title, Text } = Typography;

function ManagersPage() {
  const navigate = useNavigate();
  const [managers, setManagers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchText, setSearchText] = useState('');
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  const fetchManagers = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getManagerProfiles();
      setManagers(Array.isArray(data) ? data : []);
    } catch (err) {
      message.error('Failed to load managers: ' + err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchManagers();
  }, [fetchManagers]);

  const filteredManagers = useMemo(() => {
    if (!searchText.trim()) return managers;
    const q = searchText.toLowerCase();
    return managers.filter(
      (m) =>
        m.full_name?.toLowerCase().includes(q) ||
        m.email?.toLowerCase().includes(q),
    );
  }, [managers, searchText]);

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setDeleteLoading(true);
    try {
      await deleteManagerProfile(deleteTarget.admin_id);
      message.success('Manager deleted successfully');
      setDeleteTarget(null);
      fetchManagers();
    } catch (err) {
      message.error('Failed to delete manager: ' + err.message);
    } finally {
      setDeleteLoading(false);
    }
  };

  const getActionItems = (record) => ({
    items: [
      {
        key: 'edit',
        icon: <EditOutlined />,
        label: 'Edit Profile',
        onClick: () => navigate(`/managers/edit/${record.admin_id}`),
      },
      {
        key: 'attendance',
        icon: <CalendarOutlined />,
        label: 'View Attendance',
        onClick: () => navigate(`/manager-attendance?manager=${record.admin_id}`),
      },
      {
        key: 'config',
        icon: <SettingOutlined />,
        label: 'Attendance Config',
        onClick: () => navigate(`/managers/edit/${record.admin_id}?tab=attendance`),
      },
      { type: 'divider' },
      {
        key: 'delete',
        icon: <DeleteOutlined />,
        label: 'Delete Manager',
        danger: true,
        onClick: () => setDeleteTarget(record),
      },
    ],
  });

  const statusColor = (status) => {
    if (!status) return 'default';
    return status.toLowerCase() === 'active' ? 'green' : 'red';
  };

  const columns = [
    {
      title: 'ID',
      dataIndex: 'admin_id',
      key: 'admin_id',
      width: 60,
      render: (id) => <Text type="secondary">#{id}</Text>,
    },
    {
      title: 'Name',
      dataIndex: 'full_name',
      key: 'full_name',
      render: (text, record) => (
        <div>
          <Text strong>{text || '—'}</Text>
          <br />
          <Text type="secondary" style={{ fontSize: 12 }}>{record.email}</Text>
        </div>
      ),
    },
    {
      title: 'Designation',
      dataIndex: 'designation',
      key: 'designation',
      render: (text) => text || '—',
    },
    {
      title: 'Salary (KWD)',
      dataIndex: 'monthly_salary',
      key: 'monthly_salary',
      render: (val) => (val != null ? Number(val).toFixed(3) : '—'),
    },
    {
      title: 'Assigned Sites',
      dataIndex: 'sites',
      key: 'sites',
      render: (sites) =>
        Array.isArray(sites) && sites.length > 0
          ? sites.map((s) => (
              <Tag key={s.id ?? s} color="blue">
                {s.name ?? s}
              </Tag>
            ))
          : <Text type="secondary">None</Text>,
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Tag color={statusColor(status)}>{status ? status.toUpperCase() : 'ACTIVE'}</Tag>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 80,
      align: 'center',
      render: (_, record) => (
        <Dropdown menu={getActionItems(record)} trigger={['click']} placement="bottomRight">
          <Button icon={<MoreOutlined />} type="text" />
        </Dropdown>
      ),
    },
  ];

  return (
    <div className="layout-content">
      <Card variant="borderless" className="criclebox mb-24" style={{ marginBottom: 24 }}>
        <Row align="middle" justify="space-between" wrap={false}>
          <Col>
            <Title level={4} style={{ margin: 0 }}>
              <TeamOutlined style={{ marginRight: 8 }} />
              Managers
            </Title>
            <Text type="secondary">Manage site manager profiles and settings</Text>
          </Col>
          <Col>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => navigate('/managers/create')}
              style={{ borderRadius: 6, fontWeight: 600 }}
            >
              Create New Manager
            </Button>
          </Col>
        </Row>
      </Card>

      <Row gutter={[24, 0]}>
        <Col xs={24}>
          <Card variant="borderless" className="criclebox tablespace mb-24">
            <div style={{ padding: '12px 24px' }}>
              <Input
                placeholder="Search by name or email…"
                prefix={<SearchOutlined />}
                suffix={
                  searchText ? (
                    <CloseCircleOutlined
                      style={{ cursor: 'pointer', color: '#bfbfbf' }}
                      onClick={() => setSearchText('')}
                    />
                  ) : null
                }
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
                style={{ maxWidth: 320 }}
                allowClear
              />
            </div>
            <div className="table-responsive">
              <Table
                columns={columns}
                dataSource={filteredManagers}
                rowKey="admin_id"
                loading={loading}
                pagination={{ pageSize: 10 }}
                className="ant-border-space"
                scroll={{ x: 800 }}
              />
            </div>
          </Card>
        </Col>
      </Row>

      {/* Delete Confirmation Modal */}
      <Modal
        title={
          <Space>
            <DeleteOutlined style={{ color: '#ff4d4f' }} />
            Delete Manager
          </Space>
        }
        open={!!deleteTarget}
        onOk={handleDelete}
        onCancel={() => setDeleteTarget(null)}
        confirmLoading={deleteLoading}
        okText="Delete"
        okButtonProps={{ danger: true }}
        cancelText="Cancel"
      >
        <p>
          Are you sure you want to delete{' '}
          <Text strong>{deleteTarget?.full_name}</Text>? This action is{' '}
          <Text type="danger">permanent</Text> and cannot be undone.
        </p>
      </Modal>
    </div>
  );
}

export default ManagersPage;
