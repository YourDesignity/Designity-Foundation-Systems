/**
 * ContractDetailsPage.jsx
 *
 * Full contract details with 7 tabs:
 * Details / Modules / Assignments / Workflow / Schedule / Activity / Documents
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Row, Col, Card, Tabs, Button, Space, Typography, Tag, Descriptions,
  Breadcrumb, Spin, message, Timeline, Empty, Alert, Divider, Popconfirm,
  Table, Badge,
} from 'antd';
import {
  EditOutlined, ArrowLeftOutlined, CheckCircleOutlined, CloseCircleOutlined,
  ClockCircleOutlined, SendOutlined, PauseCircleOutlined,
  TeamOutlined, CarOutlined, ShoppingOutlined, HistoryOutlined,
  CalendarOutlined, FileTextOutlined, ReloadOutlined, SettingOutlined,
} from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { useAuth } from '../../context/AuthContext';
import WorkflowStatus, { WorkflowStateBadge, ModuleBadges } from '../../components/role-contracts/WorkflowStatus';
import ApprovalPanel, { ApprovalHistoryTimeline } from '../../components/role-contracts/ApprovalPanel';
import EmployeeAssignmentModal from '../../components/role-contracts/EmployeeAssignmentModal';
import InventoryAssignmentModal from '../../components/role-contracts/InventoryAssignmentModal';
import VehicleAssignmentModal from '../../components/role-contracts/VehicleAssignmentModal';
import ModuleConfigEditor from '../../components/role-contracts/ModuleConfigEditor';
import {
  getContractById, getWorkflowState, getApprovalHistory,
  transitionWorkflow, getAssignments, getScheduledTasks, getActivityLog,
  updateModuleConfig,
} from '../../services/contractService';
import '../../styles/contract-pages.css';

const { Title, Text, Paragraph } = Typography;

const formatDate = (dt) => {
  if (!dt) return '—';
  try {
    return new Date(dt).toLocaleDateString('en-KW', { day: '2-digit', month: 'short', year: 'numeric' });
  } catch {
    return dt;
  }
};

const formatDateTime = (dt) => {
  if (!dt) return '—';
  try {
    return new Date(dt).toLocaleString('en-KW', { dateStyle: 'medium', timeStyle: 'short' });
  } catch {
    return dt;
  }
};

const formatCurrency = (v) =>
  typeof v === 'number'
    ? `KD ${v.toLocaleString('en-KW', { minimumFractionDigits: 2 })}`
    : '—';

// ─── Workflow Action Buttons ──────────────────────────────────────────────────

const WorkflowActions = ({ state, contractId, onTransition, canManage }) => {
  const [loading, setLoading] = useState(null);

  const perform = async (action, label) => {
    setLoading(action);
    try {
      await transitionWorkflow(contractId, action);
      toast.success(`Contract ${label} successfully`);
      onTransition?.();
    } catch {
      toast.error(`Failed to ${label.toLowerCase()} contract`);
    } finally {
      setLoading(null);
    }
  };

  if (!canManage) return null;

  const actionsMap = {
    DRAFT: [
      { key: 'submit', label: 'Submit for Approval', icon: <SendOutlined />, type: 'primary' },
      { key: 'cancel', label: 'Cancel', icon: <CloseCircleOutlined />, danger: true },
    ],
    PENDING_APPROVAL: [
      { key: 'approve', label: 'Approve', icon: <CheckCircleOutlined />, type: 'primary' },
      { key: 'reject', label: 'Reject', icon: <CloseCircleOutlined />, danger: true },
    ],
    ACTIVE: [
      { key: 'complete', label: 'Complete', icon: <CheckCircleOutlined />, type: 'primary' },
      { key: 'suspend', label: 'Suspend', icon: <PauseCircleOutlined /> },
      { key: 'cancel', label: 'Cancel', icon: <CloseCircleOutlined />, danger: true },
    ],
    SUSPENDED: [
      { key: 'activate', label: 'Reactivate', icon: <CheckCircleOutlined />, type: 'primary' },
      { key: 'cancel', label: 'Cancel', icon: <CloseCircleOutlined />, danger: true },
    ],
  };

  const actions = actionsMap[state] || [];
  if (!actions.length) return null;

  return (
    <Space wrap>
      {actions.map(({ key, label, icon, type, danger }) => (
        <Button
          key={key}
          type={type || 'default'}
          danger={danger}
          icon={icon}
          loading={loading === key}
          onClick={() => perform(key, label)}
          size="small"
        >
          {label}
        </Button>
      ))}
    </Space>
  );
};

// ─── Main component ───────────────────────────────────────────────────────────

const ContractDetailsPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();

  const canManage = ['SuperAdmin', 'Admin'].includes(user?.role);

  const [loading, setLoading] = useState(false);
  const [contract, setContract] = useState(null);
  const [workflow, setWorkflow] = useState(null);
  const [approvals, setApprovals] = useState([]);
  const [approvalHistory, setApprovalHistory] = useState([]);
  const [assignments, setAssignments] = useState({});
  const [scheduledTasks, setScheduledTasks] = useState([]);
  const [activityLog, setActivityLog] = useState([]);
  const [activeTab, setActiveTab] = useState('details');

  // Modals
  const [empModalOpen, setEmpModalOpen] = useState(false);
  const [invModalOpen, setInvModalOpen] = useState(false);
  const [vehModalOpen, setVehModalOpen] = useState(false);

  const fetchAll = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      const [contractData, workflowData] = await Promise.all([
        getContractById(id),
        getWorkflowState(id).catch(() => null),
      ]);

      const c = contractData?.contract || contractData;
      setContract(c);
      setWorkflow(workflowData);

      // Fetch secondary data in parallel
      const [approvalData, taskData, logData] = await Promise.all([
        getApprovalHistory(id).catch(() => []),
        getScheduledTasks(id).catch(() => []),
        getActivityLog(id).catch(() => []),
      ]);

      const allApprovals = Array.isArray(approvalData) ? approvalData : approvalData?.approvals || [];
      setApprovals(allApprovals.filter((a) => a.status === 'PENDING'));
      setApprovalHistory(allApprovals);
      setScheduledTasks(Array.isArray(taskData) ? taskData : taskData?.jobs || []);
      setActivityLog(Array.isArray(logData) ? logData : logData?.events || []);
    } catch {
      message.error('Failed to load contract details');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const fetchAssignments = useCallback(async (moduleType) => {
    try {
      const data = await getAssignments(id, moduleType);
      const list = Array.isArray(data) ? data : data?.assignments || [];
      setAssignments((prev) => ({ ...prev, [moduleType]: list }));
    } catch {
      // Silently fail – backend endpoints may not exist yet
    }
  }, [id]);

  const handleModuleConfigSave = async (moduleType, config) => {
    try {
      await updateModuleConfig(id, moduleType, config);
      toast.success(`${moduleType} module config saved`);
    } catch {
      toast.error('Failed to save module config');
    }
  };

  if (loading && !contract) {
    return (
      <div style={{ textAlign: 'center', padding: '80px 0' }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!contract) {
    return (
      <div className="contract-page">
        <Alert type="error" message="Contract not found or could not be loaded." showIcon />
      </div>
    );
  }

  const state = workflow?.current_state || contract.workflow_state || 'DRAFT';
  const enabledModules = contract.enabled_modules || [];

  const JOB_STATUS_COLOR = {
    PENDING: 'default',
    RUNNING: 'processing',
    COMPLETED: 'success',
    FAILED: 'error',
    SCHEDULED: 'warning',
  };

  const taskColumns = [
    { title: 'Type', dataIndex: 'job_type', key: 'job_type', width: 180 },
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
      render: (v) => formatDateTime(v),
    },
    {
      title: 'Executed At',
      dataIndex: 'executed_at',
      key: 'executed_at',
      render: (v) => formatDateTime(v),
    },
    {
      title: 'Message',
      dataIndex: 'message',
      key: 'message',
      ellipsis: true,
    },
  ];

  const tabItems = [
    {
      key: 'details',
      label: <Space><FileTextOutlined /> Details</Space>,
      children: (
        <Descriptions
          bordered
          column={{ xs: 1, sm: 2, md: 3 }}
          size="small"
          style={{ marginTop: 8 }}
        >
          <Descriptions.Item label="Code">
            <Text code>{contract.contract_code}</Text>
          </Descriptions.Item>
          <Descriptions.Item label="Name">{contract.contract_name || '—'}</Descriptions.Item>
          <Descriptions.Item label="Type">{contract.contract_type}</Descriptions.Item>
          <Descriptions.Item label="Client">{contract.client_name || '—'}</Descriptions.Item>
          <Descriptions.Item label="Project">{contract.project_name || '—'}</Descriptions.Item>
          <Descriptions.Item label="Start Date">{formatDate(contract.start_date)}</Descriptions.Item>
          <Descriptions.Item label="End Date">{formatDate(contract.end_date)}</Descriptions.Item>
          <Descriptions.Item label="Duration">{contract.duration_days || 0} days</Descriptions.Item>
          <Descriptions.Item label="Days Remaining">
            {contract.days_remaining > 0 ? (
              <Badge
                color={contract.is_expiring_soon ? 'red' : 'green'}
                text={`${contract.days_remaining} days`}
              />
            ) : 'Expired'}
          </Descriptions.Item>
          <Descriptions.Item label="Contract Value">
            {formatCurrency(contract.contract_value)}
          </Descriptions.Item>
          <Descriptions.Item label="Payment Terms">{contract.payment_terms || '—'}</Descriptions.Item>
          <Descriptions.Item label="Workflow State">
            <WorkflowStateBadge state={state} />
          </Descriptions.Item>
          {contract.notes && (
            <Descriptions.Item label="Notes" span={3}>{contract.notes}</Descriptions.Item>
          )}
          {contract.contract_terms && (
            <Descriptions.Item label="Terms & Conditions" span={3}>
              <Paragraph style={{ maxHeight: 120, overflow: 'auto', margin: 0, fontSize: 12 }}>
                {contract.contract_terms}
              </Paragraph>
            </Descriptions.Item>
          )}
        </Descriptions>
      ),
    },
    {
      key: 'modules',
      label: <Space><SettingOutlined /> Modules</Space>,
      children: (
        <div>
          {enabledModules.length === 0 ? (
            <Empty description="No modules enabled for this contract" />
          ) : (
            <Tabs
              tabPosition="left"
              items={enabledModules.map((mod) => ({
                key: mod,
                label: mod.charAt(0).toUpperCase() + mod.slice(1),
                children: (
                  <div>
                    <Text type="secondary" style={{ display: 'block', marginBottom: 12, fontSize: 12 }}>
                      Current configuration for the <strong>{mod}</strong> module.
                    </Text>
                    <ModuleConfigEditor
                      moduleType={mod}
                      config={contract.module_config?.[mod] || {}}
                      readOnly={!canManage}
                      onSave={(config) => handleModuleConfigSave(mod, config)}
                    />
                  </div>
                ),
              }))}
            />
          )}
        </div>
      ),
    },
    {
      key: 'assignments',
      label: <Space><TeamOutlined /> Assignments</Space>,
      children: (
        <div>
          {enabledModules.length === 0 ? (
            <Alert
              type="info"
              message="Enable modules (employee, inventory, vehicle) to manage assignments."
              showIcon
            />
          ) : (
            <Space orientation="vertical" style={{ width: '100%' }} size={16}>
              {enabledModules.includes('employee') && (
                <Card
                  title={<Space><TeamOutlined /> Employee Assignments</Space>}
                  extra={
                    canManage && (
                      <Button size="small" type="primary" onClick={() => setEmpModalOpen(true)}>
                        Assign Employees
                      </Button>
                    )
                  }
                  size="small"
                >
                  {(assignments.employee || []).length === 0 ? (
                    <Empty description="No employees assigned" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                  ) : (
                    <Table
                      dataSource={assignments.employee}
                      size="small"
                      rowKey="uid"
                      columns={[
                        { title: 'Name', dataIndex: 'name', key: 'name' },
                        { title: 'Role', dataIndex: 'role', key: 'role' },
                        { title: 'Start', dataIndex: 'start_date', key: 'start_date', render: formatDate },
                        { title: 'End', dataIndex: 'end_date', key: 'end_date', render: formatDate },
                      ]}
                    />
                  )}
                </Card>
              )}
              {enabledModules.includes('inventory') && (
                <Card
                  title={<Space><ShoppingOutlined /> Inventory Assignments</Space>}
                  extra={
                    canManage && (
                      <Button size="small" type="primary" onClick={() => setInvModalOpen(true)}>
                        Assign Inventory
                      </Button>
                    )
                  }
                  size="small"
                >
                  <Empty description="No inventory assigned" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                </Card>
              )}
              {enabledModules.includes('vehicle') && (
                <Card
                  title={<Space><CarOutlined /> Vehicle Assignments</Space>}
                  extra={
                    canManage && (
                      <Button size="small" type="primary" onClick={() => setVehModalOpen(true)}>
                        Assign Vehicles
                      </Button>
                    )
                  }
                  size="small"
                >
                  <Empty description="No vehicles assigned" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                </Card>
              )}
            </Space>
          )}
        </div>
      ),
    },
    {
      key: 'workflow',
      label: <Space><HistoryOutlined /> Workflow</Space>,
      children: (
        <div>
          <WorkflowStatus state={state} />
          {canManage && (
            <div style={{ marginBottom: 24 }}>
              <WorkflowActions
                state={state}
                contractId={id}
                onTransition={fetchAll}
                canManage={canManage}
              />
            </div>
          )}
          <Divider>Approval History</Divider>
          <ApprovalHistoryTimeline history={approvalHistory} />
        </div>
      ),
    },
    {
      key: 'approvals',
      label: (
        <Space>
          <ClockCircleOutlined />
          Approvals
          {approvals.length > 0 && <Badge count={approvals.length} size="small" />}
        </Space>
      ),
      children: (
        <ApprovalPanel
          approvals={approvals}
          history={approvalHistory}
          contractId={id}
          onActionComplete={fetchAll}
        />
      ),
    },
    {
      key: 'schedule',
      label: <Space><CalendarOutlined /> Schedule</Space>,
      children: (
        <div>
          <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
            <Col>
              <Text strong>Scheduled Jobs ({scheduledTasks.length})</Text>
            </Col>
            <Col>
              <Button
                icon={<ReloadOutlined />}
                size="small"
                onClick={() =>
                  getScheduledTasks(id)
                    .then((d) => setScheduledTasks(Array.isArray(d) ? d : d?.jobs || []))
                    .catch(() => {})
                }
              >
                Refresh
              </Button>
            </Col>
          </Row>
          <Table
            dataSource={scheduledTasks}
            columns={taskColumns}
            rowKey={(r) => r._id || r.uid || Math.random()}
            size="small"
            pagination={{ pageSize: 10 }}
            locale={{ emptyText: 'No scheduled tasks' }}
          />
        </div>
      ),
    },
    {
      key: 'activity',
      label: 'Activity Log',
      children: (
        <div className="activity-timeline">
          {activityLog.length === 0 ? (
            <Empty description="No activity recorded" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          ) : (
            <Timeline
              items={activityLog.map((entry) => ({
                children: (
                  <div>
                    <Text strong style={{ fontSize: 13 }}>{entry.event_type || entry.action}</Text>
                    <div style={{ fontSize: 12, color: '#888' }}>{formatDateTime(entry.created_at)}</div>
                    {entry.details && (
                      <Paragraph style={{ fontSize: 12, color: '#555', margin: '2px 0 0' }}>
                        {typeof entry.details === 'object'
                          ? JSON.stringify(entry.details)
                          : entry.details}
                      </Paragraph>
                    )}
                  </div>
                ),
              }))}
            />
          )}
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
          { title: contract.contract_code },
        ]}
        style={{ marginBottom: 12 }}
      />

      {/* Header */}
      <div className="contract-detail-header">
        <Row justify="space-between" align="top" gutter={[16, 16]}>
          <Col>
            <Space align="start">
              <Button
                icon={<ArrowLeftOutlined />}
                onClick={() => navigate('/contracts')}
              />
              <div>
                <Space wrap>
                  <Title level={4} style={{ margin: 0 }}>
                    {contract.contract_name || contract.contract_code}
                  </Title>
                  <span className="contract-code-badge">{contract.contract_code}</span>
                  <WorkflowStateBadge state={state} size="normal" />
                  {contract.is_expiring_soon && contract.days_remaining > 0 && (
                    <Tag color="warning">Expires in {contract.days_remaining}d</Tag>
                  )}
                </Space>
                <div style={{ marginTop: 6 }}>
                  <ModuleBadges modules={enabledModules} />
                </div>
              </div>
            </Space>
          </Col>
          <Col>
            <Space wrap>
              {canManage && (
                <Button
                  icon={<EditOutlined />}
                  onClick={() => navigate(`/contracts/${id}/edit`)}
                >
                  Edit
                </Button>
              )}
              <Button
                icon={<CalendarOutlined />}
                onClick={() => navigate(`/contracts/${id}/schedule`)}
              >
                Schedule
              </Button>
            </Space>
          </Col>
        </Row>
      </div>

      {/* Tabs */}
      <Card>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={tabItems}
        />
      </Card>

      {/* Assignment Modals */}
      <EmployeeAssignmentModal
        open={empModalOpen}
        contractId={id}
        onClose={() => setEmpModalOpen(false)}
        onSuccess={() => fetchAssignments('employee')}
      />
      <InventoryAssignmentModal
        open={invModalOpen}
        contractId={id}
        onClose={() => setInvModalOpen(false)}
        onSuccess={() => fetchAssignments('inventory')}
      />
      <VehicleAssignmentModal
        open={vehModalOpen}
        contractId={id}
        onClose={() => setVehModalOpen(false)}
        onSuccess={() => fetchAssignments('vehicle')}
      />
    </div>
  );
};

export default ContractDetailsPage;
