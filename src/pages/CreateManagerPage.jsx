import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card, Row, Col, Form, Input, Button, Select, DatePicker, InputNumber,
  Typography, Divider, message, Space,
} from 'antd';
import {
  UserOutlined, MailOutlined, LockOutlined, PhoneOutlined,
  BankOutlined, IdcardOutlined, ArrowLeftOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { createManagerProfile, getSites } from '../services/apiService';

const { Title, Text } = Typography;
const { Option } = Select;
const { TextArea } = Input;

function CreateManagerPage() {
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [sites, setSites] = useState([]);
  const [loadingSites, setLoadingSites] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const fetchSites = async () => {
      setLoadingSites(true);
      try {
        const data = await getSites();
        setSites(Array.isArray(data) ? data : []);
      } catch {
        // non-critical
      } finally {
        setLoadingSites(false);
      }
    };
    fetchSites();
  }, []);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);

      const payload = {
        email: values.email,
        password: values.password,
        full_name: values.full_name,
        designation: values.designation,
        monthly_salary: values.monthly_salary,
        allowances: values.allowances ?? 0,
        date_of_joining: values.date_of_joining
          ? values.date_of_joining.format('YYYY-MM-DD')
          : null,
        phone: values.phone,
        nationality: values.nationality,
        address: values.address,
        emergency_contact_name: values.emergency_contact_name,
        emergency_contact_phone: values.emergency_contact_phone,
        bank_name: values.bank_name,
        account_number: values.account_number,
        iban: values.iban,
        civil_id: values.civil_id,
        passport_number: values.passport_number,
        assigned_site_uids: values.assigned_site_uids ?? [],
      };

      await createManagerProfile(payload);
      message.success('Manager created successfully!');
      navigate('/managers');
    } catch (err) {
      if (err?.errorFields) return; // validation error, antd handles display
      message.error('Failed to create manager: ' + (err?.message ?? 'Unknown error'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="layout-content">
      <Card variant="borderless" className="criclebox mb-24" style={{ marginBottom: 24 }}>
        <Row align="middle" justify="space-between">
          <Col>
            <Title level={4} style={{ margin: 0 }}>Create New Manager</Title>
            <Text type="secondary">Fill in the details to create a new site manager account</Text>
          </Col>
          <Col>
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/managers')}>
              Back to Managers
            </Button>
          </Col>
        </Row>
      </Card>

      <Form
        form={form}
        layout="vertical"
        initialValues={{ date_of_joining: dayjs() }}
      >
        {/* Login Credentials */}
        <Card variant="borderless" className="criclebox mb-24" style={{ marginBottom: 24 }}>
          <Title level={5} style={{ marginBottom: 20 }}>
            <LockOutlined style={{ marginRight: 8 }} />
            Login Credentials
          </Title>
          <Row gutter={[24, 0]}>
            <Col xs={24} md={12}>
              <Form.Item
                name="email"
                label="Email Address"
                rules={[
                  { required: true, message: 'Email is required' },
                  { type: 'email', message: 'Please enter a valid email' },
                ]}
              >
                <Input prefix={<MailOutlined />} placeholder="manager@example.com" />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item
                name="password"
                label="Password"
                rules={[
                  { required: true, message: 'Password is required' },
                  { min: 6, message: 'Password must be at least 6 characters' },
                ]}
              >
                <Input.Password prefix={<LockOutlined />} placeholder="Min. 6 characters" />
              </Form.Item>
            </Col>
          </Row>
        </Card>

        {/* Profile Information */}
        <Card variant="borderless" className="criclebox mb-24" style={{ marginBottom: 24 }}>
          <Title level={5} style={{ marginBottom: 20 }}>
            <UserOutlined style={{ marginRight: 8 }} />
            Profile Information
          </Title>
          <Row gutter={[24, 0]}>
            <Col xs={24} md={12}>
              <Form.Item
                name="full_name"
                label="Full Name"
                rules={[{ required: true, message: 'Full name is required' }]}
              >
                <Input prefix={<UserOutlined />} placeholder="e.g. Ahmed Al-Rashid" />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item
                name="designation"
                label="Designation"
                rules={[{ required: true, message: 'Designation is required' }]}
              >
                <Input prefix={<IdcardOutlined />} placeholder="e.g. Site Manager" />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item
                name="monthly_salary"
                label="Monthly Salary (KWD)"
                rules={[{ required: true, message: 'Salary is required' }]}
              >
                <InputNumber
                  style={{ width: '100%' }}
                  min={0}
                  precision={3}
                  placeholder="0.000"
                  addonAfter="KWD"
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item name="allowances" label="Allowances (KWD)">
                <InputNumber
                  style={{ width: '100%' }}
                  min={0}
                  precision={3}
                  placeholder="0.000"
                  addonAfter="KWD"
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item
                name="date_of_joining"
                label="Date of Joining"
                rules={[{ required: true, message: 'Date of joining is required' }]}
              >
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
        </Card>

        {/* Contact Information */}
        <Card variant="borderless" className="criclebox mb-24" style={{ marginBottom: 24 }}>
          <Title level={5} style={{ marginBottom: 20 }}>
            <PhoneOutlined style={{ marginRight: 8 }} />
            Contact Information <Text type="secondary" style={{ fontSize: 13, fontWeight: 400 }}>(Optional)</Text>
          </Title>
          <Row gutter={[24, 0]}>
            <Col xs={24} md={12}>
              <Form.Item name="phone" label="Phone">
                <Input prefix={<PhoneOutlined />} placeholder="+965 XXXX XXXX" />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item name="nationality" label="Nationality">
                <Input placeholder="e.g. Kuwaiti" />
              </Form.Item>
            </Col>
            <Col xs={24}>
              <Form.Item name="address" label="Address">
                <TextArea rows={2} placeholder="Residential address" />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item name="emergency_contact_name" label="Emergency Contact Name">
                <Input placeholder="e.g. John Doe" />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item name="emergency_contact_phone" label="Emergency Contact Phone">
                <Input placeholder="+965 XXXX XXXX" />
              </Form.Item>
            </Col>
          </Row>
        </Card>

        {/* Banking Details */}
        <Card variant="borderless" className="criclebox mb-24" style={{ marginBottom: 24 }}>
          <Title level={5} style={{ marginBottom: 20 }}>
            <BankOutlined style={{ marginRight: 8 }} />
            Banking Details <Text type="secondary" style={{ fontSize: 13, fontWeight: 400 }}>(Optional)</Text>
          </Title>
          <Row gutter={[24, 0]}>
            <Col xs={24} md={8}>
              <Form.Item name="bank_name" label="Bank Name">
                <Input prefix={<BankOutlined />} placeholder="e.g. NBK" />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item name="account_number" label="Account Number">
                <Input placeholder="Account number" />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item name="iban" label="IBAN">
                <Input placeholder="KW00 XXXX XXXX XXXX XXXX XXXX XXXX" />
              </Form.Item>
            </Col>
          </Row>
        </Card>

        {/* ID Documents */}
        <Card variant="borderless" className="criclebox mb-24" style={{ marginBottom: 24 }}>
          <Title level={5} style={{ marginBottom: 20 }}>
            <IdcardOutlined style={{ marginRight: 8 }} />
            ID Documents <Text type="secondary" style={{ fontSize: 13, fontWeight: 400 }}>(Optional)</Text>
          </Title>
          <Row gutter={[24, 0]}>
            <Col xs={24} md={12}>
              <Form.Item name="civil_id" label="Civil ID">
                <Input placeholder="Civil ID number" />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item name="passport_number" label="Passport Number">
                <Input placeholder="Passport number" />
              </Form.Item>
            </Col>
          </Row>
        </Card>

        {/* Site Assignments */}
        <Card variant="borderless" className="criclebox mb-24" style={{ marginBottom: 24 }}>
          <Title level={5} style={{ marginBottom: 20 }}>Site Assignments</Title>
          <Row gutter={[24, 0]}>
            <Col xs={24}>
              <Form.Item name="assigned_site_uids" label="Assigned Sites">
                <Select
                  mode="multiple"
                  placeholder="Select one or more sites"
                  loading={loadingSites}
                  allowClear
                  optionFilterProp="children"
                >
                  {sites.map((s) => (
                    <Option key={s.id} value={s.id}>
                      {s.name}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>
        </Card>

        <Divider />

        <Row justify="end">
          <Space>
            <Button onClick={() => navigate('/managers')}>Cancel</Button>
            <Button
              type="primary"
              loading={submitting}
              onClick={handleSubmit}
              style={{ fontWeight: 600 }}
            >
              Create Manager
            </Button>
          </Space>
        </Row>
      </Form>
    </div>
  );
}

export default CreateManagerPage;
