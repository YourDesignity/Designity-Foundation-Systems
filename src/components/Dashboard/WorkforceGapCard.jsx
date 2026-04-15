// src/components/Dashboard/WorkforceGapCard.jsx
import React from 'react';
import { Card, Progress, Button, Typography, Tag } from 'antd';
import { TeamOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

const { Text } = Typography;

const WorkforceGapCard = ({ gap }) => {
  const navigate = useNavigate();
  const fillPct = gap.fill_percentage ?? 0;
  const strokeColor = fillPct < 50 ? '#ff4d4f' : fillPct < 80 ? '#fa8c16' : '#52c41a';

  return (
    <Card
      size="small"
      style={{ borderRadius: 10, marginBottom: 8 }}
      styles={{ body: { padding: '12px 16px' } }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
        <div>
          <Text strong style={{ fontSize: 13 }}>{gap.site_name}</Text>
          <br />
          <Text type="secondary" style={{ fontSize: 11 }}>{gap.project_name}</Text>
        </div>
        <Tag color="red" style={{ fontSize: 11 }}>
          -{gap.gap} workers
        </Tag>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
        <Text style={{ fontSize: 11 }}>
          <TeamOutlined /> {gap.assigned_workers} / {gap.required_workers}
        </Text>
        <Text style={{ fontSize: 11 }}>{fillPct}%</Text>
      </div>

      <Progress
        percent={fillPct}
        size="small"
        showInfo={false}
        strokeColor={strokeColor}
        style={{ marginBottom: 8 }}
      />

      <Button
        size="small"
        type="primary"
        block
        onClick={() => navigate('/workforce-allocation')}
      >
        Assign Workers
      </Button>
    </Card>
  );
};

export default WorkforceGapCard;
