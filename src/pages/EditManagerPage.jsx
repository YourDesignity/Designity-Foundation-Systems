import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import {
  Card, Row, Col, Tabs, Form, Input, Button, Select, DatePicker, InputNumber,
  Switch, TimePicker, Typography, Divider, message, Space, Spin, Alert,
} from 'antd';
import {
  UserOutlined, MailOutlined, LockOutlined, PhoneOutlined,
  BankOutlined, IdcardOutlined, ArrowLeftOutlined, ClockCircleOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import {
  getManagerProfileById, updateManagerProfile, updateManagerCredentials,
  updateManagerSites, getManagerAttendanceConfig, updateManagerAttendanceConfig,
  getSites,
} from '../services/apiService';

const { Title, Text } = Typography;
const { Option } = Select;
const { TextArea } = Input;

// ---------------------------------------------------------------------------
// 1. Profile Tab
// ---------------------------------------------------------------------------
function ProfileTab({ managerId, initialData }) {
  const [form] = Form.useForm();
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (initialData) {
      form.setFieldsValue({
        ...initialData,
        date_of_joining: initialData.date_of_joining
          ? dayjs(initialData.date_of_joining)
          : null,
      });
    }
  }, [initialData, form]);

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);
      const payload = {
        ...values,
        date_of_joining: values.date_of_joining
          ? values.date_of_joining.format('YYYY-MM-DD')
          : null,
      };
      await updateManagerProfile(managerId, payload);
      message.success('Profile updated successfully');
    } catch (err) {
      if (err?.errorFields) return;
      message.error('Failed to update profile: ' + (err?.message ?? 'Unknown error'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Form form={form} layout="vertical">
      <Row gutter={[24, 0]}>
        <Col xs={24} md={12}>
          <Form.Item name="full_name" label="Full Name" rules={[{ required: true }]}>
            <Input prefix={<UserOutlined />} />
          </Form.Item>
        </Col>
        <Col xs={24} md={12}>
          <Form.Item name="designation" label="Designation" rules={[{ required: true }]}>
            <Input prefix={<IdcardOutlined />} />
          </Form.Item>
        </Col>
        <Col xs={24} md={8}>
          <Form.Item name="monthly_salary" label="Monthly Salary (KWD)" rules={[{ required: true }]}>
            <InputNumber style={{ width: '100%' }} min={0} precision={3} suffix="KWD" />
          </Form.Item>
        </Col>
        <Col xs={24} md={8}>
          <Form.Item name="allowances" label="Allowances (KWD)">
            <InputNumber style={{ width: '100%' }} min={0} precision={3} suffix="KWD" />
          </Form.Item>
        </Col>
        <Col xs={24} md={8}>
          <Form.Item name="date_of_joining" label="Date of Joining">
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
        </Col>

        <Col xs={24}><Divider titlePlacement="left">Contact</Divider></Col>
        <Col xs={24} md={12}>
          <Form.Item name="phone" label="Phone">
            <Input prefix={<PhoneOutlined />} />
          </Form.Item>
        </Col>
        <Col xs={24} md={12}>
          <Form.Item name="nationality" label="Nationality">
            <Input />
          </Form.Item>
        </Col>
        <Col xs={24}>
          <Form.Item name="address" label="Address">
            <TextArea rows={2} />
          </Form.Item>
        </Col>
        <Col xs={24} md={12}>
          <Form.Item name="emergency_contact_name" label="Emergency Contact Name">
            <Input />
          </Form.Item>
        </Col>
        <Col xs={24} md={12}>
          <Form.Item name="emergency_contact_phone" label="Emergency Contact Phone">
            <Input />
          </Form.Item>
        </Col>

        <Col xs={24}><Divider titlePlacement="left">Banking</Divider></Col>
        <Col xs={24} md={8}>
          <Form.Item name="bank_name" label="Bank Name">
            <Input prefix={<BankOutlined />} />
          </Form.Item>
        </Col>
        <Col xs={24} md={8}>
          <Form.Item name="account_number" label="Account Number">
            <Input />
          </Form.Item>
        </Col>
        <Col xs={24} md={8}>
          <Form.Item name="iban" label="IBAN">
            <Input />
          </Form.Item>
        </Col>

        <Col xs={24}><Divider titlePlacement="left">ID Documents</Divider></Col>
        <Col xs={24} md={12}>
          <Form.Item name="civil_id" label="Civil ID">
            <Input />
          </Form.Item>
        </Col>
        <Col xs={24} md={12}>
          <Form.Item name="passport_number" label="Passport Number">
            <Input />
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
// 2. Credentials Tab
// ---------------------------------------------------------------------------
function CredentialsTab({ managerId, initialEmail }) {
  const [form] = Form.useForm();
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (initialEmail) {
      form.setFieldsValue({ email: initialEmail });
    }
  }, [initialEmail, form]);

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      if (values.new_password && values.new_password !== values.confirm_password) {
        message.error('Passwords do not match');
        return;
      }
      setSubmitting(true);
      const payload = { email: values.email };
      if (values.new_password) payload.password = values.new_password;
      await updateManagerCredentials(managerId, payload);
      message.success('Credentials updated. Manager will need to log in again.');
      form.resetFields(['new_password', 'confirm_password']);
    } catch (err) {
      if (err?.errorFields) return;
      message.error('Failed to update credentials: ' + (err?.message ?? 'Unknown error'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Form form={form} layout="vertical" style={{ maxWidth: 480 }}>
      <Alert
        type="warning"
        icon={<WarningOutlined />}
        showIcon
        title="Manager will be logged out after a password change."
        style={{ marginBottom: 24 }}
      />
      <Form.Item
        name="email"
        label="Email Address"
        rules={[{ required: true }, { type: 'email' }]}
      >
        <Input prefix={<MailOutlined />} />
      </Form.Item>
      <Form.Item name="new_password" label="New Password (leave blank to keep current)">
        <Input.Password prefix={<LockOutlined />} placeholder="Min. 6 characters" />
      </Form.Item>
      <Form.Item
        name="confirm_password"
        label="Confirm New Password"
        dependencies={['new_password']}
        rules={[
          ({ getFieldValue }) => ({
            validator(_, value) {
              const np = getFieldValue('new_password');
              if (!np || !value || np === value) return Promise.resolve();
              return Promise.reject(new Error('Passwords do not match'));
            },
          }),
        ]}
      >
        <Input.Password prefix={<LockOutlined />} placeholder="Repeat password" />
      </Form.Item>
      <Divider />
      <Button type="primary" loading={submitting} onClick={handleSave} style={{ fontWeight: 600 }}>
        Update Credentials
      </Button>
    </Form>
  );
}

// ---------------------------------------------------------------------------
// 3. Sites Tab
// ---------------------------------------------------------------------------
function SitesTab({ managerId, initialSiteIds }) {
  const [allSites, setAllSites] = useState([]);
  const [selectedSites, setSelectedSites] = useState([]);
  const [loadingSites, setLoadingSites] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const fetch = async () => {
      setLoadingSites(true);
      try {
        const data = await getSites();
        setAllSites(Array.isArray(data) ? data : []);
      } catch { /* non-critical */ } finally { setLoadingSites(false); }
    };
    fetch();
  }, []);

  useEffect(() => {
    if (initialSiteIds) setSelectedSites(initialSiteIds);
  }, [initialSiteIds]);

  const handleSave = async () => {
    setSubmitting(true);
    try {
      await updateManagerSites(managerId, { site_uids: selectedSites });
      message.success('Site assignments updated');
    } catch (err) {
      message.error('Failed to update sites: ' + (err?.message ?? 'Unknown error'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ maxWidth: 560 }}>
      <Form layout="vertical">
        <Form.Item label="Assigned Sites">
          <Select
            mode="multiple"
            value={selectedSites}
            onChange={setSelectedSites}
            loading={loadingSites}
            allowClear
            optionFilterProp="children"
            placeholder="Select sites"
          >
            {allSites.map((s) => (
              <Option key={s.id} value={s.id}>{s.name}</Option>
            ))}
          </Select>
        </Form.Item>
        <Divider />
        <Button type="primary" loading={submitting} onClick={handleSave} style={{ fontWeight: 600 }}>
          Save Sites
        </Button>
      </Form>
    </div>
  );
}

// ---------------------------------------------------------------------------
// 4. Attendance Config Tab
// ---------------------------------------------------------------------------
const SEGMENTS = [
  { key: 'morning',   label: 'Morning Check-in',   defaultStart: '08:00', defaultEnd: '09:30' },
  { key: 'afternoon', label: 'Afternoon Check-in',  defaultStart: '13:00', defaultEnd: '14:00' },
  { key: 'evening',   label: 'Evening Check-out',   defaultStart: '17:00', defaultEnd: '18:30' },
];

function AttendanceConfigTab({ managerId }) {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [enabled, setEnabled] = useState({});
  const [times, setTimes] = useState({});
  const [requireAll, setRequireAll] = useState(false);

  useEffect(() => {
    const fetch = async () => {
      setLoading(true);
      try {
        const data = await getManagerAttendanceConfig(managerId);
        setConfig(data);
        // Initialise state from config
        const enabledMap = {};
        const timesMap = {};
        SEGMENTS.forEach(({ key }) => {
          enabledMap[key] = data?.[key]?.enabled ?? false;
          timesMap[`${key}_start`] = data?.[key]?.start_time
            ? dayjs(data[key].start_time, 'HH:mm') : null;
          timesMap[`${key}_end`] = data?.[key]?.end_time
            ? dayjs(data[key].end_time, 'HH:mm') : null;
        });
        setEnabled(enabledMap);
        setTimes(timesMap);
        setRequireAll(data?.require_all_segments ?? false);
      } catch {
        // Config may not exist yet — use defaults
        const defaultEnabled = {};
        const defaultTimes = {};
        SEGMENTS.forEach(({ key, defaultStart, defaultEnd }) => {
          defaultEnabled[key] = false;
          defaultTimes[`${key}_start`] = dayjs(defaultStart, 'HH:mm');
          defaultTimes[`${key}_end`] = dayjs(defaultEnd, 'HH:mm');
        });
        setEnabled(defaultEnabled);
        setTimes(defaultTimes);
      } finally {
        setLoading(false);
      }
    };
    fetch();
  }, [managerId]);

  const handleSave = async () => {
    setSubmitting(true);
    try {
      const payload = { require_all_segments: requireAll };
      SEGMENTS.forEach(({ key }) => {
        payload[key] = {
          enabled: enabled[key] ?? false,
          start_time: times[`${key}_start`]?.format('HH:mm') ?? null,
          end_time: times[`${key}_end`]?.format('HH:mm') ?? null,
        };
      });
      await updateManagerAttendanceConfig(managerId, payload);
      message.success('Attendance configuration saved');
    } catch (err) {
      message.error('Failed to save config: ' + (err?.message ?? 'Unknown error'));
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <Spin style={{ display: 'block', marginTop: 40 }} />;

  return (
    <div style={{ maxWidth: 620 }}>
      <Alert
        type="info"
        showIcon
        icon={<ClockCircleOutlined />}
        title="Manager can only check in during these time windows. After the window closes, only admins can override."
        style={{ marginBottom: 24 }}
      />

      {SEGMENTS.map(({ key, label, defaultStart, defaultEnd }) => (
        <Card
          key={key}
          size="small"
          style={{ marginBottom: 16 }}
          title={
            <Row align="middle" gutter={12}>
              <Col>
                <Switch
                  checked={enabled[key] ?? false}
                  onChange={(val) => setEnabled((prev) => ({ ...prev, [key]: val }))}
                />
              </Col>
              <Col>
                <Text strong>{label}</Text>
              </Col>
            </Row>
          }
        >
          <Row gutter={[16, 0]} align="middle">
            <Col xs={24} md={11}>
              <Form.Item label="Start Time" style={{ marginBottom: 0 }}>
                <TimePicker
                  format="HH:mm"
                  value={times[`${key}_start`]}
                  onChange={(val) =>
                    setTimes((prev) => ({ ...prev, [`${key}_start`]: val }))
                  }
                  placeholder={defaultStart}
                  style={{ width: '100%' }}
                  disabled={!enabled[key]}
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={11}>
              <Form.Item label="End Time" style={{ marginBottom: 0 }}>
                <TimePicker
                  format="HH:mm"
                  value={times[`${key}_end`]}
                  onChange={(val) =>
                    setTimes((prev) => ({ ...prev, [`${key}_end`]: val }))
                  }
                  placeholder={defaultEnd}
                  style={{ width: '100%' }}
                  disabled={!enabled[key]}
                />
              </Form.Item>
            </Col>
          </Row>
        </Card>
      ))}

      <Card size="small" title="Rules" style={{ marginBottom: 24 }}>
        <Row align="middle" gutter={12}>
          <Col>
            <Switch checked={requireAll} onChange={setRequireAll} />
          </Col>
          <Col>
            <Text>Require all enabled segments for Full Day</Text>
          </Col>
        </Row>
      </Card>

      <Divider />
      <Button type="primary" loading={submitting} onClick={handleSave} style={{ fontWeight: 600 }}>
        Save Configuration
      </Button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main EditManagerPage
// ---------------------------------------------------------------------------
function EditManagerPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const activeTab = searchParams.get('tab') || 'profile';

  const loadProfile = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getManagerProfileById(id);
      setProfile(data);
    } catch (err) {
      message.error('Failed to load manager: ' + err.message);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadProfile();
  }, [loadProfile]);

  const handleTabChange = (key) => {
    setSearchParams({ tab: key });
  };

  const tabItems = [
    {
      key: 'profile',
      label: 'Profile',
      children: loading
        ? <Spin style={{ display: 'block', marginTop: 40 }} />
        : <ProfileTab managerId={id} initialData={profile} />,
    },
    {
      key: 'credentials',
      label: 'Credentials',
      children: loading
        ? <Spin style={{ display: 'block', marginTop: 40 }} />
        : <CredentialsTab managerId={id} initialEmail={profile?.email} />,
    },
    {
      key: 'sites',
      label: 'Sites',
      children: loading
        ? <Spin style={{ display: 'block', marginTop: 40 }} />
        : <SitesTab managerId={id} initialSiteIds={profile?.site_ids ?? profile?.sites?.map((s) => s.id) ?? []} />,
    },
    {
      key: 'attendance',
      label: 'Attendance Config',
      children: <AttendanceConfigTab managerId={id} />,
    },
  ];

  return (
    <div className="layout-content">
      <Card variant="borderless" className="criclebox mb-24" style={{ marginBottom: 24 }}>
        <Row align="middle" justify="space-between">
          <Col>
            <Title level={4} style={{ margin: 0 }}>
              Edit Manager {profile ? `— ${profile.full_name}` : ''}
            </Title>
            <Text type="secondary">Update profile, credentials, sites, and attendance settings</Text>
          </Col>
          <Col>
            <Space>
              <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/managers')}>
                Back
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      <Card variant="borderless" className="criclebox">
        <Tabs
          activeKey={activeTab}
          onChange={handleTabChange}
          items={tabItems}
          style={{ minHeight: 300 }}
        />
      </Card>
    </div>
  );
}

export default EditManagerPage;
