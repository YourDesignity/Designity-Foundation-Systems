import React, { useState, useEffect } from 'react';
import {
  Card, Tabs, Tag, Space, Badge, Statistic, Row, Col,
  Empty, Spin, message, Table, Button,
} from 'antd';
import {
  FileTextOutlined, ProjectOutlined, EnvironmentOutlined,
  TeamOutlined, ApartmentOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { projectService, contractService, siteService } from '../services';

const STATUS_COLORS = {
  Active: 'green',
  Completed: 'blue',
  'On Hold': 'orange',
  Cancelled: 'red',
  Expired: 'red',
};

const STAT_COLORS = {
  projects: '#1890ff',
  contracts: '#722ed1',
  sites: '#52c41a',
  workers: '#fa8c16',
  fulfillmentOk: '#52c41a',
  fulfillmentLow: '#fa8c16',
};

const WorkflowPage = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [projects, setProjects] = useState([]);
  const [contracts, setContracts] = useState([]);
  const [sites, setSites] = useState([]);

  useEffect(() => {
    fetchAll();
  }, []);

  const fetchAll = async () => {
    setLoading(true);
    try {
      const [projectsData, contractsData, sitesData] = await Promise.all([
        projectService.getAll(),
        contractService.getWorkflowContracts(),
        siteService.getWorkflowSites(),
      ]);
      setProjects(Array.isArray(projectsData) ? projectsData : []);
      setContracts(Array.isArray(contractsData) ? contractsData : []);
      setSites(Array.isArray(sitesData) ? sitesData : []);
    } catch (error) {
      console.error('Error fetching workflow data:', error);
      message.error('Error loading workflow data');
    } finally {
      setLoading(false);
    }
  };

  const projectColumns = [
    {
      title: 'Code',
      dataIndex: 'project_code',
      key: 'project_code',
      render: (t) => <strong>{t}</strong>,
    },
    { title: 'Project Name', dataIndex: 'project_name', key: 'project_name' },
    { title: 'Client', dataIndex: 'client_name', key: 'client_name' },
    {
      title: 'Sites',
      dataIndex: 'total_sites',
      key: 'total_sites',
      align: 'center',
      render: (v) => <Badge count={v || 0} showZero style={{ backgroundColor: '#1890ff' }} />,
    },
    {
      title: 'Workers',
      dataIndex: 'total_assigned_employees',
      key: 'total_assigned_employees',
      align: 'center',
      render: (v) => <Badge count={v || 0} showZero style={{ backgroundColor: '#52c41a' }} />,
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (s) => <Tag color={STATUS_COLORS[s] || 'default'}>{s}</Tag>,
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button type="link" onClick={() => navigate(`/project-workflow/${record.uid}/contracts`)}>
            Contracts
          </Button>
          <Button type="link" onClick={() => navigate(`/project-workflow/${record.uid}/sites`)}>
            Sites
          </Button>
        </Space>
      ),
    },
  ];

  const contractColumns = [
    {
      title: 'Code',
      dataIndex: 'contract_code',
      key: 'contract_code',
      render: (t) => <strong>{t}</strong>,
    },
    { title: 'Contract Name', dataIndex: 'contract_name', key: 'contract_name', render: (t) => t || '—' },
    { title: 'Project', dataIndex: 'project_name', key: 'project_name' },
    {
      title: 'Value (KD)',
      dataIndex: 'contract_value',
      key: 'contract_value',
      render: (v) => (v != null ? Number(v).toLocaleString() : '—'),
    },
    {
      title: 'Days Left',
      dataIndex: 'days_remaining',
      key: 'days_remaining',
      render: (d, r) => (
        <span style={{ color: r.is_expiring_soon ? 'red' : 'inherit' }}>
          {d != null ? d : '—'} {r.is_expiring_soon && '⚠️'}
        </span>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (s) => <Tag color={STATUS_COLORS[s] || 'default'}>{s}</Tag>,
    },
  ];

  const siteColumns = [
    {
      title: 'Code',
      dataIndex: 'site_code',
      key: 'site_code',
      render: (t) => <strong>{t}</strong>,
    },
    { title: 'Site Name', dataIndex: 'name', key: 'name' },
    { title: 'Location', dataIndex: 'location', key: 'location' },
    { title: 'Project', dataIndex: 'project_name', key: 'project_name' },
    {
      title: 'Manager',
      dataIndex: 'assigned_manager_name',
      key: 'assigned_manager_name',
      render: (name) =>
        name ? <Tag color="blue">{name}</Tag> : <Tag color="orange">Unassigned</Tag>,
    },
    {
      title: 'Workers',
      key: 'workers',
      render: (_, r) => {
        const assigned = r.assigned_workers || 0;
        const required = r.required_workers || 0;
        // Sites with no required workers are considered fully staffed (green)
        const ok = required === 0 || assigned >= required;
        return (
          <span style={{ color: ok ? STAT_COLORS.fulfillmentOk : STAT_COLORS.fulfillmentLow }}>
            {assigned} / {required}
          </span>
        );
      },
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (s) => <Tag color={STATUS_COLORS[s] || 'default'}>{s}</Tag>,
    },
  ];

  const summary = {
    projects: projects.length,
    activeProjects: projects.filter((p) => p.status === 'Active').length,
    contracts: contracts.length,
    activeContracts: contracts.filter((c) => c.status === 'Active').length,
    sites: sites.length,
    activeSites: sites.filter((s) => s.status === 'Active').length,
    totalWorkers: sites.reduce((sum, s) => sum + (s.assigned_workers || 0), 0),
    totalRequired: sites.reduce((sum, s) => sum + (s.required_workers || 0), 0),
  };

  const tabItems = [
    {
      key: 'overview',
      label: 'Overview',
      children: (
        <Spin spinning={loading}>
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={8}>
              <Card>
                <Statistic
                  title="Projects"
                  value={summary.projects}
                  prefix={<ProjectOutlined />}
                  suffix={`(${summary.activeProjects} active)`}
                  styles={{ content: { color: STAT_COLORS.projects } }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={8}>
              <Card>
                <Statistic
                  title="Contracts"
                  value={summary.contracts}
                  prefix={<FileTextOutlined />}
                  suffix={`(${summary.activeContracts} active)`}
                  styles={{ content: { color: STAT_COLORS.contracts } }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={8}>
              <Card>
                <Statistic
                  title="Sites"
                  value={summary.sites}
                  prefix={<EnvironmentOutlined />}
                  suffix={`(${summary.activeSites} active)`}
                  styles={{ content: { color: STAT_COLORS.sites } }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12}>
              <Card>
                <Statistic
                  title="Assigned Workers"
                  value={summary.totalWorkers}
                  prefix={<TeamOutlined />}
                  suffix={`/ ${summary.totalRequired} required`}
                  styles={{ content: { color: STAT_COLORS.workers } }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12}>
              <Card>
                <Statistic
                  title="Fulfillment Rate"
                  value={
                    summary.totalRequired > 0
                      ? Math.round((summary.totalWorkers / summary.totalRequired) * 100)
                      : 100
                  }
                  suffix="%"
                  styles={{
                    content: {
                      color:
                        summary.totalRequired === 0 ||
                        summary.totalWorkers >= summary.totalRequired
                          ? STAT_COLORS.fulfillmentOk
                          : STAT_COLORS.fulfillmentLow,
                    },
                  }}
                />
              </Card>
            </Col>
          </Row>
        </Spin>
      ),
    },
    {
      key: 'projects',
      label: (
        <span>
          <ProjectOutlined /> Projects ({projects.length})
        </span>
      ),
      children: (
        <Table
          columns={projectColumns}
          dataSource={projects}
          loading={loading}
          rowKey="uid"
          pagination={{ pageSize: 10 }}
          locale={{ emptyText: <Empty description="No projects yet" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
        />
      ),
    },
    {
      key: 'contracts',
      label: (
        <span>
          <FileTextOutlined /> Contracts ({contracts.length})
        </span>
      ),
      children: (
        <Table
          columns={contractColumns}
          dataSource={contracts}
          loading={loading}
          rowKey="uid"
          pagination={{ pageSize: 10 }}
          locale={{ emptyText: <Empty description="No contracts yet" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
        />
      ),
    },
    {
      key: 'sites',
      label: (
        <span>
          <EnvironmentOutlined /> Sites ({sites.length})
        </span>
      ),
      children: (
        <Table
          columns={siteColumns}
          dataSource={sites}
          loading={loading}
          rowKey="uid"
          pagination={{ pageSize: 10 }}
          locale={{ emptyText: <Empty description="No sites yet" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
        />
      ),
    },
  ];

  return (
    <div style={{ padding: 24, background: '#f0f2f5', minHeight: 'calc(100vh - 64px)' }}>
      <div style={{ marginBottom: 24, display: 'flex', alignItems: 'center', gap: 12 }}>
        <ApartmentOutlined style={{ fontSize: 28, color: '#1890ff' }} />
        <div>
          <h1 style={{ margin: 0 }}>Workflow Management</h1>
          <p style={{ margin: 0, color: '#666' }}>
            Unified view of Projects → Contracts → Sites hierarchy
          </p>
        </div>
      </div>

      <Card>
        <Tabs defaultActiveKey="overview" items={tabItems} />
      </Card>
    </div>
  );
};

export default WorkflowPage;
