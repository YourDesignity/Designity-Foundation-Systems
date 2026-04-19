/**
 * WorkshopPage.jsx — Phase 9
 * Internal workshop for repairing damaged inventory items.
 * Admin can update status, assign employees, toggle client repair.
 * Manager can view and update status of their assigned jobs.
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  Table, Tag, Button, Select, Space, Typography, Card, Row, Col,
  Statistic, message, Modal, Form, Input, Switch, Descriptions, Empty,
} from 'antd';
import {
  ToolOutlined, UserOutlined, CheckCircleOutlined,
  ClockCircleOutlined, StopOutlined,
} from '@ant-design/icons';
import { useAuth } from '../../context/AuthContext';
import { fetchWithAuth } from '../../services/apiService';

const { Title, Text } = Typography;
const { Option } = Select;

const STATUS_CONFIG = {
  PENDING:       { color: 'default',    icon: <ClockCircleOutlined />,  label: 'Pending'       },
  IN_PROGRESS:   { color: 'processing', icon: <ToolOutlined />,         label: 'In Progress'   },
  FIXED:         { color: 'success',    icon: <CheckCircleOutlined />,  label: 'Fixed'         },
  SCRAPPED:      { color: 'error',      icon: <StopOutlined />,         label: 'Scrapped'      },
  CLIENT_REPAIR: { color: 'purple',     icon: <UserOutlined />,         label: 'Client Repair' },
};
const PRIORITY_COLORS = { LOW: 'default', MEDIUM: 'blue', HIGH: 'orange', URGENT: 'red' };
const STATUS_TRANSITIONS = {
  PENDING:       ['IN_PROGRESS', 'SCRAPPED'],
  IN_PROGRESS:   ['FIXED', 'SCRAPPED', 'CLIENT_REPAIR'],
  FIXED:         [],  SCRAPPED: [],
  CLIENT_REPAIR: ['FIXED', 'SCRAPPED'],
};

const JobModal = ({ job, open, onClose, onSave, isAdmin, employees }) => {
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);
  useEffect(() => {
    if (job && open) form.setFieldsValue({
      status: job.status, priority: job.priority,
      assigned_employee_ids: job.assigned_employee_ids || [],
      resolution_notes: job.resolution_notes || '',
      is_client_repair: job.is_client_repair || false,
    });
  }, [job, open, form]);

  if (!job) return null;
  const allowed = STATUS_TRANSITIONS[job.status] || [];

  return (
    <Modal title={<Space><ToolOutlined /><Text strong>{job.job_code}</Text><Tag color={STATUS_CONFIG[job.status]?.color}>{STATUS_CONFIG[job.status]?.label}</Tag></Space>}
      open={open} onCancel={onClose} footer={null} width={580} destroyOnHidden>
      <Descriptions size="small" bordered column={2} style={{ marginBottom: 16 }}>
        <Descriptions.Item label="Item">{job.item_name}</Descriptions.Item>
        <Descriptions.Item label="Category">{job.category}</Descriptions.Item>
        <Descriptions.Item label="Qty">{job.quantity_for_repair}</Descriptions.Item>
        <Descriptions.Item label="Condition">
          <Tag color={job.condition_on_arrival === 'DAMAGED' ? 'red' : 'orange'}>{job.condition_on_arrival}</Tag>
        </Descriptions.Item>
      </Descriptions>
      <Form form={form} layout="vertical" onFinish={async (vals) => { setSaving(true); try { await onSave(job.uid, vals); onClose(); } finally { setSaving(false); } }}>
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item name="status" label="Status">
              <Select>
                <Option value={job.status}>{STATUS_CONFIG[job.status]?.label} (current)</Option>
                {allowed.map(s => <Option key={s} value={s}>{STATUS_CONFIG[s]?.label}</Option>)}
              </Select>
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item name="priority" label="Priority">
              <Select>{['LOW','MEDIUM','HIGH','URGENT'].map(p => <Option key={p} value={p}>{p}</Option>)}</Select>
            </Form.Item>
          </Col>
        </Row>
        <Form.Item name="assigned_employee_ids" label="Assigned Employees">
          <Select mode="multiple" placeholder="Assign workers..." showSearch optionFilterProp="children">
            {employees.map(e => <Option key={e.uid} value={e.uid}>{e.name} — {e.designation}</Option>)}
          </Select>
        </Form.Item>
        {isAdmin && (
          <Form.Item name="is_client_repair" label="Client Repair" valuePropName="checked">
            <Switch checkedChildren="Yes" unCheckedChildren="No" />
          </Form.Item>
        )}
        <Form.Item name="resolution_notes" label="Resolution Notes">
          <Input.TextArea rows={3} placeholder="What was done, or why scrapped..." />
        </Form.Item>
        <div style={{ textAlign: 'right' }}>
          <Space>
            <Button onClick={onClose}>Cancel</Button>
            <Button type="primary" htmlType="submit" loading={saving}>Save</Button>
          </Space>
        </div>
      </Form>
    </Modal>
  );
};

const WorkshopPage = () => {
  const { isAdmin } = useAuth();
  const [jobs, setJobs]           = useState([]);
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading]     = useState(true);
  const [statusFilter, setStatus] = useState('');
  const [priorityFilter, setPriority] = useState('');
  const [selectedJob, setJob]     = useState(null);
  const [modalOpen, setModalOpen] = useState(false);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [jobData, empData] = await Promise.all([
        fetchWithAuth('/api/workshop-jobs'),
        fetchWithAuth('/employees').catch(() => []),
      ]);
      setJobs(Array.isArray(jobData) ? jobData : []);
      setEmployees(Array.isArray(empData) ? empData : empData?.employees || []);
    } catch { message.error('Failed to load workshop jobs.'); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const handleSave = async (uid, values) => {
    await fetchWithAuth(`/api/workshop-jobs/${uid}`, { method: 'PUT', body: JSON.stringify(values) });
    message.success('Job updated.');
    fetchAll();
  };

  const filtered = jobs.filter(j =>
    (!statusFilter || j.status === statusFilter) &&
    (!priorityFilter || j.priority === priorityFilter)
  );

  const pending = jobs.filter(j => j.status === 'PENDING').length;
  const inProg  = jobs.filter(j => j.status === 'IN_PROGRESS').length;
  const fixed   = jobs.filter(j => j.status === 'FIXED').length;
  const urgent  = jobs.filter(j => j.priority === 'URGENT' && !['FIXED','SCRAPPED'].includes(j.status)).length;

  const columns = [
    { title: 'Job', key: 'job', render: (_, r) => (
        <Space direction="vertical" size={0}>
          <Button type="link" style={{ padding: 0 }} onClick={() => { setJob(r); setModalOpen(true); }}>{r.job_code}</Button>
          <Text type="secondary" style={{ fontSize: 11 }}>{r.item_name}</Text>
        </Space>
    )},
    { title: 'Priority', dataIndex: 'priority', width: 100, render: p => <Tag color={PRIORITY_COLORS[p]}>{p}</Tag> },
    { title: 'Status', dataIndex: 'status', width: 140, render: s => { const c = STATUS_CONFIG[s] || {}; return <Tag color={c.color} icon={c.icon}>{c.label}</Tag>; } },
    { title: 'Condition', dataIndex: 'condition_on_arrival', width: 120, render: c => <Tag color={c === 'DAMAGED' ? 'red' : 'orange'}>{c}</Tag> },
    { title: 'Assigned', key: 'assigned', width: 160, render: (_, r) => (r.assigned_employee_names || []).length ? r.assigned_employee_names.join(', ') : <Text type="secondary">Unassigned</Text> },
    { title: 'Client Repair', dataIndex: 'is_client_repair', width: 110, render: v => v ? <Tag color="purple">Yes</Tag> : <Text type="secondary">No</Text> },
    { title: '', key: 'action', width: 80, render: (_, r) => <Button size="small" onClick={() => { setJob(r); setModalOpen(true); }}>{['FIXED','SCRAPPED'].includes(r.status) ? 'View' : 'Update'}</Button> },
  ];

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <Title level={3} style={{ margin: 0 }}>Workshop</Title>
          <Text type="secondary">Internal repair jobs for damaged inventory items</Text>
        </div>
      </div>
      <Row gutter={16} style={{ marginBottom: 24 }}>
        {[['Pending', pending, '#f5f5f5'], ['In Progress', inProg, '#e6f7ff'], ['Fixed', fixed, '#f6ffed'], ['Urgent', urgent, urgent > 0 ? '#fff1f0' : '#f5f5f5']].map(([t, v, bg]) => (
          <Col xs={12} sm={6} key={t}>
            <Card size="small" variant="borderless" style={{ background: bg }}>
              <Statistic title={t} value={v} styles={{ content: {t === 'Urgent' && v > 0 ? { color: '#ff4d4f' } }} : {}} />
            </Card>
          </Col>
        ))}
      </Row>
      <Row gutter={12} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={8} md={6}>
          <Select placeholder="Filter by status" style={{ width: '100%' }} value={statusFilter || undefined} onChange={setStatus} allowClear>
            {Object.entries(STATUS_CONFIG).map(([k, v]) => <Option key={k} value={k}>{v.label}</Option>)}
          </Select>
        </Col>
        <Col xs={24} sm={8} md={6}>
          <Select placeholder="Filter by priority" style={{ width: '100%' }} value={priorityFilter || undefined} onChange={setPriority} allowClear>
            {['LOW','MEDIUM','HIGH','URGENT'].map(p => <Option key={p} value={p}>{p}</Option>)}
          </Select>
        </Col>
      </Row>
      <Card variant="borderless" styles={{ body: { padding: 0 } }}>
        <Table columns={columns} dataSource={filtered} rowKey="uid" loading={loading}
          pagination={{ pageSize: 20 }} locale={{ emptyText: <Empty description="No workshop jobs yet." /> }} />
      </Card>
      <JobModal job={selectedJob} open={modalOpen} onClose={() => { setModalOpen(false); setJob(null); }}
        onSave={handleSave} isAdmin={isAdmin} employees={employees} />
    </div>
  );
};

export default WorkshopPage;
