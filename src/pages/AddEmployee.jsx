// src/pages/AddEmployee.jsx

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';
import {
    Card, Form, Tabs, Button, Input, InputNumber, Select, DatePicker,
    Upload, Avatar, Radio, Alert, Row, Col, Space, Typography, message
} from 'antd';
import {
    UserOutlined, UploadOutlined, WarningOutlined, SaveOutlined
} from '@ant-design/icons';
import Swal from 'sweetalert2';

import {
    addEmployee, getManagers, getDesignations,
    uploadEmployeePhoto, uploadEmployeeDocument
} from '../services/apiService';
import { useAuth } from '../context/AuthContext';

const { TextArea } = Input;
const { Option } = Select;
const { Title } = Typography;

const AddEmployeePage = () => {
    const { user } = useAuth();
    const navigate = useNavigate();
    const [form] = Form.useForm();

    const isHighLevelAdmin = user?.role === 'SuperAdmin' || user?.role === 'Admin';

    const [employeeType, setEmployeeType] = useState('Company');
    const [managers, setManagers] = useState([]);
    const [designations, setDesignations] = useState([]);
    const [photoFile, setPhotoFile] = useState(null);
    const [photoPreview, setPhotoPreview] = useState(null);
    const [documentFiles, setDocumentFiles] = useState({});
    const [expiryWarnings, setExpiryWarnings] = useState({});
    const [isLoading, setIsLoading] = useState(false);
    const [activeTab, setActiveTab] = useState('1');

    useEffect(() => {
        if (isHighLevelAdmin) {
            getManagers()
                .then(data => setManagers(data || []))
                .catch(() => setManagers([]));
            getDesignations()
                .then(data => setDesignations(data || []))
                .catch(() => setDesignations([]));
        }
    }, [isHighLevelAdmin]);

    const checkExpiry = (dateValue, docType) => {
        if (!dateValue) {
            setExpiryWarnings(prev => ({ ...prev, [docType]: null }));
            return;
        }
        const today = dayjs();
        // dateValue may be a dayjs object (from DatePicker) or a string — handle both
        const expiry = dayjs.isDayjs(dateValue) ? dateValue : dayjs(dateValue);
        const daysUntilExpiry = expiry.diff(today, 'day');
        if (daysUntilExpiry < 0) {
            setExpiryWarnings(prev => ({ ...prev, [docType]: 'EXPIRED' }));
        } else if (daysUntilExpiry < 30) {
            setExpiryWarnings(prev => ({ ...prev, [docType]: `Expires in ${daysUntilExpiry} days` }));
        } else {
            setExpiryWarnings(prev => ({ ...prev, [docType]: null }));
        }
    };

    const handlePhotoChange = ({ fileList }) => {
        if (fileList.length > 0) {
            const file = fileList[0].originFileObj;
            setPhotoFile(file);
            const reader = new FileReader();
            reader.onload = (e) => setPhotoPreview(e.target.result);
            reader.readAsDataURL(file);
        } else {
            setPhotoFile(null);
            setPhotoPreview(null);
        }
    };

    const handleDocumentChange = (docType, { fileList }) => {
        if (fileList.length > 0) {
            setDocumentFiles(prev => ({ ...prev, [docType]: fileList[0].originFileObj }));
        } else {
            setDocumentFiles(prev => { const n = { ...prev }; delete n[docType]; return n; });
        }
    };

    const handleSubmit = async () => {
        try {
            const values = await form.validateFields();
            setIsLoading(true);

            const formData = new FormData();
            formData.append('name', values.name);
            formData.append('designation', values.designation || '');
            formData.append('employee_type', employeeType);
            formData.append('basic_salary', values.basic_salary ?? 0);
            formData.append('standard_work_days', values.standard_work_days ?? 28);
            formData.append('allowance', values.allowance ?? 0);
            formData.append('default_hourly_rate', values.default_hourly_rate ?? 0);
            formData.append('status', values.status || 'Active');

            if (values.nationality) formData.append('nationality', values.nationality);
            if (values.permanent_address) formData.append('permanent_address', values.permanent_address);
            if (values.phone_kuwait) formData.append('phone_kuwait', values.phone_kuwait);
            if (values.phone_home_country) formData.append('phone_home_country', values.phone_home_country);
            if (values.emergency_contact_name) formData.append('emergency_contact_name', values.emergency_contact_name);
            if (values.emergency_contact_number) formData.append('emergency_contact_number', values.emergency_contact_number);
            if (values.civil_id_number) formData.append('civil_id_number', values.civil_id_number);
            if (values.civil_id_expiry) formData.append('civil_id_expiry', values.civil_id_expiry.format('YYYY-MM-DD'));
            if (values.passport_number) formData.append('passport_number', values.passport_number);
            if (values.passport_expiry) formData.append('passport_expiry', values.passport_expiry.format('YYYY-MM-DD'));
            if (values.date_of_joining) formData.append('date_of_joining', values.date_of_joining.format('YYYY-MM-DD'));
            if (values.date_of_birth) formData.append('date_of_birth', values.date_of_birth.format('YYYY-MM-DD'));
            if (values.contract_end_date) formData.append('contract_end_date', values.contract_end_date.format('YYYY-MM-DD'));
            if (isHighLevelAdmin && values.manager_id) formData.append('manager_id', values.manager_id);

            const newEmployee = await addEmployee(formData);
            const empId = newEmployee.id || newEmployee.uid;

            // Upload photo if selected
            if (photoFile && empId) {
                try {
                    await uploadEmployeePhoto(empId, photoFile);
                } catch (e) {
                    console.warn('Photo upload failed:', e);
                }
            }

            // Upload documents if selected
            for (const [docType, file] of Object.entries(documentFiles)) {
                if (file && empId) {
                    try {
                        await uploadEmployeeDocument(empId, docType, file);
                    } catch (e) {
                        console.warn(`Document upload failed (${docType}):`, e);
                    }
                }
            }

            await Swal.fire({
                title: 'Success!',
                text: 'Employee added successfully.',
                icon: 'success',
                confirmButtonText: 'Great!',
                confirmButtonColor: '#3085d6',
                timer: 3000,
                timerProgressBar: true,
            });

            navigate('/employees');
        } catch (err) {
            if (err?.errorFields) {
                message.error('Please fill in all required fields.');
                return;
            }
            Swal.fire({
                icon: 'error',
                title: 'Submission Failed',
                text: err.message || 'Failed to add employee.',
                confirmButtonColor: '#d33',
            });
        } finally {
            setIsLoading(false);
        }
    };

    const ExpiryWarning = ({ docType }) => {
        const warning = expiryWarnings[docType];
        if (!warning) return null;
        return (
            <Alert
                type={warning === 'EXPIRED' ? 'error' : 'warning'}
                title={warning}
                showIcon
                icon={<WarningOutlined />}
                style={{ marginTop: 8 }}
            />
        );
    };

    const tabItems = [
        {
            key: '1',
            label: 'Personal Details',
            children: (
                <Row gutter={24}>
                    <Col xs={24} md={8} style={{ textAlign: 'center', marginBottom: 24 }}>
                        <Form.Item label="Employee Photo">
                            <Upload
                                accept="image/*"
                                maxCount={1}
                                beforeUpload={() => false}
                                onChange={handlePhotoChange}
                                showUploadList={false}
                            >
                                <div style={{ cursor: 'pointer' }}>
                                    <Avatar
                                        size={120}
                                        src={photoPreview}
                                        icon={<UserOutlined />}
                                        style={{ marginBottom: 8 }}
                                    />
                                    <br />
                                    <Button icon={<UploadOutlined />} size="small">Upload Photo</Button>
                                </div>
                            </Upload>
                        </Form.Item>
                    </Col>
                    <Col xs={24} md={16}>
                        <Form.Item label="Employee Type" required>
                            <Radio.Group value={employeeType} onChange={e => setEmployeeType(e.target.value)}>
                                <Radio value="Company">Company Employee</Radio>
                                <Radio value="Outsourced">Outsourced Employee</Radio>
                            </Radio.Group>
                        </Form.Item>
                        <Form.Item name="name" label="Full Name" rules={[{ required: true, message: 'Full name is required' }]}>
                            <Input placeholder="Enter full name" />
                        </Form.Item>
                        <Form.Item name="date_of_birth" label="Date of Birth">
                            <DatePicker style={{ width: '100%' }} />
                        </Form.Item>
                        <Form.Item name="nationality" label="Nationality">
                            <Input placeholder="e.g. Indian, Pakistani" />
                        </Form.Item>
                        <Form.Item name="permanent_address" label="Permanent Address">
                            <TextArea rows={3} placeholder="Home country address" />
                        </Form.Item>
                    </Col>
                </Row>
            )
        },
        {
            key: '2',
            label: 'Contact Info',
            children: (
                <Row gutter={24}>
                    <Col xs={24} md={12}>
                        <Form.Item name="phone_kuwait" label="Phone (Kuwait)">
                            <Input placeholder="+965 XXXX XXXX" />
                        </Form.Item>
                        <Form.Item name="phone_home_country" label="Phone (Home Country)">
                            <Input placeholder="+XX XXXX XXXXXX" />
                        </Form.Item>
                    </Col>
                    <Col xs={24} md={12}>
                        <Form.Item name="emergency_contact_name" label="Emergency Contact Name">
                            <Input placeholder="Contact person name" />
                        </Form.Item>
                        <Form.Item name="emergency_contact_number" label="Emergency Contact Number">
                            <Input placeholder="+XX XXXX XXXXXX" />
                        </Form.Item>
                    </Col>
                </Row>
            )
        },
        {
            key: '3',
            label: 'Documents',
            children: (
                <Row gutter={16}>
                    <Col xs={24} md={8}>
                        <Card title="Civil ID" size="small" style={{ marginBottom: 16 }}>
                            <Form.Item name="civil_id_number" label="Civil ID Number">
                                <Input placeholder="Civil ID number" />
                            </Form.Item>
                            <Form.Item name="civil_id_expiry" label="Expiry Date">
                                <DatePicker
                                    style={{ width: '100%' }}
                                    onChange={(date) => checkExpiry(date, 'civil_id')}
                                />
                            </Form.Item>
                            <ExpiryWarning docType="civil_id" />
                            <Form.Item label="Civil ID PDF">
                                <Upload
                                    accept=".pdf"
                                    maxCount={1}
                                    beforeUpload={() => false}
                                    onChange={(info) => handleDocumentChange('civil_id', info)}
                                >
                                    <Button icon={<UploadOutlined />}>Upload PDF</Button>
                                </Upload>
                            </Form.Item>
                        </Card>
                    </Col>
                    <Col xs={24} md={8}>
                        <Card title="Passport" size="small" style={{ marginBottom: 16 }}>
                            <Form.Item name="passport_number" label="Passport Number">
                                <Input placeholder="Passport number" />
                            </Form.Item>
                            <Form.Item name="passport_expiry" label="Expiry Date">
                                <DatePicker
                                    style={{ width: '100%' }}
                                    onChange={(date) => checkExpiry(date, 'passport')}
                                />
                            </Form.Item>
                            <ExpiryWarning docType="passport" />
                            <Form.Item label="Passport PDF">
                                <Upload
                                    accept=".pdf"
                                    maxCount={1}
                                    beforeUpload={() => false}
                                    onChange={(info) => handleDocumentChange('passport', info)}
                                >
                                    <Button icon={<UploadOutlined />}>Upload PDF</Button>
                                </Upload>
                            </Form.Item>
                        </Card>
                    </Col>
                    <Col xs={24} md={8}>
                        <Card title="Visa" size="small" style={{ marginBottom: 16 }}>
                            <Form.Item label="Visa Document (PDF)">
                                <Upload
                                    accept=".pdf"
                                    maxCount={1}
                                    beforeUpload={() => false}
                                    onChange={(info) => handleDocumentChange('visa', info)}
                                >
                                    <Button icon={<UploadOutlined />}>Upload PDF</Button>
                                </Upload>
                            </Form.Item>
                        </Card>
                    </Col>
                </Row>
            )
        },
        {
            key: '4',
            label: 'Employment',
            children: (
                <Row gutter={24}>
                    <Col xs={24} md={12}>
                        <Form.Item
                            name="designation"
                            label="Designation"
                            rules={[{ required: true, message: 'Designation is required' }]}
                        >
                            {designations.length > 0 ? (
                                <Select placeholder="Select designation" showSearch>
                                    {designations.map(d => (
                                        <Option key={d.id} value={d.title}>{d.title}</Option>
                                    ))}
                                </Select>
                            ) : (
                                <Input placeholder="Job title / role" />
                            )}
                        </Form.Item>
                        <Form.Item name="date_of_joining" label="Date of Joining">
                            <DatePicker style={{ width: '100%' }} />
                        </Form.Item>
                        {employeeType === 'Outsourced' && (
                            <Form.Item name="contract_end_date" label="Contract End Date">
                                <DatePicker style={{ width: '100%' }} />
                            </Form.Item>
                        )}
                        <Form.Item name="status" label="Status" initialValue="Active">
                            <Select>
                                <Option value="Active">Active</Option>
                                <Option value="Inactive">Inactive</Option>
                            </Select>
                        </Form.Item>
                        {isHighLevelAdmin && (
                            <Form.Item name="manager_id" label="Assign Reporting Manager">
                                <Select placeholder="Select Manager (Optional)" allowClear>
                                    {managers.map(m => (
                                        <Option key={m.id} value={m.id}>{m.full_name}</Option>
                                    ))}
                                </Select>
                            </Form.Item>
                        )}
                    </Col>
                    <Col xs={24} md={12}>
                        {employeeType === 'Company' ? (
                            <>
                                <Form.Item
                                    name="basic_salary"
                                    label="Monthly Salary (KD)"
                                    rules={[{ required: true, message: 'Salary is required for Company employees' }]}
                                >
                                    <InputNumber style={{ width: '100%' }} min={0} step={0.01} precision={2} />
                                </Form.Item>
                                <Form.Item name="standard_work_days" label="Standard Work Days" initialValue={28}>
                                    <InputNumber style={{ width: '100%' }} min={1} max={31} />
                                </Form.Item>
                            </>
                        ) : (
                            <Form.Item
                                name="default_hourly_rate"
                                label="Hourly Rate (KD)"
                                rules={[{ required: true, message: 'Hourly rate is required for Outsourced employees' }]}
                            >
                                <InputNumber style={{ width: '100%' }} min={0} step={0.01} precision={4} />
                            </Form.Item>
                        )}
                        <Form.Item name="allowance" label="Allowance (KD)" initialValue={0}>
                            <InputNumber style={{ width: '100%' }} min={0} step={0.01} precision={2} />
                        </Form.Item>
                    </Col>
                </Row>
            )
        }
    ];

    return (
        <div style={{ padding: '24px' }}>
            <Card
                title={<Title level={4} style={{ margin: 0 }}>Add New Employee</Title>}
                extra={
                    <Space>
                        <Button onClick={() => navigate('/employees')}>Cancel</Button>
                        <Button
                            type="primary"
                            icon={<SaveOutlined />}
                            loading={isLoading}
                            onClick={handleSubmit}
                        >
                            Create Employee
                        </Button>
                    </Space>
                }
            >
                <Form form={form} layout="vertical">
                    <Tabs
                        activeKey={activeTab}
                        onChange={setActiveTab}
                        items={tabItems}
                    />
                </Form>
            </Card>
        </div>
    );
};

export default AddEmployeePage;