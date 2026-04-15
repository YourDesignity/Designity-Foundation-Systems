// src/components/Dashboard/QuickActionButton.jsx
import React from 'react';
import { Card, Typography } from 'antd';

const { Text } = Typography;

const QuickActionButton = ({ icon, label, description, onClick, color = '#52c41a' }) => (
  <Card
    hoverable
    onClick={onClick}
    style={{
      textAlign: 'center',
      cursor: 'pointer',
      borderRadius: 12,
      border: `1px solid ${color}22`,
      transition: 'all 0.2s',
    }}
    styles={{ body: { padding: '20px 12px' } }}
  >
    <div
      style={{
        fontSize: 28,
        color,
        marginBottom: 8,
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
      }}
    >
      {icon}
    </div>
    <Text strong style={{ display: 'block', fontSize: 13, color: '#262626' }}>
      {label}
    </Text>
    {description && (
      <Text type="secondary" style={{ fontSize: 11 }}>
        {description}
      </Text>
    )}
  </Card>
);

export default QuickActionButton;
