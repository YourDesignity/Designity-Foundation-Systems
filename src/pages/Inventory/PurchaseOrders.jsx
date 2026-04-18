// src/pages/Inventory/PurchaseOrders.jsx
// Purchase Order management — create POs, receive them, track status

import React, { useState, useEffect } from 'react';
import {
    Card, Table, Button, Tag, Space, Modal, Form, Input,
    InputNumber, Select, message, Popconfirm, Typography,
    Row, Col, Statistic, Divider, Descriptions, Empty,
} from 'antd';
import {
    PlusOutlined, DeleteOutlined, CheckCircleOutlined,
    FileTextOutlined, ShoppingCartOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import {
    getPurchaseOrders, createPurchaseOrder, receivePurchaseOrder,
    deletePurchaseOrder, getSuppliers, getMaterials,
} from '../../services/apiService';

const { Title, Text } = Typography;
const { Option } = Select;

const STATUS_COLORS = {
    pending: 'orange',
    received: 'green',
    partial: 'blue',
    cancelled: 'red',
};

const PurchaseOrders = () => {
    const [orders, setOrders] = useState([]);
    const [suppliers, setSuppliers] = useState([]);
    const [materials, setMaterials] = useState([]);
    const [loading, setLoading] = useState(false);
    const [createModalVisible, setCreateModalVisible] = useState(false);
    const [viewModalVisible, setViewModalVisible] = useState(false);
    const [selectedOrder, setSelectedOrder] = useState(null);
    const [poItems, setPoItems] = useState([{ material_id: null, quantity: 1, unit_cost: 0 }]);
    const [form] = Form.useForm();

    const fetchAll = async () => {
        setLoading(true);
        try {
            const [ordersData, suppliersData, materialsData] = await Promise.all([
                getPurchaseOrders(),
                getSuppliers(),
                getMaterials(),
            ]);
            setOrders(Array.isArray(ordersData) ? ordersData : []);
            setSuppliers(Array.isArray(suppliersData) ? suppliersData : []);
            setMaterials(Array.isArray(materialsData) ? materialsData : []);
        } catch {
            message.error('Failed to load data');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { fetchAll(); }, []);

    const handleCreate = async () => {
        try {
            const values = await form.validateFields();
            if (poItems.some(i => !i.material_id || i.quantity <= 0)) {
                message.warning('Please fill in all item fields');
                return;
            }
            const payload = {
                supplier_id: values.supplier_id,
                notes: values.notes,
                expected_delivery: values.expected_delivery || null,
                items: poItems.map(i => ({
                    material_id: i.material_id,
                    quantity: i.quantity,
                    unit_cost: i.unit_cost,
                })),
            };
            await createPurchaseOrder(payload);
            message.success('Purchase order created successfully');
            setCreateModalVisible(false);
            form.resetFields();
            setPoItems([{ material_id: null, quantity: 1, unit_cost: 0 }]);
            fetchAll();
        } catch (err) {
            if (err?.errorFields) return;
            message.error(err.message || 'Failed to create purchase order');
        }
    };

    const handleReceive = async (uid) => {
        try {
            await receivePurchaseOrder(uid);
            message.success('Purchase order received — stock updated!');
            fetchAll();
        } catch (err) {
            message.error(err.message || 'Failed to receive purchase order');
        }
    };

    const handleDelete = async (uid) => {
        try {
            await deletePurchaseOrder(uid);
            message.success('Purchase order deleted');
            fetchAll();
        } catch (err) {
            message.error(err.message || 'Failed to delete purchase order');
        }
    };

    const addPoItem = () => {
        setPoItems(prev => [...prev, { material_id: null, quantity: 1, unit_cost: 0 }]);
    };

    const removePoItem = (idx) => {
        setPoItems(prev => prev.filter((_, i) => i !== idx));
    };

    const updatePoItem = (idx, field, value) => {
        setPoItems(prev => {
            const updated = [...prev];
            updated[idx] = { ...updated[idx], [field]: value };
            // Auto-fill unit cost from material
            if (field === 'material_id' && value) {
                const mat = materials.find(m => m.uid === value);
                if (mat) updated[idx].unit_cost = mat.unit_cost;
            }
            return updated;
        });
    };

    const totalPoAmount = poItems.reduce((sum, i) => sum + (i.quantity * i.unit_cost), 0);

    const pendingCount = orders.filter(o => o.status === 'pending').length;
    const receivedCount = orders.filter(o => o.status === 'received').length;
    const totalOrdered = orders.reduce((sum, o) => sum + (o.total_amount || 0), 0);

    const columns = [
        {
            title: 'PO Number',
            dataIndex: 'po_number',
            key: 'po_number',
            render: (v) => <Text code>{v}</Text>,
        },
        {
            title: 'Supplier',
            dataIndex: 'supplier_name',
            key: 'supplier_name',
            render: (v) => v || '—',
        },
        {
            title: 'Items',
            dataIndex: 'items',
            key: 'items',
            render: (items) => `${items?.length || 0} item(s)`,
        },
        {
            title: 'Total Amount (KD)',
            dataIndex: 'total_amount',
            key: 'total_amount',
            render: (v) => v?.toFixed(3),
        },
        {
            title: 'Status',
            dataIndex: 'status',
            key: 'status',
            render: (v) => <Tag color={STATUS_COLORS[v] || 'default'}>{v?.toUpperCase()}</Tag>,
        },
        {
            title: 'Created',
            dataIndex: 'created_at',
            key: 'created_at',
            render: (v) => dayjs(v).format('DD MMM YYYY'),
        },
        {
            title: 'Actions',
            key: 'actions',
            render: (_, record) => (
                <Space size="small">
                    <Button
                        size="small"
                        icon={<FileTextOutlined />}
                        onClick={() => { setSelectedOrder(record); setViewModalVisible(true); }}
                    >
                        View
                    </Button>
                    {record.status === 'pending' && (
                        <Popconfirm
                            title="Mark this PO as received? This will update stock levels."
                            onConfirm={() => handleReceive(record.uid)}
                            okText="Yes, Receive"
                            cancelText="Cancel"
                        >
                            <Button size="small" type="primary" icon={<CheckCircleOutlined />}>
                                Receive
                            </Button>
                        </Popconfirm>
                    )}
                    {record.status === 'pending' && (
                        <Popconfirm
                            title="Delete this purchase order?"
                            onConfirm={() => handleDelete(record.uid)}
                            okText="Yes"
                            cancelText="No"
                        >
                            <Button size="small" icon={<DeleteOutlined />} danger />
                        </Popconfirm>
                    )}
                </Space>
            ),
        },
    ];

    return (
        <div style={{ padding: '0 24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                <Title level={4} style={{ margin: 0 }}>
                    <ShoppingCartOutlined style={{ marginRight: 8 }} />
                    Purchase Orders
                </Title>
                <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModalVisible(true)}>
                    Create Purchase Order
                </Button>
            </div>

            <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
                <Col xs={12} sm={6}>
                    <Card size="small"><Statistic title="Total Orders" value={orders.length} /></Card>
                </Col>
                <Col xs={12} sm={6}>
                    <Card size="small"><Statistic title="Pending" value={pendingCount} styles={{ content: { color: pendingCount > 0 ? '#fa8c16' : undefined }}} /></Card>
                </Col>
                <Col xs={12} sm={6}>
                    <Card size="small"><Statistic title="Received" value={receivedCount} styles={{ content: { color: '#52c41a' }}} /></Card>
                </Col>
                <Col xs={12} sm={6}>
                    <Card size="small"><Statistic title="Total Ordered (KD)" value={totalOrdered.toFixed(3)} /></Card>
                </Col>
            </Row>

            <Card>
                <Table
                    columns={columns}
                    dataSource={orders}
                    rowKey="uid"
                    loading={loading}
                    pagination={{ pageSize: 15 }}
                    size="small"
                />
            </Card>

            {/* Create PO Modal */}
            <Modal
                title="Create Purchase Order"
                open={createModalVisible}
                onOk={handleCreate}
                onCancel={() => {
                    setCreateModalVisible(false);
                    form.resetFields();
                    setPoItems([{ material_id: null, quantity: 1, unit_cost: 0 }]);
                }}
                okText="Create PO"
                width={700}
            >
                <Form form={form} layout="vertical">
                    <Row gutter={12}>
                        <Col span={12}>
                            <Form.Item name="supplier_id" label="Supplier" rules={[{ required: true }]}>
                                <Select placeholder="Select supplier" showSearch optionFilterProp="children">
                                    {suppliers.map(s => <Option key={s.uid} value={s.uid}>{s.name}</Option>)}
                                </Select>
                            </Form.Item>
                        </Col>
                        <Col span={12}>
                            <Form.Item name="expected_delivery" label="Expected Delivery">
                                <Input type="date" />
                            </Form.Item>
                        </Col>
                    </Row>

                    <Divider orientation="left">Items</Divider>

                    {poItems.map((item, idx) => (
                        <Row key={idx} gutter={8} style={{ marginBottom: 8 }} align="bottom">
                            <Col span={10}>
                                <Form.Item label={idx === 0 ? 'Material' : ''} style={{ marginBottom: 0 }}>
                                    <Select
                                        placeholder="Select material"
                                        value={item.material_id}
                                        onChange={(v) => updatePoItem(idx, 'material_id', v)}
                                        showSearch
                                        optionFilterProp="children"
                                    >
                                        {materials.map(m => (
                                            <Option key={m.uid} value={m.uid}>
                                                {m.name} ({m.material_code})
                                            </Option>
                                        ))}
                                    </Select>
                                </Form.Item>
                            </Col>
                            <Col span={5}>
                                <Form.Item label={idx === 0 ? 'Qty' : ''} style={{ marginBottom: 0 }}>
                                    <InputNumber
                                        style={{ width: '100%' }}
                                        min={0.001}
                                        precision={3}
                                        value={item.quantity}
                                        onChange={(v) => updatePoItem(idx, 'quantity', v)}
                                    />
                                </Form.Item>
                            </Col>
                            <Col span={6}>
                                <Form.Item label={idx === 0 ? 'Unit Cost (KD)' : ''} style={{ marginBottom: 0 }}>
                                    <InputNumber
                                        style={{ width: '100%' }}
                                        min={0}
                                        precision={3}
                                        value={item.unit_cost}
                                        onChange={(v) => updatePoItem(idx, 'unit_cost', v)}
                                    />
                                </Form.Item>
                            </Col>
                            <Col span={3}>
                                <Form.Item label={idx === 0 ? ' ' : ''} style={{ marginBottom: 0 }}>
                                    <Button
                                        danger
                                        icon={<DeleteOutlined />}
                                        onClick={() => removePoItem(idx)}
                                        disabled={poItems.length <= 1}
                                    />
                                </Form.Item>
                            </Col>
                        </Row>
                    ))}

                    <Button
                        type="dashed"
                        onClick={addPoItem}
                        icon={<PlusOutlined />}
                        style={{ width: '100%', marginBottom: 16 }}
                    >
                        Add Item
                    </Button>

                    <div style={{ textAlign: 'right', marginBottom: 16 }}>
                        <Text strong>Total Amount: KD {totalPoAmount.toFixed(3)}</Text>
                    </div>

                    <Form.Item name="notes" label="Notes">
                        <Input.TextArea rows={2} placeholder="Additional notes..." />
                    </Form.Item>
                </Form>
            </Modal>

            {/* View PO Modal */}
            <Modal
                title={`Purchase Order — ${selectedOrder?.po_number}`}
                open={viewModalVisible}
                onCancel={() => setViewModalVisible(false)}
                footer={[
                    <Button key="close" onClick={() => setViewModalVisible(false)}>Close</Button>,
                ]}
                width={600}
            >
                {selectedOrder && (
                    <>
                        <Descriptions bordered size="small" column={2}>
                            <Descriptions.Item label="PO Number">{selectedOrder.po_number}</Descriptions.Item>
                            <Descriptions.Item label="Status">
                                <Tag color={STATUS_COLORS[selectedOrder.status]}>{selectedOrder.status?.toUpperCase()}</Tag>
                            </Descriptions.Item>
                            <Descriptions.Item label="Supplier">{selectedOrder.supplier_name}</Descriptions.Item>
                            <Descriptions.Item label="Total Amount">KD {selectedOrder.total_amount?.toFixed(3)}</Descriptions.Item>
                            <Descriptions.Item label="Created">{dayjs(selectedOrder.created_at).format('DD MMM YYYY')}</Descriptions.Item>
                            {selectedOrder.received_at && (
                                <Descriptions.Item label="Received">{dayjs(selectedOrder.received_at).format('DD MMM YYYY')}</Descriptions.Item>
                            )}
                        </Descriptions>

                        <Divider orientation="left">Items</Divider>
                        <Table
                            size="small"
                            dataSource={selectedOrder.items || []}
                            rowKey="material_id"
                            pagination={false}
                            columns={[
                                { title: 'Material', dataIndex: 'material_name', render: (v, r) => `${v} (${r.material_code})` },
                                { title: 'Qty', dataIndex: 'quantity' },
                                { title: 'Unit Cost (KD)', dataIndex: 'unit_cost', render: (v) => v?.toFixed(3) },
                                { title: 'Total (KD)', dataIndex: 'total_cost', render: (v) => v?.toFixed(3) },
                            ]}
                        />

                        {selectedOrder.notes && (
                            <div style={{ marginTop: 16 }}>
                                <Text type="secondary">Notes: {selectedOrder.notes}</Text>
                            </div>
                        )}
                    </>
                )}
            </Modal>
        </div>
    );
};

export default PurchaseOrders;
