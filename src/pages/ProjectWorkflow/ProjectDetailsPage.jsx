/**
 * ProjectDetailsPage.jsx
 *
 * Phase 4 — Full tabbed Project overview.
 * Shows everything under a project: contracts, sites, workforce, inventory.
 * Contracts and sites are created HERE — not from standalone pages.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Card, Row, Col, Button, Table, Tag, Space, Statistic,
  Empty, message, Tabs, Breadcrumb, Spin, Typography,
  Tooltip, Badge, Modal, Form, Input, Select,
  DatePicker, InputNumber, Divider,
} from 'antd';
import {
  ArrowLeftOutlined, PlusOutlined, FileTextOutlined,
  EnvironmentOutlined, TeamOutlined, CalendarOutlined,
  DollarOutlined, CheckCircleOutlined, WarningOutlined,
  EditOutlined, FolderOpenOutlined,
} from '@ant-design/icons';
import { useParams, useNavigate, Link } from 'react-router-dom';
import dayjs from 'dayjs';
import { fetchWithAuth } from '../../services/apiService';
import { useAuth } from '../../context/AuthContext';
import {
  CONTRACT_TYPE_OPTIONS, getContractTypeLabel, getContractTypeColor,
  normaliseContractType,
} from '../../constants/contractTypes';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;
const { Option } = Select;

const STATUS_COLORS = {
  Active: 'green', Completed: 'blue',
  'On Hold': 'orange', Cancelled: 'red', Expired: 'red',
};

const WF_COLORS = {
  DRAFT: 'default', PENDING_APPROVAL: 'gold',
  ACTIVE: 'green', SUSPENDED: 'orange',
  COMPLETED: 'blue', ARCHIVED: 'purple',
};

// ─── Create Contract Modal ────────────────────────────────────────────────────
const CreateContractModal = ({ open, projectId, projectName, onCancel, onSuccess }) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (values) => {
    try {
      setLoading(true);
      const [start, end] = values.date_range;
      const payload = {
        contract_name: values.contract_name,
        contract_type: values.contract_type,
        project_id: Number(projectId),
        project_name: projectName,
        start_date: start.toISOString(),
        end_date: end.toISOString(),
        contract_value: values.contract_value || 0,
        payment_terms: values.payment_terms,
        notes: values.notes,
      };
      await fetchWithAuth('/api/contracts', { method: 'POST', body: JSON.stringify(payload) });
      message.success('Contract created successfully!');
      form.resetFields();
      onSuccess();
    } catch (err) {
      message.error(err?.message || 'Failed to create contract');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title="Create New Contract"
      open={open}
      onCancel={() => { form.resetFields(); onCancel(); }}
      footer={null}
      width={600}
      destroyOnHidden
    >
      <Form form={form} layout="vertical" onFinish={handleSubmit}>
        <Row gutter={16}>
          <Col span={16}>
            <Form.Item name="contract_name" label="Contract Name"
              rules={[{ required: true, message: 'Please enter a contract name' }]}>
              <Input placeholder="e.g. Labour Supply — Tower A" />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item name="contract_type" label="Type"
              rules={[{ required: true, message: 'Select a type' }]}
              initialValue="DEDICATED_STAFF">
              <Select>
                {CONTRACT_TYPE_OPTIONS.map(o => (
                  <Option key={o.value} value={o.value}>{o.label}</Option>
                ))}
              </Select>
            </Form.Item>
          </Col>
        </Row>
        <Form.Item name="date_range" label="Contract Period"
          rules={[{ required: true, message: 'Select start and end dates' }]}>
          <RangePicker style={{ width: '100%' }} />
        </Form.Item>
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item name="contract_value" label="Contract Value (KWD)">
              <InputNumber min={0} style={{ width: '100%' }} placeholder="0.00" />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item name="payment_terms" label="Payment Terms">
              <Select placeholder="Select..." allowClear>
                {['Monthly', 'Milestone-based', 'Weekly', 'Upon Completion'].map(t => (
                  <Option key={t} value={t}>{t}</Option>
                ))}
              </Select>
            </Form.Item>
          </Col>
        </Row>
        <Form.Item name="notes" label="Notes">
          <Input.TextArea rows={3} placeholder="Any additional notes..." />
        </Form.Item>
        <div style={{ textAlign: 'right' }}>
          <Space>
            <Button onClick={() => { form.resetFields(); onCancel(); }}>Cancel</Button>
            <Button type="primary" htmlType="submit" loading={loading}>Create Contract</Button>
          </Space>
        </div>
      </Form>
    </Modal>
  );
};

// ─── Main Page ────────────────────────────────────────────────────────────────
const ProjectDetailsPage = () => {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const { isAdmin } = useAuth();

  const [loading, setLoading]         = useState(false);
  const [project, setProject]         = useState(null);
  const [contracts, setContracts]     = useState([]);
  const [sites, setSites]             = useState([]);
  const [workforce, setWorkforce]     = useState(null);
  const [activeTab, setActiveTab]     = useState('overview');
  const [createContractOpen, setCreateContractOpen] = useState(false);

  const fetchData = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    try {
      const [detail, wf] = await Promise.all([
        fetchWithAuth(`/projects/${projectId}`),
        fetchWithAuth(`/projects/${projectId}/workforce-summary`).catch(() => null),
      ]);
      setProject(detail?.project || detail);
      setContracts(Array.isArray(detail?.contracts) ? detail.contracts : []);
      setSites(Array.isArray(detail?.sites) ? detail.sites : []);
      setWorkforce(wf);
    } catch {
      message.error('Error loading project details');
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => { fetchData(); }, [fetchData]);

  // ── Contract columns ────────────────────────────────────────────────────
  const contractColumns = [
    {
      title: 'Code', dataIndex: 'contract_code', key: 'contract_code', width: 130,
      render: (text, record) => (
        <Button type="link" style={{ padding: 0 }}
          onClick={() => navigate(`/projects/${projectId}/contracts/${record.uid}`)}>
          {text}
        </Button>
      ),
    },
    {
      title: 'Name', dataIndex: 'contract_name', key: 'contract_name',
      render: t => t || '—',
    },
    {
      title: 'Type', dataIndex: 'contract_type', key: 'contract_type', width: 160,
      render: t => (
        <Tag color={getContractTypeColor(t)}>{getContractTypeLabel(t)}</Tag>
      ),
    },
    {
      title: 'Status', dataIndex: 'workflow_state', key: 'workflow_state', width: 140,
      render: s => <Tag color={WF_COLORS[s] || 'default'}>{s}</Tag>,
    },
    {
      title: 'Value (KWD)', dataIndex: 'contract_value', key: 'contract_value', width: 130,
      render: v => v != null ? Number(v).toLocaleString() : '—',
    },
    {
      title: 'Days Left', dataIndex: 'days_remaining', key: 'days_remaining', width: 100,
      render: (d, r) => d > 0
        ? <Tag color={r.is_expiring_soon ? 'warning' : 'default'}>{d}d</Tag>
        : <Tag color="red">Expired</Tag>,
    },
    {
      title: '', key: 'action', width: 60,
      render: (_, r) => (
        <Tooltip title="View Contract">
          <Button size="small" type="text" icon={<FileTextOutlined />}
            onClick={() => navigate(`/projects/${projectId}/contracts/${r.uid}`)} />
        </Tooltip>
      ),
    },
  ];

  // ── Site columns ────────────────────────────────────────────────────────
  const siteColumns = [
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
      title: 'Contract', dataIndex: 'contract_code', key: 'contract_code',
      render: c => c ? <Tag>{c}</Tag> : '—',
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
          {r.is_understaffed && <Tag color="red">Short</Tag>}
        </Space>
      ),
    },
    {
      title: 'Status', dataIndex: 'status', key: 'status', width: 110,
      render: s => <Tag color={STATUS_COLORS[s] || 'default'}>{s}</Tag>,
    },
  ];

  if (loading && !project) {
    return <div style={{ padding: 24, textAlign: 'center' }}><Spin size="large" /></div>;
  }

  if (!project) {
    return (
      <div style={{ padding: 24 }}>
        <Empty description="Project not found">
          <Button onClick={() => navigate('/projects')}>Back to Projects</Button>
        </Empty>
      </div>
    );
  }

  // ── KPI bar ─────────────────────────────────────────────────────────────
  const activeContracts   = contracts.filter(c => c.workflow_state === 'ACTIVE').length;
  const expiringSoon      = contracts.filter(c => c.is_expiring_soon).length;
  const totalWorkers      = sites.reduce((s, x) => s + (x.assigned_workers || 0), 0);
  const understaffed      = sites.filter(s => s.is_understaffed).length;

  const tabItems = [
    {
      key: 'overview',
      label: 'Overview',
      children: (
        <Row gutter={[16, 16]}>
          <Col xs={12} sm={6}>
            <Card size="small" variant="borderless" style={{ background: '#f0f5ff' }}>
              <Statistic title="Contracts" value={contracts.length}
                suffix={<Text type="secondary" style={{ fontSize: 13 }}>/ {activeContracts} active</Text>} />
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card size="small" variant="borderless" style={{ background: '#f6ffed' }}>
              <Statistic title="Sites" value={sites.length} prefix={<EnvironmentOutlined />} />
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card size="small" variant="borderless" style={{ background: '#fff7e6' }}>
              <Statistic title="Workforce" value={totalWorkers} prefix={<TeamOutlined />} />
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card size="small" variant="borderless"
              style={{ background: expiringSoon > 0 ? '#fff1f0' : '#f5f5f5' }}>
              <Statistic title="Expiring Soon" value={expiringSoon}
                prefix={expiringSoon > 0 ? <WarningOutlined style={{ color: '#ff4d4f' }} /> : null} />
            </Card>
          </Col>

          {understaffed > 0 && (
            <Col span={24}>
              <Card size="small" style={{ borderColor: '#ff4d4f', background: '#fff1f0' }}>
                <Space>
                  <WarningOutlined style={{ color: '#ff4d4f' }} />
                  <Text type="danger">
                    {understaffed} site{understaffed > 1 ? 's are' : ' is'} understaffed
                  </Text>
                </Space>
              </Card>
            </Col>
          )}

          <Col span={24}>
            <Divider orientation="left">Recent Contracts</Divider>
            <Table
              columns={contractColumns}
              dataSource={contracts.slice(0, 5)}
              rowKey="uid"
              size="small"
              pagination={false}
              locale={{ emptyText: 'No contracts yet' }}
            />
            {contracts.length > 5 && (
              <Button type="link" onClick={() => setActiveTab('contracts')}>
                View all {contracts.length} contracts →
              </Button>
            )}
          </Col>
        </Row>
      ),
    },
    {
      key: 'contracts',
      label: (
        <Space>
          <FileTextOutlined />
          Contracts
          <Badge count={contracts.length} style={{ backgroundColor: '#1677ff' }} />
        </Space>
      ),
      children: (
        <>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
            <Text type="secondary">{contracts.length} contract{contracts.length !== 1 ? 's' : ''} under this project</Text>
            {isAdmin && (
              <Button type="primary" icon={<PlusOutlined />}
                onClick={() => setCreateContractOpen(true)}>
                New Contract
              </Button>
            )}
          </div>
          <Table
            columns={contractColumns}
            dataSource={contracts}
            rowKey="uid"
            pagination={{ pageSize: 10 }}
            locale={{ emptyText: <Empty description="No contracts yet. Create one above." /> }}
          />
        </>
      ),
    },
    {
      key: 'sites',
      label: (
        <Space>
          <EnvironmentOutlined />
          Sites
          <Badge count={sites.length} style={{ backgroundColor: '#52c41a' }} />
        </Space>
      ),
      children: (
        <>
          <div style={{ marginBottom: 16 }}>
            <Text type="secondary">
              Sites are created inside a contract. Go to a contract and add sites there.
            </Text>
          </div>
          <Table
            columns={siteColumns}
            dataSource={sites}
            rowKey="uid"
            pagination={{ pageSize: 10 }}
            locale={{ emptyText: <Empty description="No sites yet." /> }}
          />
        </>
      ),
    },
    {
      key: 'workforce',
      label: <Space><TeamOutlined />Workforce</Space>,
      children: (
        <Row gutter={[16, 16]}>
          {workforce ? (
            <>
              <Col xs={12} sm={6}>
                <Card size="small" variant="borderless" style={{ background: '#f0f5ff' }}>
                  <Statistic title="Total Assigned" value={workforce.total_assigned || 0} />
                </Card>
              </Col>
              <Col xs={12} sm={6}>
                <Card size="small" variant="borderless" style={{ background: '#f6ffed' }}>
                  <Statistic title="Available" value={workforce.total_available || 0} />
                </Card>
              </Col>
              <Col xs={12} sm={6}>
                <Card size="small" variant="borderless" style={{ background: '#fff7e6' }}>
                  <Statistic title="On Leave" value={workforce.on_leave || 0} />
                </Card>
              </Col>
              <Col xs={12} sm={6}>
                <Card size="small" variant="borderless"
                  style={{ background: understaffed > 0 ? '#fff1f0' : '#f5f5f5' }}>
                  <Statistic title="Understaffed Sites" value={understaffed} />
                </Card>
              </Col>
            </>
          ) : (
            <Col span={24}>
              <Empty description="Workforce data unavailable" />
            </Col>
          )}
        </Row>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      {/* Breadcrumb */}
      <Breadcrumb style={{ marginBottom: 16 }} items={[
        { title: <Link to="/projects">Projects</Link> },
        { title: project.project_name },
      ]} />

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 }}>
        <div>
          <Space align="center" style={{ marginBottom: 4 }}>
            <Button icon={<ArrowLeftOutlined />} type="text" onClick={() => navigate('/projects')} />
            <Title level={3} style={{ margin: 0 }}>{project.project_name}</Title>
            <Tag color={STATUS_COLORS[project.status] || 'default'}>{project.status}</Tag>
          </Space>
          <Space split="·" style={{ marginLeft: 36 }}>
            <Text type="secondary">{project.project_code}</Text>
            <Text type="secondary">{project.client_name}</Text>
            {project.client_email && <Text type="secondary">{project.client_email}</Text>}
          </Space>
        </div>
      </div>

      {/* Tabs */}
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={tabItems}
        destroyInactiveTabPane={false}
      />

      {/* Create Contract Modal */}
      <CreateContractModal
        open={createContractOpen}
        projectId={projectId}
        projectName={project?.project_name}
        onCancel={() => setCreateContractOpen(false)}
        onSuccess={() => { setCreateContractOpen(false); fetchData(); setActiveTab('contracts'); }}
      />
    </div>
  );
};

export default ProjectDetailsPage;
