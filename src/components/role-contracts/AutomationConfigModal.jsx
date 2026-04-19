/**
 * AutomationConfigModal.jsx
 *
 * Modal for creating / editing automation rules on a contract.
 * Lets users select a trigger event, define an action, and set conditions.
 */

import React, { useState } from 'react';
import {
  Modal, Form, Select, Input, Button, Space, Typography, Switch,
  Divider, Alert,
} from 'antd';
import { ThunderboltOutlined, InfoCircleOutlined } from '@ant-design/icons';
import { toast } from 'react-toastify';
import { createAutomation } from '../../services/contractService';

const { Text } = Typography;
const { TextArea } = Input;

const TRIGGER_OPTIONS = [
  { value: 'CONTRACT_START', label: 'Contract Start' },
  { value: 'CONTRACT_END', label: 'Contract End (Expiry)' },
  { value: 'STATUS_CHANGE', label: 'Status Change' },
  { value: 'MILESTONE_REACHED', label: 'Milestone Reached' },
  { value: 'EXPIRY_WARNING_30D', label: 'Expiry Warning (30 days)' },
  { value: 'EXPIRY_WARNING_15D', label: 'Expiry Warning (15 days)' },
  { value: 'EXPIRY_WARNING_7D', label: 'Expiry Warning (7 days)' },
  { value: 'PAYMENT_DUE', label: 'Payment Due' },
];

const ACTION_OPTIONS = [
  { value: 'SEND_NOTIFICATION', label: 'Send Notification' },
  { value: 'UPDATE_STATUS', label: 'Update Status' },
  { value: 'ASSIGN_RESOURCES', label: 'Assign Resources' },
  { value: 'CREATE_TASK', label: 'Create Task' },
  { value: 'SEND_EMAIL', label: 'Send Email' },
  { value: 'REQUEST_APPROVAL', label: 'Request Approval' },
];

const AutomationConfigModal = ({
  open,
  contractId,
  automation = null,
  onClose,
  onSuccess,
}) => {
  const [form] = Form.useForm();
  const [submitting, setSubmitting] = useState(false);

  const isEditing = !!automation;

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);

      const payload = {
        trigger: values.trigger,
        action: values.action,
        action_config: {
          message: values.message,
          recipients: values.recipients,
          status: values.target_status,
        },
        conditions: values.conditions || '',
        is_enabled: values.is_enabled !== false,
        description: values.description,
      };

      await createAutomation(contractId, payload);
      toast.success(`Automation ${isEditing ? 'updated' : 'created'} successfully`);
      form.resetFields();
      onSuccess?.();
      onClose?.();
    } catch (err) {
      if (err?.errorFields) return;
      toast.error('Failed to save automation');
    } finally {
      setSubmitting(false);
    }
  };

  const initialValues = automation
    ? {
        trigger: automation.trigger,
        action: automation.action,
        message: automation.action_config?.message,
        recipients: automation.action_config?.recipients,
        target_status: automation.action_config?.status,
        conditions: automation.conditions,
        is_enabled: automation.is_enabled,
        description: automation.description,
      }
    : { is_enabled: true };

  return (
    <Modal
      open={open}
      title={
        <Space>
          <ThunderboltOutlined style={{ color: '#faad14' }} />
          {isEditing ? 'Edit Automation Rule' : 'Create Automation Rule'}
        </Space>
      }
      onCancel={onClose}
      footer={[
        <Button key="cancel" onClick={onClose}>Cancel</Button>,
        <Button key="submit" type="primary" loading={submitting} onClick={handleSubmit}>
          {isEditing ? 'Update' : 'Create'} Automation
        </Button>,
      ]}
      width={600}
    >
      <Alert
        message="Automations run automatically when the trigger condition is met."
        type="info"
        icon={<InfoCircleOutlined />}
        showIcon
        style={{ marginBottom: 16 }}
      />

      <Form
        form={form}
        layout="vertical"
        initialValues={initialValues}
      >
        <Form.Item
          name="trigger"
          label="Trigger Event"
          rules={[{ required: true, message: 'Please select a trigger' }]}
        >
          <Select options={TRIGGER_OPTIONS} placeholder="When should this run?" />
        </Form.Item>

        <Form.Item
          name="action"
          label="Action to Perform"
          rules={[{ required: true, message: 'Please select an action' }]}
        >
          <Select options={ACTION_OPTIONS} placeholder="What should happen?" />
        </Form.Item>

        <Form.Item name="message" label="Message / Content">
          <TextArea
            rows={3}
            placeholder="Message or content for the action (e.g. notification text)…"
          />
        </Form.Item>

        <Form.Item name="recipients" label="Recipients (comma-separated emails or user IDs)">
          <Input placeholder="e.g. admin@company.com, manager@company.com" />
        </Form.Item>

        <Form.Item name="conditions" label="Conditions (optional JSON)">
          <TextArea
            rows={2}
            placeholder={'{"min_days_remaining": 7, "status": "ACTIVE"}'}
            style={{ fontFamily: 'monospace', fontSize: 12 }}
          />
        </Form.Item>

        <Form.Item name="description" label="Description">
          <Input placeholder="Brief description of what this automation does…" />
        </Form.Item>

        <Form.Item
          name="is_enabled"
          label="Enabled"
          valuePropName="checked"
        >
          <Switch defaultChecked />
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default AutomationConfigModal;
