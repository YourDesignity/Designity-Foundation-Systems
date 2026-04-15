import React, { useState, useEffect, useCallback } from 'react';
import {
  Card, Row, Col, Button, Table, Tag, Space, Statistic,
  Empty, message, Tabs, Progress, Breadcrumb, Spin, Typography,
  Tooltip, Badge,
} from 'antd';
import {
  ArrowLeftOutlined, ProjectOutlined, FileTextOutlined,
  EnvironmentOutlined, TeamOutlined, PlusOutlined,
  CalendarOutlined, DollarOutlined, CheckCircleOutlined,
} from '@ant-design/icons';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { fetchWithAuth } from '../../services/apiService';
import './ProjectDetailsPage.css';

const { Title, Text } = Typography;

const STATUS_COLORS = {
  Active: 'green',
  Completed: 'blue',
  'On Hold': 'orange',
  Cancelled: 'red',
  Expired: 'red',
};

const ProjectDetailsPage = () => {
  const { projectId } = useParams();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(false);
  const [project, setProject] = useState(null);
  const [contracts, setContracts] = useState([]);
  const [sites, setSites] = useState([]);
  const [workforce, setWorkforce] = useState(null);

  const fetchData = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    try {
      const [detailsData, workforceData] = await Promise.all([
        fetchWithAuth(`/projects/${projectId}`),
        fetchWithAuth(`/projects/${projectId}/workforce-summary`),
      ]);

      setProject(detailsData?.project || detailsData);
      setContracts(Array.isArray(detailsData?.contracts) ? detailsData.contracts : []);
      setSites(Array.isArray(detailsData?.sites) ? detailsData.sites : []);
      setWorkforce(workforceData);
    } catch (error) {
      console.error('Error fetching project details:', error);
      message.error('Error loading project details');
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const contractColumns = [
    {
      title: 'Contract Code',
      dataIndex: 'contract_code',
      key: 'contract_code',
      render: (text, record) => (
        <Button
          type="link"
          style={{ padding: 0 }}
          onClick={() => navigate(`/project-workflow/contracts/${record.uid}/details`)}
        >
          {text}
        </Button>
      ),
    },
    {
      title: 'Name',
      dataIndex: 'contract_name',
      key: 'contract_name',
      render: (text) => text || '—',
    },
    {
      title: 'Start Date',
      dataIndex: 'start_date',
      key: 'start_date',
    },
    {
      title: 'End Date',
      dataIndex: 'end_date',
      key: 'end_date',
    },
    {
      title: 'Value (KD)',
      dataIndex: 'contract_value',
      key: 'contract_value',
      render: (v) => (v != null ? Number(v).toLocaleString() : '—'),
    },
    {
      title: 'Days Remaining',
      dataIndex: 'days_remaining',
      key: 'days_remaining',
      render: (days) => {
        if (days == null) return '—';
        const color = days <= 7 ? 'red' : days <= 30 ? 'orange' : 'green';
        return <Tag color={color}>{days} days</Tag>;
      },
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
        <Button
          type="link"
          size="small"
          onClick={() => navigate(`/project-workflow/contracts/${record.uid}/details`)}
        >
          View Details
        </Button>
      ),
    },
  ];

  const siteColumns = [
    {
      title: 'Site Code',
      dataIndex: 'site_code',
      key: 'site_code',
      render: (text, record) => (
        <Button
          type="link"
          style={{ padding: 0 }}
          onClick={() => navigate(`/project-workflow/sites/${record.uid}/details`)}
        >
          {text || `SITE-${record.uid}`}
        </Button>
      ),
    },
    {
      title: 'Site Name',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: 'Location',
      dataIndex: 'location',
      key: 'location',
    },
    {
      title: 'Manager',
      dataIndex: 'assigned_manager_name',
      key: 'assigned_manager_name',
      render: (name) => name || <Text type="secondary">Unassigned</Text>,
    },
    {
      title: 'Workers',
      key: 'workers',
      render: (_, record) => (
        <span>
          {record.assigned_workers}/{record.required_workers}
        </span>
      ),
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
        <Button
          type="link"
          size="small"
          onClick={() => navigate(`/project-workflow/sites/${record.uid}/details`)}
        >
          View Details
        </Button>
      ),
    },
  ];

  const totalContractValue = contracts.reduce((sum, c) => sum + (c.contract_value || 0), 0);
  const activeContracts = contracts.filter((c) => c.status === 'Active').length;
  const activeSites = sites.filter((s) => s.status === 'Active').length;
  const expiringContracts = contracts.filter(
    (c) => c.status === 'Active' && c.days_remaining != null && c.days_remaining <= 30
  ).length;

  const tabItems = [
    {
      key: 'contracts',
      label: (
        <span>
          <FileTextOutlined /> Contracts{' '}
          <Badge count={contracts.length} style={{ backgroundColor: '#722ed1' }} />
        </span>
      ),
      children: (
        <div>
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col xs={12} sm={8} md={6}>
              <Card size="small">
                <Statistic title="Total Contracts" value={contracts.length} valueStyle={{ color: '#1890ff' }} />
              </Card>
            </Col>
            <Col xs={12} sm={8} md={6}>
              <Card size="small">
                <Statistic title="Active" value={activeContracts} valueStyle={{ color: '#52c41a' }} />
              </Card>
            </Col>
            <Col xs={12} sm={8} md={6}>
              <Card size="small">
                <Statistic title="Expiring ≤30 days" value={expiringContracts} valueStyle={{ color: '#fa8c16' }} />
              </Card>
            </Col>
            <Col xs={12} sm={8} md={6}>
              <Card size="small">
                <Statistic
                  title="Total Value (KD)"
                  value={Number(totalContractValue).toLocaleString()}
                  valueStyle={{ color: '#52c41a' }}
                />
              </Card>
            </Col>
          </Row>
          <Table
            columns={contractColumns}
            dataSource={contracts}
            rowKey="uid"
            size="small"
            pagination={{ pageSize: 10 }}
            locale={{ emptyText: <Empty description="No contracts yet" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
          />
        </div>
      ),
    },
    {
      key: 'sites',
      label: (
        <span>
          <EnvironmentOutlined /> Sites{' '}
          <Badge count={sites.length} style={{ backgroundColor: '#52c41a' }} />
        </span>
      ),
      children: (
        <div>
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col xs={12} sm={8} md={6}>
              <Card size="small">
                <Statistic title="Total Sites" value={sites.length} valueStyle={{ color: '#1890ff' }} />
              </Card>
            </Col>
            <Col xs={12} sm={8} md={6}>
              <Card size="small">
                <Statistic title="Active Sites" value={activeSites} valueStyle={{ color: '#52c41a' }} />
              </Card>
            </Col>
            <Col xs={12} sm={8} md={6}>
              <Card size="small">
                <Statistic
                  title="Total Capacity"
                  value={sites.reduce((sum, s) => sum + (s.required_workers || 0), 0)}
                  valueStyle={{ color: '#722ed1' }}
                />
              </Card>
            </Col>
            <Col xs={12} sm={8} md={6}>
              <Card size="small">
                <Statistic
                  title="Total Assigned"
                  value={sites.reduce((sum, s) => sum + (s.assigned_workers || 0), 0)}
                  valueStyle={{ color: '#fa8c16' }}
                />
              </Card>
            </Col>
          </Row>
          <Table
            columns={siteColumns}
            dataSource={sites}
            rowKey="uid"
            size="small"
            pagination={{ pageSize: 10 }}
            locale={{ emptyText: <Empty description="No sites yet" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
          />
        </div>
      ),
    },
    {
      key: 'workforce',
      label: (
        <span>
          <TeamOutlined /> Workforce
        </span>
      ),
      children: (
        <div>
          {workforce ? (
            <>
              <Row gutter={16} style={{ marginBottom: 16 }}>
                <Col xs={12} sm={8} md={6}>
                  <Card size="small">
                    <Statistic
                      title="Company Employees"
                      value={workforce.company_employees}
                      valueStyle={{ color: '#1890ff' }}
                    />
                  </Card>
                </Col>
                <Col xs={12} sm={8} md={6}>
                  <Card size="small">
                    <Statistic
                      title="Temp Workers"
                      value={workforce.external_workers}
                      valueStyle={{ color: '#fa8c16' }}
                    />
                  </Card>
                </Col>
                <Col xs={12} sm={8} md={6}>
                  <Card size="small">
                    <Statistic
                      title="Required"
                      value={workforce.total_required_workers}
                      valueStyle={{ color: '#722ed1' }}
                    />
                  </Card>
                </Col>
                <Col xs={12} sm={8} md={6}>
                  <Card size="small">
                    <Statistic
                      title="Assigned"
                      value={workforce.total_assigned_workers}
                      valueStyle={{ color: '#52c41a' }}
                    />
                  </Card>
                </Col>
              </Row>
              <Card size="small" title="Workforce Utilization">
                <div style={{ marginBottom: 8 }}>
                  <Text>
                    Fulfillment Rate: {workforce.fulfillment_rate != null
                      ? `${Number(workforce.fulfillment_rate).toFixed(1)}%`
                      : 'N/A'}
                  </Text>
                </div>
                <Progress
                  percent={Number(workforce.fulfillment_rate || 0).toFixed(1)}
                  strokeColor={
                    workforce.fulfillment_rate >= 80 ? '#52c41a'
                      : workforce.fulfillment_rate >= 50 ? '#fa8c16'
                        : '#f5222d'
                  }
                />
              </Card>
              <div style={{ marginTop: 16 }}>
                <Table
                  columns={[
                    { title: 'Site Name', dataIndex: 'name', key: 'name' },
                    { title: 'Location', dataIndex: 'location', key: 'location' },
                    {
                      title: 'Manager',
                      dataIndex: 'assigned_manager_name',
                      key: 'assigned_manager_name',
                      render: (n) => n || '—',
                    },
                    {
                      title: 'Assigned / Required',
                      key: 'workers',
                      render: (_, r) => `${r.assigned_workers} / ${r.required_workers}`,
                    },
                    {
                      title: 'Fill %',
                      key: 'fill',
                      render: (_, r) =>
                        r.required_workers > 0
                          ? `${((r.assigned_workers / r.required_workers) * 100).toFixed(0)}%`
                          : '—',
                    },
                  ]}
                  dataSource={sites}
                  rowKey="uid"
                  size="small"
                  pagination={false}
                  locale={{ emptyText: <Empty description="No sites" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
                />
              </div>
            </>
          ) : (
            <Empty description="Workforce data unavailable" />
          )}
        </div>
      ),
    },
    {
      key: 'timeline',
      label: (
        <span>
          <CalendarOutlined /> Timeline
        </span>
      ),
      children: (
        <div className="timeline-section">
          {contracts.length === 0 ? (
            <Empty description="No contracts to display" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          ) : (
            contracts.map((c) => (
              <Card
                key={c.uid}
                size="small"
                style={{ marginBottom: 12 }}
                title={
                  <Space>
                    <FileTextOutlined />
                    <strong>{c.contract_code}</strong>
                    {c.contract_name && <span>— {c.contract_name}</span>}
                    <Tag color={STATUS_COLORS[c.status] || 'default'}>{c.status}</Tag>
                  </Space>
                }
              >
                <Row gutter={16}>
                  <Col span={8}>
                    <Text type="secondary">Start:</Text>{' '}
                    <Text>{c.start_date || '—'}</Text>
                  </Col>
                  <Col span={8}>
                    <Text type="secondary">End:</Text>{' '}
                    <Text>{c.end_date || '—'}</Text>
                  </Col>
                  <Col span={8}>
                    <Text type="secondary">Days Remaining:</Text>{' '}
                    {c.days_remaining != null ? (
                      <Tag color={c.days_remaining <= 30 ? 'orange' : 'green'}>
                        {c.days_remaining} days
                      </Tag>
                    ) : (
                      '—'
                    )}
                  </Col>
                </Row>
                {sites.filter((s) => s.contract_id === c.uid).length > 0 && (
                  <div style={{ marginTop: 8 }}>
                    <Text type="secondary">Sites:</Text>{' '}
                    {sites
                      .filter((s) => s.contract_id === c.uid)
                      .map((s) => (
                        <Tag key={s.uid} color="blue">
                          {s.site_code || s.name}
                        </Tag>
                      ))}
                  </div>
                )}
              </Card>
            ))
          )}
        </div>
      ),
    },
  ];

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 60 }}>
        <Spin size="large" />
        <p style={{ marginTop: 16, color: '#666' }}>Loading project details...</p>
      </div>
    );
  }

  if (!project) {
    return (
      <div style={{ padding: 24 }}>
        <Empty description="Project not found" />
        <div style={{ textAlign: 'center', marginTop: 16 }}>
          <Button onClick={() => navigate('/project-workflow')}>Back to Projects</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="project-details-page">
      {/* Breadcrumb */}
      <Breadcrumb style={{ marginBottom: 16 }}>
        <Breadcrumb.Item>
          <Link to="/dashboard">Dashboard</Link>
        </Breadcrumb.Item>
        <Breadcrumb.Item>
          <Link to="/project-workflow">Projects</Link>
        </Breadcrumb.Item>
        <Breadcrumb.Item>{project.project_name}</Breadcrumb.Item>
        <Breadcrumb.Item>Details</Breadcrumb.Item>
      </Breadcrumb>

      {/* Header */}
      <div className="page-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/project-workflow')}>
            Back
          </Button>
          <div>
            <Title level={4} style={{ margin: 0 }}>
              <ProjectOutlined /> {project.project_name}
            </Title>
            <Text type="secondary">{project.project_code}</Text>
          </div>
        </div>
        <Space>
          <Button
            icon={<PlusOutlined />}
            onClick={() => navigate(`/project-workflow/${projectId}/contracts`)}
          >
            Manage Contracts
          </Button>
          <Button
            icon={<EnvironmentOutlined />}
            onClick={() => navigate(`/project-workflow/${projectId}/sites`)}
          >
            Manage Sites
          </Button>
        </Space>
      </div>

      {/* Project Overview Card */}
      <Card className="overview-card" style={{ marginBottom: 24 }}>
        <Row gutter={24}>
          <Col xs={24} md={16}>
            <Space direction="vertical" size={4}>
              <div>
                <Text type="secondary">Client: </Text>
                <Text strong>{project.client_name}</Text>
                {project.client_contact && (
                  <Text type="secondary"> · {project.client_contact}</Text>
                )}
              </div>
              {project.description && (
                <div>
                  <Text type="secondary">Description: </Text>
                  <Text>{project.description}</Text>
                </div>
              )}
              <div>
                <Text type="secondary">Created: </Text>
                <Text>{project.created_at ? new Date(project.created_at).toLocaleDateString() : '—'}</Text>
                {project.updated_at && (
                  <>
                    <Text type="secondary"> · Updated: </Text>
                    <Text>{new Date(project.updated_at).toLocaleDateString()}</Text>
                  </>
                )}
              </div>
            </Space>
          </Col>
          <Col xs={24} md={8} style={{ textAlign: 'right' }}>
            <Tag color={STATUS_COLORS[project.status] || 'default'} style={{ fontSize: 14, padding: '4px 12px' }}>
              {project.status}
            </Tag>
          </Col>
        </Row>
      </Card>

      {/* Financial Summary */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={8} md={6}>
          <Card size="small">
            <Statistic
              title="Total Contract Value"
              value={Number(totalContractValue).toLocaleString()}
              suffix="KD"
              prefix={<DollarOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={6}>
          <Card size="small">
            <Statistic
              title="Active Contracts"
              value={activeContracts}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={6}>
          <Card size="small">
            <Statistic
              title="Total Sites"
              value={sites.length}
              prefix={<EnvironmentOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={6}>
          <Card size="small">
            <Statistic
              title="Workforce"
              value={(workforce?.company_employees || 0) + (workforce?.external_workers || 0)}
              prefix={<TeamOutlined />}
              valueStyle={{ color: '#fa8c16' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Tabs */}
      <Card>
        <Tabs defaultActiveKey="contracts" items={tabItems} />
      </Card>
    </div>
  );
};

export default ProjectDetailsPage;
