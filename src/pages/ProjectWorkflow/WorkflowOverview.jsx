import React, { useState, useEffect, useCallback } from 'react';
import {
  Card, Row, Col, Statistic, Tag, Empty, message, Spin,
  Table, Collapse, Typography, Space, Badge, Alert, Button,
  Input,
} from 'antd';
import {
  ProjectOutlined, FileTextOutlined, EnvironmentOutlined,
  TeamOutlined, DollarOutlined, WarningOutlined,
  SearchOutlined, ApartmentOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { fetchWithAuth } from '../../services/apiService';
import './WorkflowOverview.css';

const { Title, Text } = Typography;

const STATUS_COLORS = {
  Active: 'green',
  Completed: 'blue',
  'On Hold': 'orange',
  Cancelled: 'red',
  Expired: 'red',
};

const WorkflowOverview = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [searchText, setSearchText] = useState('');

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const result = await fetchWithAuth('/dashboard/workflow-summary');
      setData(result);
    } catch (error) {
      console.error('Error fetching workflow summary:', error);
      message.error('Error loading workflow overview');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const filteredHierarchy = (data?.hierarchy || []).filter((p) => {
    if (!searchText) return true;
    const q = searchText.toLowerCase();
    return (
      p.project_name?.toLowerCase().includes(q) ||
      p.project_code?.toLowerCase().includes(q) ||
      p.client_name?.toLowerCase().includes(q) ||
      p.contracts?.some(
        (c) =>
          c.contract_code?.toLowerCase().includes(q) ||
          c.contract_name?.toLowerCase().includes(q) ||
          c.sites?.some(
            (s) =>
              s.name?.toLowerCase().includes(q) ||
              s.site_code?.toLowerCase().includes(q)
          )
      )
    );
  });

  const expiryColumns = [
    {
      title: 'Contract',
      dataIndex: 'contract_code',
      key: 'contract_code',
      render: (text, record) => (
        <Button
          type="link"
          style={{ padding: 0 }}
          onClick={() =>
            navigate(`/project-workflow/contracts/${record.contract_id}/details`)
          }
        >
          {text}
        </Button>
      ),
    },
    {
      title: 'Project',
      dataIndex: 'project_name',
      key: 'project_name',
    },
    {
      title: 'End Date',
      dataIndex: 'end_date',
      key: 'end_date',
    },
    {
      title: 'Days Left',
      dataIndex: 'days_remaining',
      key: 'days_remaining',
      render: (days) => (
        <Tag color={days <= 7 ? 'red' : 'orange'}>{days} days</Tag>
      ),
    },
  ];

  const gapColumns = [
    {
      title: 'Site',
      dataIndex: 'site_name',
      key: 'site_name',
      render: (text, record) => (
        <Button
          type="link"
          style={{ padding: 0 }}
          onClick={() => navigate(`/project-workflow/sites/${record.site_id}/details`)}
        >
          {record.site_code ? `${record.site_code} — ${text}` : text}
        </Button>
      ),
    },
    {
      title: 'Project',
      dataIndex: 'project_name',
      key: 'project_name',
    },
    {
      title: 'Assigned / Required',
      key: 'workers',
      render: (_, r) => `${r.assigned_workers} / ${r.required_workers}`,
    },
    {
      title: 'Gap',
      dataIndex: 'gap',
      key: 'gap',
      render: (gap) => <Tag color="red">-{gap} workers</Tag>,
    },
  ];

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 60 }}>
        <Spin size="large" />
        <p style={{ marginTop: 16, color: '#666' }}>Loading workflow overview...</p>
      </div>
    );
  }

  return (
    <div className="workflow-overview-page">
      {/* Header */}
      <div className="overview-header">
        <div>
          <Title level={3} style={{ margin: 0 }}>
            <ApartmentOutlined /> Workflow Overview
          </Title>
          <Text type="secondary">
            Complete view of Projects → Contracts → Sites hierarchy
          </Text>
        </div>
        <Button type="primary" onClick={fetchData}>
          Refresh
        </Button>
      </div>

      {/* Quick Stats */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={8} md={4}>
          <Card size="small">
            <Statistic
              title="Total Projects"
              value={data?.total_projects || 0}
              prefix={<ProjectOutlined />}
              styles={{ content: { color: '#1890ff' }}}
            />
            <div style={{ fontSize: 12, color: '#888', marginTop: 4 }}>
              {data?.active_projects || 0} active · {data?.completed_projects || 0} completed
            </div>
          </Card>
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Card size="small">
            <Statistic
              title="Total Contracts"
              value={data?.total_contracts || 0}
              prefix={<FileTextOutlined />}
              styles={{ content: { color: '#722ed1' }}}
            />
            <div style={{ fontSize: 12, color: '#888', marginTop: 4 }}>
              {data?.active_contracts || 0} active
            </div>
          </Card>
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Card size="small">
            <Statistic
              title="Total Sites"
              value={data?.total_sites || 0}
              prefix={<EnvironmentOutlined />}
              styles={{ content: { color: '#52c41a' }}}
            />
            <div style={{ fontSize: 12, color: '#888', marginTop: 4 }}>
              {data?.active_sites || 0} active
            </div>
          </Card>
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Card size="small">
            <Statistic
              title="Temp Workers"
              value={data?.total_active_temp_workers || 0}
              prefix={<TeamOutlined />}
              styles={{ content: { color: '#fa8c16' }}}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Card size="small">
            <Statistic
              title="Contract Value (KD)"
              value={Number(data?.total_contract_value || 0).toLocaleString()}
              prefix={<DollarOutlined />}
              styles={{ content: { color: '#52c41a' }}}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Card size="small">
            <Statistic
              title="Expiring Contracts"
              value={data?.expiring_contracts || 0}
              prefix={<WarningOutlined />}
              styles={{ content: { color: data?.expiring_contracts > 0 ? '#fa8c16' : '#52c41a' }}}
            />
          </Card>
        </Col>
      </Row>

      {/* Alerts */}
      {(data?.expiring_soon?.length > 0 || data?.workforce_gaps?.length > 0) && (
        <Row gutter={16} style={{ marginBottom: 24 }}>
          {data?.expiring_soon?.length > 0 && (
            <Col xs={24} md={12}>
              <Card
                title={
                  <Space>
                    <WarningOutlined style={{ color: '#fa8c16' }} />
                    <span>Contracts Expiring Soon</span>
                    <Badge
                      count={data.expiring_soon.length}
                      style={{ backgroundColor: '#fa8c16' }}
                    />
                  </Space>
                }
                size="small"
              >
                <Table
                  columns={expiryColumns}
                  dataSource={data.expiring_soon}
                  rowKey="contract_id"
                  size="small"
                  pagination={{ pageSize: 5 }}
                />
              </Card>
            </Col>
          )}
          {data?.workforce_gaps?.length > 0 && (
            <Col xs={24} md={12}>
              <Card
                title={
                  <Space>
                    <TeamOutlined style={{ color: '#f5222d' }} />
                    <span>Sites with Workforce Gaps</span>
                    <Badge
                      count={data.workforce_gaps.length}
                      style={{ backgroundColor: '#f5222d' }}
                    />
                  </Space>
                }
                size="small"
              >
                <Table
                  columns={gapColumns}
                  dataSource={data.workforce_gaps}
                  rowKey="site_id"
                  size="small"
                  pagination={{ pageSize: 5 }}
                />
              </Card>
            </Col>
          )}
        </Row>
      )}

      {/* Hierarchy */}
      <Card
        title={
          <Space>
            <ApartmentOutlined />
            <span>Project Hierarchy</span>
          </Space>
        }
        extra={
          <Input
            prefix={<SearchOutlined />}
            placeholder="Search projects, contracts, sites..."
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            style={{ width: 280 }}
            allowClear
          />
        }
      >
        {filteredHierarchy.length === 0 ? (
          <Empty description="No projects found" image={Empty.PRESENTED_IMAGE_SIMPLE}>
            <Button
              type="primary"
              onClick={() => navigate('/project-workflow')}
            >
              Go to Projects
            </Button>
          </Empty>
        ) : (
          <Collapse
            accordion
            items={filteredHierarchy.map((proj) => ({
              key: proj.uid,
              label: (
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                  <ProjectOutlined />
                  <strong>{proj.project_code}</strong>
                  <span>—</span>
                  <span>{proj.project_name}</span>
                  <Tag color="cyan">{proj.client_name}</Tag>
                  <Tag color={STATUS_COLORS[proj.status] || 'default'}>{proj.status}</Tag>
                  <Badge
                    count={proj.contracts?.length || 0}
                    style={{ backgroundColor: '#722ed1' }}
                    title="Contracts"
                  />
                  <Badge
                    count={proj.contracts?.reduce((s, c) => s + (c.sites?.length || 0), 0) || 0}
                    style={{ backgroundColor: '#52c41a' }}
                    title="Sites"
                  />
                </div>
              ),
              children: (
                <div style={{ paddingLeft: 16 }}>
                  <Button
                    type="link"
                    size="small"
                    onClick={() => navigate(`/project-workflow/${proj.uid}/details`)}
                    style={{ marginBottom: 8 }}
                  >
                    View Project Details →
                  </Button>

                  {!proj.contracts || proj.contracts.length === 0 ? (
                    <Empty
                      description="No contracts"
                      image={Empty.PRESENTED_IMAGE_SIMPLE}
                    />
                  ) : (
                    <Collapse
                      items={proj.contracts.map((contract) => ({
                        key: contract.uid,
                        label: (
                          <div
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: 8,
                              flexWrap: 'wrap',
                            }}
                          >
                            <FileTextOutlined />
                            <strong>{contract.contract_code}</strong>
                            {contract.contract_name && (
                              <span>— {contract.contract_name}</span>
                            )}
                            <Tag
                              color={STATUS_COLORS[contract.status] || 'default'}
                            >
                              {contract.status}
                            </Tag>
                            {contract.days_remaining != null && (
                              <Tag
                                color={
                                  contract.days_remaining <= 7
                                    ? 'red'
                                    : contract.days_remaining <= 30
                                    ? 'orange'
                                    : 'green'
                                }
                              >
                                {contract.days_remaining}d left
                              </Tag>
                            )}
                            <Tag color="green">
                              KD {Number(contract.contract_value || 0).toLocaleString()}
                            </Tag>
                            <Badge
                              count={contract.sites?.length || 0}
                              style={{ backgroundColor: '#52c41a' }}
                              title="Sites"
                            />
                          </div>
                        ),
                        children: (
                          <div style={{ paddingLeft: 16 }}>
                            <Button
                              type="link"
                              size="small"
                              onClick={() =>
                                navigate(
                                  `/project-workflow/contracts/${contract.uid}/details`
                                )
                              }
                              style={{ marginBottom: 8 }}
                            >
                              View Contract Details →
                            </Button>

                            {!contract.sites || contract.sites.length === 0 ? (
                              <Empty
                                description="No sites"
                                image={Empty.PRESENTED_IMAGE_SIMPLE}
                              />
                            ) : (
                              <div className="sites-grid">
                                {contract.sites.map((site) => (
                                  <Card
                                    key={site.uid}
                                    size="small"
                                    className="site-card"
                                    hoverable
                                    onClick={() =>
                                      navigate(
                                        `/project-workflow/sites/${site.uid}/details`
                                      )
                                    }
                                  >
                                    <Space>
                                      <EnvironmentOutlined
                                        style={{ color: '#52c41a' }}
                                      />
                                      <div>
                                        <div style={{ fontWeight: 500 }}>
                                          {site.site_code || site.name}
                                        </div>
                                        <div
                                          style={{ fontSize: 12, color: '#888' }}
                                        >
                                          {site.location}
                                        </div>
                                        {site.assigned_manager_name && (
                                          <div
                                            style={{ fontSize: 12, color: '#888' }}
                                          >
                                            Manager: {site.assigned_manager_name}
                                          </div>
                                        )}
                                        <div
                                          style={{ fontSize: 12, marginTop: 4 }}
                                        >
                                          <Tag
                                            color={
                                              STATUS_COLORS[site.status] || 'default'
                                            }
                                            style={{ fontSize: 11 }}
                                          >
                                            {site.status}
                                          </Tag>
                                          <span
                                            style={{
                                              fontSize: 11,
                                              color: '#888',
                                            }}
                                          >
                                            {site.assigned_workers}/
                                            {site.required_workers} workers
                                          </span>
                                        </div>
                                      </div>
                                    </Space>
                                  </Card>
                                ))}
                              </div>
                            )}
                          </div>
                        ),
                      }))}
                    />
                  )}
                </div>
              ),
            }))}
          />
        )}
      </Card>
    </div>
  );
};

export default WorkflowOverview;
