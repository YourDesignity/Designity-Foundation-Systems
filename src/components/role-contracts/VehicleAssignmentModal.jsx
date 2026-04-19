/**
 * VehicleAssignmentModal.jsx
 *
 * Modal for assigning vehicles to a contract.
 */

import React, { useState, useEffect } from 'react';
import {
  Modal, Form, Select, DatePicker, InputNumber, Input, Button, Space, Spin,
} from 'antd';
import { CarOutlined } from '@ant-design/icons';
import { toast } from 'react-toastify';
import { assignVehicle } from '../../services/contractService';
import { fetchWithAuth } from '../../services/apiService';

const { RangePicker } = DatePicker;

const VehicleAssignmentModal = ({ open, contractId, onClose, onSuccess }) => {
  const [form] = Form.useForm();
  const [vehicles, setVehicles] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (open) {
      loadData();
    }
  }, [open]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [vehicleData, empData] = await Promise.all([
        fetchWithAuth('/vehicles/'),
        fetchWithAuth('/employees/'),
      ]);
      setVehicles(Array.isArray(vehicleData) ? vehicleData : vehicleData?.vehicles || []);
      setEmployees(Array.isArray(empData) ? empData : empData?.employees || []);
    } catch {
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);

      const [startDate, endDate] = values.usage_period || [];
      await assignVehicle(contractId, values.vehicle_ids, {
        driver_ids: values.driver_ids || [],
        start_date: startDate?.toISOString(),
        end_date: endDate?.toISOString(),
        starting_mileage: values.starting_mileage,
        notes: values.notes,
      });

      toast.success('Vehicles assigned successfully');
      form.resetFields();
      onSuccess?.();
      onClose?.();
    } catch (err) {
      if (err?.errorFields) return;
      toast.error('Failed to assign vehicles');
    } finally {
      setSubmitting(false);
    }
  };

  const vehicleOptions = vehicles.map((v) => ({
    value: v.uid ?? v.id,
    label: `${v.plate_number || v.registration_number || `Vehicle #${v.uid}`} — ${v.make || ''} ${v.model || ''}`.trim(),
  }));

  const driverOptions = employees
    .filter((e) => !e.designation || e.designation?.toLowerCase().includes('driver'))
    .map((emp) => ({
      value: emp.uid ?? emp.id,
      label: emp.name || emp.full_name || `Employee #${emp.uid}`,
    }));

  // Fallback: all employees
  const employeeOptions = employees.map((emp) => ({
    value: emp.uid ?? emp.id,
    label: emp.name || emp.full_name || `Employee #${emp.uid}`,
  }));

  return (
    <Modal
      open={open}
      title={
        <Space>
          <CarOutlined style={{ color: '#722ed1' }} />
          Assign Vehicles
        </Space>
      }
      onCancel={onClose}
      footer={[
        <Button key="cancel" onClick={onClose}>Cancel</Button>,
        <Button key="submit" type="primary" loading={submitting} onClick={handleSubmit}>
          Assign
        </Button>,
      ]}
      width={580}
    >
      <Spin spinning={loading}>
        <Form form={form} layout="vertical" style={{ marginTop: 12 }}>
          <Form.Item
            name="vehicle_ids"
            label="Select Vehicles"
            rules={[{ required: true, message: 'Please select at least one vehicle' }]}
          >
            <Select
              mode="multiple"
              placeholder="Search vehicles…"
              options={vehicleOptions}
              filterOption={(input, option) =>
                (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
              }
              showSearch
              maxTagCount={3}
            />
          </Form.Item>

          <Form.Item name="driver_ids" label="Assign Driver(s)">
            <Select
              mode="multiple"
              placeholder="Select driver(s)…"
              options={driverOptions.length > 0 ? driverOptions : employeeOptions}
              filterOption={(input, option) =>
                (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
              }
              showSearch
              maxTagCount={3}
            />
          </Form.Item>

          <Form.Item name="usage_period" label="Usage Period">
            <RangePicker style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item name="starting_mileage" label="Starting Mileage (km)">
            <InputNumber min={0} style={{ width: '100%' }} placeholder="e.g. 45200" />
          </Form.Item>

          <Form.Item name="notes" label="Notes">
            <Input.TextArea rows={2} placeholder="Any notes for this vehicle assignment…" />
          </Form.Item>
        </Form>
      </Spin>
    </Modal>
  );
};

export default VehicleAssignmentModal;
