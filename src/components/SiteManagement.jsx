/**
 * SiteManagement.jsx — View-Only Sites List
 *
 * Phase 3 change: Sites can no longer be created independently.
 * Sites are created inside a Contract (inside a Project).
 * This page is a read-only overview. Clicking a site navigates to
 * its parent project page.
 */

import React, { useState, useEffect } from 'react';
import {
  Table, Tag, Typography, Input, Select, Space, Card,
  Row, Col, Statistic, Button, Tooltip, message,
} from 'antd';
import {
  EnvironmentOutlined, TeamOutlined, SearchOutlined,
  ArrowRightOutlined, InfoCircleOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

const { Title, Text } = Typography;
const { Option } = Select;

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

const STATUS_COLOR = {
  Active: 'green',
  Completed: 'blue',
  'On Hold': 'orange',
};

const SiteManagement = () => {
  const navigate = useNavigate();
  const [sites, setSites]       = useState([]);
  const [loading, setLoading]   = useState(true);
  const [search, setSearch]     = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  useEffect(() => { fetchSites(); }, []);

  const fetchSites = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('access_token');
      const res = await fetch(`${API_BASE}/sites`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('Failed to fetch sites');
      const data = await res.json();
      setSites(Array.isArray(data) ? data : []);
    } catch (err) {
      message.error('Could not load sites.');
    } finally {
      setLoading(false);
    }
  };

  const filtered = sites.filter(s => {
    const matchSearch = !search ||
      s.name?.toLowerCase().includes(search.toLowerCase()) ||
      s.site_code?.toLowerCase().includes(search.toLowerCase()) ||
      s.location?.toLowerCase().includes(search.toLowerCase());
    const matchStatus = !statusFilter || s.status === statusFilter;
    return matchSearch && matchStatus;
  });

  const goToProject = (site) => {
    if (site.project_id) {
      navigate(`/projects/${site.project_id}`);
    }
  };

  const columns = [
    {
      title: 'Site',
      key: 'site',
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{record.name}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>{record.site_code}</Text>
        </Space>
      ),
    },
    {
      title: 'Location',
      dataIndex: 'location',
      key: 'location',
      render: (loc) => loc ? (
        <Space>
          <EnvironmentOutlined style={{ color: '#1677ff' }} />
          <Text>{loc}</Text>
        </Space>
      ) : <Text type="secondary">—</Text>,
    },
    {
      title: 'Project',
      key: 'project',
      render: (_, record) => record.project_name ? (
        <Button
          type="link"
          size="small"
          style={{ padding: 0 }}
          onClick={() => goToProject(record)}
        >
          {record.project_name}
        </Button>
      ) : <Text type="secondary">—</Text>,
    },
    {
      title: 'Contract',
      dataIndex: 'contract_code',
      key: 'contract',
      render: (code) => code ? <Tag>{code}</Tag> : <Text type="secondary">—</Text>,
    },
    {
      title: 'Manager',
      key: 'manager',
      render: (_, record) => {
        const names = record.assigned_manager_names || [];
        if (names.length === 0) return <Text type="secondary">Unassigned</Text>;
        return <Text>{names.join(', ')}</Text>;
      },
    },
    {
      title: 'Workforce',
      key: 'workforce',
      render: (_, record) => (
        <Space>
          <TeamOutlined />
          <Text>{record.assigned_workers || 0}
            {record.required_workers > 0 && ` / ${record.required_workers}`}
          </Text>
          {record.is_understaffed && <Tag color="red">Understaffed</Tag>}
        </Space>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status) => <Tag color={STATUS_COLOR[status] || 'default'}>{status}</Tag>,
    },
    {
      title: '',
      key: 'action',
      width: 60,
      render: (_, record) => (
        <Tooltip title="Go to Project">
          <Button
            icon={<ArrowRightOutlined />}
            size="small"
            type="text"
            onClick={() => goToProject(record)}
          />
        </Tooltip>
      ),
    },
  ];

  const activeCount    = sites.filter(s => s.status === 'Active').length;
  const completedCount = sites.filter(s => s.status === 'Completed').length;

  return (
    <div style={{ padding: 24 }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <Title level={3} style={{ margin: 0 }}>Sites</Title>
        <Space style={{ marginTop: 4 }}>
          <InfoCircleOutlined style={{ color: '#888' }} />
          <Text type="secondary">
            Sites are created inside Projects → Contracts. Click a site's project to manage it.
          </Text>
        </Space>
      </div>

      {/* Stats */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={8} sm={6}>
          <Card size="small" variant="borderless" style={{ background: '#f0f5ff' }}>
            <Statistic title="Total Sites" value={sites.length} />
          </Card>
        </Col>
        <Col xs={8} sm={6}>
          <Card size="small" variant="borderless" style={{ background: '#f6ffed' }}>
            <Statistic title="Active" value={activeCount} />
          </Card>
        </Col>
        <Col xs={8} sm={6}>
          <Card size="small" variant="borderless" style={{ background: '#f5f5f5' }}>
            <Statistic title="Completed" value={completedCount} />
          </Card>
        </Col>
      </Row>

      {/* Filters */}
      <Row gutter={12} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={12} md={8}>
          <Input
            prefix={<SearchOutlined />}
            placeholder="Search by name, code, or location..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            allowClear
          />
        </Col>
        <Col xs={24} sm={8} md={6}>
          <Select
            placeholder="Filter by status"
            style={{ width: '100%' }}
            value={statusFilter || undefined}
            onChange={setStatusFilter}
            allowClear
          >
            <Option value="Active">Active</Option>
            <Option value="Completed">Completed</Option>
            <Option value="On Hold">On Hold</Option>
          </Select>
        </Col>
      </Row>

      {/* Table */}
      <Card variant="borderless" styles={{ body: { padding: 0 } }}>
        <Table
          columns={columns}
          dataSource={filtered}
          rowKey="uid"
          loading={loading}
          pagination={{ pageSize: 20, showSizeChanger: false }}
          onRow={(record) => ({ onClick: () => goToProject(record), style: { cursor: 'pointer' } })}
          locale={{ emptyText: 'No sites found.' }}
        />
      </Card>
    </div>
  );
};

export default SiteManagement;
