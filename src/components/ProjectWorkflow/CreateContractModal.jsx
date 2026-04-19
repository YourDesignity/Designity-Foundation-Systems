import React, { useState, useEffect } from 'react';
import { Modal, Form, Input, DatePicker, InputNumber, message } from 'antd';
import { fetchWithAuth } from '../../services/apiService';

const { TextArea } = Input;

const CreateContractModal = ({ visible, projectId, onCancel, onSuccess }) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!visible) {
      form.resetFields();
    }
  }, [visible, form]);

  const handleSubmit = async () => {
    try {
      await form.validateFields(['start_date', 'end_date', 'contract_value']);
      const values = form.getFieldsValue(true);
      setLoading(true);

      const payload = {
        project_id: projectId,
        contract_name: values.contract_name,
        start_date: values.start_date.format('YYYY-MM-DD'),
        end_date: values.end_date.format('YYYY-MM-DD'),
        contract_value: values.contract_value,
        payment_terms: values.payment_terms,
        notes: values.notes,
      };

      const data = await fetchWithAuth('/workflow/contracts/', {
        method: 'POST',
        body: JSON.stringify(payload),
      });

      message.success(`Contract ${data.contract_code} created successfully!`);
      form.resetFields();
      onSuccess(data);
    } catch (error) {
      console.error('Error creating contract:', error);
      message.error(error.message || 'Error creating contract');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title="Add New Contract"
      open={visible}
      onOk={handleSubmit}
      onCancel={onCancel}
      okText="Create Contract"
      confirmLoading={loading}
      width={600}
    >
      <Form form={form} layout="vertical">
        <Form.Item name="contract_name" label="Contract Name">
          <Input placeholder="Optional contract name" />
        </Form.Item>

        <Form.Item
          name="start_date"
          label="Start Date"
          rules={[{ required: true, message: 'Please select start date' }]}
        >
          <DatePicker style={{ width: '100%' }} />
        </Form.Item>

        <Form.Item
          name="end_date"
          label="End Date"
          rules={[{ required: true, message: 'Please select end date' }]}
        >
          <DatePicker style={{ width: '100%' }} />
        </Form.Item>

        <Form.Item
          name="contract_value"
          label="Contract Value (KD)"
          rules={[{ required: true, message: 'Please enter contract value' }]}
        >
          <InputNumber
            style={{ width: '100%' }}
            min={0}
            formatter={(v) => `${v}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
            parser={(v) => v.replace(/,/g, '')}
          />
        </Form.Item>

        <Form.Item name="payment_terms" label="Payment Terms">
          <Input placeholder="e.g., Net 30 days" />
        </Form.Item>

        <Form.Item name="notes" label="Notes">
          <TextArea rows={3} placeholder="Additional notes..." />
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default CreateContractModal;
