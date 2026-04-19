// src/pages/Inventory/SuppliersList.jsx
// Supplier management page

import React, { useState, useEffect } from 'react';
import {
    Card, Table, Button, Space, Modal, Form, Input,
    message, Popconfirm, Typography, Row, Col, Statistic,
} from 'antd';
import {
    PlusOutlined, EditOutlined, DeleteOutlined, ShopOutlined,
} from '@ant-design/icons';
import {
    getSuppliers, createSupplier, updateSupplier, deleteSupplier,
} from '../../services/apiService';

const { Title, Text } = Typography;

const SuppliersList = () => {
    const [suppliers, setSuppliers] = useState([]);
    const [loading, setLoading] = useState(false);
    const [createModalVisible, setCreateModalVisible] = useState(false);
    const [editModalVisible, setEditModalVisible] = useState(false);
    const [selectedSupplier, setSelectedSupplier] = useState(null);
    const [form] = Form.useForm();

    const fetchSuppliers = async () => {
        setLoading(true);
        try {
            const data = await getSuppliers();
            setSuppliers(Array.isArray(data) ? data : []);
        } catch {
            message.error('Failed to load suppliers');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { fetchSuppliers(); }, []);

    const handleCreate = async () => {
        try {
            const values = await form.validateFields();
            await createSupplier(values);
            message.success('Supplier created successfully');
            setCreateModalVisible(false);
            form.resetFields();
            fetchSuppliers();
        } catch (err) {
            if (err?.errorFields) return;
            message.error(err.message || 'Failed to create supplier');
        }
    };

    const handleEdit = async () => {
        try {
            const values = await form.validateFields();
            await updateSupplier(selectedSupplier.uid, values);
            message.success('Supplier updated');
            setEditModalVisible(false);
            form.resetFields();
            fetchSuppliers();
        } catch (err) {
            if (err?.errorFields) return;
            message.error(err.message || 'Failed to update supplier');
        }
    };

    const handleDelete = async (uid) => {
        try {
            await deleteSupplier(uid);
            message.success('Supplier deleted');
            fetchSuppliers();
        } catch (err) {
            message.error(err.message || 'Failed to delete supplier');
        }
    };

    const openEditModal = (supplier) => {
        setSelectedSupplier(supplier);
        form.setFieldsValue({
            name: supplier.name,
            contact_person: supplier.contact_person,
            phone: supplier.phone,
            email: supplier.email,
            address: supplier.address,
        });
        setEditModalVisible(true);
    };

    const columns = [
        {
            title: 'Code',
            dataIndex: 'supplier_code',
            key: 'supplier_code',
            render: (v) => <Text code>{v}</Text>,
        },
        {
            title: 'Company Name',
            dataIndex: 'name',
            key: 'name',
            render: (v) => <strong>{v}</strong>,
        },
        {
            title: 'Contact Person',
            dataIndex: 'contact_person',
            key: 'contact_person',
            render: (v) => v || '—',
        },
        {
            title: 'Phone',
            dataIndex: 'phone',
            key: 'phone',
            render: (v) => v || '—',
        },
        {
            title: 'Email',
            dataIndex: 'email',
            key: 'email',
            render: (v) => v || '—',
        },
        {
            title: 'Address',
            dataIndex: 'address',
            key: 'address',
            render: (v) => v || '—',
            ellipsis: true,
        },
        {
            title: 'Actions',
            key: 'actions',
            render: (_, record) => (
                <Space size="small">
                    <Button size="small" icon={<EditOutlined />} onClick={() => openEditModal(record)} />
                    <Popconfirm
                        title="Delete this supplier?"
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

    const supplierFormFields = (
        <>
            <Form.Item name="supplier_code" label="Supplier Code" rules={[{ required: true }]}>
                <Input placeholder="e.g. SUP-001" />
            </Form.Item>
            <Form.Item name="name" label="Company Name" rules={[{ required: true }]}>
                <Input placeholder="e.g. Al-Sayer Building Materials" />
            </Form.Item>
            <Row gutter={12}>
                <Col span={12}>
                    <Form.Item name="contact_person" label="Contact Person">
                        <Input placeholder="e.g. Ahmed Al-Sayer" />
                    </Form.Item>
                </Col>
                <Col span={12}>
                    <Form.Item name="phone" label="Phone">
                        <Input placeholder="+965 XXXX XXXX" />
                    </Form.Item>
                </Col>
            </Row>
            <Form.Item name="email" label="Email">
                <Input type="email" placeholder="contact@supplier.com" />
            </Form.Item>
            <Form.Item name="address" label="Address">
                <Input.TextArea rows={2} placeholder="Supplier address..." />
            </Form.Item>
        </>
    );

    return (
        <div style={{ padding: '0 24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                <Title level={4} style={{ margin: 0 }}>
                    <ShopOutlined style={{ marginRight: 8 }} />
                    Suppliers
                </Title>
                <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModalVisible(true)}>
                    Add Supplier
                </Button>
            </div>

            <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
                <Col xs={12} sm={6}>
                    <Card size="small">
                        <Statistic title="Total Suppliers" value={suppliers.length} />
                    </Card>
                </Col>
            </Row>

            <Card>
                <Table
                    columns={columns}
                    dataSource={suppliers}
                    rowKey="uid"
                    loading={loading}
                    pagination={{ pageSize: 20 }}
                    size="small"
                />
            </Card>

            {/* Create Supplier Modal */}
            <Modal
                title="Add New Supplier"
                open={createModalVisible}
                onOk={handleCreate}
                onCancel={() => { setCreateModalVisible(false); form.resetFields(); }}
                okText="Create"
                width={550}
            >
                <Form form={form} layout="vertical">
                    {supplierFormFields}
                </Form>
            </Modal>

            {/* Edit Supplier Modal */}
            <Modal
                title="Edit Supplier"
                open={editModalVisible}
                onOk={handleEdit}
                onCancel={() => { setEditModalVisible(false); form.resetFields(); }}
                okText="Save"
                width={550}
            >
                <Form form={form} layout="vertical">
                    <Form.Item name="name" label="Company Name" rules={[{ required: true }]}>
                        <Input />
                    </Form.Item>
                    <Row gutter={12}>
                        <Col span={12}>
                            <Form.Item name="contact_person" label="Contact Person">
                                <Input />
                            </Form.Item>
                        </Col>
                        <Col span={12}>
                            <Form.Item name="phone" label="Phone">
                                <Input />
                            </Form.Item>
                        </Col>
                    </Row>
                    <Form.Item name="email" label="Email">
                        <Input type="email" />
                    </Form.Item>
                    <Form.Item name="address" label="Address">
                        <Input.TextArea rows={2} />
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    );
};

export default SuppliersList;
