/**
 * AuditTrailPage.jsx
 *
 * Admin-only page for viewing and exporting the complete audit trail
 * of all admin/manager actions in the system.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Table, Card, Row, Col, Button, Input, Select, DatePicker, Space, Tag,
  Typography, Modal, Descriptions, Spin, Statistic, Divider, Tooltip,
  Badge, Empty,
} from 'antd';
import {
  SearchOutlined, DownloadOutlined, ReloadOutlined, EyeOutlined,
  UserOutlined, AuditOutlined, FilterOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import apiClient from '../services/base/apiClient';
import { useAuth } from '../context/AuthContext';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;
const { Option } = Select;

const BASE = '/audit-logs';

// ─── Helpers ─────────────────────────────────────────────────────────────────

const CATEGORY_COLORS = {
  employees: 'blue',
  contracts: 'purple',
  attendance: 'green',
  payroll: 'gold',
  settings: 'orange',
  vehicles: 'cyan',
  inventory: 'lime',
};

const ACTION_LABELS = {
  employee_created: 'Created Employee',
  employee_updated: 'Updated Employee',
  employee_deleted: 'Deleted Employee',
  contract_created: 'Created Contract',
  contract_updated: 'Updated Contract',
  contract_deleted: 'Deleted Contract',
  contract_workflow_transition: 'Workflow Transition',
  contract_submit: 'Submitted Contract',
  contract_approve: 'Approved Contract',
  contract_reject: 'Rejected Contract',
  contract_complete: 'Completed Contract',
  contract_cancel: 'Cancelled Contract',
  attendance_marked: 'Marked Attendance',
  settings_updated: 'Updated Settings',
};

const formatDateTime = (dt) => {
  if (!dt) return '—';
  try {
    return new Date(dt).toLocaleString('en-KW', { dateStyle: 'medium', timeStyle: 'short' });
  } catch {
    return dt;
  }
};

// ─── Detail Modal ─────────────────────────────────────────────────────────────

const DetailModal = ({ log, onClose }) => {
  if (!log) return null;

  const renderJSON = (data) => {
    if (!data || typeof data !== 'object') return <Text type="secondary">None</Text>;
    return (
      <pre style={{ fontSize: 12, background: '#f5f5f5', padding: 8, borderRadius: 4, maxHeight: 200, overflow: 'auto' }}>
        {JSON.stringify(data, null, 2)}
      </pre>
    );
  };

  return (
    <Modal
      open={!!log}
      onCancel={onClose}
      footer={[<Button key="close" onClick={onClose}>Close</Button>]}
      title={<Space><AuditOutlined /> Audit Log Detail</Space>}
      width={700}
    >
      <Descriptions column={2} bordered size="small" style={{ marginBottom: 16 }}>
        <Descriptions.Item label="Timestamp" span={2}>{formatDateTime(log.timestamp)}</Descriptions.Item>
        <Descriptions.Item label="User">{log.user_name}</Descriptions.Item>
        <Descriptions.Item label="Role">{log.user_role}</Descriptions.Item>
        <Descriptions.Item label="Action">
          <Tag color={CATEGORY_COLORS[log.category] || 'default'}>
            {ACTION_LABELS[log.action] || log.action}
          </Tag>
        </Descriptions.Item>
        <Descriptions.Item label="Category">{log.category}</Descriptions.Item>
        <Descriptions.Item label="Entity Type">{log.entity_type}</Descriptions.Item>
        <Descriptions.Item label="Entity ID">{log.entity_id || '—'}</Descriptions.Item>
        <Descriptions.Item label="Entity Name" span={2}>{log.entity_name || '—'}</Descriptions.Item>
        <Descriptions.Item label="Description" span={2}>{log.description}</Descriptions.Item>
        <Descriptions.Item label="IP Address" span={2}>{log.ip_address || '—'}</Descriptions.Item>
      </Descriptions>

      {(log.before_data || log.after_data) && (
        <>
          <Divider>Before / After</Divider>
          <Row gutter={16}>
            <Col span={12}>
              <Text strong>Before:</Text>
              {renderJSON(log.before_data)}
            </Col>
            <Col span={12}>
              <Text strong>After:</Text>
              {renderJSON(log.after_data)}
            </Col>
          </Row>
        </>
      )}
    </Modal>
  );
};

// ─── Stats Dashboard ──────────────────────────────────────────────────────────

const StatsDashboard = ({ stats }) => {
  if (!stats) return null;
  const topCategories = Object.entries(stats.by_category || {}).slice(0, 5);

  return (
    <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
      <Col span={6}>
        <Card size="small">
          <Statistic title="Total Actions" value={stats.total} prefix={<AuditOutlined />} />
        </Card>
      </Col>
      {topCategories.map(([cat, count]) => (
        <Col span={4} key={cat}>
          <Card size="small">
            <Statistic
              title={cat}
              value={count}
              valueStyle={{ color: `var(--ant-${CATEGORY_COLORS[cat] || 'primary'})` }}
            />
          </Card>
        </Col>
      ))}
    </Row>
  );
};

// ─── Main Page ────────────────────────────────────────────────────────────────

const AuditTrailPage = () => {
  const { user } = useAuth();

  const [logs, setLogs] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState(null);
  const [selectedLog, setSelectedLog] = useState(null);
  const [exporting, setExporting] = useState(false);

  // Filters
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [userRole, setUserRole] = useState('');
  const [dateRange, setDateRange] = useState(null);
  const [page, setPage] = useState(1);
  const pageSize = 50;

  // Check admin access
  const isAdmin = user?.role === 'SuperAdmin' || user?.role === 'Admin';

  const fetchLogs = useCallback(async () => {
    if (!isAdmin) return;
    setLoading(true);
    try {
      const params = { page, page_size: pageSize };
      if (search) params.search = search;
      if (category) params.category = category;
      if (userRole) params.user_role = userRole;
      if (dateRange) {
        params.date_from = dateRange[0].toISOString();
        params.date_to = dateRange[1].toISOString();
      }
      const res = await apiClient.get(BASE + '/', { params });
      setLogs(res.items || []);
      setTotal(res.total || 0);
    } catch (err) {
      console.error('Failed to load audit logs:', err);
    } finally {
      setLoading(false);
    }
  }, [isAdmin, page, search, category, userRole, dateRange]);

  const fetchStats = useCallback(async () => {
    if (!isAdmin) return;
    try {
      const params = {};
      if (dateRange) {
        params.date_from = dateRange[0].toISOString();
        params.date_to = dateRange[1].toISOString();
      }
      const res = await apiClient.get(BASE + '/stats', { params });
      setStats(res);
    } catch (err) {
      console.error('Failed to load audit stats:', err);
    }
  }, [isAdmin, dateRange]);

  useEffect(() => {
    fetchLogs();
    fetchStats();
  }, [fetchLogs, fetchStats]);

  const handleExport = async (format) => {
    setExporting(true);
    try {
      const params = { format };
      if (category) params.category = category;
      if (userRole) params.user_role = userRole;
      if (dateRange) {
        params.date_from = dateRange[0].toISOString();
        params.date_to = dateRange[1].toISOString();
      }
      const query = new URLSearchParams(params).toString();
      const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token');
      const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';
      const url = `${apiBase}/audit-logs/export?${query}`;
      const response = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) throw new Error('Export failed');
      const blob = await response.blob();
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = `audit_logs.${format}`;
      link.click();
    } catch (err) {
      console.error('Export failed:', err);
    } finally {
      setExporting(false);
    }
  };

  const columns = [
    {
      title: 'Timestamp',
      dataIndex: 'timestamp',
      key: 'timestamp',
      width: 170,
      render: (v) => <Text style={{ fontSize: 12 }}>{formatDateTime(v)}</Text>,
    },
    {
      title: 'User',
      dataIndex: 'user_name',
      key: 'user_name',
      width: 140,
      render: (name, record) => (
        <Space orientation="vertical" size={0}>
          <Text strong style={{ fontSize: 13 }}>{name}</Text>
          <Text type="secondary" style={{ fontSize: 11 }}>{record.user_role}</Text>
        </Space>
      ),
    },
    {
      title: 'Action',
      dataIndex: 'action',
      key: 'action',
      width: 180,
      render: (action, record) => (
        <Space orientation="vertical" size={0}>
          <Tag color={CATEGORY_COLORS[record.category] || 'default'} style={{ fontSize: 11 }}>
            {ACTION_LABELS[action] || action}
          </Tag>
          <Text type="secondary" style={{ fontSize: 11 }}>{record.category}</Text>
        </Space>
      ),
    },
    {
      title: 'Entity',
      key: 'entity',
      width: 150,
      render: (_, record) => (
        <Space orientation="vertical" size={0}>
          <Text style={{ fontSize: 12 }}>{record.entity_name || record.entity_id || '—'}</Text>
          <Text type="secondary" style={{ fontSize: 11 }}>{record.entity_type}</Text>
        </Space>
      ),
    },
    {
      title: 'Description',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (v) => <Text style={{ fontSize: 12 }}>{v}</Text>,
    },
    {
      title: '',
      key: 'actions',
      width: 60,
      render: (_, record) => (
        <Tooltip title="View details">
          <Button
            size="small"
            icon={<EyeOutlined />}
            onClick={() => setSelectedLog(record)}
          />
        </Tooltip>
      ),
    },
  ];

  if (!isAdmin) {
    return (
      <Card>
        <Empty description="Access denied. Audit trail is only available to Admins." />
      </Card>
    );
  }

  return (
    <div style={{ padding: '24px' }}>
      <Row justify="space-between" align="middle" style={{ marginBottom: 20 }}>
        <Col>
          <Title level={3} style={{ margin: 0 }}>
            <AuditOutlined /> Audit Trail
          </Title>
          <Text type="secondary">Complete log of all admin and manager actions</Text>
        </Col>
        <Col>
          <Space>
            <Button
              icon={<DownloadOutlined />}
              onClick={() => handleExport('csv')}
              loading={exporting}
            >
              Export CSV
            </Button>
            <Button
              icon={<DownloadOutlined />}
              onClick={() => handleExport('json')}
              loading={exporting}
            >
              Export JSON
            </Button>
            <Button icon={<ReloadOutlined />} onClick={() => { fetchLogs(); fetchStats(); }}>
              Refresh
            </Button>
          </Space>
        </Col>
      </Row>

      <StatsDashboard stats={stats} />

      {/* Filters */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Row gutter={[12, 12]} align="middle">
          <Col flex="auto">
            <Input
              placeholder="Search by description, user, entity…"
              prefix={<SearchOutlined />}
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
              allowClear
            />
          </Col>
          <Col>
            <Select
              placeholder="Category"
              value={category || undefined}
              onChange={(v) => { setCategory(v || ''); setPage(1); }}
              allowClear
              style={{ width: 140 }}
            >
              {['employees', 'contracts', 'attendance', 'payroll', 'settings', 'vehicles', 'inventory'].map((c) => (
                <Option key={c} value={c}>{c}</Option>
              ))}
            </Select>
          </Col>
          <Col>
            <Select
              placeholder="User Role"
              value={userRole || undefined}
              onChange={(v) => { setUserRole(v || ''); setPage(1); }}
              allowClear
              style={{ width: 140 }}
            >
              <Option value="SuperAdmin">SuperAdmin</Option>
              <Option value="Admin">Admin</Option>
              <Option value="Site Manager">Site Manager</Option>
            </Select>
          </Col>
          <Col>
            <RangePicker
              onChange={(dates) => {
                setDateRange(dates ? [dates[0].toDate(), dates[1].toDate()] : null);
                setPage(1);
              }}
              style={{ width: 240 }}
            />
          </Col>
        </Row>
      </Card>

      <Card styles={{ body: { padding: 0 } }}>
        <Table
          rowKey="id"
          dataSource={logs}
          columns={columns}
          loading={loading}
          size="small"
          pagination={{
            current: page,
            pageSize,
            total,
            onChange: setPage,
            showSizeChanger: false,
            showTotal: (t) => `${t} total actions`,
          }}
          locale={{ emptyText: <Empty description="No audit logs found" /> }}
        />
      </Card>

      <DetailModal log={selectedLog} onClose={() => setSelectedLog(null)} />
    </div>
  );
};

export default AuditTrailPage;
