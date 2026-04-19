/**
 * ContractDetailsPage.jsx
 *
 * Phase 5 — Type-aware contract detail page.
 * Shows different sections based on contract_type.
 * Accessible via /projects/:projectId/contracts/:contractId
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Card, Row, Col, Button, Table, Tag, Space, Statistic,
  Empty, message, Tabs, Breadcrumb, Spin, Typography,
  Descriptions, Badge, Divider, Alert, Tooltip,
} from 'antd';
import {
  ArrowLeftOutlined, FileTextOutlined, EnvironmentOutlined,
  TeamOutlined, CalendarOutlined, DollarOutlined,
  WarningOutlined, CheckCircleOutlined, ClockCircleOutlined,
} from '@ant-design/icons';
import { useParams, useNavigate, Link } from 'react-router-dom';
import dayjs from 'dayjs';
import { fetchWithAuth } from '../../services/apiService';
import { useAuth } from '../../context/AuthContext';
import {
  getContractTypeLabel, getContractTypeColor,
  CONTRACT_TYPES,
} from '../../constants/contractTypes';

const { Title, Text } = Typography;

const STATUS_COLORS = {
  Active: 'green', Completed: 'blue',
  'On Hold': 'orange', Cancelled: 'red', Expired: 'red',
};

const WF_COLORS = {
  DRAFT: 'default', PENDING_APPROVAL: 'gold',
  ACTIVE: 'green', SUSPENDED: 'orange',
  COMPLETED: 'blue', ARCHIVED: 'purple',
};

// ── Shared site columns ───────────────────────────────────────────────────────
const makeSiteColumns = (navigate, projectId) => [
  {
    title: 'Site', key: 'site',
    render: (_, r) => (
      <Space direction="vertical" size={0}>
        <Text strong>{r.name}</Text>
        <Text type="secondary" style={{ fontSize: 11 }}>{r.site_code}</Text>
      </Space>
    ),
  },
  {
    title: 'Location', dataIndex: 'location', key: 'location',
    render: l => l ? <Space><EnvironmentOutlined />{l}</Space> : '—',
  },
  {
    title: 'Manager', key: 'manager',
    render: (_, r) => {
      const names = r.assigned_manager_names || [];
      return names.length ? names.join(', ') : <Text type="secondary">Unassigned</Text>;
    },
  },
  {
    title: 'Workforce', key: 'workforce',
    render: (_, r) => (
      <Space>
        <TeamOutlined />
        <Text>{r.assigned_workers || 0}{r.required_workers > 0 && ` / ${r.required_workers}`}</Text>
        {r.is_understaffed && <Tag color="red">Understaffed</Tag>}
      </Space>
    ),
  },
  {
    title: 'Status', dataIndex: 'status', key: 'status', width: 110,
    render: s => <Tag color={STATUS_COLORS[s] || 'default'}>{s}</Tag>,
  },
];

// ── Role Slots table (Dedicated Staff + Shift-Based) ─────────────────────────
const RoleSlotsTab = ({ contract, isAdmin }) => {
  const slots = contract?.role_slots || [];
  const columns = [
    { title: 'Slot ID', dataIndex: 'slot_id', key: 'slot_id', width: 120 },
    { title: 'Designation', dataIndex: 'designation', key: 'designation' },
    ...(isAdmin ? [{
      title: 'Daily Rate (KWD)', dataIndex: 'daily_rate', key: 'daily_rate', width: 150,
      render: v => v?.toFixed(3),
    }] : []),
    {
      title: 'Current Employee', key: 'employee',
      render: (_, r) => r.current_employee_name
        ? <Text>{r.current_employee_name}</Text>
        : <Text type="secondary">Unfilled</Text>,
    },
  ];
  return (
    <Table
      columns={columns}
      dataSource={slots}
      rowKey="slot_id"
      size="small"
      pagination={false}
      locale={{ emptyText: 'No role slots configured yet.' }}
    />
  );
};

// ── Daily Muster section (Shift-Based contracts) ──────────────────────────────
const DailyMusterTab = ({ contract, navigate, projectId }) => {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!contract?.uid) return;
    fetchWithAuth(`/role-contracts/daily-fulfillment/?contract_id=${contract.uid}&limit=30`)
      .then(d => setRecords(Array.isArray(d) ? d : []))
      .catch(() => setRecords([]))
      .finally(() => setLoading(false));
  }, [contract?.uid]);

  const columns = [
    {
      title: 'Date', dataIndex: 'date', key: 'date', width: 140,
      render: d => dayjs(d).format('DD MMM YYYY'),
    },
    {
      title: 'Slots Filled', key: 'filled',
      render: (_, r) => (
        <Space>
          <Text>{r.total_roles_filled} / {r.total_roles_required}</Text>
          {r.total_roles_filled < r.total_roles_required && (
            <Tag color="red">{r.total_roles_required - r.total_roles_filled} unfilled</Tag>
          )}
        </Space>
      ),
    },
    {
      title: 'Submitted', key: 'submitted',
      render: (_, r) => r.is_submitted
        ? <Tag color="green" icon={<CheckCircleOutlined />}>Submitted</Tag>
        : <Tag color="orange" icon={<ClockCircleOutlined />}>Pending</Tag>,
    },
    {
      title: '', key: 'action', width: 120,
      render: (_, r) => (
        <Button size="small" type="link"
          onClick={() => navigate(`/projects/${projectId}/contracts/${contract.uid}/muster/${dayjs(r.date).format('YYYY-MM-DD')}`)}>
          View →
        </Button>
      ),
    },
  ];

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Text type="secondary">Daily Muster records for this contract</Text>
        <Button type="primary" size="small"
          onClick={() => navigate(`/projects/${projectId}/contracts/${contract.uid}/muster`)}>
          Record Today's Muster
        </Button>
      </div>
      <Table
        columns={columns}
        dataSource={records}
        rowKey="uid"
        loading={loading}
        pagination={{ pageSize: 15 }}
        locale={{ emptyText: 'No muster records yet.' }}
      />
    </>
  );
};

// ── Main Page ─────────────────────────────────────────────────────────────────
const ContractDetailsPage = () => {
  const { projectId, contractId } = useParams();
  const navigate = useNavigate();
  const { isAdmin, isSiteManager } = useAuth();

  const [loading, setLoading]     = useState(true);
  const [contract, setContract]   = useState(null);
  const [project, setProject]     = useState(null);
  const [sites, setSites]         = useState([]);
  const [activeTab, setActiveTab] = useState('overview');

  const fetchData = useCallback(async () => {
    if (!contractId) return;
    setLoading(true);
    try {
      const [contractData, projectData] = await Promise.all([
        fetchWithAuth(`/api/contracts/${contractId}`),
        projectId ? fetchWithAuth(`/projects/${projectId}`) : Promise.resolve(null),
      ]);
      const c = contractData?.contract || contractData;
      setContract(c);
      setProject(projectData?.project || projectData);
      // Fetch sites for this contract
      const sitesData = await fetchWithAuth(`/api/sites?contract_id=${contractId}`).catch(() => []);
      setSites(Array.isArray(sitesData) ? sitesData : []);
    } catch {
      message.error('Error loading contract details');
    } finally {
      setLoading(false);
    }
  }, [contractId, projectId]);

  useEffect(() => { fetchData(); }, [fetchData]);

  if (loading) {
    return <div style={{ padding: 24, textAlign: 'center' }}><Spin size="large" /></div>;
  }

  if (!contract) {
    return (
      <div style={{ padding: 24 }}>
        <Empty description="Contract not found">
          <Button onClick={() => navigate(`/projects/${projectId}`)}>Back to Project</Button>
        </Empty>
      </div>
    );
  }

  const contractType    = contract.contract_type;
  const isShiftBased    = contractType === CONTRACT_TYPES.SHIFT_BASED;
  const isDedicatedStaff = contractType === CONTRACT_TYPES.DEDICATED_STAFF;
  const isGoodsStorage  = contractType === CONTRACT_TYPES.GOODS_STORAGE;
  const isTransportation = contractType === CONTRACT_TYPES.TRANSPORTATION;

  const siteColumns = makeSiteColumns(navigate, projectId);

  // ── Build tabs based on contract type ──────────────────────────────────
  const tabItems = [
    {
      key: 'overview',
      label: 'Overview',
      children: (
        <Descriptions bordered size="small" column={{ xs: 1, sm: 2 }}>
          <Descriptions.Item label="Contract Code">{contract.contract_code}</Descriptions.Item>
          <Descriptions.Item label="Contract Name">{contract.contract_name || '—'}</Descriptions.Item>
          <Descriptions.Item label="Type">
            <Tag color={getContractTypeColor(contractType)}>{getContractTypeLabel(contractType)}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="Workflow State">
            <Tag color={WF_COLORS[contract.workflow_state] || 'default'}>{contract.workflow_state}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="Start Date">
            {contract.start_date ? dayjs(contract.start_date).format('DD MMM YYYY') : '—'}
          </Descriptions.Item>
          <Descriptions.Item label="End Date">
            {contract.end_date ? dayjs(contract.end_date).format('DD MMM YYYY') : '—'}
          </Descriptions.Item>
          {isAdmin && (
            <Descriptions.Item label="Contract Value">
              {contract.contract_value != null ? `KWD ${Number(contract.contract_value).toLocaleString()}` : '—'}
            </Descriptions.Item>
          )}
          {isAdmin && (
            <Descriptions.Item label="Payment Terms">{contract.payment_terms || '—'}</Descriptions.Item>
          )}
          <Descriptions.Item label="Days Remaining" span={2}>
            {contract.days_remaining > 0
              ? <Tag color={contract.is_expiring_soon ? 'warning' : 'green'}>{contract.days_remaining} days</Tag>
              : <Tag color="red">Expired</Tag>
            }
          </Descriptions.Item>
          {contract.notes && (
            <Descriptions.Item label="Notes" span={2}>{contract.notes}</Descriptions.Item>
          )}
        </Descriptions>
      ),
    },

    // Sites tab — all types
    {
      key: 'sites',
      label: <Space><EnvironmentOutlined />Sites <Badge count={sites.length} /></Space>,
      children: (
        <Table
          columns={siteColumns}
          dataSource={sites}
          rowKey="uid"
          pagination={false}
          locale={{ emptyText: 'No sites under this contract.' }}
        />
      ),
    },

    // Role Slots tab — Dedicated Staff + Shift-Based
    ...(isDedicatedStaff || isShiftBased ? [{
      key: 'roles',
      label: <Space><TeamOutlined />Role Slots</Space>,
      children: <RoleSlotsTab contract={contract} isAdmin={isAdmin} />,
    }] : []),

    // Daily Muster tab — Shift-Based only
    ...(isShiftBased ? [{
      key: 'muster',
      label: (
        <Space>
          <CalendarOutlined />
          Daily Muster
          {contract.total_role_slots > 0 && (
            <Badge count={contract.total_role_slots} style={{ backgroundColor: '#1677ff' }} />
          )}
        </Space>
      ),
      children: (
        <DailyMusterTab
          contract={contract}
          navigate={navigate}
          projectId={projectId}
        />
      ),
    }] : []),

    // Inventory Batches tab — Goods & Storage
    ...(isGoodsStorage ? [{
      key: 'inventory',
      label: 'Inventory Batches',
      children: (
        <Alert
          title="Inventory Batches"
          description="Inventory batch logging (Phase 7) will appear here. Managers can log arrivals and classify item conditions."
          type="info"
          showIcon
        />
      ),
    }] : []),

    // Vehicles tab — Transportation
    ...(isTransportation ? [{
      key: 'vehicles',
      label: 'Vehicles & Drivers',
      children: (
        <Alert
          title="Transportation Details"
          description="Vehicle and driver assignments for this transportation contract will appear here."
          type="info"
          showIcon
        />
      ),
    }] : []),
  ];

  return (
    <div style={{ padding: 24 }}>
      {/* Breadcrumb */}
      <Breadcrumb style={{ marginBottom: 16 }} items={[
        { title: <Link to="/projects">Projects</Link> },
        { title: <Link to={`/projects/${projectId}`}>{project?.project_name || `Project ${projectId}`}</Link> },
        { title: contract.contract_name || contract.contract_code },
      ]} />

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 }}>
        <Space align="start" direction="vertical" size={4}>
          <Space>
            <Button icon={<ArrowLeftOutlined />} type="text"
              onClick={() => navigate(`/projects/${projectId}`)} />
            <Title level={3} style={{ margin: 0 }}>
              {contract.contract_name || contract.contract_code}
            </Title>
            <Tag color={getContractTypeColor(contractType)}>{getContractTypeLabel(contractType)}</Tag>
            <Tag color={WF_COLORS[contract.workflow_state] || 'default'}>{contract.workflow_state}</Tag>
          </Space>
          <Text type="secondary" style={{ marginLeft: 36 }}>
            {contract.contract_code} · {contract.client_name || project?.client_name}
          </Text>
        </Space>
      </div>

      <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />
    </div>
  );
};

export default ContractDetailsPage;
