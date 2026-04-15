// src/components/Dashboard/ContractExpiryAlert.jsx
import React from 'react';
import { Alert, Button, Space, Typography } from 'antd';
import { ClockCircleOutlined, WarningOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

const { Text } = Typography;

const ContractExpiryAlert = ({ contract }) => {
  const navigate = useNavigate();

  const isDanger = contract.alert_level === 'danger';
  const type = isDanger ? 'error' : 'warning';

  const message = (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
      <div>
        <Text strong style={{ fontSize: 13 }}>
          {isDanger ? <WarningOutlined style={{ color: '#ff4d4f', marginRight: 6 }} /> : <ClockCircleOutlined style={{ marginRight: 6 }} />}
          {contract.contract_code}
          {contract.contract_name ? ` – ${contract.contract_name}` : ''}
        </Text>
        <br />
        <Text type="secondary" style={{ fontSize: 12 }}>
          {contract.project_name} &nbsp;·&nbsp; Expires: {contract.end_date} &nbsp;·&nbsp;
          <Text strong style={{ color: isDanger ? '#ff4d4f' : '#fa8c16' }}>
            {contract.days_remaining} days remaining
          </Text>
        </Text>
      </div>
      <Space>
        <Button
          size="small"
          type="primary"
          danger={isDanger}
          onClick={() => navigate('/project-workflow')}
        >
          View
        </Button>
      </Space>
    </div>
  );

  return (
    <Alert
      message={message}
      type={type}
      showIcon={false}
      style={{ marginBottom: 8, borderRadius: 8 }}
    />
  );
};

export default ContractExpiryAlert;
