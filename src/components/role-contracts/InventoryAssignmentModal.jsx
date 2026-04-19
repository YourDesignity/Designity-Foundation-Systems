/**
 * InventoryAssignmentModal.jsx
 *
 * Modal for allocating inventory items to a contract.
 */

import React, { useState, useEffect } from 'react';
import {
  Modal, Form, Select, DatePicker, InputNumber, Input, Button, Space, Spin,
} from 'antd';
import { ShoppingOutlined } from '@ant-design/icons';
import { toast } from 'react-toastify';
import { assignInventory } from '../../services/contractService';
import { fetchWithAuth } from '../../services/apiService';

const InventoryAssignmentModal = ({ open, contractId, onClose, onSuccess }) => {
  const [form] = Form.useForm();
  const [items, setItems] = useState([]);
  const [loadingItems, setLoadingItems] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (open) {
      loadItems();
    }
  }, [open]);

  const loadItems = async () => {
    setLoadingItems(true);
    try {
      const data = await fetchWithAuth('/inventory/materials/');
      setItems(Array.isArray(data) ? data : data?.materials || []);
    } catch {
      toast.error('Failed to load inventory');
    } finally {
      setLoadingItems(false);
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);

      await assignInventory(contractId, values.inventory_ids, {
        quantity: values.quantity,
        expected_return_date: values.expected_return_date?.toISOString(),
        notes: values.notes,
        condition: values.condition,
      });

      toast.success('Inventory assigned successfully');
      form.resetFields();
      onSuccess?.();
      onClose?.();
    } catch (err) {
      if (err?.errorFields) return;
      toast.error('Failed to assign inventory');
    } finally {
      setSubmitting(false);
    }
  };

  const itemOptions = items.map((item) => ({
    value: item.uid ?? item.id ?? item.material_id,
    label: `${item.name || item.material_name || `Item #${item.uid}`}${item.unit ? ` (${item.unit})` : ''}`,
  }));

  return (
    <Modal
      open={open}
      title={
        <Space>
          <ShoppingOutlined style={{ color: '#fa8c16' }} />
          Assign Inventory
        </Space>
      }
      onCancel={onClose}
      footer={[
        <Button key="cancel" onClick={onClose}>Cancel</Button>,
        <Button key="submit" type="primary" loading={submitting} onClick={handleSubmit}>
          Assign
        </Button>,
      ]}
      width={560}
    >
      <Spin spinning={loadingItems}>
        <Form form={form} layout="vertical" style={{ marginTop: 12 }}>
          <Form.Item
            name="inventory_ids"
            label="Select Items"
            rules={[{ required: true, message: 'Please select at least one item' }]}
          >
            <Select
              mode="multiple"
              placeholder="Search inventory items…"
              options={itemOptions}
              filterOption={(input, option) =>
                (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
              }
              showSearch
              maxTagCount={4}
            />
          </Form.Item>

          <Form.Item name="quantity" label="Quantity">
            <InputNumber min={1} style={{ width: '100%' }} placeholder="Enter quantity" />
          </Form.Item>

          <Form.Item name="expected_return_date" label="Expected Return Date">
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item name="condition" label="Condition">
            <Select
              options={[
                { value: 'new', label: 'New' },
                { value: 'good', label: 'Good' },
                { value: 'fair', label: 'Fair' },
                { value: 'poor', label: 'Poor' },
              ]}
              placeholder="Select condition"
            />
          </Form.Item>

          <Form.Item name="notes" label="Notes / Conditions">
            <Input.TextArea rows={2} placeholder="Any special notes or conditions…" />
          </Form.Item>
        </Form>
      </Spin>
    </Modal>
  );
};

export default InventoryAssignmentModal;
