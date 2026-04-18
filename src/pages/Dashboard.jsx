// src/pages/Dashboard.jsx
// Project Workflow Overview Dashboard

import React from 'react';
import {
  Row, Col, Card, Statistic, Typography, Button, Space,
  Spin, Tag, Alert, Progress,
} from 'antd';
import {
  ProjectOutlined, TeamOutlined, EnvironmentOutlined,
  WarningOutlined, CheckCircleOutlined, ReloadOutlined,
  ClockCircleOutlined, AlertOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useDashboardMetrics, useAttendanceTrend, useRevenueTrend, useCostBreakdown, useProjectMetrics } from '../hooks/useDashboard';
import AttendanceTrendChart from '../components/Dashboard/AttendanceTrendChart';
import RevenueTrendChart from '../components/Dashboard/RevenueTrendChart';
import CostBreakdownChart from '../components/Dashboard/CostBreakdownChart';
import ProjectStatusChart from '../components/Dashboard/ProjectStatusChart';

const { Title, Text } = Typography;

// ─── Main Dashboard Component ────────────────────────────────────────────────

const Dashboard = () => {
  const navigate = useNavigate();

  const { data, isLoading: loading, error, refetch: loadData } = useDashboardMetrics();
  const { data: attendanceTrend = [], isLoading: loadingAttendance } = useAttendanceTrend();
  const { data: revenueTrend = [], isLoading: loadingRevenue } = useRevenueTrend();
  const { data: costBreakdown = [], isLoading: loadingCost } = useCostBreakdown();
  const { data: projectMetrics = [], isLoading: loadingProjects } = useProjectMetrics();

  if (loading) {
    return (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 400 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (error) {
    return (
      <Alert
        type="error"
        message="Dashboard Error"
        description={error.message || 'Failed to load dashboard data'}
        action={<Button onClick={loadData} icon={<ReloadOutlined />}>Retry</Button>}
        style={{ margin: 24 }}
      />
    );
  }

  const d = data || {};
  const utilizationPct = Math.round((d.workforce_utilization || 0) * 100);

  return (
    <div style={{ padding: '0 4px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <Title level={3} style={{ margin: 0 }}>📊 Overview Dashboard</Title>
          <Text type="secondary">Project Workflow &amp; Workforce Summary</Text>
        </div>
        <Button icon={<ReloadOutlined />} onClick={loadData}>Refresh</Button>
      </div>

      {/* KPI Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
        <Col xs={24} sm={12} md={6}>
          <Card size="small" style={{ borderLeft: '4px solid #1890ff', borderRadius: 10 }}>
              <Statistic
                title="Total Projects"
                value={d.total_projects || 0}
                prefix={<ProjectOutlined style={{ color: '#1890ff' }} />}
                styles={{ content: { color: '#1890ff', fontSize: 20 } }}
              />
            <Text type="secondary" style={{ fontSize: 11 }}>
              {d.active_projects || 0} active
            </Text>
          </Card>
        </Col>

        <Col xs={24} sm={12} md={6}>
          <Card size="small" style={{ borderLeft: '4px solid #52c41a', borderRadius: 10 }}>
              <Statistic
                title="Total Sites"
                value={d.total_sites || 0}
                prefix={<EnvironmentOutlined style={{ color: '#52c41a' }} />}
                styles={{ content: { color: '#52c41a', fontSize: 20 } }}
              />
            <Text type="secondary" style={{ fontSize: 11 }}>
              Across all projects
            </Text>
          </Card>
        </Col>

        <Col xs={24} sm={12} md={6}>
          <Card size="small" style={{ borderLeft: '4px solid #722ed1', borderRadius: 10 }}>
              <Statistic
                title="Total Employees"
                value={d.total_employees || 0}
                prefix={<TeamOutlined style={{ color: '#722ed1' }} />}
                styles={{ content: { color: '#722ed1', fontSize: 20 } }}
              />
            <Text type="secondary" style={{ fontSize: 11 }}>
              {d.assigned_employees || 0} assigned / {d.available_employees || 0} available
            </Text>
          </Card>
        </Col>

        <Col xs={24} sm={12} md={6}>
          <Card size="small" style={{ borderLeft: '4px solid #fa8c16', borderRadius: 10 }}>
              <Statistic
                title="Workforce Utilization"
                value={utilizationPct}
                suffix="%"
                prefix={<CheckCircleOutlined style={{ color: utilizationPct >= 70 ? '#52c41a' : '#fa8c16' }} />}
                styles={{ content: { color: utilizationPct >= 70 ? '#52c41a' : '#fa8c16', fontSize: 20 } }}
              />
            <Progress
              percent={utilizationPct}
              strokeColor={utilizationPct >= 70 ? '#52c41a' : '#fa8c16'}
              showInfo={false}
              size="small"
              style={{ marginTop: 4 }}
            />
          </Card>
        </Col>
      </Row>

      {/* Contract Expiry Alerts & Workforce Gaps */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        {/* Contract Expiry Alerts */}
        <Col xs={24} lg={12}>
          <Card
            title={
              <Space>
                <ClockCircleOutlined style={{ color: '#fa8c16' }} />
                <span>Contract Expiry Alerts</span>
                {(d.contracts_expiring_soon || 0) > 0 && (
                  <Tag color="orange">{d.contracts_expiring_soon}</Tag>
                )}
              </Space>
            }
            size="small"
            style={{ borderRadius: 10 }}
            extra={
              <Button size="small" onClick={() => navigate('/project-workflow')}>
                View All
              </Button>
            }
          >
            {(d.expiring_contracts || []).length === 0 ? (
              <div style={{ textAlign: 'center', padding: 20 }}>
                <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 24 }} />
                <br />
                <Text type="secondary" style={{ marginTop: 8, display: 'block' }}>
                  No contracts expiring soon
                </Text>
              </div>
            ) : (
              <Space orientation="vertical" size={8} style={{ width: '100%' }}>
                {d.expiring_contracts.map((contract, index) => {
                  const daysLeft = contract.days_remaining ?? contract.days_until_expiry ?? 0;
                  const urgency = daysLeft <= 7 ? 'red' : daysLeft <= 14 ? 'orange' : 'gold';
                  const contractKey = contract.uid || contract.contract_id || `contract-${index}`;
                  return (
                    <Card key={contractKey} size="small">
                      <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center' }}>
                        <div>
                          <Text strong style={{ fontSize: 13 }}>
                            {contract.contract_name || contract.name}
                          </Text>
                          {contract.project_name && (
                            <>
                              <br />
                              <Text type="secondary" style={{ fontSize: 11 }}>{contract.project_name}</Text>
                            </>
                          )}
                        </div>
                        <Tag color={urgency}>
                          {daysLeft} day{daysLeft !== 1 ? 's' : ''} left
                        </Tag>
                      </div>
                    </Card>
                  );
                })}
              </Space>
            )}
          </Card>
        </Col>

        {/* Workforce Gaps */}
        <Col xs={24} lg={12}>
          <Card
            title={
              <Space>
                <AlertOutlined style={{ color: '#ff4d4f' }} />
                <span>Workforce Gaps</span>
                {(d.workforce_gaps || []).length > 0 && (
                  <Tag color="red">{(d.workforce_gaps || []).length}</Tag>
                )}
              </Space>
            }
            size="small"
            style={{ borderRadius: 10 }}
            extra={
              <Button size="small" onClick={() => navigate('/workforce-allocation')}>
                View All
              </Button>
            }
          >
            {(d.workforce_gaps || []).length === 0 ? (
              <div style={{ textAlign: 'center', padding: 20 }}>
                <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 24 }} />
                <br />
                <Text type="secondary" style={{ marginTop: 8, display: 'block' }}>
                  No workforce gaps detected
                </Text>
              </div>
            ) : (
              <Space orientation="vertical" size={8} style={{ width: '100%' }}>
                {d.workforce_gaps.map((gap, index) => {
                  const needed = gap.workers_needed ?? gap.gap ?? gap.shortage ?? 0;
                  const gapKey = gap.uid || gap.site_id || `gap-${index}`;
                  return (
                    <Card key={gapKey} size="small">
                      <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center' }}>
                        <div>
                          <Text strong style={{ fontSize: 13 }}>
                            {gap.site_name || gap.site || gap.name}
                          </Text>
                          {gap.project_name && (
                            <>
                              <br />
                              <Text type="secondary" style={{ fontSize: 11 }}>{gap.project_name}</Text>
                            </>
                          )}
                        </div>
                        <Tag color="red" icon={<WarningOutlined />}>
                          Needs {needed} worker{needed !== 1 ? 's' : ''}
                        </Tag>
                      </div>
                    </Card>
                  );
                })}
              </Space>
            )}
          </Card>
        </Col>
      </Row>

      {/* Active Projects List */}
      {(d.projects || []).length > 0 && (
        <Row gutter={[16, 16]}>
          <Col xs={24}>
            <Card
              title={
                <Space>
                  <ProjectOutlined style={{ color: '#1890ff' }} />
                  <span>Active Projects</span>
                  <Tag color="blue">{(d.projects || []).length}</Tag>
                </Space>
              }
              size="small"
              style={{ borderRadius: 10 }}
              extra={
                <Button size="small" onClick={() => navigate('/projects')}>
                  View All
                </Button>
              }
            >
              <Row gutter={[12, 12]}>
                {(d.projects || []).slice(0, 6).map((project, index) => (
                  <Col xs={24} sm={12} md={8} key={project.id || project.project_id || project.uid || `project-${index}`}>
                    <Card
                      size="small"
                      style={{
                        borderRadius: 8,
                        borderLeft: `3px solid ${project.status === 'active' ? '#52c41a' : '#d9d9d9'}`,
                      }}
                    >
                      <Text strong style={{ fontSize: 13 }}>
                        {project.name || project.project_name}
                      </Text>
                      <br />
                      <Space size={4} style={{ marginTop: 4 }}>
                        <Tag color={project.status === 'active' ? 'green' : 'default'} style={{ fontSize: 10 }}>
                          {project.status || 'unknown'}
                        </Tag>
                        {project.sites_count != null && (
                          <Text type="secondary" style={{ fontSize: 11 }}>
                            {project.sites_count} site{project.sites_count !== 1 ? 's' : ''}
                          </Text>
                        )}
                      </Space>
                    </Card>
                  </Col>
                ))}
              </Row>
            </Card>
          </Col>
        </Row>
      )}

      {/* ── Analytics Charts ─────────────────────────────────────────────── */}
      <Row gutter={[16, 16]} style={{ marginTop: 16, marginBottom: 16 }}>
        <Col xs={24} lg={12}>
          <Card
            title="📈 Attendance Trend (Last 30 Days)"
            size="small"
            style={{ borderRadius: 10 }}
          >
            <AttendanceTrendChart data={attendanceTrend} loading={loadingAttendance} />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card
            title="💰 Monthly Revenue"
            size="small"
            style={{ borderRadius: 10 }}
          >
            <RevenueTrendChart data={revenueTrend} loading={loadingRevenue} />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card
            title="🧾 Cost Breakdown"
            size="small"
            style={{ borderRadius: 10 }}
          >
            <CostBreakdownChart data={costBreakdown} loading={loadingCost} />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card
            title="🏗️ Project Status"
            size="small"
            style={{ borderRadius: 10 }}
          >
            <ProjectStatusChart data={projectMetrics} loading={loadingProjects} />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;
