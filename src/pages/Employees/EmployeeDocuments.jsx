// src/pages/Employees/EmployeeDocuments.jsx
// Tabbed document viewer for employee documents (Visa, Passport, Civil ID)

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';
import {
    Card, Tabs, Button, Tag, Space, Typography, Spin,
    Alert, Upload, message, Modal, Descriptions, Empty,
    Row, Col,
} from 'antd';
import {
    ArrowLeftOutlined, UploadOutlined, DownloadOutlined,
    EyeOutlined, FilePdfOutlined, IdcardOutlined,
    GlobalOutlined, FileProtectOutlined,
} from '@ant-design/icons';
import {
    getEmployeeById,
    uploadEmployeeDocument,
    downloadEmployeeDocument,
    API_BASE_URL,
} from '../../services/apiService';

const { Title, Text } = Typography;

function ExpiryBadge({ date }) {
    if (!date) return <Tag color="default">No date set</Tag>;
    const daysUntil = dayjs(date).diff(dayjs(), 'day');
    if (daysUntil < 0) return <Tag color="red">EXPIRED {dayjs(date).format('DD MMM YYYY')}</Tag>;
    if (daysUntil < 30) return <Tag color="orange">Expires in {daysUntil} days — {dayjs(date).format('DD MMM YYYY')}</Tag>;
    if (daysUntil < 90) return <Tag color="gold">Valid — {dayjs(date).format('DD MMM YYYY')}</Tag>;
    return <Tag color="green">Valid — {dayjs(date).format('DD MMM YYYY')}</Tag>;
}

const DOC_TYPES = [
    {
        key: 'civil_id',
        label: 'Civil ID',
        icon: <IdcardOutlined />,
        pathField: 'civil_id_document_path',
        expiryField: 'civil_id_expiry',
        numberField: 'civil_id_number',
        numberLabel: 'Civil ID Number',
    },
    {
        key: 'passport',
        label: 'Passport',
        icon: <GlobalOutlined />,
        pathField: 'passport_document_path',
        expiryField: 'passport_expiry',
        numberField: 'passport_number',
        numberLabel: 'Passport Number',
    },
    {
        key: 'visa',
        label: 'Visa',
        icon: <FileProtectOutlined />,
        pathField: 'visa_document_path',
        expiryField: null,
        numberField: null,
        numberLabel: null,
    },
];

const EmployeeDocuments = () => {
    const { employeeId } = useParams();
    const navigate = useNavigate();

    const [employee, setEmployee] = useState(null);
    const [loading, setLoading] = useState(true);
    const [uploading, setUploading] = useState({});
    const [previewDoc, setPreviewDoc] = useState(null);  // { type, url }

    const fetchEmployee = async () => {
        if (!employeeId) return;
        try {
            setLoading(true);
            const data = await getEmployeeById(employeeId);
            setEmployee(data);
        } catch (err) {
            message.error('Failed to load employee data');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchEmployee();
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [employeeId]);

    const handleUpload = async (docType, file) => {
        setUploading(prev => ({ ...prev, [docType]: true }));
        try {
            await uploadEmployeeDocument(employeeId, docType, file);
            message.success(`${docType.replace('_', ' ')} uploaded successfully!`);
            fetchEmployee();
        } catch (err) {
            message.error(err.message || 'Upload failed');
        } finally {
            setUploading(prev => ({ ...prev, [docType]: false }));
        }
        return false; // Prevent default antd upload
    };

    const handleDownload = (docType) => {
        downloadEmployeeDocument(employeeId, docType);
    };

    const handlePreview = async (docType) => {
        const token = localStorage.getItem('access_token');
        if (!token) {
            message.error('Authentication required. Please log in again.');
            return;
        }
        try {
            const response = await fetch(
                `${API_BASE_URL}/employees/${employeeId}/download/${docType}`,
                { headers: { Authorization: `Bearer ${token}` } }
            );
            if (!response.ok) {
                throw new Error(`Failed to load document: ${response.status}`);
            }
            const blob = await response.blob();
            const blobUrl = URL.createObjectURL(blob);
            setPreviewDoc({ type: docType, url: blobUrl });
        } catch (error) {
            message.error('Failed to load document preview');
            console.error('Preview error:', error);
        }
    };

    const handleClosePreview = () => {
        if (previewDoc?.url) {
            URL.revokeObjectURL(previewDoc.url);
        }
        setPreviewDoc(null);
    };

    if (loading) {
        return (
            <div style={{ display: 'flex', justifyContent: 'center', padding: 80 }}>
                <Spin size="large" />
            </div>
        );
    }

    if (!employee) {
        return (
            <div style={{ padding: 24 }}>
                <Alert type="error" title="Employee not found" showIcon />
                <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/employees')} style={{ marginTop: 16 }}>
                    Back to Employees
                </Button>
            </div>
        );
    }

    const tabItems = DOC_TYPES.map(docType => {
        const hasDoc = !!employee[docType.pathField];
        return {
            key: docType.key,
            label: (
                <Space>
                    {docType.icon}
                    {docType.label}
                    {hasDoc
                        ? <Tag color="green" style={{ marginLeft: 4 }}>Uploaded</Tag>
                        : <Tag color="default" style={{ marginLeft: 4 }}>Missing</Tag>
                    }
                </Space>
            ),
            children: (
                <div style={{ padding: '8px 0' }}>
                    <Row gutter={[16, 16]}>
                        <Col xs={24} md={12}>
                            <Card size="small" title="Document Info">
                                <Descriptions column={1} size="small">
                                    {docType.numberField && (
                                        <Descriptions.Item label={docType.numberLabel}>
                                            {employee[docType.numberField] || <Text type="secondary">Not set</Text>}
                                        </Descriptions.Item>
                                    )}
                                    {docType.expiryField && (
                                        <Descriptions.Item label="Expiry Date">
                                            <ExpiryBadge date={employee[docType.expiryField]} />
                                        </Descriptions.Item>
                                    )}
                                    <Descriptions.Item label="Document Status">
                                        {hasDoc
                                            ? <Tag color="green"><FilePdfOutlined /> File Uploaded</Tag>
                                            : <Tag color="orange">No document</Tag>
                                        }
                                    </Descriptions.Item>
                                </Descriptions>
                            </Card>
                        </Col>
                        <Col xs={24} md={12}>
                            <Card size="small" title="Actions">
                                <Space orientation="vertical" style={{ width: '100%' }}>
                                    <Upload
                                        accept=".pdf,.jpg,.jpeg,.png"
                                        beforeUpload={(file) => handleUpload(docType.key, file)}
                                        showUploadList={false}
                                    >
                                        <Button
                                            icon={<UploadOutlined />}
                                            loading={uploading[docType.key]}
                                            type="primary"
                                            block
                                        >
                                            {hasDoc ? 'Re-upload Document' : 'Upload Document'}
                                        </Button>
                                    </Upload>

                                    {hasDoc && (
                                        <>
                                            <Button
                                                icon={<EyeOutlined />}
                                                onClick={() => handlePreview(docType.key)}
                                                block
                                            >
                                                Preview in Browser
                                            </Button>
                                            <Button
                                                icon={<DownloadOutlined />}
                                                onClick={() => handleDownload(docType.key)}
                                                block
                                            >
                                                Download
                                            </Button>
                                        </>
                                    )}
                                </Space>
                            </Card>
                        </Col>
                    </Row>

                    {!hasDoc && (
                        <Empty
                            description={`No ${docType.label} document uploaded`}
                            style={{ marginTop: 24 }}
                            image={Empty.PRESENTED_IMAGE_SIMPLE}
                        />
                    )}
                </div>
            ),
        };
    });

    return (
        <div style={{ padding: '0 24px' }}>
            <Space style={{ marginBottom: 16 }}>
                <Button
                    icon={<ArrowLeftOutlined />}
                    onClick={() => navigate(`/employees/${employeeId}`)}
                >
                    Back to Profile
                </Button>
            </Space>

            <Card>
                <div style={{ marginBottom: 16 }}>
                    <Title level={4} style={{ margin: 0 }}>
                        <FilePdfOutlined style={{ marginRight: 8 }} />
                        Employee Documents — {employee.name}
                    </Title>
                    <Text type="secondary">{employee.designation}</Text>
                </div>

                <Tabs items={tabItems} />
            </Card>

            {/* Document Preview Modal */}
            <Modal
                title={`Preview: ${previewDoc?.type?.replace('_', ' ').toUpperCase()}`}
                open={!!previewDoc}
                onCancel={handleClosePreview}
                footer={[
                    <Button key="download" icon={<DownloadOutlined />} onClick={() => handleDownload(previewDoc?.type)}>
                        Download
                    </Button>,
                    <Button key="close" onClick={handleClosePreview}>Close</Button>,
                ]}
                width={800}
                styles={{ body: { padding: 0, height: '70vh' } }}
            >
                {previewDoc?.url ? (
                    <iframe
                        src={previewDoc.url}
                        style={{ width: '100%', height: '70vh', border: 'none' }}
                        title="Document Preview"
                    />
                ) : (
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '70vh' }}>
                        <Spin size="large" />
                    </div>
                )}
            </Modal>
        </div>
    );
};

export default EmployeeDocuments;
