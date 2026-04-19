// src/pages/WorkforceDashboard.jsx
// Phase 6: Dedicated Workforce Allocation Page

import React, { useState, useEffect, useCallback } from 'react';
import {
  Row, Col, Card, Typography, Spin, Empty, Input, Select,
  Tag, Statistic, Progress, Alert, Button, Space,
} from 'antd';
import {
  SearchOutlined, TeamOutlined, UserOutlined,
  ReloadOutlined, ApartmentOutlined,
} from '@ant-design/icons';
import { workforceService } from '../services';
import WorkforceAllocationCard from '../components/Dashboard/WorkforceAllocationCard.jsx';

const { Title, Text } = Typography;
const { Option } = Select;

const WorkforceDashboard = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [designationFilter, setDesignationFilter] = useState('all');

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await workforceService.getAllocation();
      setData(res);
    } catch (err) {
      setError(err.message || 'Failed to load workforce data');
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
        <Spin size="large" description="Loading workforce data..." />
      </div>
    );
  }

  if (error) {
    return (
      <Alert
        type="error"
        title="Error"
        description={error}
        action={<Button onClick={load} icon={<ReloadOutlined />}>Retry</Button>}
        style={{ margin: 24 }}
      />
    );
  }

  const available = data?.available_employees ?? [];
  const projectMap = data?.assignments_by_project ?? {};
  const external = data?.external_workers ?? [];
  const summary = data?.summary ?? {};

  // Unique designations for filter
  const designations = [...new Set(available.map((e) => e.designation).filter(Boolean))];

  const filteredAvailable = available.filter((e) => {
    const matchSearch = !search || e.name.toLowerCase().includes(search.toLowerCase());
    const matchDes = designationFilter === 'all' || e.designation === designationFilter;
    return matchSearch && matchDes;
  });

  return (
    <div style={{ padding: '0 4px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <Title level={3} style={{ margin: 0 }}>
          👥 Workforce Allocation
        </Title>
        <Button icon={<ReloadOutlined />} onClick={load} size="small">
          Refresh
        </Button>
      </div>

      {/* Summary Stats */}
      <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
        <Col xs={12} sm={6}>
          <Card size="small" style={{ borderRadius: 10, borderLeft: '4px solid #52c41a' }}>
            <Statistic
              title="Available"
              value={summary.available_company_employees ?? 0}
              prefix={<UserOutlined style={{ color: '#52c41a' }} />}
              styles={{ content: { color: '#52c41a', fontSize: 22 } }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small" style={{ borderRadius: 10, borderLeft: '4px solid #1677ff' }}>
            <Statistic
              title="Assigned"
              value={summary.assigned_company_employees ?? 0}
              prefix={<TeamOutlined style={{ color: '#1677ff' }} />}
              styles={{ content: { color: '#1677ff', fontSize: 22 } }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small" style={{ borderRadius: 10, borderLeft: '4px solid #fa8c16' }}>
            <Statistic
              title="External"
              value={summary.active_external_workers ?? 0}
              prefix={<UserOutlined style={{ color: '#fa8c16' }} />}
              styles={{ content: { color: '#fa8c16', fontSize: 22 } }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small" style={{ borderRadius: 10, borderLeft: '4px solid #13c2c2' }}>
            <Statistic
              title="Utilization"
              value={summary.utilization_percentage ?? 0}
              suffix="%"
              styles={{ content: { color: '#13c2c2', fontSize: 22 } }}
            />
            <Progress
              percent={summary.utilization_percentage ?? 0}
              size="small"
              showInfo={false}
              strokeColor="#13c2c2"
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        {/* Left: Available Employees */}
        <Col xs={24} md={8}>
          <Card
            title={
              <Space>
                <UserOutlined style={{ color: '#52c41a' }} />
                <span>Available Pool</span>
                <Tag color="green">{filteredAvailable.length}</Tag>
              </Space>
            }
            size="small"
            style={{ borderRadius: 10 }}
            extra={
              <Space>
                <Input
                  size="small"
                  placeholder="Search..."
                  prefix={<SearchOutlined />}
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  style={{ width: 120 }}
                />
                <Select
                  size="small"
                  value={designationFilter}
                  onChange={setDesignationFilter}
                  style={{ width: 110 }}
                >
                  <Option value="all">All</Option>
                  {designations.map((d) => (
                    <Option key={d} value={d}>{d}</Option>
                  ))}
                </Select>
              </Space>
            }
          >
            <div style={{ maxHeight: 500, overflowY: 'auto' }}>
              {filteredAvailable.length === 0 ? (
                <Empty description="No available employees" styles={{ image: { height: 40 } }} />
              ) : (
                filteredAvailable.map((emp) => (
                  <WorkforceAllocationCard key={emp.employee_id} employee={emp} />
                ))
              )}
            </div>
          </Card>
        </Col>

        {/* Right: Projects/Sites */}
        <Col xs={24} md={16}>
          <Card
            title={
              <Space>
                <ApartmentOutlined style={{ color: '#722ed1' }} />
                <span>Projects & Sites</span>
              </Space>
            }
            size="small"
            style={{ borderRadius: 10 }}
          >
            {Object.keys(projectMap).length === 0 ? (
              <Empty description="No active project assignments" styles={{ image: { height: 40 } }} />
            ) : (
              <div style={{ maxHeight: 520, overflowY: 'auto' }}>
                {Object.values(projectMap).map((proj) => (
                  <Card
                    key={proj.project_id}
                    size="small"
                    style={{ borderRadius: 8, marginBottom: 12, background: '#fafafa' }}
                    title={
                      <Space>
                        <Text strong>{proj.project_code}</Text>
                        <Text type="secondary" style={{ fontSize: 12 }}>{proj.project_name}</Text>
                        <Tag color="blue">{proj.total_assigned} workers</Tag>
                      </Space>
                    }
                  >
                    <Row gutter={[8, 8]}>
                      {(proj.sites ?? []).map((site) => (
                        <Col key={site.site_id} xs={24} sm={12}>
                          <Card
                            size="small"
                            style={{ borderRadius: 6, border: '1px solid #e8e8e8' }}
                            styles={{ body: { padding: '8px 12px' } }}
                          >
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                              <Text strong style={{ fontSize: 12 }}>{site.site_name}</Text>
                              <Tag color={site.fill_pct >= 100 ? 'green' : 'orange'} style={{ fontSize: 10 }}>
                                {site.assigned_workers}/{site.required_workers}
                              </Tag>
                            </div>
                            <Progress
                              percent={Math.min(site.fill_pct, 100)}
                              size="small"
                              showInfo={false}
                              strokeColor={site.fill_pct >= 100 ? '#52c41a' : '#fa8c16'}
                            />
                            {(site.employees ?? []).slice(0, 3).map((emp) => (
                              <div key={emp.assignment_id} style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 4 }}>
                                <UserOutlined style={{ fontSize: 11, color: '#888' }} />
                                <Text style={{ fontSize: 11 }}>{emp.employee_name}</Text>
                                <Text type="secondary" style={{ fontSize: 10 }}>{emp.designation}</Text>
                              </div>
                            ))}
                            {(site.employees ?? []).length > 3 && (
                              <Text type="secondary" style={{ fontSize: 11 }}>
                                +{site.employees.length - 3} more
                              </Text>
                            )}
                          </Card>
                        </Col>
                      ))}
                    </Row>
                  </Card>
                ))}
              </div>
            )}
          </Card>

          {/* External Workers */}
          {external.length > 0 && (
            <Card
              title={
                <Space>
                  <UserOutlined style={{ color: '#fa8c16' }} />
                  <span>Active External Workers</span>
                  <Tag color="orange">{external.length}</Tag>
                </Space>
              }
              size="small"
              style={{ borderRadius: 10, marginTop: 16 }}
            >
              <Row gutter={[8, 8]}>
                {external.map((t) => (
                  <Col key={t.assignment_id} xs={24} sm={12} md={8}>
                    <Card
                      size="small"
                      style={{ borderRadius: 8, background: '#fff7e6', border: '1px solid #ffd591' }}
                      styles={{ body: { padding: '8px 12px' } }}
                    >
                      <Text strong style={{ fontSize: 12 }}>{t.employee_name}</Text>
                      <br />
                      <Text type="secondary" style={{ fontSize: 11 }}>{t.designation}</Text>
                      <br />
                      <Text style={{ fontSize: 11, color: '#fa8c16' }}>📍 {t.site_name}</Text>
                      <br />
                      <Text type="secondary" style={{ fontSize: 10 }}>
                        {t.start_date} → {t.end_date}
                      </Text>
                    </Card>
                  </Col>
                ))}
              </Row>
            </Card>
          )}
        </Col>
      </Row>
    </div>
  );
};

export default WorkforceDashboard;
