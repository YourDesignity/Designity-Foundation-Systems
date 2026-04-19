/**
 * EmployeeAssignmentModal.jsx
 *
 * Modal for assigning employees to a contract.
 * Supports multi-select, role/responsibility assignment, and date ranges.
 */

import React, { useState, useEffect } from 'react';
import {
  Modal, Form, Select, DatePicker, Input, Button, Space,
  Typography, Tag, Divider, Spin,
} from 'antd';
import { TeamOutlined } from '@ant-design/icons';
import { toast } from 'react-toastify';
import dayjs from 'dayjs';
import { assignEmployee } from '../../services/contractService';
import { fetchWithAuth } from '../../services/apiService';

const { Text } = Typography;
const { RangePicker } = DatePicker;

const PERMISSION_OPTIONS = [
  { value: 'view', label: 'View' },
  { value: 'edit', label: 'Edit' },
  { value: 'manage', label: 'Manage' },
];

const EmployeeAssignmentModal = ({ open, contractId, onClose, onSuccess }) => {
  const [form] = Form.useForm();
  const [employees, setEmployees] = useState([]);
  const [loadingEmployees, setLoadingEmployees] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (open) {
      loadEmployees();
    }
  }, [open]);

  const loadEmployees = async () => {
    setLoadingEmployees(true);
    try {
      const data = await fetchWithAuth('/employees/');
      setEmployees(Array.isArray(data) ? data : data?.employees || []);
    } catch {
      toast.error('Failed to load employees');
    } finally {
      setLoadingEmployees(false);
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);

      const [startDate, endDate] = values.date_range || [];
      await assignEmployee(contractId, values.employee_ids, {
        start_date: startDate?.toISOString(),
        end_date: endDate?.toISOString(),
        role: values.role,
        responsibilities: values.responsibilities,
        permissions: values.permissions || ['view'],
      });

      toast.success('Employees assigned successfully');
      form.resetFields();
      onSuccess?.();
      onClose?.();
    } catch (err) {
      if (err?.errorFields) return; // Ant Design validation error
      toast.error('Failed to assign employees');
    } finally {
      setSubmitting(false);
    }
  };

  const employeeOptions = employees.map((emp) => ({
    value: emp.uid ?? emp.id,
    label: `${emp.name || emp.full_name || `Employee #${emp.uid}`} — ${emp.designation || ''}`,
  }));

  return (
    <Modal
      open={open}
      title={
        <Space>
          <TeamOutlined style={{ color: '#1890ff' }} />
          Assign Employees
        </Space>
      }
      onCancel={onClose}
      footer={[
        <Button key="cancel" onClick={onClose}>Cancel</Button>,
        <Button key="submit" type="primary" loading={submitting} onClick={handleSubmit}>
          Assign
        </Button>,
      ]}
      width={600}
    >
      <Spin spinning={loadingEmployees}>
        <Form form={form} layout="vertical" style={{ marginTop: 12 }}>
          <Form.Item
            name="employee_ids"
            label="Select Employees"
            rules={[{ required: true, message: 'Please select at least one employee' }]}
          >
            <Select
              mode="multiple"
              placeholder="Search and select employees…"
              options={employeeOptions}
              filterOption={(input, option) =>
                (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
              }
              showSearch
              maxTagCount={4}
            />
          </Form.Item>

          <Form.Item name="role" label="Role / Title">
            <Input placeholder="e.g. Site Supervisor, Driver, Labour" />
          </Form.Item>

          <Form.Item name="date_range" label="Assignment Period">
            <RangePicker style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item name="responsibilities" label="Responsibilities">
            <Input.TextArea rows={3} placeholder="Describe responsibilities for this assignment…" />
          </Form.Item>

          <Form.Item name="permissions" label="Access Permissions">
            <Select
              mode="multiple"
              placeholder="Select permissions"
              options={PERMISSION_OPTIONS}
            />
          </Form.Item>
        </Form>
      </Spin>
    </Modal>
  );
};

export default EmployeeAssignmentModal;
