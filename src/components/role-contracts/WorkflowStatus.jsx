/**
 * WorkflowStatus.jsx
 *
 * Visual representation of the contract workflow state machine.
 * Displays the current state with a progress bar / step indicator,
 * and shows the next available actions.
 */

import React from 'react';
import { Steps, Tag, Space, Typography, Tooltip } from 'antd';
import {
  EditOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  PauseCircleOutlined,
  FileTextOutlined,
} from '@ant-design/icons';

const { Text } = Typography;

// ─── Constants ───────────────────────────────────────────────────────────────

const WORKFLOW_STATES = [
  { key: 'DRAFT', label: 'Draft', icon: <EditOutlined /> },
  { key: 'PENDING_APPROVAL', label: 'Pending Approval', icon: <ClockCircleOutlined /> },
  { key: 'ACTIVE', label: 'Active', icon: <CheckCircleOutlined /> },
  { key: 'COMPLETED', label: 'Completed', icon: <FileTextOutlined /> },
];

const STATE_CONFIG = {
  DRAFT: { color: 'default', tagColor: '#666', bg: '#f0f0f0' },
  PENDING_APPROVAL: { color: 'warning', tagColor: '#d46b08', bg: '#fff7e6' },
  ACTIVE: { color: 'success', tagColor: '#389e0d', bg: '#f6ffed' },
  SUSPENDED: { color: 'error', tagColor: '#cf1322', bg: '#fff0f0' },
  COMPLETED: { color: 'processing', tagColor: '#096dd9', bg: '#e6f7ff' },
  CANCELLED: { color: 'error', tagColor: '#a8071a', bg: '#fff1f0' },
};

const NEXT_ACTIONS = {
  DRAFT: ['Submit for Approval', 'Cancel'],
  PENDING_APPROVAL: ['Approve', 'Reject'],
  ACTIVE: ['Complete', 'Suspend', 'Cancel'],
  SUSPENDED: ['Reactivate', 'Cancel'],
  COMPLETED: [],
  CANCELLED: [],
};

// ─── Helpers ─────────────────────────────────────────────────────────────────

const getStepStatus = (stepKey, currentState) => {
  const stepIndex = WORKFLOW_STATES.findIndex((s) => s.key === stepKey);
  const currentIndex = WORKFLOW_STATES.findIndex((s) => s.key === currentState);

  if (currentState === 'CANCELLED' || currentState === 'SUSPENDED') {
    return stepIndex <= currentIndex - 1 ? 'finish' : 'wait';
  }
  if (stepIndex < currentIndex) return 'finish';
  if (stepIndex === currentIndex) return 'process';
  return 'wait';
};

const getStepIndex = (state) => {
  if (state === 'CANCELLED' || state === 'SUSPENDED') return -1;
  return WORKFLOW_STATES.findIndex((s) => s.key === state);
};

// ─── Components ──────────────────────────────────────────────────────────────

/**
 * Compact badge showing just the current state.
 */
export const WorkflowStateBadge = ({ state, size = 'small' }) => {
  const config = STATE_CONFIG[state] || STATE_CONFIG.DRAFT;
  return (
    <Tag
      color={config.color}
      style={{
        fontWeight: 600,
        fontSize: size === 'small' ? 11 : 13,
        textTransform: 'uppercase',
        letterSpacing: '0.4px',
      }}
    >
      {state?.replace('_', ' ') || 'DRAFT'}
    </Tag>
  );
};

/**
 * Module badges row.
 */
export const ModuleBadges = ({ modules = [] }) => {
  if (!modules.length) return <Text type="secondary" style={{ fontSize: 12 }}>No modules</Text>;
  return (
    <Space size={4} wrap>
      {modules.map((mod) => (
        <Tag
          key={mod}
          style={{ fontSize: 11, fontWeight: 600, textTransform: 'capitalize' }}
          color={mod === 'employee' ? 'blue' : mod === 'inventory' ? 'orange' : 'purple'}
        >
          {mod}
        </Tag>
      ))}
    </Space>
  );
};

/**
 * Full workflow steps bar showing all states.
 */
const WorkflowStatus = ({ state = 'DRAFT', compact = false }) => {
  const currentIndex = getStepIndex(state);
  const isCancelled = state === 'CANCELLED';
  const isSuspended = state === 'SUSPENDED';

  const items = WORKFLOW_STATES.map((s) => ({
    title: s.label,
    icon: s.icon,
    status: getStepStatus(s.key, state),
  }));

  if (compact) {
    return (
      <Space size={8} align="center" wrap>
        <WorkflowStateBadge state={state} />
        {NEXT_ACTIONS[state]?.length > 0 && (
          <Text type="secondary" style={{ fontSize: 12 }}>
            → Next: {NEXT_ACTIONS[state].join(' or ')}
          </Text>
        )}
      </Space>
    );
  }

  return (
    <div className="workflow-steps-bar">
      {(isCancelled || isSuspended) && (
        <div style={{ marginBottom: 12 }}>
          <Tag
            icon={isCancelled ? <CloseCircleOutlined /> : <PauseCircleOutlined />}
            color={isCancelled ? 'error' : 'warning'}
            style={{ fontWeight: 600, fontSize: 13 }}
          >
            Contract is {state.replace('_', ' ')}
          </Tag>
        </div>
      )}
      <Steps
        size="small"
        current={currentIndex}
        status={isCancelled ? 'error' : isSuspended ? 'error' : 'process'}
        items={items}
      />
    </div>
  );
};

export default WorkflowStatus;
