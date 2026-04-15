import React, { useState, useEffect } from 'react';
import { Modal, Form, Input, InputNumber, Select, message } from 'antd';
import { fetchWithAuth } from '../../services/apiService';

const { TextArea } = Input;

const CreateSiteModal = ({ visible, projectId, contracts, onCancel, onSuccess }) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!visible) {
      form.resetFields();
    }
  }, [visible, form]);

  const handleSubmit = async () => {
    try {
      await form.validateFields(['site_name', 'location', 'contract_id']);
      const values = form.getFieldsValue(true);
      setLoading(true);

      const payload = {
        site_name: values.site_name,
        location: values.location,
        description: values.description,
        project_id: projectId,
        contract_id: values.contract_id,
        required_workers: values.required_workers || 0,
      };

      const data = await fetchWithAuth('/workflow/sites/', {
        method: 'POST',
        body: JSON.stringify(payload),
      });

      message.success(`Site ${data.site_code} created successfully!`);
      form.resetFields();
      onSuccess(data);
    } catch (error) {
      console.error('Error creating site:', error);
      message.error(error.message || 'Error creating site');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title="Add New Site"
      open={visible}
      onOk={handleSubmit}
      onCancel={onCancel}
      okText="Create Site"
      confirmLoading={loading}
      width={600}
    >
      <Form form={form} layout="vertical">
        <Form.Item
          name="site_name"
          label="Site Name"
          rules={[{ required: true, message: 'Please enter site name' }]}
        >
          <Input placeholder="e.g., Block A - Ground Floor" />
        </Form.Item>

        <Form.Item
          name="location"
          label="Location"
          rules={[{ required: true, message: 'Please enter location' }]}
        >
          <Input placeholder="e.g., Kuwait City, Block 5" />
        </Form.Item>

        <Form.Item
          name="contract_id"
          label="Contract"
          rules={[{ required: true, message: 'Please select a contract' }]}
        >
          <Select placeholder="Select contract">
            {(contracts || []).map((c) => (
              <Select.Option key={c.uid} value={c.uid}>
                {c.contract_code} {c.contract_name ? `– ${c.contract_name}` : ''}
              </Select.Option>
            ))}
          </Select>
        </Form.Item>

        <Form.Item name="required_workers" label="Required Workers">
          <InputNumber style={{ width: '100%' }} min={0} placeholder="0" />
        </Form.Item>

        <Form.Item name="description" label="Description">
          <TextArea rows={3} placeholder="Site description..." />
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default CreateSiteModal;
