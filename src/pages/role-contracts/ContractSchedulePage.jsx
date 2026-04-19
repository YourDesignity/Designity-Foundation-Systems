/**
 * ContractSchedulePage.jsx
 *
 * Calendar / list view of scheduled tasks and automation jobs for a contract.
 * Allows creating, editing, and enabling/disabling automations.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Row, Col, Card, Table, Tag, Button, Space, Typography, Breadcrumb,
  Spin, message, Badge, Tabs, Divider, Switch,
} from 'antd';
import {
  ArrowLeftOutlined, PlusOutlined, ReloadOutlined,
  ThunderboltOutlined, CalendarOutlined, ClockCircleOutlined,
} from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import AutomationConfigModal from '../../components/role-contracts/AutomationConfigModal';
import {
  getContractById, getScheduledTasks, getAutomations,
} from '../../services/contractService';
import '../../styles/contract-pages.css';

const { Title, Text } = Typography;

const JOB_TYPE_LABELS = {
  CONTRACT_ACTIVATION: 'Contract Activation',
  EXPIRY_WARNING: 'Expiry Warning',
  AUTO_COMPLETION: 'Auto Completion',
  RENEWAL_REQUEST: 'Renewal Request',
  PAYMENT_REMINDER: 'Payment Reminder',
  STATUS_CHANGE: 'Status Change',
};

const JOB_STATUS_COLOR = {
  PENDING: 'default',
  SCHEDULED: 'processing',
  RUNNING: 'blue',
  COMPLETED: 'success',
  FAILED: 'error',
  CANCELLED: 'default',
};

const formatDateTime = (dt) => {
  if (!dt) return '—';
  try {
    return new Date(dt).toLocaleString('en-KW', { dateStyle: 'medium', timeStyle: 'short' });
  } catch {
    return dt;
  }
};

const ContractSchedulePage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const canManage = ['SuperAdmin', 'Admin'].includes(user?.role);

  const [contract, setContract] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [automations, setAutomations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [automationModalOpen, setAutomationModalOpen] = useState(false);
  const [selectedAutomation, setSelectedAutomation] = useState(null);

  const fetchData = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      const [contractData, tasksData, automationsData] = await Promise.all([
        getContractById(id),
        getScheduledTasks(id).catch(() => []),
        getAutomations(id).catch(() => []),
      ]);

      setContract(contractData?.contract || contractData);
      setTasks(Array.isArray(tasksData) ? tasksData : tasksData?.jobs || []);
      setAutomations(Array.isArray(automationsData) ? automationsData : automationsData?.automations || []);
    } catch {
      message.error('Failed to load schedule data');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const taskColumns = [
    {
      title: 'Job Type',
      dataIndex: 'job_type',
      key: 'job_type',
      render: (v) => JOB_TYPE_LABELS[v] || v,
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (s) => <Tag color={JOB_STATUS_COLOR[s] || 'default'}>{s}</Tag>,
    },
    {
      title: 'Scheduled At',
      dataIndex: 'scheduled_at',
      key: 'scheduled_at',
      width: 180,
      render: formatDateTime,
    },
    {
      title: 'Executed At',
      dataIndex: 'executed_at',
      key: 'executed_at',
      width: 180,
      render: formatDateTime,
    },
    {
      title: 'Retry Count',
      dataIndex: 'retry_count',
      key: 'retry_count',
      width: 100,
      align: 'center',
      render: (v) => v || 0,
    },
    {
      title: 'Message',
      dataIndex: 'message',
      key: 'message',
      ellipsis: true,
      render: (v) => v || '—',
    },
  ];

  const automationColumns = [
    {
      title: 'Trigger',
      dataIndex: 'trigger',
      key: 'trigger',
      render: (v) => <Text code style={{ fontSize: 12 }}>{v}</Text>,
    },
    {
      title: 'Action',
      dataIndex: 'action',
      key: 'action',
    },
    {
      title: 'Description',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: 'Enabled',
      dataIndex: 'is_enabled',
      key: 'is_enabled',
      width: 90,
      render: (v) => <Switch checked={!!v} size="small" disabled={!canManage} />,
    },
    canManage && {
      title: 'Actions',
      key: 'actions',
      width: 80,
      render: (_, record) => (
        <Button
          type="link"
          size="small"
          onClick={() => {
            setSelectedAutomation(record);
            setAutomationModalOpen(true);
          }}
        >
          Edit
        </Button>
      ),
    },
  ].filter(Boolean);

  // Stats
  const pending = tasks.filter((t) => ['PENDING', 'SCHEDULED'].includes(t.status)).length;
  const completed = tasks.filter((t) => t.status === 'COMPLETED').length;
  const failed = tasks.filter((t) => t.status === 'FAILED').length;

  const tabItems = [
    {
      key: 'jobs',
      label: (
        <Space>
          <ClockCircleOutlined />
          Scheduled Jobs
          {pending > 0 && <Badge count={pending} size="small" />}
        </Space>
      ),
      children: (
        <Table
          dataSource={tasks}
          columns={taskColumns}
          rowKey={(r) => r._id || r.uid || Math.random()}
          size="small"
          pagination={{ pageSize: 15 }}
          locale={{ emptyText: 'No scheduled jobs' }}
        />
      ),
    },
    {
      key: 'automations',
      label: (
        <Space>
          <ThunderboltOutlined />
          Automations
        </Space>
      ),
      children: (
        <div>
          {canManage && (
            <div style={{ marginBottom: 12 }}>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => {
                  setSelectedAutomation(null);
                  setAutomationModalOpen(true);
                }}
              >
                Create Automation
              </Button>
            </div>
          )}
          <Table
            dataSource={automations}
            columns={automationColumns}
            rowKey={(r) => r._id || r.uid || Math.random()}
            size="small"
            locale={{ emptyText: 'No automation rules configured' }}
          />
        </div>
      ),
    },
  ];

  return (
    <div className="contract-page">
      <Breadcrumb
        items={[
          { title: 'Home' },
          { title: <a onClick={() => navigate('/contracts')}>Contracts</a> },
          {
            title: (
              <a onClick={() => navigate(`/contracts/${id}`)}>
                {contract?.contract_code || id}
              </a>
            ),
          },
          { title: 'Schedule' },
        ]}
        style={{ marginBottom: 12 }}
      />

      <div className="page-header">
        <Row justify="space-between" align="middle">
          <Col>
            <Space>
              <Button
                icon={<ArrowLeftOutlined />}
                onClick={() => navigate(`/contracts/${id}`)}
              />
              <div>
                <div className="page-title">
                  Schedule — {contract?.contract_name || contract?.contract_code || id}
                </div>
                <div className="page-subtitle">
                  Scheduled jobs and automation rules for this contract
                </div>
              </div>
            </Space>
          </Col>
          <Col>
            <Button icon={<ReloadOutlined />} onClick={fetchData} loading={loading}>
              Refresh
            </Button>
          </Col>
        </Row>
      </div>

      {/* Stats */}
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        {[
          { label: 'Pending / Scheduled', value: pending, color: '#1890ff' },
          { label: 'Completed', value: completed, color: '#52c41a' },
          { label: 'Failed', value: failed, color: '#ff4d4f' },
          { label: 'Automations', value: automations.length, color: '#722ed1' },
        ].map(({ label, value, color }) => (
          <Col key={label} xs={12} sm={6}>
            <Card size="small">
              <Text style={{ fontSize: 12, color: '#888' }}>{label}</Text>
              <div style={{ fontSize: 22, fontWeight: 700, color }}>{value}</div>
            </Card>
          </Col>
        ))}
      </Row>

      <Spin spinning={loading}>
        <Card>
          <Tabs items={tabItems} />
        </Card>
      </Spin>

      <AutomationConfigModal
        open={automationModalOpen}
        contractId={id}
        automation={selectedAutomation}
        onClose={() => {
          setAutomationModalOpen(false);
          setSelectedAutomation(null);
        }}
        onSuccess={fetchData}
      />
    </div>
  );
};

export default ContractSchedulePage;
