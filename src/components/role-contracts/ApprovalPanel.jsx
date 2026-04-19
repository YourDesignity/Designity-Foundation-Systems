/**
 * ApprovalPanel.jsx
 *
 * Lists pending approvals for the current user.
 * Shows Approve / Reject actions with a comment field,
 * and renders approval history as a timeline.
 */

import React, { useState } from 'react';
import {
  Card, Button, Input, Space, Typography, Avatar, Tag,
  Divider, Empty, Spin, Tooltip, Timeline,
} from 'antd';
import {
  CheckCircleOutlined, CloseCircleOutlined,
  ClockCircleOutlined, UserOutlined,
} from '@ant-design/icons';
import { toast } from 'react-toastify';
import { approveContract, rejectContract } from '../../services/contractService';

const { Text, Paragraph } = Typography;
const { TextArea } = Input;

// ─── Status helpers ───────────────────────────────────────────────────────────

const APPROVAL_STATUS = {
  PENDING: { label: 'Pending', color: 'warning', icon: <ClockCircleOutlined /> },
  APPROVED: { label: 'Approved', color: 'success', icon: <CheckCircleOutlined /> },
  REJECTED: { label: 'Rejected', color: 'error', icon: <CloseCircleOutlined /> },
};

const formatDate = (dt) =>
  dt ? new Date(dt).toLocaleString('en-KW', { dateStyle: 'medium', timeStyle: 'short' }) : '—';

// ─── Single approval item ─────────────────────────────────────────────────────

const ApprovalItem = ({ approval, contractId, onActionComplete }) => {
  const [comment, setComment] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const isPending = approval.status === 'PENDING';
  const config = APPROVAL_STATUS[approval.status] || APPROVAL_STATUS.PENDING;

  const handleApprove = async () => {
    setSubmitting(true);
    try {
      await approveContract(contractId, comment);
      toast.success('Contract approved successfully');
      onActionComplete?.();
    } catch {
      toast.error('Failed to approve contract');
    } finally {
      setSubmitting(false);
    }
  };

  const handleReject = async () => {
    if (!comment.trim()) {
      toast.warning('Please provide a reason for rejection');
      return;
    }
    setSubmitting(true);
    try {
      await rejectContract(contractId, comment);
      toast.success('Contract rejected');
      onActionComplete?.();
    } catch {
      toast.error('Failed to reject contract');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className={`approval-item ${approval.status?.toLowerCase() || 'pending'}`}>
      <Space align="start" style={{ width: '100%' }}>
        <Avatar icon={<UserOutlined />} size={36} style={{ flexShrink: 0, background: '#1890ff' }} />
        <div style={{ flex: 1 }}>
          <Space style={{ marginBottom: 4 }} wrap>
            <Text strong>{approval.approver_name || `Approver #${approval.approver_id}`}</Text>
            <Tag color={config.color} icon={config.icon} style={{ fontWeight: 600 }}>
              {config.label}
            </Tag>
          </Space>
          <div style={{ fontSize: 12, color: '#888', marginBottom: 6 }}>
            Requested: {formatDate(approval.requested_at)}
            {approval.resolved_at && (
              <> · Resolved: {formatDate(approval.resolved_at)}</>
            )}
          </div>
          {approval.comment && (
            <Paragraph
              style={{ fontSize: 13, margin: '4px 0', background: '#f9f9f9', padding: '8px 12px', borderRadius: 6 }}
            >
              {approval.comment}
            </Paragraph>
          )}

          {isPending && (
            <Space direction="vertical" style={{ width: '100%', marginTop: 12 }} size={8}>
              <TextArea
                rows={2}
                placeholder="Add a comment (required for rejection)…"
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                maxLength={500}
              />
              <Space>
                <Button
                  type="primary"
                  icon={<CheckCircleOutlined />}
                  onClick={handleApprove}
                  loading={submitting}
                  size="small"
                >
                  Approve
                </Button>
                <Button
                  danger
                  icon={<CloseCircleOutlined />}
                  onClick={handleReject}
                  loading={submitting}
                  size="small"
                >
                  Reject
                </Button>
              </Space>
            </Space>
          )}
        </div>
      </Space>
    </div>
  );
};

// ─── Approval history timeline ────────────────────────────────────────────────

export const ApprovalHistoryTimeline = ({ history = [] }) => {
  if (!history.length) {
    return <Empty description="No approval history" image={Empty.PRESENTED_IMAGE_SIMPLE} />;
  }

  const items = history.map((entry) => {
    const config = APPROVAL_STATUS[entry.status] || APPROVAL_STATUS.PENDING;
    return {
      color: entry.status === 'APPROVED' ? 'green' : entry.status === 'REJECTED' ? 'red' : 'blue',
      dot: config.icon,
      children: (
        <div>
          <Space wrap style={{ marginBottom: 2 }}>
            <Text strong style={{ fontSize: 13 }}>
              {entry.approver_name || `Approver #${entry.approver_id}`}
            </Text>
            <Tag color={config.color}>{config.label}</Tag>
          </Space>
          <div style={{ fontSize: 12, color: '#888' }}>{formatDate(entry.resolved_at || entry.requested_at)}</div>
          {entry.comment && (
            <Paragraph style={{ fontSize: 12, margin: '4px 0', color: '#555' }}>
              {entry.comment}
            </Paragraph>
          )}
        </div>
      ),
    };
  });

  return <Timeline items={items} style={{ paddingTop: 12 }} />;
};

// ─── Main ApprovalPanel ───────────────────────────────────────────────────────

const ApprovalPanel = ({
  approvals = [],
  history = [],
  contractId,
  loading = false,
  onActionComplete,
}) => {
  const pendingApprovals = approvals.filter((a) => a.status === 'PENDING');

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 40 }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div className="approval-panel">
      {pendingApprovals.length > 0 ? (
        <>
          <Text strong style={{ fontSize: 14, display: 'block', marginBottom: 12 }}>
            Pending Approvals ({pendingApprovals.length})
          </Text>
          {pendingApprovals.map((approval, index) => (
            <ApprovalItem
              key={approval._id || approval.uid || index}
              approval={approval}
              contractId={contractId}
              onActionComplete={onActionComplete}
            />
          ))}
        </>
      ) : (
        <Empty
          description="No pending approvals"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          style={{ marginBottom: 24 }}
        />
      )}

      {history.length > 0 && (
        <>
          <Divider style={{ margin: '24px 0 16px' }}>Approval History</Divider>
          <ApprovalHistoryTimeline history={history} />
        </>
      )}
    </div>
  );
};

export default ApprovalPanel;
