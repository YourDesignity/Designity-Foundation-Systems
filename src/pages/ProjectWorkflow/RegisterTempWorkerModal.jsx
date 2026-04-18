// src/pages/ProjectWorkflow/RegisterTempWorkerModal.jsx
import React, { useState } from 'react';
import {
    Modal, Form, Input, InputNumber, Select, Radio, message
} from 'antd';
import { registerTempWorker } from '../../services/tempWorkerService';

const { Option } = Select;

const DESIGNATIONS = [
    'Security Guard',
    'Cleaner',
    'Driver',
    'Technician',
    'Supervisor',
    'Laborer',
    'Helper',
    'Electrician',
    'Plumber',
    'Carpenter',
    'Other',
];

const RegisterTempWorkerModal = ({ visible, onCancel, onSuccess }) => {
    const [form] = Form.useForm();
    const [loading, setLoading] = useState(false);
    const [rateType, setRateType] = useState('Daily');

    const handleSubmit = async () => {
        try {
            const values = await form.validateFields();
            setLoading(true);

            const data = {
                name: values.name,
                phone_kuwait: values.phone_kuwait || null,
                designation: values.designation,
                agency_name: values.agency_name || null,
                rate_type: values.rate_type || 'Daily',
                daily_rate: values.daily_rate || 0.0,
                hourly_rate: values.hourly_rate || 0.0,
            };

            const result = await registerTempWorker(data);
            message.success(`Worker "${result.name}" registered successfully (${result.employee_code})`);
            form.resetFields();
            setRateType('Daily');
            onSuccess(result);
        } catch (error) {
            if (error.errorFields) return; // Validation error, don't show message
            message.error(error.message || 'Failed to register worker');
        } finally {
            setLoading(false);
        }
    };

    const handleCancel = () => {
        form.resetFields();
        setRateType('Daily');
        onCancel();
    };

    return (
        <Modal
            title="Register New Temporary Worker"
            open={visible}
            onOk={handleSubmit}
            onCancel={handleCancel}
            okText="Register Worker"
            width={560}
            confirmLoading={loading}
            destroyOnHidden
        >
            <Form form={form} layout="vertical" initialValues={{ rate_type: 'Daily' }}>
                <Form.Item
                    name="name"
                    label="Full Name"
                    rules={[{ required: true, message: 'Full name is required' }]}
                >
                    <Input placeholder="e.g. Ahmed Al-Rashidi" />
                </Form.Item>

                <Form.Item name="phone_kuwait" label="Phone Number (Kuwait)">
                    <Input placeholder="e.g. +965 9999 9999" />
                </Form.Item>

                <Form.Item
                    name="designation"
                    label="Designation"
                    rules={[{ required: true, message: 'Designation is required' }]}
                >
                    <Select placeholder="Select designation" showSearch allowClear>
                        {DESIGNATIONS.map(d => (
                            <Option key={d} value={d}>{d}</Option>
                        ))}
                    </Select>
                </Form.Item>

                <Form.Item name="agency_name" label="Agency Name (Optional)">
                    <Input placeholder="e.g. Gulf Staffing Solutions" />
                </Form.Item>

                <Form.Item name="rate_type" label="Rate Type">
                    <Radio.Group onChange={e => setRateType(e.target.value)}>
                        <Radio value="Daily">Daily Rate (KD/day)</Radio>
                        <Radio value="Hourly">Hourly Rate (KD/hour)</Radio>
                    </Radio.Group>
                </Form.Item>

                {rateType === 'Daily' || rateType === undefined ? (
                    <Form.Item
                        name="daily_rate"
                        label="Daily Rate (KD)"
                        rules={[{ required: rateType === 'Daily', message: 'Daily rate is required' }]}
                    >
                        <InputNumber
                            style={{ width: '100%' }}
                            min={0}
                            step={0.5}
                            precision={3}
                            placeholder="e.g. 15.000"
                            addonAfter="KD/day"
                        />
                    </Form.Item>
                ) : null}

                {rateType === 'Hourly' ? (
                    <Form.Item
                        name="hourly_rate"
                        label="Hourly Rate (KD)"
                        rules={[{ required: rateType === 'Hourly', message: 'Hourly rate is required' }]}
                    >
                        <InputNumber
                            style={{ width: '100%' }}
                            min={0}
                            step={0.1}
                            precision={3}
                            placeholder="e.g. 1.875"
                            addonAfter="KD/hr"
                        />
                    </Form.Item>
                ) : null}
            </Form>
        </Modal>
    );
};

export default RegisterTempWorkerModal;
