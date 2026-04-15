import React, { useState, useEffect } from 'react';
import {
  Card, Form, Input, Button, Upload, Avatar, message,
  Tabs, Divider, Typography, Row, Col, Spin,
} from 'antd';
import {
  UserOutlined, LockOutlined, PhoneOutlined, MailOutlined,
  CameraOutlined, SaveOutlined, IdcardOutlined,
} from '@ant-design/icons';
import { fetchWithAuth } from '../services/apiService';

const { Title, Text } = Typography;

// ---------------------------------------------------------------------------
// Profile Information Tab
// ---------------------------------------------------------------------------
function ProfileTab({ profileData, onSaved }) {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (profileData) {
      form.setFieldsValue({
        full_name: profileData.full_name,
        designation: profileData.designation,
        phone: profileData.phone,
      });
    }
  }, [profileData, form]);

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);
      await fetchWithAuth('/admins/me', {
        method: 'PUT',
        body: JSON.stringify(values),
      });
      message.success('Profile updated successfully!');
      onSaved();
    } catch (err) {
      if (err?.errorFields) return;
      message.error(err?.message || 'Failed to update profile');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Form form={form} layout="vertical" style={{ maxWidth: 600 }}>
      <Row gutter={[24, 0]}>
        <Col xs={24} md={12}>
          <Form.Item name="full_name" label="Full Name" rules={[{ required: true, message: 'Please enter your name' }]}>
            <Input prefix={<UserOutlined />} />
          </Form.Item>
        </Col>
        <Col xs={24} md={12}>
          <Form.Item name="designation" label="Designation">
            <Input prefix={<IdcardOutlined />} />
          </Form.Item>
        </Col>
        <Col xs={24} md={12}>
          <Form.Item name="phone" label="Phone Number">
            <Input prefix={<PhoneOutlined />} />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={[24, 0]}>
        <Col xs={24} md={12}>
          <Form.Item label="Email (read-only)">
            <Input prefix={<MailOutlined />} value={profileData?.email} disabled />
          </Form.Item>
        </Col>
        <Col xs={24} md={12}>
          <Form.Item label="Role (read-only)">
            <Input value={profileData?.role} disabled />
          </Form.Item>
        </Col>
      </Row>

      <Divider />
      <Button type="primary" icon={<SaveOutlined />} loading={loading} onClick={handleSave} style={{ fontWeight: 600 }}>
        Save Changes
      </Button>
    </Form>
  );
}

// ---------------------------------------------------------------------------
// Change Password Tab
// ---------------------------------------------------------------------------
function PasswordTab() {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);
      await fetchWithAuth('/admins/me/password', {
        method: 'PUT',
        body: JSON.stringify({
          current_password: values.current_password,
          new_password: values.new_password,
        }),
      });
      message.success('Password changed successfully!');
      form.resetFields();
    } catch (err) {
      if (err?.errorFields) return;
      message.error(err?.message || 'Failed to change password');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Form form={form} layout="vertical" style={{ maxWidth: 480 }}>
      <Form.Item
        name="current_password"
        label="Current Password"
        rules={[{ required: true, message: 'Please enter your current password' }]}
      >
        <Input.Password prefix={<LockOutlined />} />
      </Form.Item>

      <Form.Item
        name="new_password"
        label="New Password"
        rules={[
          { required: true, message: 'Please enter a new password' },
          { min: 6, message: 'Password must be at least 6 characters' },
        ]}
      >
        <Input.Password prefix={<LockOutlined />} />
      </Form.Item>

      <Form.Item
        name="confirm_password"
        label="Confirm New Password"
        dependencies={['new_password']}
        rules={[
          { required: true, message: 'Please confirm your new password' },
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
        <Input.Password prefix={<LockOutlined />} />
      </Form.Item>

      <Divider />
      <Button type="primary" icon={<LockOutlined />} loading={loading} onClick={handleSave} style={{ fontWeight: 600 }}>
        Change Password
      </Button>
    </Form>
  );
}

// ---------------------------------------------------------------------------
// Main MyProfile Page
// ---------------------------------------------------------------------------
export default function MyProfile() {
  const [profileData, setProfileData] = useState(null);
  const [loadingProfile, setLoadingProfile] = useState(true);
  const [uploadingPhoto, setUploadingPhoto] = useState(false);

  const loadProfile = async () => {
    setLoadingProfile(true);
    try {
      const data = await fetchWithAuth('/admins/me');
      setProfileData(data);
    } catch {
      message.error('Failed to load profile');
    } finally {
      setLoadingProfile(false);
    }
  };

  useEffect(() => {
    loadProfile();
  }, []);

  const handlePhotoUpload = async ({ file }) => {
    setUploadingPhoto(true);
    const formData = new FormData();
    formData.append('photo', file);
    try {
      const result = await fetchWithAuth('/admins/me/photo', {
        method: 'POST',
        body: formData,
      });
      setProfileData((prev) => ({ ...prev, profile_photo: result.photo_url }));
      message.success('Profile photo updated!');
    } catch (err) {
      message.error(err?.message || 'Failed to upload photo');
    } finally {
      setUploadingPhoto(false);
    }
  };

  const tabItems = [
    {
      key: 'profile',
      label: 'Profile Information',
      children: loadingProfile
        ? <Spin style={{ display: 'block', marginTop: 40 }} />
        : <ProfileTab profileData={profileData} onSaved={loadProfile} />,
    },
    {
      key: 'password',
      label: 'Change Password',
      children: <PasswordTab />,
    },
  ];

  const photoSrc = profileData?.profile_photo
    ? `${import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'}${profileData.profile_photo}`
    : null;

  return (
    <div className="layout-content">
      <Card variant="borderless" className="criclebox mb-24" style={{ marginBottom: 24 }}>
        <Row align="middle" gutter={[24, 0]}>
          <Col>
            <Upload
              showUploadList={false}
              customRequest={handlePhotoUpload}
              accept="image/jpeg,image/png"
              disabled={uploadingPhoto}
            >
              <div style={{ position: 'relative', cursor: 'pointer' }}>
                <Avatar size={80} icon={<UserOutlined />} src={photoSrc} />
                <div style={{
                  position: 'absolute', bottom: 0, right: 0,
                  background: '#1890ff', borderRadius: '50%',
                  width: 24, height: 24, display: 'flex',
                  alignItems: 'center', justifyContent: 'center',
                }}>
                  <CameraOutlined style={{ color: '#fff', fontSize: 12 }} />
                </div>
              </div>
            </Upload>
          </Col>
          <Col>
            <Title level={4} style={{ margin: 0 }}>
              {profileData?.full_name || 'My Profile'}
            </Title>
            <Text type="secondary">{profileData?.role}</Text>
          </Col>
        </Row>
      </Card>

      <Card variant="borderless" className="criclebox">
        <Tabs defaultActiveKey="profile" items={tabItems} style={{ minHeight: 300 }} />
      </Card>
    </div>
  );
}
