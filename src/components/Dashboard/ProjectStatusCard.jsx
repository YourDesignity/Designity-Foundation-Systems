// src/components/Dashboard/ProjectStatusCard.jsx
import React from 'react';
import { Card, Tag, Progress, Button, Space, Typography, Tooltip } from 'antd';
import {
  ProjectOutlined,
  TeamOutlined,
  ClockCircleOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

const { Text, Title } = Typography;

const ProjectStatusCard = ({ project }) => {
  const navigate = useNavigate();

  const statusColor = {
    Active: 'green',
    Completed: 'blue',
    'On Hold': 'orange',
    Cancelled: 'red',
  }[project.status] || 'default';

  const expiryColor =
    project.days_to_expiry <= 7
      ? '#ff4d4f'
      : project.days_to_expiry <= 30
      ? '#fa8c16'
      : '#52c41a';

  const completionPct = project.total_sites
    ? Math.round((project.completed_sites / project.total_sites) * 100)
    : 0;

  return (
    <Card
      size="small"
      style={{ borderRadius: 10, height: '100%' }}
      styles={{ body: { padding: 16 } }}
    >
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
        <div>
          <Text type="secondary" style={{ fontSize: 11 }}>
            {project.project_code}
          </Text>
          <Title level={5} style={{ margin: 0, fontSize: 14 }}>
            {project.project_name}
          </Title>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {project.client_name}
          </Text>
        </div>
        <Tag color={statusColor}>{project.status}</Tag>
      </div>

      {/* Progress */}
      <div style={{ marginBottom: 8 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
          <Text style={{ fontSize: 11 }}>
            <ProjectOutlined /> Sites: {project.completed_sites ?? 0}/{project.total_sites ?? 0}
          </Text>
          <Text style={{ fontSize: 11 }}>{completionPct}%</Text>
        </div>
        <Progress percent={completionPct} size="small" showInfo={false} strokeColor="#52c41a" />
      </div>

      {/* Workforce */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 8, flexWrap: 'wrap' }}>
        <Text style={{ fontSize: 11 }}>
          <TeamOutlined /> Workers: {project.permanent_workers ?? project.total_assigned_employees ?? 0}
        </Text>
        {project.active_external_workers > 0 && (
          <Text style={{ fontSize: 11, color: '#fa8c16' }}>
            +{project.active_external_workers} ext
          </Text>
        )}
      </div>

      {/* Contract Expiry */}
      {project.days_to_expiry !== null && project.days_to_expiry !== undefined && (
        <div style={{ marginBottom: 10 }}>
          <Text style={{ fontSize: 11, color: expiryColor }}>
            <ClockCircleOutlined /> Contract: {project.days_to_expiry} days left
          </Text>
        </div>
      )}

      {/* Actions */}
      <Space>
        <Button
          size="small"
          icon={<EyeOutlined />}
          onClick={() => navigate('/project-workflow')}
        >
          View
        </Button>
      </Space>
    </Card>
  );
};

export default ProjectStatusCard;
