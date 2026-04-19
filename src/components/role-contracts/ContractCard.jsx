/**
 * ContractCard.jsx
 *
 * Card component for displaying a contract summary in grid/list views.
 * Shows key metadata, workflow state badge, and enabled module badges.
 */

import React from 'react';
import { Card, Tag, Space, Typography, Tooltip, Progress } from 'antd';
import {
  CalendarOutlined, DollarOutlined, ProjectOutlined,
  TeamOutlined, CarOutlined, ShoppingOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { WorkflowStateBadge, ModuleBadges } from './WorkflowStatus';

const { Text, Paragraph } = Typography;

const TYPE_COLORS = {
  Labour: 'blue',
  'Goods Supply': 'orange',
  'Equipment Rental': 'purple',
  'Role-Based': 'cyan',
  Hybrid: 'magenta',
};

const formatDate = (dt) => {
  if (!dt) return '—';
  try {
    return new Date(dt).toLocaleDateString('en-KW', { day: '2-digit', month: 'short', year: 'numeric' });
  } catch {
    return dt;
  }
};

const formatCurrency = (amount) =>
  typeof amount === 'number'
    ? `KD ${amount.toLocaleString('en-KW', { minimumFractionDigits: 2 })}`
    : '—';

const ContractCard = ({ contract, onClick }) => {
  const navigate = useNavigate();

  const handleClick = () => {
    if (onClick) {
      onClick(contract);
    } else {
      navigate(`/contracts/${contract.uid}`);
    }
  };

  const daysRemaining = contract.days_remaining || 0;
  const durationDays = contract.duration_days || 1;
  const progressPercent = Math.max(
    0,
    Math.min(100, Math.round(((durationDays - daysRemaining) / durationDays) * 100))
  );

  return (
    <Card
      className="contract-card"
      onClick={handleClick}
      hoverable
      size="small"
    >
      <div className="card-header">
        <div style={{ flex: 1 }}>
          <div className="card-code">{contract.contract_code}</div>
          <div className="card-title">
            {contract.contract_name || contract.contract_code}
          </div>
        </div>
        <WorkflowStateBadge state={contract.workflow_state} />
      </div>

      <div className="card-meta">
        {contract.project_name && (
          <Tooltip title="Project">
            <Text style={{ fontSize: 12 }}>
              <ProjectOutlined style={{ marginRight: 4 }} />
              {contract.project_name}
            </Text>
          </Tooltip>
        )}
        {contract.client_name && (
          <Tooltip title="Client">
            <Text style={{ fontSize: 12, color: '#888' }}>
              {contract.client_name}
            </Text>
          </Tooltip>
        )}
      </div>

      <Space wrap size={4} style={{ marginBottom: 10 }}>
        <Tag color={TYPE_COLORS[contract.contract_type] || 'default'} style={{ fontSize: 11 }}>
          {contract.contract_type}
        </Tag>
        {contract.is_expiring_soon && daysRemaining > 0 && (
          <Tag color="warning" style={{ fontSize: 11 }}>
            Expires in {daysRemaining}d
          </Tag>
        )}
      </Space>

      <Space direction="vertical" size={4} style={{ width: '100%', marginBottom: 10 }}>
        <Space size={16}>
          <Tooltip title="Start – End dates">
            <Text style={{ fontSize: 11, color: '#888' }}>
              <CalendarOutlined style={{ marginRight: 3 }} />
              {formatDate(contract.start_date)} – {formatDate(contract.end_date)}
            </Text>
          </Tooltip>
          {contract.contract_value > 0 && (
            <Tooltip title="Contract value">
              <Text style={{ fontSize: 11, color: '#888' }}>
                <DollarOutlined style={{ marginRight: 3 }} />
                {formatCurrency(contract.contract_value)}
              </Text>
            </Tooltip>
          )}
        </Space>
      </Space>

      {durationDays > 1 && (
        <div style={{ marginBottom: 10 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
            <Text style={{ fontSize: 11, color: '#888' }}>Progress</Text>
            <Text style={{ fontSize: 11, color: '#888' }}>{progressPercent}%</Text>
          </div>
          <Progress percent={progressPercent} size="small" showInfo={false} />
        </div>
      )}

      <div className="module-badges">
        <ModuleBadges modules={contract.enabled_modules || []} />
      </div>
    </Card>
  );
};

export default ContractCard;
