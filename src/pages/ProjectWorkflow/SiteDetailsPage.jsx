import React, { useState, useEffect, useCallback } from 'react';
import {
  Card, Row, Col, Button, Table, Tag, Space, Statistic,
  Empty, message, Tabs, Breadcrumb, Spin, Typography,
  Progress, Avatar, Badge,
} from 'antd';
import {
  ArrowLeftOutlined, EnvironmentOutlined, TeamOutlined,
  UserOutlined, ProjectOutlined, FileTextOutlined,
  UserAddOutlined,
} from '@ant-design/icons';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { fetchWithAuth } from '../../services/apiService';
import './SiteDetailsPage.css';

const { Title, Text } = Typography;

const STATUS_COLORS = {
  Active: 'green',
  Completed: 'blue',
  'On Hold': 'orange',
  Cancelled: 'red',
};

const SiteDetailsPage = () => {
  const { siteId } = useParams();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(false);
  const [site, setSite] = useState(null);
  const [employees, setEmployees] = useState([]);
  const [assignments, setAssignments] = useState([]);
  const [tempWorkers, setTempWorkers] = useState([]);
  const [activity, setActivity] = useState([]);

  const fetchData = useCallback(async () => {
    if (!siteId) return;
    setLoading(true);
    try {
      const [siteData, tempData, activityData] = await Promise.all([
        fetchWithAuth(`/workflow/sites/${siteId}`),
        fetchWithAuth(`/temp-assignments/site/${siteId}`).catch(() => ({ workers: [] })),
        fetchWithAuth(`/workflow/sites/${siteId}/activity`).catch(() => ({ activities: [] })),
      ]);

      setSite(siteData?.site || null);
      setEmployees(Array.isArray(siteData?.assigned_employees) ? siteData.assigned_employees : []);
      setAssignments(Array.isArray(siteData?.assignments) ? siteData.assignments : []);
      setTempWorkers(Array.isArray(tempData?.workers) ? tempData.workers : []);
      setActivity(Array.isArray(activityData?.activities) ? activityData.activities : []);
    } catch (error) {
      console.error('Error fetching site details:', error);
      message.error('Error loading site details');
    } finally {
      setLoading(false);
    }
  }, [siteId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleUnassignEmployee = async (employeeId) => {
    try {
      await fetchWithAuth(`/workflow/sites/${siteId}/employees/${employeeId}`, {
        method: 'DELETE',
      });
      message.success('Employee unassigned successfully');
      fetchData();
    } catch (error) {
      message.error(error.message || 'Error unassigning employee');
    }
  };

  const employeeColumns = [
    {
      title: 'Employee',
      key: 'employee',
      render: (_, record) => (
        <Space>
          <Avatar icon={<UserOutlined />} size="small" />
          <div>
            <div style={{ fontWeight: 500 }}>{record.name}</div>
            <div style={{ fontSize: 12, color: '#888' }}>{record.designation}</div>
          </div>
        </Space>
      ),
    },
    {
      title: 'Type',
      dataIndex: 'employee_type',
      key: 'employee_type',
      render: (t) => <Tag color={t === 'Company' ? 'blue' : 'orange'}>{t}</Tag>,
    },
    {
      title: 'Status',
      dataIndex: 'availability_status',
      key: 'availability_status',
      render: (s) => <Tag color={s === 'Assigned' ? 'green' : 'default'}>{s || 'Assigned'}</Tag>,
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Button
          type="link"
          danger
          size="small"
          onClick={() => handleUnassignEmployee(record.uid)}
        >
          Unassign
        </Button>
      ),
    },
  ];

  const tempWorkerColumns = [
    {
      title: 'Worker',
      dataIndex: 'employee_name',
      key: 'employee_name',
      render: (name) => (
        <Space>
          <Avatar icon={<UserOutlined />} size="small" />
          <Text>{name}</Text>
        </Space>
      ),
    },
    {
      title: 'Rate Type',
      dataIndex: 'rate_type',
      key: 'rate_type',
      render: (t) => <Tag color="cyan">{t}</Tag>,
    },
    {
      title: 'Daily Rate (KD)',
      dataIndex: 'daily_rate',
      key: 'daily_rate',
      render: (v) => (v != null ? Number(v).toFixed(2) : '—'),
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
      title: 'Est. Cost (KD)',
      dataIndex: 'total_cost',
      key: 'total_cost',
      render: (v) => (v != null ? Number(v).toLocaleString() : '—'),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (s) => (
        <Tag color={s === 'Active' ? 'green' : 'default'}>{s}</Tag>
      ),
    },
  ];

  const activityTypeColors = {
    employee_assigned: 'green',
    employee_unassigned: 'red',
    temp_worker_assigned: 'orange',
    temp_worker_ended: 'default',
  };

  const activityColumns = [
    {
      title: 'Type',
      dataIndex: 'type',
      key: 'type',
      render: (t) => (
        <Tag color={activityTypeColors[t] || 'default'}>
          {t?.replace(/_/g, ' ')}
        </Tag>
      ),
    },
    {
      title: 'Description',
      dataIndex: 'description',
      key: 'description',
    },
    {
      title: 'Date',
      dataIndex: 'date',
      key: 'date',
      render: (d) => (d ? new Date(d).toLocaleDateString() : '—'),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (s) => <Tag color={s === 'Active' ? 'green' : 'default'}>{s}</Tag>,
    },
  ];

  const totalTempCost = tempWorkers.reduce(
    (sum, w) => sum + (w.total_cost || 0), 0
  );

  const tabItems = [
    {
      key: 'employees',
      label: (
        <span>
          <TeamOutlined /> Company Employees{' '}
          <Badge count={employees.length} style={{ backgroundColor: '#1890ff' }} />
        </span>
      ),
      children: (
        <div>
          <Table
            columns={employeeColumns}
            dataSource={employees}
            rowKey="uid"
            size="small"
            pagination={{ pageSize: 10 }}
            locale={{
              emptyText: (
                <Empty description="No employees assigned" image={Empty.PRESENTED_IMAGE_SIMPLE}>
                  <Button
                    type="primary"
                    icon={<UserAddOutlined />}
                    onClick={() => navigate(`/sites/${siteId}/assign-employees`)}
                  >
                    Assign Employees
                  </Button>
                </Empty>
              ),
            }}
          />
        </div>
      ),
    },
    {
      key: 'temp_workers',
      label: (
        <span>
          <UserOutlined /> Temp Workers{' '}
          <Badge count={tempWorkers.length} style={{ backgroundColor: '#fa8c16' }} />
        </span>
      ),
      children: (
        <div>
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col xs={12} sm={8} md={6}>
              <Card size="small">
                <Statistic
                  title="Active Temp Workers"
                  value={tempWorkers.filter((w) => w.status === 'Active').length}
                  valueStyle={{ color: '#fa8c16' }}
                />
              </Card>
            </Col>
            <Col xs={12} sm={8} md={6}>
              <Card size="small">
                <Statistic
                  title="Total Cost (KD)"
                  value={Number(totalTempCost).toLocaleString()}
                  valueStyle={{ color: '#f5222d' }}
                />
              </Card>
            </Col>
          </Row>
          <Table
            columns={tempWorkerColumns}
            dataSource={tempWorkers}
            rowKey={(r) => r.assignment_id || r.uid}
            size="small"
            pagination={{ pageSize: 10 }}
            locale={{
              emptyText: (
                <Empty
                  description="No temp workers assigned"
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                >
                  <Button
                    type="primary"
                    onClick={() => navigate(`/sites/${siteId}/workforce`)}
                  >
                    Assign Temp Workers
                  </Button>
                </Empty>
              ),
            }}
          />
        </div>
      ),
    },
    {
      key: 'activity',
      label: (
        <span>
          <FileTextOutlined /> Recent Activity
        </span>
      ),
      children: (
        <Table
          columns={activityColumns}
          dataSource={activity}
          rowKey={(r, i) => `${r.type}-${i}`}
          size="small"
          pagination={{ pageSize: 10 }}
          locale={{ emptyText: <Empty description="No activity recorded" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
        />
      ),
    },
  ];

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 60 }}>
        <Spin size="large" />
        <p style={{ marginTop: 16, color: '#666' }}>Loading site details...</p>
      </div>
    );
  }

  if (!site) {
    return (
      <div style={{ padding: 24 }}>
        <Empty description="Site not found" />
        <div style={{ textAlign: 'center', marginTop: 16 }}>
          <Button onClick={() => navigate(-1)}>Go Back</Button>
        </div>
      </div>
    );
  }

  const capacityPercent =
    site.required_workers > 0
      ? Math.round((site.assigned_workers / site.required_workers) * 100)
      : 0;

  return (
    <div className="site-details-page">
      {/* Breadcrumb */}
      <Breadcrumb style={{ marginBottom: 16 }}>
        <Breadcrumb.Item>
          <Link to="/dashboard">Dashboard</Link>
        </Breadcrumb.Item>
        <Breadcrumb.Item>
          <Link to="/project-workflow">Projects</Link>
        </Breadcrumb.Item>
        {site.project_id && (
          <Breadcrumb.Item>
            <Link to={`/project-workflow/${site.project_id}/details`}>
              {site.project_name || `Project ${site.project_id}`}
            </Link>
          </Breadcrumb.Item>
        )}
        {site.contract_id && (
          <Breadcrumb.Item>
            <Link to={`/project-workflow/contracts/${site.contract_id}/details`}>
              {site.contract_code || `Contract ${site.contract_id}`}
            </Link>
          </Breadcrumb.Item>
        )}
        <Breadcrumb.Item>{site.site_code || site.name}</Breadcrumb.Item>
      </Breadcrumb>

      {/* Header */}
      <div className="page-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)}>
            Back
          </Button>
          <div>
            <Title level={4} style={{ margin: 0 }}>
              <EnvironmentOutlined /> {site.name}
            </Title>
            <Text type="secondary">
              {site.site_code} · {site.location}
            </Text>
          </div>
        </div>
        <Space>
          <Button
            icon={<UserAddOutlined />}
            onClick={() => navigate(`/sites/${siteId}/assign-employees`)}
          >
            Assign Employees
          </Button>
          <Button onClick={() => navigate(`/sites/${siteId}/workforce`)}>
            Manage Temp Workers
          </Button>
        </Space>
      </div>

      {/* Stats row */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={8} md={4}>
          <Card size="small">
            <Statistic
              title="Total Workers"
              value={employees.length + tempWorkers.filter((w) => w.status === 'Active').length}
              prefix={<TeamOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Card size="small">
            <Statistic
              title="Company Employees"
              value={employees.length}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Card size="small">
            <Statistic
              title="Temp Workers"
              value={tempWorkers.filter((w) => w.status === 'Active').length}
              valueStyle={{ color: '#fa8c16' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Card size="small">
            <Statistic
              title="Temp Cost (KD)"
              value={Number(totalTempCost).toLocaleString()}
              valueStyle={{ color: '#f5222d' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Card size="small">
            <Statistic
              title="Capacity"
              value={`${site.assigned_workers}/${site.required_workers}`}
              valueStyle={{ color: capacityPercent >= 80 ? '#52c41a' : '#fa8c16' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Site Overview Card */}
      <Card className="overview-card" style={{ marginBottom: 24 }}>
        <Row gutter={24}>
          <Col xs={24} md={16}>
            <Space direction="vertical" size={4}>
              {site.project_name && (
                <div>
                  <Text type="secondary">Project: </Text>
                  <Link to={`/project-workflow/${site.project_id}/details`}>
                    <Text strong>{site.project_name}</Text>
                  </Link>
                </div>
              )}
              {site.contract_code && (
                <div>
                  <Text type="secondary">Contract: </Text>
                  <Link to={`/project-workflow/contracts/${site.contract_id}/details`}>
                    <Text>{site.contract_code}</Text>
                  </Link>
                </div>
              )}
              {site.assigned_manager_name ? (
                <div>
                  <Text type="secondary">Manager: </Text>
                  <Text strong>{site.assigned_manager_name}</Text>
                </div>
              ) : (
                <div>
                  <Text type="secondary">Manager: </Text>
                  <Text type="warning">Not assigned</Text>
                </div>
              )}
              {site.description && (
                <div>
                  <Text type="secondary">Description: </Text>
                  <Text>{site.description}</Text>
                </div>
              )}
            </Space>
          </Col>
          <Col xs={24} md={8}>
            <Tag
              color={STATUS_COLORS[site.status] || 'default'}
              style={{ fontSize: 14, padding: '4px 12px', marginBottom: 8 }}
            >
              {site.status}
            </Tag>
            <div>
              <Text type="secondary">Capacity Utilization</Text>
              <Progress
                percent={capacityPercent}
                size="small"
                strokeColor={
                  capacityPercent >= 80 ? '#52c41a'
                    : capacityPercent >= 50 ? '#fa8c16'
                      : '#f5222d'
                }
              />
              <Text style={{ fontSize: 12 }}>
                {site.assigned_workers} of {site.required_workers} workers
              </Text>
            </div>
          </Col>
        </Row>
      </Card>

      {/* Tabs */}
      <Card>
        <Tabs defaultActiveKey="employees" items={tabItems} />
      </Card>
    </div>
  );
};

export default SiteDetailsPage;
