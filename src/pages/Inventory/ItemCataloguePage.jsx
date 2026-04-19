/**
 * ItemCataloguePage.jsx
 *
 * Phase 7 — Admin-managed predefined item catalogue.
 * Managers select from this catalogue when logging inventory batch arrivals.
 * Admin can create, edit, and deactivate items at any time.
 * Changes reflect in all contracts using the item.
 */

import React, { useState, useEffect } from 'react';
import {
  Table, Button, Modal, Form, Input, Select, Tag, Space,
  Typography, Popconfirm, message, Card, Row, Col, Statistic,
  Switch, Tooltip, Badge,
} from 'antd';
import {
  PlusOutlined, EditOutlined, DeleteOutlined,
  InboxOutlined, TagsOutlined,
} from '@ant-design/icons';
import { useAuth } from '../../context/AuthContext';
import { fetchWithAuth } from '../../services/apiService';

const { Title, Text } = Typography;
const { Option } = Select;

const CATEGORIES = [
  'Packaging', 'Construction', 'Equipment', 'Furniture',
  'Electronics', 'Raw Materials', 'Tools', 'Safety', 'Other',
];

const UNITS = ['pcs', 'kg', 'tons', 'meters', 'liters', 'boxes', 'pallets', 'sets', 'rolls'];

const ItemCataloguePage = () => {
  const { isAdmin } = useAuth();
  const [items, setItems]         = useState([]);
  const [loading, setLoading]     = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing]     = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [form] = Form.useForm();

  useEffect(() => { fetchItems(); }, []);

  const fetchItems = async () => {
    try {
      setLoading(true);
      const data = await fetchWithAuth('/api/item-catalogue');
      setItems(Array.isArray(data) ? data : []);
    } catch {
      message.error('Could not load item catalogue.');
    } finally {
      setLoading(false);
    }
  };

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({ is_active: true });
    setModalOpen(true);
  };

  const openEdit = (item) => {
    setEditing(item);
    form.setFieldsValue({
      name: item.name,
      category: item.category,
      unit: item.unit,
      description: item.description,
      is_active: item.is_active,
    });
    setModalOpen(true);
  };

  const handleSubmit = async (values) => {
    try {
      setSubmitting(true);
      if (editing) {
        await fetchWithAuth(`/api/item-catalogue/${editing.uid}`, {
          method: 'PUT',
          body: JSON.stringify(values),
        });
        message.success('Item updated.');
      } else {
        await fetchWithAuth('/api/item-catalogue', {
          method: 'POST',
          body: JSON.stringify(values),
        });
        message.success(`"${values.name}" added to catalogue.`);
      }
      setModalOpen(false);
      form.resetFields();
      fetchItems();
    } catch (err) {
      message.error(err?.message || 'Failed to save item.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (uid) => {
    try {
      await fetchWithAuth(`/api/item-catalogue/${uid}`, { method: 'DELETE' });
      message.success('Item removed from catalogue.');
      fetchItems();
    } catch {
      message.error('Failed to delete item.');
    }
  };

  const activeCount   = items.filter(i => i.is_active).length;
  const categoryCount = [...new Set(items.map(i => i.category))].length;

  const columns = [
    {
      title: 'Item Name', dataIndex: 'name', key: 'name',
      render: (name, r) => (
        <Space>
          <InboxOutlined style={{ color: '#1677ff' }} />
          <Space direction="vertical" size={0}>
            <Text strong>{name}</Text>
            {r.description && <Text type="secondary" style={{ fontSize: 11 }}>{r.description}</Text>}
          </Space>
        </Space>
      ),
    },
    {
      title: 'Category', dataIndex: 'category', key: 'category',
      render: c => <Tag color="blue">{c}</Tag>,
    },
    {
      title: 'Unit', dataIndex: 'unit', key: 'unit', width: 90,
      render: u => <Tag>{u}</Tag>,
    },
    {
      title: 'Status', dataIndex: 'is_active', key: 'is_active', width: 100,
      render: active => active
        ? <Tag color="green">Active</Tag>
        : <Tag color="default">Inactive</Tag>,
    },
    ...(isAdmin ? [{
      title: 'Actions', key: 'actions', width: 100,
      render: (_, record) => (
        <Space>
          <Tooltip title="Edit">
            <Button icon={<EditOutlined />} size="small" type="text"
              onClick={() => openEdit(record)} />
          </Tooltip>
          <Popconfirm
            title="Remove this item?"
            description="This won't affect existing inventory logs."
            onConfirm={() => handleDelete(record.uid)}
            okText="Remove" cancelText="Cancel" okButtonProps={{ danger: true }}
          >
            <Tooltip title="Delete">
              <Button icon={<DeleteOutlined />} size="small" type="text" danger />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    }] : []),
  ];

  return (
    <div style={{ padding: 24 }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 }}>
        <div>
          <Title level={3} style={{ margin: 0 }}>Item Catalogue</Title>
          <Text type="secondary">
            Predefined items used in Goods & Storage contracts. Admin manages this list.
          </Text>
        </div>
        {isAdmin && (
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            Add Item
          </Button>
        )}
      </div>

      {/* Stats */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={8} sm={6}>
          <Card size="small" variant="borderless" style={{ background: '#f0f5ff' }}>
            <Statistic title="Total Items" value={items.length} prefix={<InboxOutlined />} />
          </Card>
        </Col>
        <Col xs={8} sm={6}>
          <Card size="small" variant="borderless" style={{ background: '#f6ffed' }}>
            <Statistic title="Active" value={activeCount} />
          </Card>
        </Col>
        <Col xs={8} sm={6}>
          <Card size="small" variant="borderless" style={{ background: '#fff7e6' }}>
            <Statistic title="Categories" value={categoryCount} prefix={<TagsOutlined />} />
          </Card>
        </Col>
      </Row>

      {/* Table */}
      <Card variant="borderless" styles={{ body: { padding: 0 } }}>
        <Table
          columns={columns}
          dataSource={items}
          rowKey="uid"
          loading={loading}
          pagination={{ pageSize: 20 }}
          locale={{ emptyText: 'No items in catalogue yet.' }}
        />
      </Card>

      {/* Create / Edit Modal */}
      <Modal
        title={editing ? 'Edit Catalogue Item' : 'Add New Item'}
        open={modalOpen}
        onCancel={() => { setModalOpen(false); form.resetFields(); setEditing(null); }}
        footer={null}
        destroyOnHidden
        width={520}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}
          initialValues={{ is_active: true }}>
          <Form.Item name="name" label="Item Name"
            rules={[{ required: true, message: 'Please enter a name' }]}>
            <Input placeholder="e.g. Wooden Pallet, Steel Beam" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="category" label="Category"
                rules={[{ required: true, message: 'Select a category' }]}>
                <Select placeholder="Select...">
                  {CATEGORIES.map(c => <Option key={c} value={c}>{c}</Option>)}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="unit" label="Unit"
                rules={[{ required: true, message: 'Select a unit' }]}>
                <Select placeholder="Select...">
                  {UNITS.map(u => <Option key={u} value={u}>{u}</Option>)}
                </Select>
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="description" label="Description">
            <Input.TextArea rows={2} placeholder="Optional description..." />
          </Form.Item>
          {editing && (
            <Form.Item name="is_active" label="Active" valuePropName="checked">
              <Switch />
            </Form.Item>
          )}
          <div style={{ textAlign: 'right' }}>
            <Space>
              <Button onClick={() => { setModalOpen(false); form.resetFields(); setEditing(null); }}>
                Cancel
              </Button>
              <Button type="primary" htmlType="submit" loading={submitting}>
                {editing ? 'Save Changes' : 'Add to Catalogue'}
              </Button>
            </Space>
          </div>
        </Form>
      </Modal>
    </div>
  );
};

export default ItemCataloguePage;
