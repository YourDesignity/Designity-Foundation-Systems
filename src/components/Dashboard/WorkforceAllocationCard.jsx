// src/components/Dashboard/WorkforceAllocationCard.jsx
import React from 'react';
import { Card, Avatar, Tag, Button, Typography } from 'antd';
import { UserOutlined, CheckCircleOutlined } from '@ant-design/icons';

const { Text } = Typography;

const WorkforceAllocationCard = ({ employee, onAssign }) => {
  const isAssigned = employee.is_currently_assigned || employee.availability_status === 'Assigned';
  const tagColor = isAssigned ? 'blue' : 'green';
  const tagText = isAssigned ? 'Assigned' : 'Available';

  return (
    <Card
      size="small"
      style={{ borderRadius: 10, marginBottom: 8 }}
      styles={{ body: { padding: '10px 14px' } }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <Avatar
          size={36}
          src={employee.photo_path ? `http://127.0.0.1:8000/static/${employee.photo_path}` : undefined}
          icon={<UserOutlined />}
          style={{ flexShrink: 0 }}
        />
        <div style={{ flex: 1, minWidth: 0 }}>
          <Text strong style={{ fontSize: 13, display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {employee.name}
          </Text>
          <Text type="secondary" style={{ fontSize: 11 }}>
            {employee.designation}
          </Text>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4 }}>
          <Tag color={tagColor} style={{ margin: 0, fontSize: 10 }}>
            {tagText}
          </Tag>
          {!isAssigned && onAssign && (
            <Button size="small" type="primary" ghost onClick={() => onAssign(employee)}>
              Assign
            </Button>
          )}
        </div>
      </div>
    </Card>
  );
};

export default WorkforceAllocationCard;
