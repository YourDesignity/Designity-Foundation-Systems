import React, { useState, useEffect } from 'react';
import {
  Modal, Tabs, Form, Input, Select, Switch, Button,
  Row, Col, Divider, message, Tag, Space, Typography,
  Avatar, Upload,
} from 'antd';
import {
  UserOutlined, MailOutlined, LockOutlined, PhoneOutlined,
  IdcardOutlined, SafetyCertificateOutlined, CameraOutlined,
} from '@ant-design/icons';
import { updateAdminProfile, updateAdminPassword, uploadAdminPhoto } from '../../services/apiService';

const { Option } = Select;
const { Text, Title } = Typography;

// Role permission map (mirrors backend/config/roles.json).
// NOTE: Keep in sync with backend/config/roles.json when roles change.
const ROLE_PERMISSIONS = {
  1: { name: 'SuperAdmin', permissions: ['all'] },
  2: {
    name: 'Admin',
    permissions: [
      'employee:view_all', 'employee:create', 'employee:edit', 'employee:delete',
      'attendance:update', 'site:create', 'site:view',
    ],
  },
  3: {
    name: 'Site Manager',
    permissions: [
      'employee:view_assigned', 'attendance:update', 'site:view', 'schedule:edit',
    ],
  },
};

// Shared helper: resolve role string (object.name or plain string) to a legacy ID
const getRoleId = (roleNameOrObj) => {
  const roleName = typeof roleNameOrObj === 'object' && roleNameOrObj !== null
    ? roleNameOrObj.name
    : roleNameOrObj;
  const entry = Object.entries(ROLE_PERMISSIONS).find(([, v]) => v.name === roleName);
  return entry ? parseInt(entry[0]) : 2;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

// ---------------------------------------------------------------------------
// Profile Tab
// ---------------------------------------------------------------------------
function ProfileTab({ adminId, initialData, onSaved }) {
  const [form] = Form.useForm();
  const [submitting, setSubmitting] = useState(false);
  const [photoUrl, setPhotoUrl] = useState(initialData?.profile_photo || null);
  const [uploadingPhoto, setUploadingPhoto] = useState(false);

  useEffect(() => {
    setPhotoUrl(initialData?.profile_photo || null);
  }, [initialData]);

  const handlePhotoUpload = async ({ file }) => {
    setUploadingPhoto(true);
    try {
      const result = await uploadAdminPhoto(adminId, file);
      setPhotoUrl(result.photo_url);
      message.success('Profile photo updated!');
      if (onSaved) onSaved();
    } catch (err) {
      message.error(err?.message || 'Failed to upload photo');
    } finally {
      setUploadingPhoto(false);
    }
  };

  useEffect(() => {
    if (initialData) {
      form.setFieldsValue({
        full_name: initialData.full_name,
        designation: initialData.designation,
        phone: initialData.phone || '',
        role_id: getRoleId(initialData.role),
        is_active: initialData.is_active !== false,
      });
    }
  }, [initialData, form]);

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);
      await updateAdminProfile(adminId, {
        full_name: values.full_name,
        designation: values.designation,
        phone: values.phone || null,
        role_id: values.role_id,
        is_active: values.is_active,
      });
      message.success('Admin profile updated successfully!');
      onSaved();
    } catch (err) {
      if (err?.errorFields) return;
      message.error(err?.message || 'Failed to update profile');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Form form={form} layout="vertical" style={{ marginTop: 8 }}>
      <div style={{ textAlign: 'center', marginBottom: 24 }}>
        <Avatar
          size={100}
          src={photoUrl ? `${API_BASE_URL}${photoUrl}` : undefined}
          icon={<UserOutlined />}
          style={{ marginBottom: 12, border: '3px solid #f0f0f0' }}
        />
        <div>
          <Upload
            showUploadList={false}
            customRequest={handlePhotoUpload}
            accept="image/jpeg,image/png"
            disabled={uploadingPhoto}
          >
            <Button icon={<CameraOutlined />} loading={uploadingPhoto}>
              Change Photo
            </Button>
          </Upload>
          <div style={{ marginTop: 8 }}>
            <Text type="secondary" style={{ fontSize: 12 }}>JPG, PNG • Max 5MB</Text>
          </div>
        </div>
      </div>
      <Row gutter={[16, 0]}>
        <Col xs={24} md={12}>
          <Form.Item
            name="full_name"
            label="Full Name"
            rules={[{ required: true, message: 'Please enter the full name' }]}
          >
            <Input prefix={<UserOutlined />} placeholder="e.g. John Smith" />
          </Form.Item>
        </Col>
        <Col xs={24} md={12}>
          <Form.Item label="Email (read-only)">
            <Input
              prefix={<MailOutlined />}
              value={initialData?.email}
              disabled
              style={{ backgroundColor: '#f5f5f5' }}
            />
          </Form.Item>
        </Col>
        <Col xs={24} md={12}>
          <Form.Item
            name="designation"
            label="Designation"
            rules={[{ required: true, message: 'Please enter a designation' }]}
          >
            <Input prefix={<IdcardOutlined />} placeholder="e.g. HR Manager" />
          </Form.Item>
        </Col>
        <Col xs={24} md={12}>
          <Form.Item name="phone" label="Phone Number">
            <Input prefix={<PhoneOutlined />} placeholder="+965 XXXX XXXX" />
          </Form.Item>
        </Col>
        <Col xs={24} md={12}>
          <Form.Item
            name="role_id"
            label="Role"
            rules={[{ required: true, message: 'Please select a role' }]}
          >
            <Select>
              <Option value={1}>SuperAdmin</Option>
              <Option value={2}>Admin / HR</Option>
              <Option value={3}>Site Manager</Option>
            </Select>
          </Form.Item>
        </Col>
        <Col xs={24} md={12}>
          <Form.Item name="is_active" label="Account Status" valuePropName="checked">
            <Switch checkedChildren="Active" unCheckedChildren="Inactive" />
          </Form.Item>
        </Col>
      </Row>
      <Divider />
      <Row justify="end">
        <Button type="primary" loading={submitting} onClick={handleSave} style={{ fontWeight: 600 }}>
          Save Profile
        </Button>
      </Row>
    </Form>
  );
}

// ---------------------------------------------------------------------------
// Password Tab
// ---------------------------------------------------------------------------
function PasswordTab({ adminId }) {
  const [form] = Form.useForm();
  const [submitting, setSubmitting] = useState(false);

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);
      await updateAdminPassword(adminId, { new_password: values.new_password });
      message.success('Password updated successfully!');
      form.resetFields();
    } catch (err) {
      if (err?.errorFields) return;
      message.error(err?.message || 'Failed to update password');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Form form={form} layout="vertical" style={{ marginTop: 8, maxWidth: 400 }}>
      <Form.Item
        name="new_password"
        label="New Password"
        rules={[
          { required: true, message: 'Please enter a new password' },
          { min: 6, message: 'Password must be at least 6 characters' },
        ]}
      >
        <Input.Password prefix={<LockOutlined />} placeholder="New password" />
      </Form.Item>
      <Form.Item
        name="confirm_password"
        label="Confirm Password"
        dependencies={['new_password']}
        rules={[
          { required: true, message: 'Please confirm the password' },
          ({ getFieldValue }) => ({
            validator(_, value) {
              if (!value || getFieldValue('new_password') === value) {
                return Promise.resolve();
              }
              return Promise.reject(new Error('Passwords do not match'));
            },
          }),
        ]}
      >
        <Input.Password prefix={<LockOutlined />} placeholder="Confirm password" />
      </Form.Item>
      <Divider />
      <Row justify="end">
        <Button type="primary" loading={submitting} onClick={handleSave} style={{ fontWeight: 600 }}>
          Update Password
        </Button>
      </Row>
    </Form>
  );
}

// ---------------------------------------------------------------------------
// Permissions Tab
// ---------------------------------------------------------------------------
function PermissionsTab({ currentRoleId }) {
  const roleInfo = ROLE_PERMISSIONS[currentRoleId] || ROLE_PERMISSIONS[2];
  const isAll = roleInfo.permissions.includes('all');

  return (
    <div style={{ marginTop: 8 }}>
      <Title level={5} style={{ marginBottom: 12 }}>
        <SafetyCertificateOutlined style={{ marginRight: 8 }} />
        Permissions for: <Tag color="blue">{roleInfo.name}</Tag>
      </Title>
      <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
        Permissions are automatically assigned based on the selected role. Change the role in the
        Profile tab to update these permissions.
      </Text>
      {isAll ? (
        <Tag color="gold" style={{ fontSize: 13, padding: '4px 12px' }}>
          Full Access — All permissions granted
        </Tag>
      ) : (
        <Space wrap>
          {roleInfo.permissions.map((perm) => (
            <Tag key={perm} color="green" style={{ fontSize: 12, padding: '3px 8px' }}>
              {perm}
            </Tag>
          ))}
        </Space>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main EditAdminModal
// ---------------------------------------------------------------------------
function EditAdminModal({ admin, open, onClose, onSaved }) {
  const [activeTab, setActiveTab] = useState('profile');

  // Reset to profile tab when modal opens with a different admin
  useEffect(() => {
    if (open) setActiveTab('profile');
  }, [open, admin?.id]);

  const tabItems = [
    {
      key: 'profile',
      label: 'Profile',
      children: admin ? (
        <ProfileTab adminId={admin.id} initialData={admin} onSaved={onSaved} />
      ) : null,
    },
    {
      key: 'password',
      label: 'Change Password',
      children: admin ? <PasswordTab adminId={admin.id} /> : null,
    },
    {
      key: 'permissions',
      label: 'Permissions',
      children: admin ? (
        <PermissionsTab currentRoleId={getRoleId(admin.role)} />
      ) : null,
    },
  ];

  return (
    <Modal
      title={`Edit Admin: ${admin?.full_name || ''}`}
      open={open}
      onCancel={onClose}
      footer={null}
      width={640}
      destroyOnHidden
    >
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={tabItems}
        style={{ minHeight: 300 }}
      />
    </Modal>
  );
}

export default EditAdminModal;
