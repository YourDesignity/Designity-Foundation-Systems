/**
 * InventoryBatchPage.jsx
 *
 * Phase 8 — Manager logs an inventory arrival batch.
 * Items are picked from the admin-managed catalogue.
 * Manager sets quantity and condition (Good / Damaged / Needs Repair).
 * Admin sees all batches across all contracts.
 * Damaged items can be sent to Workshop from the batch detail view.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Table, Button, Modal, Form, Select, InputNumber, Input,
  Tag, Space, Typography, Card, Row, Col, Statistic,
  message, Popconfirm, Tooltip, Badge, Divider, Empty,
  Breadcrumb,
} from 'antd';
import {
  PlusOutlined, InboxOutlined, WarningOutlined,
  CheckCircleOutlined, ToolOutlined, ArrowRightOutlined,
  DeleteOutlined,
} from '@ant-design/icons';
import { useNavigate, useParams, Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { fetchWithAuth } from '../../services/apiService';

const { Title, Text } = Typography;
const { Option } = Select;

const CONDITION_CONFIG = {
  GOOD:         { color: 'green',  label: 'Good',         icon: <CheckCircleOutlined /> },
  DAMAGED:      { color: 'red',    label: 'Damaged',      icon: <WarningOutlined /> },
  NEEDS_REPAIR: { color: 'orange', label: 'Needs Repair', icon: <ToolOutlined /> },
};

// ─── Batch Detail Modal ───────────────────────────────────────────────────────
const BatchDetailModal = ({ batch, open, onClose, onSendToWorkshop, isAdmin }) => {
  if (!batch) return null;

  const columns = [
    {
      title: 'Item', dataIndex: 'catalogue_item_name', key: 'name',
      render: (name, r) => (
        <Space direction="vertical" size={0}>
          <Text strong>{name}</Text>
          <Text type="secondary" style={{ fontSize: 11 }}>{r.category}</Text>
        </Space>
      ),
    },
    {
      title: 'Qty', key: 'qty', width: 100,
      render: (_, r) => `${r.quantity} ${r.unit}`,
    },
    {
      title: 'Condition', dataIndex: 'condition', key: 'condition', width: 140,
      render: c => {
        const cfg = CONDITION_CONFIG[c] || {};
        return <Tag color={cfg.color} icon={cfg.icon}>{cfg.label || c}</Tag>;
      },
    },
    {
      title: 'Notes', dataIndex: 'condition_notes', key: 'notes',
      render: n => n || <Text type="secondary">—</Text>,
    },
    {
      title: 'Workshop', key: 'workshop', width: 140,
      render: (_, r) => {
        if (r.condition === 'GOOD') return <Text type="secondary">—</Text>;
        if (r.workshop_job_id) return <Tag color="purple">In Workshop</Tag>;
        return (
          <Button size="small" icon={<ToolOutlined />}
            onClick={() => onSendToWorkshop(batch, r)}>
            Send to Workshop
          </Button>
        );
      },
    },
  ];

  return (
    <Modal
      title={
        <Space>
          <InboxOutlined />
          <Text strong>{batch.batch_code}</Text>
          <Tag color={batch.status === 'OPEN' ? 'blue' : 'default'}>{batch.status}</Tag>
        </Space>
      }
      open={open}
      onCancel={onClose}
      footer={[<Button key="close" onClick={onClose}>Close</Button>]}
      width={760}
    >
      <Row gutter={12} style={{ marginBottom: 16 }}>
        <Col span={6}><Statistic title="Total Items" value={batch.total_items} /></Col>
        <Col span={6}><Statistic title="Good" value={batch.total_good} styles={{ content: {{ color: '#52c41a' } }}} /></Col>
        <Col span={6}><Statistic title="Damaged" value={batch.total_damaged} styles={{ content: {{ color: '#ff4d4f' } }}} /></Col>
        <Col span={6}><Statistic title="Needs Repair" value={batch.total_needs_repair} styles={{ content: {{ color: '#fa8c16' } }}} /></Col>
      </Row>
      {batch.notes && (
        <Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
          Notes: {batch.notes}
        </Text>
      )}
      <Table
        columns={columns}
        dataSource={batch.items || []}
        rowKey="uid"
        pagination={false}
        size="small"
      />
    </Modal>
  );
};

// ─── Log Batch Modal ──────────────────────────────────────────────────────────
const LogBatchModal = ({ open, contractId, siteId, catalogueItems, onClose, onSuccess }) => {
  const [form] = Form.useForm();
  const [items, setItems]       = useState([{ key: 0, catalogue_item_id: null, quantity: 1, condition: 'GOOD', condition_notes: '' }]);
  const [submitting, setSubmitting] = useState(false);

  const addItem = () => {
    setItems(prev => [...prev, { key: Date.now(), catalogue_item_id: null, quantity: 1, condition: 'GOOD', condition_notes: '' }]);
  };

  const removeItem = (key) => setItems(prev => prev.filter(i => i.key !== key));

  const updateItem = (key, field, value) => {
    setItems(prev => prev.map(i => i.key === key ? { ...i, [field]: value } : i));
  };

  const handleSubmit = async () => {
    if (items.some(i => !i.catalogue_item_id)) {
      message.warning('Please select an item for each row.');
      return;
    }
    try {
      setSubmitting(true);
      const vals = await form.validateFields();
      const payload = {
        contract_id: Number(contractId),
        site_id: Number(siteId),
        notes: vals.notes,
        items: items.map(i => ({
          catalogue_item_id: i.catalogue_item_id,
          quantity: i.quantity,
          condition: i.condition,
          condition_notes: i.condition_notes || '',
        })),
      };
      await fetchWithAuth('/api/inventory-batches', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      message.success('Batch logged successfully!');
      form.resetFields();
      setItems([{ key: 0, catalogue_item_id: null, quantity: 1, condition: 'GOOD', condition_notes: '' }]);
      onSuccess();
    } catch {
      message.error('Failed to log batch.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal
      title="Log New Arrival Batch"
      open={open}
      onCancel={onClose}
      onOk={handleSubmit}
      okText="Log Batch"
      confirmLoading={submitting}
      width={720}
      destroyOnHidden
    >
      <Form form={form} layout="vertical">
        <Form.Item name="notes" label="Notes (optional)">
          <Input.TextArea rows={2} placeholder="Delivery notes, truck number, etc." />
        </Form.Item>
      </Form>

      <Divider orientation="left">Items in this batch</Divider>

      {items.map((item, idx) => (
        <Card key={item.key} size="small" style={{ marginBottom: 8 }}
          extra={items.length > 1 && (
            <Button danger size="small" type="text" icon={<DeleteOutlined />}
              onClick={() => removeItem(item.key)} />
          )}>
          <Row gutter={8} align="middle">
            <Col span={8}>
              <Select
                placeholder="Select item..."
                style={{ width: '100%' }}
                value={item.catalogue_item_id || undefined}
                onChange={v => updateItem(item.key, 'catalogue_item_id', v)}
                showSearch
                optionFilterProp="children"
              >
                {catalogueItems.map(c => (
                  <Option key={c.uid} value={c.uid}>{c.name} ({c.unit})</Option>
                ))}
              </Select>
            </Col>
            <Col span={4}>
              <InputNumber
                min={0.01} step={0.1}
                value={item.quantity}
                onChange={v => updateItem(item.key, 'quantity', v)}
                style={{ width: '100%' }}
                placeholder="Qty"
              />
            </Col>
            <Col span={5}>
              <Select
                value={item.condition}
                onChange={v => updateItem(item.key, 'condition', v)}
                style={{ width: '100%' }}
              >
                {Object.entries(CONDITION_CONFIG).map(([k, v]) => (
                  <Option key={k} value={k}>
                    <Tag color={v.color}>{v.label}</Tag>
                  </Option>
                ))}
              </Select>
            </Col>
            <Col span={7}>
              <Input
                placeholder="Condition notes..."
                value={item.condition_notes}
                onChange={e => updateItem(item.key, 'condition_notes', e.target.value)}
              />
            </Col>
          </Row>
        </Card>
      ))}

      <Button type="dashed" block icon={<PlusOutlined />} onClick={addItem} style={{ marginTop: 8 }}>
        Add Another Item
      </Button>
    </Modal>
  );
};

// ─── Main Page ────────────────────────────────────────────────────────────────
const InventoryBatchPage = () => {
  const { contractId, projectId } = useParams();
  const navigate = useNavigate();
  const { isAdmin, isSiteManager } = useAuth();

  const [batches, setBatches]           = useState([]);
  const [catalogueItems, setCatalogue]  = useState([]);
  const [contract, setContract]         = useState(null);
  const [loading, setLoading]           = useState(true);
  const [logModalOpen, setLogModalOpen] = useState(false);
  const [detailBatch, setDetailBatch]   = useState(null);
  const [detailOpen, setDetailOpen]     = useState(false);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [batchData, catData, contractData] = await Promise.all([
        fetchWithAuth(`/api/inventory-batches?contract_id=${contractId}`),
        fetchWithAuth('/api/item-catalogue?active_only=true'),
        fetchWithAuth(`/api/contracts/${contractId}`),
      ]);
      setBatches(Array.isArray(batchData) ? batchData : []);
      setCatalogue(Array.isArray(catData) ? catData : []);
      setContract(contractData?.contract || contractData);
    } catch {
      message.error('Failed to load inventory data.');
    } finally {
      setLoading(false);
    }
  }, [contractId]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const openDetail = (batch) => { setDetailBatch(batch); setDetailOpen(true); };

  const sendToWorkshop = async (batch, item) => {
    try {
      await fetchWithAuth('/api/workshop-jobs', {
        method: 'POST',
        body: JSON.stringify({
          batch_id: batch.uid,
          batch_item_uid: item.uid,
          contract_id: batch.contract_id,
          site_id: batch.site_id,
          project_id: batch.project_id,
          item_name: item.catalogue_item_name,
          category: item.category,
          quantity_for_repair: item.quantity,
          condition_on_arrival: item.condition,
          priority: 'MEDIUM',
        }),
      });
      message.success(`${item.catalogue_item_name} sent to Workshop.`);
      fetchAll();
      setDetailOpen(false);
    } catch {
      message.error('Failed to create workshop job.');
    }
  };

  const totalItems    = batches.reduce((s, b) => s + (b.total_items || 0), 0);
  const totalDamaged  = batches.reduce((s, b) => s + (b.total_damaged || 0) + (b.total_needs_repair || 0), 0);

  const columns = [
    {
      title: 'Batch', dataIndex: 'batch_code', key: 'batch_code',
      render: (code, r) => (
        <Button type="link" style={{ padding: 0 }} onClick={() => openDetail(r)}>{code}</Button>
      ),
    },
    {
      title: 'Date', dataIndex: 'logged_at', key: 'logged_at', width: 130,
      render: d => d ? new Date(d).toLocaleDateString() : '—',
    },
    {
      title: 'Items', key: 'items',
      render: (_, r) => (
        <Space>
          <Badge count={r.total_good} color="green" />
          {r.total_damaged > 0 && <Badge count={r.total_damaged} color="red" title="Damaged" />}
          {r.total_needs_repair > 0 && <Badge count={r.total_needs_repair} color="orange" title="Needs Repair" />}
        </Space>
      ),
    },
    {
      title: 'Status', dataIndex: 'status', key: 'status', width: 100,
      render: s => <Tag color={s === 'OPEN' ? 'blue' : 'default'}>{s}</Tag>,
    },
    {
      title: 'Notes', dataIndex: 'notes', key: 'notes',
      render: n => n ? <Text type="secondary" style={{ fontSize: 12 }}>{n}</Text> : '—',
    },
    {
      title: '', key: 'action', width: 60,
      render: (_, r) => (
        <Tooltip title="View Details">
          <Button size="small" type="text" icon={<ArrowRightOutlined />}
            onClick={() => openDetail(r)} />
        </Tooltip>
      ),
    },
  ];

  // Determine site_id from contract data
  const siteId = contract?.site_ids?.[0] || 0;

  return (
    <div style={{ padding: 24 }}>
      <Breadcrumb style={{ marginBottom: 16 }} items={[
        { title: <Link to="/projects">Projects</Link> },
        projectId && { title: <Link to={`/projects/${projectId}`}>Project</Link> },
        contractId && { title: <Link to={`/projects/${projectId}/contracts/${contractId}`}>{contract?.contract_code || 'Contract'}</Link> },
        { title: 'Inventory Batches' },
      ].filter(Boolean)} />

      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <Title level={3} style={{ margin: 0 }}>Inventory Batches</Title>
          <Text type="secondary">Arrival logs for {contract?.contract_name || contract?.contract_code}</Text>
        </div>
        <Button type="primary" icon={<PlusOutlined />}
          onClick={() => setLogModalOpen(true)}>
          Log New Arrival
        </Button>
      </div>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={8} sm={6}>
          <Card size="small" variant="borderless" style={{ background: '#f0f5ff' }}>
            <Statistic title="Total Batches" value={batches.length} />
          </Card>
        </Col>
        <Col xs={8} sm={6}>
          <Card size="small" variant="borderless" style={{ background: '#f6ffed' }}>
            <Statistic title="Total Items" value={totalItems} prefix={<InboxOutlined />} />
          </Card>
        </Col>
        <Col xs={8} sm={6}>
          <Card size="small" variant="borderless"
            style={{ background: totalDamaged > 0 ? '#fff1f0' : '#f5f5f5' }}>
            <Statistic title="Damaged / Repair" value={totalDamaged}
              styles={{ content: {totalDamaged > 0 ? { color: '#ff4d4f' } }} : {}} />
          </Card>
        </Col>
      </Row>

      <Card variant="borderless" styles={{ body: { padding: 0 } }}>
        <Table
          columns={columns}
          dataSource={batches}
          rowKey="uid"
          loading={loading}
          pagination={{ pageSize: 15 }}
          locale={{ emptyText: <Empty description="No batches logged yet. Log the first arrival above." /> }}
        />
      </Card>

      <LogBatchModal
        open={logModalOpen}
        contractId={contractId}
        siteId={siteId}
        catalogueItems={catalogueItems}
        onClose={() => setLogModalOpen(false)}
        onSuccess={() => { setLogModalOpen(false); fetchAll(); }}
      />

      <BatchDetailModal
        batch={detailBatch}
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
        onSendToWorkshop={sendToWorkshop}
        isAdmin={isAdmin}
      />
    </div>
  );
};

export default InventoryBatchPage;
