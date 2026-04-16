import React from 'react';
import { Card, Tag, Space, Progress, Typography } from 'antd';

const { Text } = Typography;

const getStatus = (filled = 0, total = 0) => {
  if (!total) return { label: 'Unfilled', color: '#EF4444', percent: 0 };
  const percent = Math.round((filled / total) * 100);
  if (percent === 100) return { label: 'Fully Filled', color: '#10B981', percent };
  if (percent >= 60) return { label: 'Partially Filled', color: '#F59E0B', percent };
  return { label: 'Unfilled', color: '#EF4444', percent };
};

const ContractRoleCard = ({ contract, filledSlots = 0, siteName = '—' }) => {
  const status = getStatus(filledSlots, contract?.total_role_slots || 0);

  return (
    <Card hoverable>
      <Space orientation="vertical" size={8} style={{ width: '100%' }}>
        <Space style={{ justifyContent: 'space-between', width: '100%' }}>
          <Text strong>{contract.contract_code}</Text>
          <Tag color={status.color}>{status.label}</Tag>
        </Space>
        <Text type="secondary">Site: {siteName}</Text>
        <Text type="secondary">Slots: {filledSlots}/{contract.total_role_slots || 0}</Text>
        <Progress
          percent={status.percent}
          size="small"
          strokeColor={status.color}
          status="active"
        />
        <Text>Total Daily Cost: KD {Number(contract.total_daily_cost || 0).toFixed(2)}</Text>
      </Space>
    </Card>
  );
};

export default ContractRoleCard;
