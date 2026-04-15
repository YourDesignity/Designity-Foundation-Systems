// src/pages/EmployeeProfilePage.jsx

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';
import {
    Card, Row, Col, Avatar, Typography, Tag, Space, Button, Descriptions,
    Statistic, Divider, Spin, Alert, Tooltip
} from 'antd';
import {
    UserOutlined, DownloadOutlined, ArrowLeftOutlined, PhoneOutlined,
    IdcardOutlined, FileTextOutlined, CalendarOutlined
} from '@ant-design/icons';

import { getEmployeeById, downloadEmployeeDocument, getEmployeePhoto } from '../services/apiService';

const { Title, Text } = Typography;

function ExpiryBadge({ date }) {
    if (!date) return <Tag color="default">No date set</Tag>;
    const daysUntil = dayjs(date).diff(dayjs(), 'day');
    if (daysUntil < 0) return <Tag color="red">EXPIRED</Tag>;
    if (daysUntil < 30) return <Tag color="orange">Expires in {daysUntil} days</Tag>;
    return <Tag color="green">Valid — {dayjs(date).format('DD MMM YYYY')}</Tag>;
}

const EmployeeProfilePage = () => {
    const { employeeId } = useParams();
    const navigate = useNavigate();
    const [employee, setEmployee] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [photoSrc, setPhotoSrc] = useState(null);

    useEffect(() => {
        const fetchEmployee = async () => {
            if (!employeeId) return;
            try {
                setLoading(true);
                setError('');
                const data = await getEmployeeById(employeeId);
                setEmployee(data);
                if (data.photo_path) {
                    setPhotoSrc(getEmployeePhoto(data.id || data.uid));
                }
            } catch (err) {
                if (err.message?.includes('403') || err.message?.includes('Forbidden')) {
                    setError("You don't have permission to view this employee's profile.");
                } else if (err.message?.includes('404') || err.message?.includes('not found')) {
                    setError('Employee not found.');
                } else {
                    setError('Failed to fetch employee data.');
                }
            } finally {
                setLoading(false);
            }
        };
        fetchEmployee();
    }, [employeeId]);

    if (loading) {
        return (
            <div style={{ display: 'flex', justifyContent: 'center', padding: 80 }}>
                <Spin size="large" />
            </div>
        );
    }

    if (error) {
        return (
            <div style={{ padding: 24 }}>
                <Alert type="error" message={error} showIcon />
                <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/employees')} style={{ marginTop: 16 }}>
                    Back to Employees
                </Button>
            </div>
        );
    }

    if (!employee) {
        return (
            <div style={{ padding: 24 }}>
                <Alert type="warning" message="Employee not found." showIcon />
            </div>
        );
    }

    const empId = employee.id || employee.uid;

    return (
        <div style={{ padding: 24 }}>
            <Button
                icon={<ArrowLeftOutlined />}
                onClick={() => navigate('/employees')}
                style={{ marginBottom: 16 }}
            >
                Back to Employees
            </Button>
            <Button
                icon={<FileTextOutlined />}
                onClick={() => navigate(`/employees/${empId}/documents`)}
                style={{ marginBottom: 16, marginLeft: 8 }}
            >
                View Documents
            </Button>

            {/* Header Card */}
            <Card style={{ marginBottom: 16 }}>
                <Row gutter={24} align="middle">
                    <Col xs={24} md={6} style={{ textAlign: 'center' }}>
                        <Avatar
                            size={160}
                            src={photoSrc}
                            icon={<UserOutlined />}
                            style={{ border: '3px solid #f0f0f0' }}
                        />
                    </Col>
                    <Col xs={24} md={18}>
                        <Space direction="vertical" size={4}>
                            <Title level={2} style={{ margin: 0 }}>{employee.name}</Title>
                            <Space wrap>
                                <Tag color={employee.employee_type === 'Company' ? 'blue' : 'orange'} style={{ fontSize: 13 }}>
                                    {employee.employee_type || 'Company'} Employee
                                </Tag>
                                <Tag color={employee.status === 'Active' ? 'green' : 'red'} style={{ fontSize: 13 }}>
                                    {employee.status}
                                </Tag>
                            </Space>
                            <Text type="secondary" style={{ fontSize: 15 }}>
                                {employee.nationality && `${employee.nationality} • `}{employee.designation}
                            </Text>
                            {employee.date_of_joining && (
                                <Text type="secondary">
                                    <CalendarOutlined style={{ marginRight: 4 }} />
                                    Joined: {dayjs(employee.date_of_joining).format('DD MMM YYYY')}
                                </Text>
                            )}
                        </Space>
                    </Col>
                </Row>
            </Card>

            <Row gutter={16}>
                {/* Personal Details */}
                <Col xs={24} md={12}>
                    <Card title="Personal Details" style={{ marginBottom: 16 }} size="small">
                        <Descriptions column={1} size="small">
                            {employee.date_of_birth && (
                                <Descriptions.Item label="Date of Birth">
                                    {dayjs(employee.date_of_birth).format('DD MMM YYYY')}
                                </Descriptions.Item>
                            )}
                            {employee.nationality && (
                                <Descriptions.Item label="Nationality">{employee.nationality}</Descriptions.Item>
                            )}
                            {employee.permanent_address && (
                                <Descriptions.Item label="Address">{employee.permanent_address}</Descriptions.Item>
                            )}
                        </Descriptions>
                    </Card>
                </Col>

                {/* Contact Information */}
                <Col xs={24} md={12}>
                    <Card title={<><PhoneOutlined /> Contact Information</>} style={{ marginBottom: 16 }} size="small">
                        <Descriptions column={1} size="small">
                            {employee.phone_kuwait && (
                                <Descriptions.Item label="Kuwait">{employee.phone_kuwait}</Descriptions.Item>
                            )}
                            {employee.phone_home_country && (
                                <Descriptions.Item label="Home Country">{employee.phone_home_country}</Descriptions.Item>
                            )}
                            {employee.emergency_contact_name && (
                                <Descriptions.Item label="Emergency Contact">
                                    {employee.emergency_contact_name}
                                    {employee.emergency_contact_number && ` — ${employee.emergency_contact_number}`}
                                </Descriptions.Item>
                            )}
                        </Descriptions>
                    </Card>
                </Col>

                {/* Identity Documents */}
                <Col xs={24}>
                    <Card title={<><IdcardOutlined /> Identity Documents</>} style={{ marginBottom: 16 }} size="small">
                        <Row gutter={16}>
                            <Col xs={24} md={8}>
                                <Card size="small" title="Civil ID" type="inner">
                                    <Statistic
                                        title="ID Number"
                                        value={employee.civil_id_number || '—'}
                                        styles={{ content: { fontSize: 16 } }}
                                    />
                                    <div style={{ marginTop: 8 }}>
                                        <ExpiryBadge date={employee.civil_id_expiry} />
                                    </div>
                                    {employee.civil_id_document_path && (
                                        <Button
                                            size="small"
                                            icon={<DownloadOutlined />}
                                            style={{ marginTop: 8 }}
                                            onClick={() => downloadEmployeeDocument(empId, 'civil_id')}
                                        >
                                            Download
                                        </Button>
                                    )}
                                </Card>
                            </Col>
                            <Col xs={24} md={8}>
                                <Card size="small" title="Passport" type="inner">
                                    <Statistic
                                        title="Passport Number"
                                        value={employee.passport_number || '—'}
                                        styles={{ content: { fontSize: 16 } }}
                                    />
                                    <div style={{ marginTop: 8 }}>
                                        <ExpiryBadge date={employee.passport_expiry} />
                                    </div>
                                    {(employee.passport_document_path || employee.passport_path) && (
                                        <Button
                                            size="small"
                                            icon={<DownloadOutlined />}
                                            style={{ marginTop: 8 }}
                                            onClick={() => downloadEmployeeDocument(empId, 'passport')}
                                        >
                                            Download
                                        </Button>
                                    )}
                                </Card>
                            </Col>
                            <Col xs={24} md={8}>
                                <Card size="small" title="Visa" type="inner">
                                    <Statistic
                                        title="Status"
                                        value={employee.visa_document_path || employee.visa_path ? 'Document on file' : 'No document'}
                                        styles={{ content: { fontSize: 16 } }}
                                    />
                                    {(employee.visa_document_path || employee.visa_path) && (
                                        <Button
                                            size="small"
                                            icon={<DownloadOutlined />}
                                            style={{ marginTop: 8 }}
                                            onClick={() => downloadEmployeeDocument(empId, 'visa')}
                                        >
                                            Download
                                        </Button>
                                    )}
                                </Card>
                            </Col>
                        </Row>
                    </Card>
                </Col>

                {/* Financial / Employment */}
                <Col xs={24}>
                    <Card title={<><FileTextOutlined /> Employment & Finance</>} size="small">
                        <Row gutter={16}>
                            {employee.employee_type !== 'Outsourced' ? (
                                <>
                                    <Col xs={12} md={6}>
                                        <Statistic
                                            title="Monthly Salary (KD)"
                                            value={(employee.basic_salary ?? 0).toFixed(3)}
                                        />
                                    </Col>
                                    <Col xs={12} md={6}>
                                        <Statistic
                                            title="Standard Work Days"
                                            value={employee.standard_work_days ?? 28}
                                        />
                                    </Col>
                                </>
                            ) : (
                                <Col xs={12} md={6}>
                                    <Statistic
                                        title="Hourly Rate (KD)"
                                        value={(employee.default_hourly_rate ?? 0).toFixed(4)}
                                    />
                                </Col>
                            )}
                            <Col xs={12} md={6}>
                                <Statistic
                                    title="Allowance (KD)"
                                    value={(employee.allowance ?? 0).toFixed(3)}
                                />
                            </Col>
                            {employee.contract_end_date && (
                                <Col xs={12} md={6}>
                                    <Statistic
                                        title="Contract End Date"
                                        value={dayjs(employee.contract_end_date).format('DD MMM YYYY')}
                                    />
                                </Col>
                            )}
                        </Row>
                    </Card>
                </Col>
            </Row>
        </div>
    );
};

export default EmployeeProfilePage;