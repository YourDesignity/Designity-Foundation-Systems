import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';
import { 
  Table, Card, Input, Select, Button, Space, Avatar, Typography, Tag, Row, Col, Modal, Form, message, Badge, Tooltip, Upload
} from 'antd';
import { 
  SearchOutlined, PlusOutlined, FileTextOutlined, 
  EditOutlined, DeleteOutlined, UserOutlined, EyeOutlined, WarningOutlined, UploadOutlined
} from '@ant-design/icons';
// --- Services ---
import { 
    createPayslips, getManagers
} from '../services/apiService';
import { employeeService } from '../services';
import websocketService from '../services/websocketService';
import { useAuth } from '../context/AuthContext'; 

// --- Typography Extraction ---
const { Title, Text } = Typography;
const { Option } = Select;

function checkDocExpiry(dateStr) {
    if (!dateStr) return false;
    return dayjs(dateStr).diff(dayjs(), 'day') < 30;
}

function EmployeesPage() {
    const navigate = useNavigate();
    const { user } = useAuth(); 
    const [form] = Form.useForm();

    const [employees, setEmployees] = useState([]);
    const [managers, setManagers] = useState([]); 
    const [loading, setLoading] = useState(true);
    
    const [searchText, setSearchText] = useState('');
    const [selectedDesignation, setSelectedDesignation] = useState('all');
    const [selectedType, setSelectedType] = useState('all');
    const [selectedRowKeys, setSelectedRowKeys] = useState([]);

    const [isEditModalOpen, setIsEditModalOpen] = useState(false);
    const [editingEmployee, setEditingEmployee] = useState(null);
    const [isPayslipLoading, setIsPayslipLoading] = useState(false);
    const [editPhotoFile, setEditPhotoFile] = useState(null);
    const [editPhotoPreview, setEditPhotoPreview] = useState(null);

    const isHighLevelAdmin = user?.role === 'SuperAdmin' || user?.role === 'Admin';

    // --- 1. Load Data Function ---
    const loadData = useCallback(async () => {
        if (!user) return;
        try {
            setLoading(true);

            // Backend already filters employees by manager_id for Site Manager role
            const promises = [employeeService.getAll()];
            if (isHighLevelAdmin) promises.push(getManagers());

            const results = await Promise.all(promises);
            const empData = results[0] || [];
            const adminData = isHighLevelAdmin ? (results[1] || []) : [];

            setEmployees(empData);
            if (isHighLevelAdmin) {
                setManagers(adminData);
            }
        } catch (e) {
            console.error("Load Error:", e);
            message.error("Failed to sync workforce data");
        } finally {
            setLoading(false);
        }
    }, [user, isHighLevelAdmin]);

    // --- 2. Lifecycle & WebSockets ---
    useEffect(() => {
        loadData();

        const handleWsMessage = (data) => {
            if (['employee_update', 'duty_update', 'employee_delete'].includes(data.type)) {
                loadData();
            }
        };

        websocketService.register(handleWsMessage);

        return () => {
            websocketService.unregister();
        };
    }, [loadData]);

    // --- 3. Filtering Logic ---
    const designations = useMemo(() => {
        const counts = {};
        employees.forEach(emp => {
            if(emp.designation) counts[emp.designation] = (counts[emp.designation] || 0) + 1;
        });
        return counts;
    }, [employees]);

    const filteredEmployees = useMemo(() => {
        return employees.filter(emp => {
            const matchesSearch = emp.name?.toLowerCase().includes(searchText.toLowerCase()) || 
                                  emp.designation?.toLowerCase().includes(searchText.toLowerCase());
            const matchesRole = selectedDesignation === 'all' || emp.designation === selectedDesignation;
            const matchesType = selectedType === 'all' || emp.employee_type === selectedType;
            return matchesSearch && matchesRole && matchesType;
        });
    }, [employees, searchText, selectedDesignation, selectedType]);

    // --- 4. Handlers ---
    const handleCreatePayslips = async () => {
        if (selectedRowKeys.length === 0) return;
        setIsPayslipLoading(true);
        try {
            await createPayslips(selectedRowKeys);
            message.success('Payslips generated for selected team members');
            setSelectedRowKeys([]);
        } catch (err) { 
            message.error(err.message || "Failed to generate payslips"); 
        } finally { 
            setIsPayslipLoading(false); 
        }
    };

    const handleDelete = (id) => {
        Modal.confirm({
            title: 'Delete Employee',
            content: 'Removing this employee will delete their historical records. Proceed?',
            okText: 'Delete',
            okType: 'danger',
            onOk: async () => {
                try {
                    await employeeService.remove(id);
                    message.success("Employee removed successfully");
                    loadData();
                } catch (err) { message.error("Delete failed"); }
            }
        });
    };

    const openEditModal = (record) => {
        setEditingEmployee(record);
        form.setFieldsValue(record);
        if (record.photo_path) {
            setEditPhotoPreview(employeeService.getPhotoUrl(record.id || record.uid));
        } else {
            setEditPhotoPreview(null);
        }
        setEditPhotoFile(null);
        setIsEditModalOpen(true);
    };

    const handleEditPhotoChange = ({ fileList }) => {
        if (fileList.length > 0) {
            const file = fileList[0].originFileObj;
            setEditPhotoFile(file);
            const reader = new FileReader();
            reader.onload = (e) => setEditPhotoPreview(e.target.result);
            reader.readAsDataURL(file);
        } else {
            setEditPhotoFile(null);
            setEditPhotoPreview(null);
        }
    };

    const handleSaveEdit = async () => {
        try {
            const vals = await form.validateFields();
            const empId = editingEmployee.id || editingEmployee.uid;
            await employeeService.update(empId, vals);
            if (editPhotoFile) {
                try {
                    await employeeService.uploadPhoto(empId, editPhotoFile);
                    message.success("Employee details and photo updated");
                } catch (e) {
                    console.warn('Photo upload failed:', e);
                    message.warning("Employee details updated, but photo upload failed");
                }
            } else {
                message.success("Employee details updated");
            }
            setIsEditModalOpen(false);
            setEditPhotoFile(null);
            setEditPhotoPreview(null);
            loadData();
        } catch (err) {
            console.error("Update failed:", err);
            message.error("Failed to update employee details. Please try again.");
        }
    };

    const columns = [
        {
            title: 'Workforce Member',
            dataIndex: 'name',
            key: 'name',
            render: (text, record) => (
                <Space>
                    <Avatar 
                        shape="square" 
                        icon={<UserOutlined />} 
                        src={record.photo_path ? employeeService.getPhotoUrl(record.id || record.uid) : null}
                        onError={() => true}
                    />
                    <div>
                        <Text strong style={{ display: 'block' }}>{text}</Text>
                        <Text type="secondary" style={{ fontSize: 12 }}>{record.designation}</Text>
                    </div>
                </Space>
            )
        },
        {
            title: 'Type',
            dataIndex: 'employee_type',
            key: 'employee_type',
            render: (type) => (
                <Tag color={type === 'Outsourced' ? 'orange' : 'blue'}>
                    {type || 'Company'}
                </Tag>
            )
        },
        {
            title: 'Finance Status',
            key: 'finance',
            render: (_, r) => (
                <Space>
                    <Tag color="blue">
                        {r.employee_type === 'Outsourced'
                            ? `Rate: ${(r.default_hourly_rate ?? 0).toFixed(4)} KD/hr`
                            : `Salary: ${r.basic_salary} KD`}
                    </Tag>
                    {r.allowance > 0 && <Tag color="cyan">Allow: {r.allowance} KD</Tag>}
                </Space>
            )
        },
        {
            title: 'Documents',
            key: 'documents',
            render: (_, record) => {
                const civilExpiring = checkDocExpiry(record.civil_id_expiry);
                const passportExpiring = checkDocExpiry(record.passport_expiry);
                if (!civilExpiring && !passportExpiring) return <Text type="secondary" style={{ fontSize: 12 }}>—</Text>;
                return (
                    <Space size={4}>
                        {civilExpiring && (
                            <Tooltip title={`Civil ID expiry: ${record.civil_id_expiry || 'expired'}`}>
                                <Tag color="red" icon={<WarningOutlined />}>Civil ID</Tag>
                            </Tooltip>
                        )}
                        {passportExpiring && (
                            <Tooltip title={`Passport expiry: ${record.passport_expiry || 'expired'}`}>
                                <Tag color="red" icon={<WarningOutlined />}>Passport</Tag>
                            </Tooltip>
                        )}
                    </Space>
                );
            }
        },
        {
            title: 'Actions',
            align: 'right',
            render: (_, record) => (
                <Space>
                    <Button
                        type="text"
                        icon={<EyeOutlined />}
                        onClick={() => navigate(`/employees/${record.id || record.uid}`)}
                    />
                    {isHighLevelAdmin && (
                        <Button type="text" icon={<EditOutlined />} onClick={() => openEditModal(record)} />
                    )}
                    {isHighLevelAdmin && (
                        <Button type="text" danger icon={<DeleteOutlined />} onClick={() => handleDelete(record.id || record.uid)} />
                    )}
                </Space>
            )
        }
    ];

    return (
        <div className="layout-content">
            <Card variant="borderless" style={{ marginBottom: 24 }}>
                <Row gutter={[16, 16]}>
                    <Col xs={24}>
                        <Title level={4} style={{ margin: 0 }}>
                            {isHighLevelAdmin ? "Workforce Grid" : "My Assigned Team"}
                        </Title>
                    </Col>
                    <Col xs={24}>
                        <Row gutter={[8, 8]} justify="space-between" align="middle">
                            <Col xs={24} sm={24} md={16} lg={16}>
                                <Space wrap size={8} style={{ width: '100%' }}>
                                    <Input 
                                        placeholder="Search employees..." 
                                        prefix={<SearchOutlined />} 
                                        onChange={e => setSearchText(e.target.value)}
                                        style={{ width: 200, minWidth: 150 }}
                                    />
                                    <Select value={selectedDesignation} onChange={setSelectedDesignation} style={{ width: 150, minWidth: 120 }}>
                                        <Option value="all">All Roles</Option>
                                        {Object.keys(designations).map(role => (
                                            <Option key={role} value={role}>{role}</Option>
                                        ))}
                                    </Select>
                                    <Select value={selectedType} onChange={setSelectedType} style={{ width: 160, minWidth: 120 }}>
                                        <Option value="all">All Types</Option>
                                        <Option value="Company">Company</Option>
                                        <Option value="Outsourced">Outsourced</Option>
                                    </Select>
                                </Space>
                            </Col>
                            <Col xs={24} sm={24} md={8} lg={8} style={{ textAlign: 'right' }}>
                                {isHighLevelAdmin && (
                                    <Button 
                                        type="primary" 
                                        icon={<PlusOutlined />} 
                                        onClick={() => navigate('/add-employee')}
                                        style={{ minWidth: 140 }}
                                    >
                                        Add Employee
                                    </Button>
                                )}
                            </Col>
                        </Row>
                    </Col>
                </Row>
            </Card>

            <Card variant="borderless">
                <Table 
                    columns={columns} 
                    dataSource={filteredEmployees} 
                    rowKey={(record) => record.id || record.uid}
                    loading={loading}
                    rowSelection={isHighLevelAdmin ? { 
                        selectedRowKeys, 
                        onChange: setSelectedRowKeys 
                    } : null}
                    pagination={{ pageSize: 10 }}
                />
            </Card>

            <Modal 
                title="Edit Employee Details" 
                open={isEditModalOpen} 
                onCancel={() => {
                    setIsEditModalOpen(false);
                    setEditPhotoFile(null);
                    setEditPhotoPreview(null);
                }}
                destroyOnHidden
                onOk={handleSaveEdit}
                okText="Save Changes"
                width={700}
            >
                <Form form={form} layout="vertical">
                    <Row gutter={16} style={{ marginBottom: 16 }}>
                        <Col span={24} style={{ textAlign: 'center' }}>
                            <Form.Item label="Employee Photo">
                                <Upload
                                    accept="image/*"
                                    maxCount={1}
                                    beforeUpload={() => false}
                                    onChange={handleEditPhotoChange}
                                    showUploadList={false}
                                >
                                    <div style={{ cursor: 'pointer' }}>
                                        <Avatar
                                            size={100}
                                            src={editPhotoPreview}
                                            icon={<UserOutlined />}
                                            style={{ marginBottom: 8 }}
                                        />
                                        <br />
                                        <Button icon={<UploadOutlined />} size="small">
                                            {editPhotoPreview ? 'Change Photo' : 'Upload Photo'}
                                        </Button>
                                    </div>
                                </Upload>
                            </Form.Item>
                        </Col>
                    </Row>
                    <Form.Item name="name" label="Full Name" rules={[{ required: true }]}><Input /></Form.Item>
                    <Form.Item name="designation" label="Designation" rules={[{ required: true }]}><Input /></Form.Item>
                    <Form.Item name="employee_type" label="Employee Type">
                        <Select>
                            <Option value="Company">Company</Option>
                            <Option value="Outsourced">Outsourced</Option>
                        </Select>
                    </Form.Item>
                    
                    {isHighLevelAdmin && (
                        <Form.Item name="manager_id" label="Assign Reporting Manager">
                            <Select placeholder="Select Manager" allowClear>
                                {managers.map(m => (
                                    <Option key={m.id} value={m.id}>{m.full_name}</Option>
                                ))}
                            </Select>
                        </Form.Item>
                    )}

                    <Row gutter={16}>
                        <Col span={12}><Form.Item name="basic_salary" label="Basic Rate"><Input type="number" /></Form.Item></Col>
                        <Col span={12}><Form.Item name="allowance" label="Fixed Allowance"><Input type="number" /></Form.Item></Col>
                    </Row>
                    <Row gutter={16}>
                        <Col span={12}><Form.Item name="default_hourly_rate" label="Hourly Rate"><Input type="number" /></Form.Item></Col>
                        <Col span={12}><Form.Item name="standard_work_days" label="Work Days"><Input type="number" /></Form.Item></Col>
                    </Row>
                    <Row gutter={16}>
                        <Col span={12}><Form.Item name="civil_id_number" label="Civil ID No."><Input /></Form.Item></Col>
                        <Col span={12}><Form.Item name="passport_number" label="Passport No."><Input /></Form.Item></Col>
                    </Row>
                    <Row gutter={16}>
                        <Col span={12}><Form.Item name="phone_kuwait" label="Phone (Kuwait)"><Input /></Form.Item></Col>
                        <Col span={12}><Form.Item name="nationality" label="Nationality"><Input /></Form.Item></Col>
                    </Row>
                    <Form.Item name="status" label="Status">
                        <Select>
                            <Option value="Active">Active</Option>
                            <Option value="Inactive">Inactive</Option>
                        </Select>
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    );
}

export default EmployeesPage;
