import React from 'react';
import { Alert, Badge, Space } from 'antd';

const UnfilledSlotsAlert = ({ count = 0 }) => {
  if (!count) return null;
  return (
    <Alert
      type="warning"
      showIcon
      title={
        <Space>
          <span>Unfilled role slots detected</span>
          <Badge count={count} style={{ backgroundColor: '#EF4444' }} />
        </Space>
      }
      description="Please record fulfillment or assign replacements to reduce shortages."
    />
  );
};

export default UnfilledSlotsAlert;
