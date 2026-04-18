import React, { useState, useEffect } from 'react';
import { 
  Card, Row, Col, Typography, Button, Table, 
  Avatar, Tag, Modal, Form, Input, Select, message, Space, Popconfirm
} from 'antd';
import { 
  PlusOutlined, UserOutlined, SafetyCertificateOutlined, 
  MailOutlined, IdcardOutlined, LockOutlined, EditOutlined, DeleteOutlined
} from '@ant-design/icons';

import { getAdmins, createAdmin, deleteAdmin } from '../services/apiService';
import EditAdminModal from '../components/Admin/EditAdminModal';
import { useAuth } from '../context/AuthContext';

const { Title, Text } = Typography;
const { Option } = Select;
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

function AdminManagementPage() {
  const { user } = useAuth();
  const [admins, setAdmins] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [editAdmin, setEditAdmin] = useState(null);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  
  const [form] = Form.useForm();

  // --- 1. Fetch Admins with Role-Based Filtering ---
  const fetchAdmins = async () => {
    setLoading(true);
    try {
      const data = await getAdmins();
      
      // Role-based filtering: SuperAdmin sees everyone, Regular Admin hides SuperAdmins
      const visibleAdmins = Array.isArray(data)
        ? data.filter(admin => {
            if (user?.role === 'SuperAdmin') {
              return true;
            }
            return admin.role?.name?.toLowerCase() !== 'superadmin';
          })
        : [];

      setAdmins(visibleAdmins);
    } catch (err) {
      message.error("Failed to load admins: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAdmins();
  }, []);

  // --- 2. Create Admin ---
  const handleCreateAdmin = async () => {
    try {
      const values = await form.validateFields();
      setIsSubmitting(true);
      
      const newAdminData = {
        full_name: values.full_name,
        email: values.email,
        password: values.password,
        designation: values.designation,
        role_id: values.role_id
      };

      await createAdmin(newAdminData);
      
      message.success("Admin created successfully!");
      setIsModalOpen(false);
      form.resetFields();
      fetchAdmins(); 
      
    } catch (err) {
      if (err.message) message.error(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  // --- 3. Edit Admin ---
  const handleEditAdmin = (record) => {
    // Security check: Regular Admins cannot edit SuperAdmins
    if (user?.role !== 'SuperAdmin' && record.role?.name?.toLowerCase() === 'superadmin') {
      message.error('You do not have permission to edit SuperAdmin accounts');
      return;
    }
    setEditAdmin(record);
    setIsEditModalOpen(true);
  };

  const handleEditSaved = () => {
    setIsEditModalOpen(false);
    setEditAdmin(null);
    fetchAdmins();
  };

  // --- 4. Delete Admin ---
  const handleDeleteAdmin = async (adminId) => {
    // Safety check: Cannot delete yourself
    if (adminId === user?.id) {
      message.error('You cannot delete your own account!');
      return;
    }
    try {
      await deleteAdmin(adminId);
      message.success('Admin deleted successfully');
      fetchAdmins();
    } catch (err) {
      message.error('Failed to delete admin: ' + (err.message || 'Unknown error'));
    }
  };

  // --- 5. Table Columns ---
  const columns = [
    {
      title: 'ADMIN USER',
      dataIndex: 'full_name',
      key: 'full_name',
      width: '35%',
      render: (text, record) => (
        <div className="avatar-info" style={{ display: 'flex', alignItems: 'center' }}>
          <Avatar 
            shape="square" 
            size={40} 
            src={record.profile_photo ? `${API_BASE_URL}${record.profile_photo}` : undefined}
            icon={<UserOutlined />} 
            style={{ backgroundColor: '#1890ff', marginRight: 12 }} 
          />
          <div>
            <Title level={5} style={{ margin: 0, fontSize: '14px' }}>{text}</Title>
            <Text type="secondary" style={{ fontSize: '12px' }}>{record.email}</Text>
          </div>
        </div>
      ),
    },
    {
      title: 'DESIGNATION',
      dataIndex: 'designation',
      key: 'designation',
      render: (text) => (
        <span style={{ fontWeight: 600, color: '#555' }}>
          {text || 'N/A'}
        </span>
      ),
    },
    {
      title: 'ROLE',
      dataIndex: 'role',
      key: 'role',
      render: (role) => {
        const roleName = role ? role.name : 'Unknown';
        let color = 'green';
        let icon = <UserOutlined />;

        if (roleName === 'SuperAdmin') {
            color = 'red';
            icon = <SafetyCertificateOutlined />;
        } else if (roleName === 'Site Manager') {
            color = 'cyan';
            icon = <IdcardOutlined />;
        }

        return (
          <Tag color={color} icon={icon} style={{ borderRadius: '4px', padding: '4px 10px' }}>
            {roleName.toUpperCase()}
          </Tag>
        );
      },
    },
    {
      title: 'CREATED AT',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date) => (
        <Text type="secondary" style={{ fontSize: '12px' }}>
          {date ? new Date(date).toLocaleDateString() : '-'}
        </Text>
      )
    },
    {
      title: 'ACTIONS',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEditAdmin(record)}
            style={{ padding: '0 4px' }}
          >
            Edit
          </Button>
          <Popconfirm
            title="Delete this admin?"
            description="This action cannot be undone."
            onConfirm={() => handleDeleteAdmin(record.id)}
            okText="Delete"
            okButtonProps={{ danger: true }}
            cancelText="Cancel"
          >
            <Button type="link" danger icon={<DeleteOutlined />} style={{ padding: '0 4px' }}>
              Delete
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div className="layout-content">
      {/* --- Header Card --- */}
      <Card variant="borderless" className="criclebox mb-24" style={{ marginBottom: 24 }}>
        <Row align="middle" justify="space-between">
          <Col>
            <Title level={4} style={{ margin: 0 }}>Admin Management</Title>
            <Text type="secondary">Manage system administrators and access roles</Text>
          </Col>
          <Col>
            <Button 
              type="primary" 
              icon={<PlusOutlined />} 
              onClick={() => setIsModalOpen(true)}
              style={{ borderRadius: '6px', fontWeight: 600 }}
            >
              Add New Admin
            </Button>
          </Col>
        </Row>
      </Card>

      {/* --- Admins List Table --- */}
      <Row gutter={[24, 0]}>
        <Col xs={24} xl={24} className="mb-24">
          <Card variant="borderless" className="criclebox tablespace mb-24">
            <div className="table-responsive">
              <Table
                columns={columns}
                dataSource={admins}
                pagination={{ pageSize: 5 }}
                className="ant-border-space"
                rowKey="id"
                loading={loading}
              />
            </div>
          </Card>
        </Col>
      </Row>

      {/* --- Create Modal --- */}
      <Modal
        title="Create New Admin"
        open={isModalOpen}
        onOk={handleCreateAdmin}
        onCancel={() => setIsModalOpen(false)}
        confirmLoading={isSubmitting}
        okText="Create Admin"
        width={500}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 20 }}>
          <Form.Item
            name="full_name"
            label="Full Name"
            rules={[{ required: true, message: 'Please enter the full name' }]}
          >
            <Input prefix={<UserOutlined style={{ color: '#bfbfbf' }} />} placeholder="e.g. John Doe" />
          </Form.Item>

          <Form.Item
            name="email"
            label="Email Address"
            rules={[
              { required: true, message: 'Please enter an email' },
              { type: 'email', message: 'Please enter a valid email' }
            ]}
          >
            <Input prefix={<MailOutlined style={{ color: '#bfbfbf' }} />} placeholder="e.g. admin@company.com" />
          </Form.Item>

          <Form.Item
            name="password"
            label="Password"
            rules={[{ required: true, message: 'Please enter a password' }]}
          >
            <Input.Password prefix={<LockOutlined style={{ color: '#bfbfbf' }} />} placeholder="••••••••" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="designation"
                label="Designation"
                rules={[{ required: true, message: 'Please enter designation' }]}
              >
                <Input prefix={<IdcardOutlined style={{ color: '#bfbfbf' }} />} placeholder="e.g. HR Manager" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="role_id"
                label="Role"
                initialValue={2}
                rules={[{ required: true, message: 'Please select a role' }]}
              >
                <Select>
                  {/* HIDDEN SUPERADMIN OPTION HERE TOO - Only create lower roles */}
                  <Option value={2}>Admin / HR</Option>
                  <Option value={3}>Site Manager</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>
      {/* --- Edit Admin Modal --- */}
      <EditAdminModal
        admin={editAdmin}
        open={isEditModalOpen}
        onClose={() => { setIsEditModalOpen(false); setEditAdmin(null); }}
        onSaved={handleEditSaved}
      />
    </div>
  );
}

export default AdminManagementPage;