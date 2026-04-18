import React, { useState, useEffect, useCallback } from 'react';
import { Card, Form, InputNumber, Switch, Button, message, Row, Col, Typography, Alert, Divider, Statistic, Input } from 'antd';
import { SaveOutlined, SettingOutlined, DollarOutlined, ClockCircleOutlined, WarningOutlined, FolderOutlined } from '@ant-design/icons';
import { settingsService } from '../services';

const { Title, Text } = Typography;

function CompanySettingsPage() {
    const [form] = Form.useForm();
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [settings, setSettings] = useState(null);


    const fetchSettings = useCallback(async () => {
        setLoading(true);
        try {
            const response = await settingsService.getAll();
            setSettings(response);
        } catch (err) {
            message.error('Failed to load settings: ' + (err.message || 'Unknown error'));
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchSettings();
    }, [fetchSettings]);

    useEffect(() => {
        if (settings) {
            form.setFieldsValue(settings);
        }
    }, [settings, form]);

    const handleSave = async () => {
        try {
            const values = await form.validateFields();
            setSaving(true);
            await settingsService.update(values);
            message.success('Company settings updated successfully');
            fetchSettings();
        } catch (err) {
            message.error('Failed to save settings: ' + (err.message || 'Unknown error'));
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="layout-content">
            <Card variant="borderless" style={{ marginBottom: 24 }}>
                <Title level={4} style={{ margin: 0 }}>
                    <SettingOutlined style={{ marginRight: 8 }} />
                    Company Settings
                </Title>
                <Text type="secondary">Configure salary calculation parameters and business rules</Text>
            </Card>

            <Card variant="borderless" loading={loading}>
                <Alert
                    type="warning"
                    showIcon
                    title="Admin Only"
                    description="These settings affect all payslip calculations. Changes apply to future payslips immediately."
                    style={{ marginBottom: 16 }}
                />

                <Alert
                    type="error"
                    showIcon
                    title="⚠️ Critical: These Settings Affect All Future Payslips"
                    description={
                        <div>
                            <p><strong>Important Notes:</strong></p>
                            <ul>
                                <li>✅ Changes apply <strong>immediately</strong> to all payslip calculations</li>
                                <li>✅ Affects <strong>all employees</strong> (salaried and hourly workers)</li>
                                <li>❌ Does NOT recalculate past/generated payslips</li>
                                <li>📊 Test changes on a single payslip before company-wide rollout</li>
                            </ul>
                            <p style={{ marginTop: 12 }}>
                                <strong>Recommended:</strong> After saving, go to Payslips → Calculate → Test with 1 employee to verify results before processing the full payroll.
                            </p>
                        </div>
                    }
                    style={{ marginBottom: 24, borderColor: '#ff4d4f' }}
                />

                <Form form={form} layout="vertical" onFinish={handleSave}>
                    <Divider titlePlacement="left">
                        <ClockCircleOutlined /> Overtime Multipliers
                    </Divider>

                    <Alert
                        type="info"
                        showIcon
                        title="Normal Overtime Multiplier"
                        description={
                            <div>
                                <p><strong>What this means:</strong> Employees earn this multiplier of their hourly rate for regular overtime hours.</p>
                                <p><strong>Example:</strong> If an employee's hourly rate is 0.50 KD/hour and you set 1.25:</p>
                                <ul>
                                    <li>Normal hourly rate: 0.50 KD</li>
                                    <li>OT rate: 0.50 × 1.25 = <strong>0.625 KD per hour</strong></li>
                                    <li>10 OT hours = 10 × 0.625 = <strong>6.25 KD total OT pay</strong></li>
                                </ul>
                                <p style={{ marginTop: 12, color: '#fa8c16' }}>
                                    <WarningOutlined /> <strong>Impact:</strong> Applies to all future payslip calculations for regular overtime hours logged in the Attendance page or via daily attendance overtime field.
                                </p>
                            </div>
                        }
                        style={{ marginBottom: 16 }}
                    />

                    <Row gutter={24}>
                        <Col xs={24} md={12}>
                            <Form.Item
                                name="normal_overtime_multiplier"
                                label="Normal Overtime Rate"
                                tooltip="Percentage multiplier for regular overtime. 1.25 means 125% of hourly rate (25% premium). Common values: 1.25 (Kuwait Labor Law standard for first 2 hours), 1.5 (after 2 hours)."
                                rules={[{ required: true, message: 'Required' }]}
                            >
                                <InputNumber
                                    style={{ width: '100%' }}
                                    min={1.0}
                                    max={3.0}
                                    step={0.05}
                                    precision={2}
                                    prefix="×"
                                    placeholder="1.25"
                                />
                            </Form.Item>
                            <Text type="secondary" style={{ fontSize: 12 }}>
                                Example: 1.25 means employees get 125% of their hourly rate for normal OT
                            </Text>
                        </Col>

                        <Col xs={24} md={12}>
                            <Alert
                                type="info"
                                showIcon
                                title="Off-Day Overtime Multiplier"
                                description={
                                    <div>
                                        <p><strong>What this means:</strong> Employees earn this multiplier for overtime worked on weekends or holidays (marked as "Offday" type in Overtime records).</p>
                                        <p><strong>Example:</strong> If an employee's hourly rate is 0.50 KD/hour and you set 1.50:</p>
                                        <ul>
                                            <li>Normal hourly rate: 0.50 KD</li>
                                            <li>Off-day OT rate: 0.50 × 1.50 = <strong>0.75 KD per hour</strong></li>
                                            <li>8 off-day hours = 8 × 0.75 = <strong>6.00 KD total</strong></li>
                                        </ul>
                                        <p style={{ marginTop: 12, color: '#fa8c16' }}>
                                            <WarningOutlined /> <strong>Impact:</strong> Only applies to overtime records explicitly marked as "Offday" type in the Overtime management page.
                                        </p>
                                    </div>
                                }
                                style={{ marginBottom: 16 }}
                            />
                            <Form.Item
                                name="offday_overtime_multiplier"
                                label="Off-Day Overtime Rate"
                                tooltip="Percentage multiplier for weekend/holiday overtime. 1.50 means 150% of hourly rate (50% premium). Kuwait Labor Law: 1.5× for first 2 hours, 2.0× after."
                                rules={[{ required: true, message: 'Required' }]}
                            >
                                <InputNumber
                                    style={{ width: '100%' }}
                                    min={1.0}
                                    max={3.0}
                                    step={0.05}
                                    precision={2}
                                    prefix="×"
                                    placeholder="1.50"
                                />
                            </Form.Item>
                            <Text type="secondary" style={{ fontSize: 12 }}>
                                Example: 1.50 means employees get 150% of their hourly rate for off-day OT
                            </Text>
                        </Col>
                    </Row>

                    <Divider titlePlacement="left">
                        <DollarOutlined /> Work Hours
                    </Divider>

                    <Alert
                        type="info"
                        showIcon
                        title="Standard Work Hours Per Day"
                        description={
                            <div>
                                <p><strong>What this means:</strong> The number of hours in a standard workday, used to calculate hourly rates from daily/monthly salaries.</p>
                                <p><strong>How it's used:</strong></p>
                                <ul>
                                    <li><strong>Daily Rate:</strong> Basic Salary ÷ Standard Days = Daily Rate</li>
                                    <li><strong>Hourly Rate:</strong> Daily Rate ÷ Hours Per Day = Hourly Rate</li>
                                </ul>
                                <p><strong>Example with 8 hours:</strong></p>
                                <ul>
                                    <li>Employee Salary: 280 KD/month</li>
                                    <li>Standard Days: 28</li>
                                    <li>Daily Rate: 280 ÷ 28 = 10 KD/day</li>
                                    <li>Hourly Rate: 10 ÷ 8 = <strong>1.25 KD/hour</strong></li>
                                </ul>
                                <p><strong>Example with 12 hours:</strong></p>
                                <ul>
                                    <li>Same salary: 280 KD/month</li>
                                    <li>Hourly Rate: 10 ÷ 12 = <strong>0.833 KD/hour</strong></li>
                                </ul>
                                <p style={{ marginTop: 12, color: '#fa8c16' }}>
                                    <WarningOutlined /> <strong>Impact:</strong> Changing this affects ALL overtime calculations and hourly employee pay rates. Higher hours = lower hourly rate (same salary spread over more hours).
                                </p>
                            </div>
                        }
                        style={{ marginBottom: 16 }}
                    />

                    <Row gutter={24}>
                        <Col xs={24} md={12}>
                            <Form.Item
                                name="standard_hours_per_day"
                                label="Standard Hours Per Day"
                                tooltip="Number of hours in a standard shift. Used to convert daily rates to hourly rates. Common: 8 hours (office), 12 hours (security/shifts)."
                                rules={[{ required: true, message: 'Required' }]}
                            >
                                <InputNumber
                                    style={{ width: '100%' }}
                                    min={6}
                                    max={12}
                                    step={1}
                                    suffix="hours"
                                    placeholder="8"
                                />
                            </Form.Item>
                            <Text type="secondary" style={{ fontSize: 12 }}>
                                Used to calculate: Hourly Rate = Daily Rate ÷ Hours Per Day
                            </Text>
                        </Col>

                        <Col xs={24} md={12}>
                            <Alert
                                type="info"
                                showIcon
                                title="Absence Deduction Policy"
                                description={
                                    <div>
                                        <p><strong>What this means:</strong> Controls whether absent days are automatically deducted from salaried employees' monthly pay.</p>
                                        <p><strong>When Enabled:</strong></p>
                                        <ul>
                                            <li>Absent days are calculated: Standard Days - Present Days</li>
                                            <li>Deduction = Absent Days × Daily Rate</li>
                                            <li>Example: 2 absent days × 10 KD/day = <strong>20 KD deducted</strong></li>
                                        </ul>
                                        <p><strong>When Disabled:</strong></p>
                                        <ul>
                                            <li>Employees receive full monthly salary regardless of absences</li>
                                            <li>You must manually add deductions if needed</li>
                                        </ul>
                                        <p style={{ marginTop: 12, color: '#fa8c16' }}>
                                            <WarningOutlined /> <strong>Impact:</strong> Only affects salaried employees (monthly fixed salary). Hourly employees are always paid based on hours worked.
                                        </p>
                                    </div>
                                }
                                style={{ marginBottom: 16 }}
                            />
                            <Form.Item
                                name="enable_absence_deduction"
                                label="Absence Deductions"
                                valuePropName="checked"
                            >
                                <Switch
                                    checkedChildren="Enabled"
                                    unCheckedChildren="Disabled"
                                />
                            </Form.Item>
                            <Text type="secondary" style={{ fontSize: 12 }}>
                                When enabled, absent days are deducted from salaried employees' pay
                            </Text>
                        </Col>
                    </Row>

                    <Divider titlePlacement="left">
                        <FolderOutlined /> File Storage Configuration
                    </Divider>

                    <Alert
                        type="info"
                        showIcon
                        description={
                            <div>
                                <p><strong>How it works:</strong> Files are saved in TWO locations:</p>
                                <ul>
                                    <li>📁 <strong>Database Storage:</strong> Automatic (backend/uploads) - used by the application</li>
                                    <li>📂 <strong>Custom Folder:</strong> Your choice (e.g., D:\MONTREAL_Files) - easy manual access</li>
                                </ul>
                                <p style={{ marginTop: 12 }}>
                                    <strong>Benefits:</strong> Database integrity + Easy file browsing in Windows Explorer
                                </p>
                            </div>
                        }
                        style={{ marginBottom: 24 }}
                    />

                    <Row gutter={24}>
                        <Col xs={24} md={12}>
                            <Form.Item
                                name="enable_local_storage"
                                label="Enable Custom Folder Backup"
                                valuePropName="checked"
                            >
                                <Switch
                                    checkedChildren="Enabled"
                                    unCheckedChildren="Disabled"
                                />
                            </Form.Item>
                            <Text type="secondary" style={{ fontSize: 12 }}>
                                When enabled, files are copied to your custom folder for easy access
                            </Text>
                        </Col>

                        <Col xs={24} md={12}>
                            <Form.Item
                                name="use_employee_name_in_filename"
                                label="Use Employee Names in Filenames"
                                valuePropName="checked"
                            >
                                <Switch
                                    checkedChildren="Yes"
                                    unCheckedChildren="No"
                                />
                            </Form.Item>
                            <Text type="secondary" style={{ fontSize: 12 }}>
                                Example: "13_Naveen_photo.jpg" vs "emp_13_20260404.jpg"
                            </Text>
                        </Col>
                    </Row>

                    <Form.Item
                        name="custom_storage_path"
                        label="Custom Storage Folder Path"
                        tooltip="Local folder where files will be backed up (e.g., D:\MONTREAL_Files or \\NetworkShare\HR)"
                    >
                        <Input
                            placeholder="D:\MONTREAL_Files"
                            prefix={<FolderOutlined />}
                        />
                    </Form.Item>

                    <Alert
                        type="warning"
                        message="Important: Folder must exist and be writable"
                        description="Make sure the folder path exists and the application has write permissions. If the folder is unavailable, files will still be saved to the database storage."
                        showIcon
                        style={{ marginTop: 8, marginBottom: 16 }}
                    />

                    {settings?.last_updated && (
                        <Alert
                            type="info"
                            title={`Last updated: ${new Date(settings.last_updated).toLocaleString()} by ${settings.updated_by || 'Admin'}`}
                            style={{ marginTop: 24, marginBottom: 16 }}
                        />
                    )}

                    {settings && (
                        <Card style={{ marginTop: 24, background: '#f0f5ff', borderColor: '#1890ff' }}>
                            <Title level={5}>💡 Quick Preview with Current Settings</Title>
                            <p>For an employee earning <strong>280 KD/month</strong> working <strong>28 days</strong>:</p>
                            <Row gutter={16}>
                                <Col span={8}>
                                    <Statistic
                                        title="Hourly Rate"
                                        value={(280 / 28 / (settings.standard_hours_per_day || 8)).toFixed(3)}
                                        suffix="KD/hr"
                                    />
                                </Col>
                                <Col span={8}>
                                    <Statistic
                                        title="Normal OT Rate"
                                        value={(280 / 28 / (settings.standard_hours_per_day || 8) * (settings.normal_overtime_multiplier || 1.25)).toFixed(3)}
                                        suffix="KD/hr"
                                        styles={{ content: { color: '#fa8c16' } }}
                                    />
                                </Col>
                                <Col span={8}>
                                    <Statistic
                                        title="Off-Day OT Rate"
                                        value={(280 / 28 / (settings.standard_hours_per_day || 8) * (settings.offday_overtime_multiplier || 1.5)).toFixed(3)}
                                        suffix="KD/hr"
                                        styles={{ content: { color: '#cf1322' } }}
                                    />
                                </Col>
                            </Row>
                        </Card>
                    )}

                    <Button
                        type="primary"
                        htmlType="submit"
                        icon={<SaveOutlined />}
                        loading={saving}
                        size="large"
                        style={{ marginTop: 16 }}
                    >
                        Save Settings
                    </Button>
                </Form>
            </Card>
        </div>
    );
}

export default CompanySettingsPage;
