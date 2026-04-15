// src/pages/Inventory/MaterialsList.jsx
// Material management with stock tracking

import React, { useState, useEffect } from 'react';
import {
    Card, Table, Button, Tag, Space, Modal, Form, Input,
    InputNumber, Select, message, Popconfirm, Typography,
    Row, Col, Statistic, Tabs, Descriptions, Empty,
    Drawer,
} from 'antd';
import {
    PlusOutlined, EditOutlined, DeleteOutlined,
    ArrowUpOutlined, ArrowDownOutlined, HistoryOutlined,
    BoxPlotOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import {
    getMaterials, createMaterial, updateMaterial, deleteMaterial,
    adjustMaterialStock, getMaterialMovements,
} from '../../services/apiService';

const { Title, Text } = Typography;
const { Option } = Select;

const CATEGORIES = ['raw_material', 'finished_good', 'consumable', 'tool', 'safety', 'other'];
const UNITS = ['pcs', 'kg', 'm', 'm2', 'm3', 'ltr', 'roll', 'box', 'bag', 'sheet'];

function StockTag({ current, minimum }) {
    if (current <= 0) return <Tag color="red">Out of Stock</Tag>;
    if (current <= minimum) return <Tag color="orange">Low Stock ({current})</Tag>;
    return <Tag color="green">{current}</Tag>;
}

const MaterialsList = () => {
    const [materials, setMaterials] = useState([]);
    const [loading, setLoading] = useState(false);
    const [createModalVisible, setCreateModalVisible] = useState(false);
    const [editModalVisible, setEditModalVisible] = useState(false);
    const [stockModalVisible, setStockModalVisible] = useState(false);
    const [movementsDrawerVisible, setMovementsDrawerVisible] = useState(false);
    const [selectedMaterial, setSelectedMaterial] = useState(null);
    const [movements, setMovements] = useState([]);
    const [movementsLoading, setMovementsLoading] = useState(false);
    const [form] = Form.useForm();
    const [stockForm] = Form.useForm();

    const fetchMaterials = async () => {
        setLoading(true);
        try {
            const data = await getMaterials();
            setMaterials(Array.isArray(data) ? data : []);
        } catch {
            message.error('Failed to load materials');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { fetchMaterials(); }, []);

    const handleCreate = async () => {
        try {
            const values = await form.validateFields();
            await createMaterial(values);
            message.success('Material created successfully');
            setCreateModalVisible(false);
            form.resetFields();
            fetchMaterials();
        } catch (err) {
            if (err?.errorFields) return; // Validation error
            message.error(err.message || 'Failed to create material');
        }
    };

    const handleEdit = async () => {
        try {
            const values = await form.validateFields();
            await updateMaterial(selectedMaterial.uid, values);
            message.success('Material updated');
            setEditModalVisible(false);
            form.resetFields();
            fetchMaterials();
        } catch (err) {
            if (err?.errorFields) return;
            message.error(err.message || 'Failed to update material');
        }
    };

    const handleDelete = async (uid) => {
        try {
            await deleteMaterial(uid);
            message.success('Material deleted');
            fetchMaterials();
        } catch (err) {
            message.error(err.message || 'Failed to delete material');
        }
    };

    const openEditModal = (material) => {
        setSelectedMaterial(material);
        form.setFieldsValue({
            name: material.name,
            category: material.category,
            unit_of_measure: material.unit_of_measure,
            minimum_stock: material.minimum_stock,
            unit_cost: material.unit_cost,
            description: material.description,
        });
        setEditModalVisible(true);
    };

    const openStockModal = (material) => {
        setSelectedMaterial(material);
        stockForm.resetFields();
        setStockModalVisible(true);
    };

    const handleStockAdjust = async () => {
        try {
            const values = await stockForm.validateFields();
            await adjustMaterialStock(selectedMaterial.uid, values);
            message.success('Stock updated successfully');
            setStockModalVisible(false);
            stockForm.resetFields();
            fetchMaterials();
        } catch (err) {
            if (err?.errorFields) return;
            message.error(err.message || 'Failed to adjust stock');
        }
    };

    const openMovements = async (material) => {
        setSelectedMaterial(material);
        setMovementsDrawerVisible(true);
        setMovementsLoading(true);
        try {
            const data = await getMaterialMovements(material.uid);
            setMovements(Array.isArray(data) ? data : []);
        } catch {
            message.error('Failed to load movements');
        } finally {
            setMovementsLoading(false);
        }
    };

    const lowStockCount = materials.filter(m => m.current_stock <= m.minimum_stock).length;
    const outOfStockCount = materials.filter(m => m.current_stock <= 0).length;
    const totalValue = materials.reduce((sum, m) => sum + (m.current_stock * m.unit_cost), 0);

    const columns = [
        {
            title: 'Code',
            dataIndex: 'material_code',
            key: 'material_code',
            render: (v) => <Text code>{v}</Text>,
        },
        {
            title: 'Name',
            dataIndex: 'name',
            key: 'name',
            render: (v) => <strong>{v}</strong>,
        },
        {
            title: 'Category',
            dataIndex: 'category',
            key: 'category',
            render: (v) => <Tag>{v?.replace('_', ' ')}</Tag>,
        },
        {
            title: 'Stock',
            key: 'stock',
            render: (_, record) => (
                <StockTag current={record.current_stock} minimum={record.minimum_stock} />
            ),
        },
        {
            title: 'Unit',
            dataIndex: 'unit_of_measure',
            key: 'unit_of_measure',
        },
        {
            title: 'Unit Cost (KD)',
            dataIndex: 'unit_cost',
            key: 'unit_cost',
            render: (v) => v?.toFixed(3),
        },
        {
            title: 'Stock Value (KD)',
            key: 'stock_value',
            render: (_, record) => (record.current_stock * record.unit_cost).toFixed(3),
        },
        {
            title: 'Actions',
            key: 'actions',
            render: (_, record) => (
                <Space size="small">
                    <Button
                        size="small"
                        icon={<ArrowUpOutlined />}
                        onClick={() => openStockModal(record)}
                        title="Adjust Stock"
                    />
                    <Button
                        size="small"
                        icon={<HistoryOutlined />}
                        onClick={() => openMovements(record)}
                        title="View Movements"
                    />
                    <Button
                        size="small"
                        icon={<EditOutlined />}
                        onClick={() => openEditModal(record)}
                    />
                    <Popconfirm
                        title="Delete this material?"
                        onConfirm={() => handleDelete(record.uid)}
                        okText="Yes"
                        cancelText="No"
                    >
                        <Button size="small" icon={<DeleteOutlined />} danger />
                    </Popconfirm>
                </Space>
            ),
        },
    ];

    const movementColumns = [
        {
            title: 'Date',
            dataIndex: 'created_at',
            key: 'created_at',
            render: (v) => dayjs(v).format('DD MMM YYYY HH:mm'),
        },
        {
            title: 'Type',
            dataIndex: 'movement_type',
            key: 'movement_type',
            render: (v) => (
                <Tag color={v === 'IN' ? 'green' : 'red'} icon={v === 'IN' ? <ArrowDownOutlined /> : <ArrowUpOutlined />}>
                    {v}
                </Tag>
            ),
        },
        { title: 'Quantity', dataIndex: 'quantity', key: 'quantity' },
        { title: 'Unit Cost', dataIndex: 'unit_cost', render: (v) => v?.toFixed(3) },
        { title: 'Reference', dataIndex: 'reference_code', key: 'reference_code', render: (v) => v || '—' },
        { title: 'Notes', dataIndex: 'notes', key: 'notes', render: (v) => v || '—' },
    ];

    const materialFormFields = (
        <>
            <Form.Item name="material_code" label="Material Code" rules={[{ required: true }]}>
                <Input placeholder="e.g. WD-001" />
            </Form.Item>
            <Form.Item name="name" label="Name" rules={[{ required: true }]}>
                <Input placeholder="e.g. Pine Wood Planks" />
            </Form.Item>
            <Row gutter={12}>
                <Col span={12}>
                    <Form.Item name="category" label="Category" rules={[{ required: true }]}>
                        <Select placeholder="Select category">
                            {CATEGORIES.map(c => <Option key={c} value={c}>{c.replace('_', ' ')}</Option>)}
                        </Select>
                    </Form.Item>
                </Col>
                <Col span={12}>
                    <Form.Item name="unit_of_measure" label="Unit" rules={[{ required: true }]}>
                        <Select placeholder="Select unit">
                            {UNITS.map(u => <Option key={u} value={u}>{u}</Option>)}
                        </Select>
                    </Form.Item>
                </Col>
            </Row>
            <Row gutter={12}>
                <Col span={12}>
                    <Form.Item name="minimum_stock" label="Minimum Stock" initialValue={0}>
                        <InputNumber style={{ width: '100%' }} min={0} />
                    </Form.Item>
                </Col>
                <Col span={12}>
                    <Form.Item name="unit_cost" label="Unit Cost (KD)" initialValue={0}>
                        <InputNumber style={{ width: '100%' }} min={0} precision={3} />
                    </Form.Item>
                </Col>
            </Row>
            <Form.Item name="description" label="Description">
                <Input.TextArea rows={2} placeholder="Optional description..." />
            </Form.Item>
        </>
    );

    return (
        <div style={{ padding: '0 24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                <Title level={4} style={{ margin: 0 }}>
                    <BoxPlotOutlined style={{ marginRight: 8 }} />
                    Materials
                </Title>
                <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModalVisible(true)}>
                    Add Material
                </Button>
            </div>

            <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
                <Col xs={12} sm={6}>
                    <Card size="small">
                        <Statistic title="Total Materials" value={materials.length} />
                    </Card>
                </Col>
                <Col xs={12} sm={6}>
                    <Card size="small">
                        <Statistic title="Low Stock Alerts" value={lowStockCount} valueStyle={{ color: lowStockCount > 0 ? '#fa8c16' : '#52c41a' }} />
                    </Card>
                </Col>
                <Col xs={12} sm={6}>
                    <Card size="small">
                        <Statistic title="Out of Stock" value={outOfStockCount} valueStyle={{ color: outOfStockCount > 0 ? '#ff4d4f' : '#52c41a' }} />
                    </Card>
                </Col>
                <Col xs={12} sm={6}>
                    <Card size="small">
                        <Statistic title="Stock Value (KD)" value={totalValue.toFixed(3)} />
                    </Card>
                </Col>
            </Row>

            <Card>
                <Table
                    columns={columns}
                    dataSource={materials}
                    rowKey="uid"
                    loading={loading}
                    pagination={{ pageSize: 20 }}
                    size="small"
                />
            </Card>

            {/* Create Material Modal */}
            <Modal
                title="Add New Material"
                open={createModalVisible}
                onOk={handleCreate}
                onCancel={() => { setCreateModalVisible(false); form.resetFields(); }}
                okText="Create"
                width={600}
            >
                <Form form={form} layout="vertical">
                    {materialFormFields}
                </Form>
            </Modal>

            {/* Edit Material Modal */}
            <Modal
                title="Edit Material"
                open={editModalVisible}
                onOk={handleEdit}
                onCancel={() => { setEditModalVisible(false); form.resetFields(); }}
                okText="Save"
                width={600}
            >
                <Form form={form} layout="vertical">
                    <Form.Item name="name" label="Name" rules={[{ required: true }]}>
                        <Input />
                    </Form.Item>
                    <Row gutter={12}>
                        <Col span={12}>
                            <Form.Item name="category" label="Category" rules={[{ required: true }]}>
                                <Select>
                                    {CATEGORIES.map(c => <Option key={c} value={c}>{c.replace('_', ' ')}</Option>)}
                                </Select>
                            </Form.Item>
                        </Col>
                        <Col span={12}>
                            <Form.Item name="unit_of_measure" label="Unit" rules={[{ required: true }]}>
                                <Select>
                                    {UNITS.map(u => <Option key={u} value={u}>{u}</Option>)}
                                </Select>
                            </Form.Item>
                        </Col>
                    </Row>
                    <Row gutter={12}>
                        <Col span={12}>
                            <Form.Item name="minimum_stock" label="Minimum Stock">
                                <InputNumber style={{ width: '100%' }} min={0} />
                            </Form.Item>
                        </Col>
                        <Col span={12}>
                            <Form.Item name="unit_cost" label="Unit Cost (KD)">
                                <InputNumber style={{ width: '100%' }} min={0} precision={3} />
                            </Form.Item>
                        </Col>
                    </Row>
                    <Form.Item name="description" label="Description">
                        <Input.TextArea rows={2} />
                    </Form.Item>
                </Form>
            </Modal>

            {/* Stock Adjustment Modal */}
            <Modal
                title={`Stock Adjustment — ${selectedMaterial?.name}`}
                open={stockModalVisible}
                onOk={handleStockAdjust}
                onCancel={() => { setStockModalVisible(false); stockForm.resetFields(); }}
                okText="Save"
            >
                {selectedMaterial && (
                    <div style={{ marginBottom: 16 }}>
                        <Tag>Current Stock: {selectedMaterial.current_stock} {selectedMaterial.unit_of_measure}</Tag>
                    </div>
                )}
                <Form form={stockForm} layout="vertical">
                    <Form.Item name="movement_type" label="Movement Type" rules={[{ required: true }]}>
                        <Select>
                            <Option value="IN">
                                <Tag color="green">IN — Add Stock</Tag>
                            </Option>
                            <Option value="OUT">
                                <Tag color="red">OUT — Remove Stock</Tag>
                            </Option>
                        </Select>
                    </Form.Item>
                    <Form.Item name="quantity" label="Quantity" rules={[{ required: true }]}>
                        <InputNumber style={{ width: '100%' }} min={0.001} precision={3} />
                    </Form.Item>
                    <Form.Item name="unit_cost" label="Unit Cost (KD)" initialValue={selectedMaterial?.unit_cost || 0}>
                        <InputNumber style={{ width: '100%' }} min={0} precision={3} />
                    </Form.Item>
                    <Form.Item name="notes" label="Notes">
                        <Input.TextArea rows={2} placeholder="Reason for adjustment..." />
                    </Form.Item>
                </Form>
            </Modal>

            {/* Movements History Drawer */}
            <Drawer
                title={`Stock Movements — ${selectedMaterial?.name}`}
                open={movementsDrawerVisible}
                onClose={() => setMovementsDrawerVisible(false)}
                width={700}
            >
                {movements.length === 0 && !movementsLoading
                    ? <Empty description="No movements recorded" />
                    : (
                        <Table
                            columns={movementColumns}
                            dataSource={movements}
                            rowKey="uid"
                            loading={movementsLoading}
                            size="small"
                            pagination={{ pageSize: 15 }}
                        />
                    )
                }
            </Drawer>
        </div>
    );
};

export default MaterialsList;
