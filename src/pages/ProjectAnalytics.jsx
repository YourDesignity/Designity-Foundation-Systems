// src/pages/ProjectAnalytics.jsx
// Phase 6: Comprehensive Analytics Dashboard

import React, { useState, useEffect, useCallback } from 'react';
import {
  Row, Col, Card, Statistic, Typography, Spin,
  Alert, Button, Table, Tag, Progress, Tabs, Empty, Space,
} from 'antd';
import {
  ProjectOutlined, TeamOutlined, DollarOutlined,
  ReloadOutlined, BarChartOutlined, RiseOutlined,
} from '@ant-design/icons';
import { fetchWithAuth } from '../services/apiService.jsx';

const { Title, Text } = Typography;

// Simple bar chart using divs (avoids external chart library issues)
const SimpleBarChart = ({ data, valueKey, nameKey, color = '#52c41a', maxHeight = 200 }) => {
  if (!data || data.length === 0) return <Empty styles={{ image: { height: 40 } }} />;
  const maxVal = Math.max(...data.map((d) => d[valueKey] || 0), 1);
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', gap: 6, height: maxHeight, padding: '0 4px' }}>
      {data.slice(0, 8).map((item, i) => {
        const pct = Math.round(((item[valueKey] || 0) / maxVal) * 100);
        return (
          <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
            <Text style={{ fontSize: 10, color: '#888' }}>{item[valueKey] || 0}</Text>
            <div
              style={{
                width: '100%',
                height: `${Math.max(pct, 4)}%`,
                background: color,
                borderRadius: '4px 4px 0 0',
                transition: 'height 0.5s',
              }}
            />
            <Text
              style={{ fontSize: 9, color: '#555', textAlign: 'center', wordBreak: 'break-word', lineHeight: 1.2 }}
              title={item[nameKey]}
            >
              {String(item[nameKey] || '').slice(0, 8)}
            </Text>
          </div>
        );
      })}
    </div>
  );
};

// Simple donut/pie visual using CSS
const SimplePieChart = ({ available = 0, assigned_company = 0, assigned_external = 0 }) => {
  const total = available + assigned_company + assigned_external || 1;
  const items = [
    { label: 'Available', value: available, color: '#52c41a' },
    { label: 'Assigned', value: assigned_company, color: '#1677ff' },
    { label: 'External', value: assigned_external, color: '#fa8c16' },
  ];
  return (
    <div>
      {items.map((item) => (
        <div key={item.label} style={{ marginBottom: 8 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
            <Text style={{ fontSize: 12 }}>
              <span style={{ display: 'inline-block', width: 10, height: 10, borderRadius: '50%', background: item.color, marginRight: 6 }} />
              {item.label}
            </Text>
            <Text style={{ fontSize: 12 }}>
              {item.value} ({Math.round((item.value / total) * 100)}%)
            </Text>
          </div>
          <Progress
            percent={Math.round((item.value / total) * 100)}
            size="small"
            showInfo={false}
            strokeColor={item.color}
          />
        </div>
      ))}
    </div>
  );
};

const ProjectAnalytics = () => {
  const [projectData, setProjectData] = useState(null);
  const [workforceData, setWorkforceData] = useState(null);
  const [externalData, setExternalData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [pData, wData, eData] = await Promise.all([
        fetchWithAuth('/analytics/projects'),
        fetchWithAuth('/analytics/workforce'),
        fetchWithAuth('/analytics/external-workers'),
      ]);
      setProjectData(pData);
      setWorkforceData(wData);
      setExternalData(eData);
    } catch (err) {
      setError(err.message || 'Failed to load analytics');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 400 }}>
        <Spin size="large" description="Loading analytics..." />
      </div>
    );
  }

  if (error) {
    return (
      <Alert
        type="error"
        message="Analytics Error"
        description={error}
        action={<Button onClick={load} icon={<ReloadOutlined />}>Retry</Button>}
        style={{ margin: 24 }}
      />
    );
  }

  const ps = projectData?.summary ?? {};
  const projects = projectData?.projects ?? [];
  const topEmps = workforceData?.top_employees ?? [];
  const perProject = externalData?.per_project ?? [];
  const pieData = {
    available: workforceData?.total_company_employees
      ? workforceData.total_company_employees - workforceData.assigned_company_employees
      : 0,
    assigned_company: workforceData?.assigned_company_employees ?? 0,
    assigned_external: externalData?.active_external_workers ?? 0,
  };

  const projectColumns = [
    { title: 'Code', dataIndex: 'project_code', key: 'code', width: 90 },
    { title: 'Project', dataIndex: 'project_name', key: 'name', ellipsis: true },
    { title: 'Client', dataIndex: 'client_name', key: 'client', ellipsis: true },
    {
      title: 'Status', dataIndex: 'status', key: 'status', width: 90,
      render: (v) => (
        <Tag color={{ Active: 'green', Completed: 'blue', 'On Hold': 'orange' }[v] || 'default'}>{v}</Tag>
      ),
    },
    {
      title: 'Contract Value', dataIndex: 'contract_value', key: 'value', width: 120,
      render: (v) => `KD ${(v || 0).toLocaleString()}`,
      sorter: (a, b) => (a.contract_value || 0) - (b.contract_value || 0),
    },
    {
      title: 'Completion', dataIndex: 'completion_percentage', key: 'completion', width: 120,
      render: (v) => <Progress percent={v || 0} size="small" strokeColor="#52c41a" />,
    },
    {
      title: 'Workers', dataIndex: 'permanent_workers', key: 'workers', width: 80,
      render: (v, r) => `${v ?? 0} + ${r.active_external_workers ?? 0} ext`,
    },
    {
      title: 'Contract Expiry', dataIndex: 'days_to_expiry', key: 'expiry', width: 110,
      render: (v) =>
        v == null ? <Text type="secondary">—</Text> : (
          <Tag color={v <= 7 ? 'red' : v <= 30 ? 'orange' : 'green'}>{v} days</Tag>
        ),
    },
  ];

  const empColumns = [
    { title: '#', render: (_, __, i) => i + 1, width: 40 },
    { title: 'Employee', dataIndex: 'employee_name', key: 'name' },
    { title: 'Designation', dataIndex: 'designation', key: 'des', ellipsis: true },
    { title: 'Total Assignments', dataIndex: 'total_assignments', key: 'total', sorter: (a, b) => a.total_assignments - b.total_assignments },
    { title: 'Active', dataIndex: 'active_assignments', key: 'active', render: (v) => <Tag color="green">{v}</Tag> },
    { title: 'Total Days', dataIndex: 'total_days', key: 'days' },
  ];

  const externalColumns = [
    { title: 'Project', dataIndex: 'project_code', key: 'code' },
    { title: 'Name', dataIndex: 'project_name', key: 'name', ellipsis: true },
    { title: 'Workers', dataIndex: 'worker_count', key: 'count' },
    { title: 'Total Days', dataIndex: 'total_days', key: 'days' },
    {
      title: 'Total Cost (KD)',
      dataIndex: 'total_cost',
      key: 'cost',
      render: (v) => `KD ${(v || 0).toLocaleString()}`,
      sorter: (a, b) => (a.total_cost || 0) - (b.total_cost || 0),
    },
  ];

  const tabItems = [
    {
      key: 'projects',
      label: (
        <Space>
          <ProjectOutlined />
          Project Performance
        </Space>
      ),
      children: (
        <>
          <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            <Col xs={24} sm={8}>
              <Card size="small" style={{ borderRadius: 10, borderLeft: '4px solid #52c41a' }}>
                <Statistic
                  title="Total Projects"
                  value={ps.total_projects ?? 0}
                  styles={{ content: { color: '#52c41a' } }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={8}>
              <Card size="small" style={{ borderRadius: 10, borderLeft: '4px solid #1677ff' }}>
                <Statistic
                  title="Total Contract Value"
                  value={`KD ${(ps.total_contract_value ?? 0).toLocaleString()}`}
                  styles={{ content: { color: '#1677ff' } }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={8}>
              <Card size="small" style={{ borderRadius: 10, borderLeft: '4px solid #722ed1' }}>
                <Statistic
                  title="Active Contract Value"
                  value={`KD ${(ps.active_contract_value ?? 0).toLocaleString()}`}
                  styles={{ content: { color: '#722ed1' } }}
                />
              </Card>
            </Col>
          </Row>

          <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            <Col xs={24} md={14}>
              <Card title="Contract Value by Project" size="small" style={{ borderRadius: 10 }}>
                <SimpleBarChart
                  data={projects.slice(0, 8)}
                  valueKey="contract_value"
                  nameKey="project_code"
                  color="#1677ff"
                />
              </Card>
            </Col>
            <Col xs={24} md={10}>
              <Card title="Workers per Project" size="small" style={{ borderRadius: 10 }}>
                <SimpleBarChart
                  data={projects.slice(0, 8)}
                  valueKey="permanent_workers"
                  nameKey="project_code"
                  color="#52c41a"
                />
              </Card>
            </Col>
          </Row>

          <Card title="Project Details" size="small" style={{ borderRadius: 10 }}>
            <Table
              dataSource={projects}
              columns={projectColumns}
              rowKey="project_id"
              size="small"
              pagination={{ pageSize: 10 }}
              scroll={{ x: 900 }}
            />
          </Card>
        </>
      ),
    },
    {
      key: 'workforce',
      label: (
        <Space>
          <TeamOutlined />
          Workforce
        </Space>
      ),
      children: (
        <>
          <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            <Col xs={24} sm={6}>
              <Card size="small" style={{ borderRadius: 10, borderLeft: '4px solid #52c41a' }}>
                <Statistic
                  title="Utilization Rate"
                  value={workforceData?.utilization_rate ?? 0}
                  suffix="%"
                  styles={{ content: { color: '#52c41a' } }}
                />
                <Progress percent={workforceData?.utilization_rate ?? 0} size="small" showInfo={false} strokeColor="#52c41a" />
              </Card>
            </Col>
            <Col xs={24} sm={6}>
              <Card size="small" style={{ borderRadius: 10, borderLeft: '4px solid #1677ff' }}>
                <Statistic
                  title="Total Employees"
                  value={workforceData?.total_company_employees ?? 0}
                  styles={{ content: { color: '#1677ff' } }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={6}>
              <Card size="small" style={{ borderRadius: 10, borderLeft: '4px solid #722ed1' }}>
                <Statistic
                  title="Assigned"
                  value={workforceData?.assigned_company_employees ?? 0}
                  styles={{ content: { color: '#722ed1' } }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={6}>
              <Card size="small" style={{ borderRadius: 10, borderLeft: '4px solid #13c2c2' }}>
                <Statistic
                  title="Avg Assignment"
                  value={workforceData?.average_assignment_duration_days ?? 0}
                  suffix="days"
                  styles={{ content: { color: '#13c2c2' } }}
                />
              </Card>
            </Col>
          </Row>

          <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            <Col xs={24} md={10}>
              <Card title="Workforce Distribution" size="small" style={{ borderRadius: 10 }}>
                <SimplePieChart {...pieData} />
              </Card>
            </Col>
            <Col xs={24} md={14}>
              <Card title="Top Assigned Employees" size="small" style={{ borderRadius: 10 }}>
                <SimpleBarChart
                  data={topEmps}
                  valueKey="total_assignments"
                  nameKey="employee_name"
                  color="#722ed1"
                />
              </Card>
            </Col>
          </Row>

          <Card title="Employee Assignment Details" size="small" style={{ borderRadius: 10 }}>
            <Table
              dataSource={topEmps}
              columns={empColumns}
              rowKey="employee_id"
              size="small"
              pagination={{ pageSize: 10 }}
            />
          </Card>
        </>
      ),
    },
    {
      key: 'external',
      label: (
        <Space>
          <DollarOutlined />
          External Workers
        </Space>
      ),
      children: (
        <>
          <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            <Col xs={24} sm={8}>
              <Card size="small" style={{ borderRadius: 10, borderLeft: '4px solid #fa8c16' }}>
                <Statistic
                  title="Total Assignments"
                  value={externalData?.total_external_assignments ?? 0}
                  styles={{ content: { color: '#fa8c16' } }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={8}>
              <Card size="small" style={{ borderRadius: 10, borderLeft: '4px solid #ff4d4f' }}>
                <Statistic
                  title="Currently Active"
                  value={externalData?.active_external_workers ?? 0}
                  styles={{ content: { color: '#ff4d4f' } }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={8}>
              <Card size="small" style={{ borderRadius: 10, borderLeft: '4px solid #52c41a' }}>
                <Statistic
                  title="Total Cost (KD)"
                  value={(externalData?.total_external_cost ?? 0).toLocaleString()}
                  prefix="KD"
                  styles={{ content: { color: '#52c41a' } }}
                />
              </Card>
            </Col>
          </Row>

          <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            <Col xs={24}>
              <Card title="External Labor Cost by Project" size="small" style={{ borderRadius: 10 }}>
                <SimpleBarChart
                  data={perProject}
                  valueKey="total_cost"
                  nameKey="project_code"
                  color="#fa8c16"
                  maxHeight={180}
                />
              </Card>
            </Col>
          </Row>

          <Card title="External Worker Cost Breakdown" size="small" style={{ borderRadius: 10 }}>
            <Table
              dataSource={perProject}
              columns={externalColumns}
              rowKey="project_id"
              size="small"
              pagination={{ pageSize: 10 }}
            />
          </Card>
        </>
      ),
    },
  ];

  return (
    <div style={{ padding: '0 4px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <Title level={3} style={{ margin: 0 }}>
          Project Analytics
        </Title>
        <Button icon={<ReloadOutlined />} onClick={load} size="small">
          Refresh
        </Button>
      </div>

      <Tabs items={tabItems} defaultActiveKey="projects" />
    </div>
  );
};

export default ProjectAnalytics;
