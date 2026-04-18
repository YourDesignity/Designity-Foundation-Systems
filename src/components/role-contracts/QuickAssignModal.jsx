import React, { useMemo } from 'react';
import { Modal, Select, Form, Typography, Tag, Alert } from 'antd';
import { useEmployees } from '../../hooks/useEmployees';
import { useAssignEmployeeToSlot } from '../../hooks/useRoleContracts';

const { Text } = Typography;

/**
 * QuickAssignModal – one-click assignment of an employee to an unfilled slot.
 *
 * Props:
 *   open          – boolean – controls visibility
 *   slot          – { slot_id, designation, fulfillment_id } | null
 *   assignedIds   – number[] – employee IDs already assigned to this record
 *   onCancel      – () => void
 *   onSuccess     – () => void – called after a successful assignment
 */
const QuickAssignModal = ({ open, slot, assignedIds = [], onCancel, onSuccess }) => {
  const [form] = Form.useForm();

  const { data: employees = [] } = useEmployees();
  const assignMutation = useAssignEmployeeToSlot();

  const available = useMemo(
    () =>
      employees.filter(
        (emp) =>
          emp.designation === slot?.designation &&
          !assignedIds.includes(emp.uid),
      ),
    [employees, slot, assignedIds],
  );

  const handleOk = () => {
    form
      .validateFields()
      .then(({ employee_id }) => {
        assignMutation.mutate(
          {
            fulfillmentId: slot.fulfillment_id,
            payload: { slot_id: slot.slot_id, employee_id, attendance_status: 'Present' },
          },
          {
            onSuccess: () => {
              form.resetFields();
              onSuccess?.();
              onCancel();
            },
          },
        );
      })
      .catch(() => {});
  };

  return (
    <Modal
      title={`Quick Assign – Slot ${slot?.slot_id ?? ''}`}
      open={open}
      onCancel={() => {
        form.resetFields();
        onCancel();
      }}
      onOk={handleOk}
      confirmLoading={assignMutation.isPending}
      okText="Assign"
      destroyOnHidden
    >
      {slot && (
        <div style={{ marginBottom: 12 }}>
          <Text type="secondary">Designation: </Text>
          <Tag color="blue">{slot.designation}</Tag>
        </div>
      )}

      {available.length === 0 && (
        <Alert
          type="warning"
          message="No available employees match this designation."
          style={{ marginBottom: 12 }}
          showIcon
        />
      )}

      <Form form={form} layout="vertical">
        <Form.Item
          name="employee_id"
          label="Select Employee"
          rules={[{ required: true, message: 'Please select an employee' }]}
        >
          <Select
            showSearch
            placeholder="Search by name…"
            optionFilterProp="label"
            options={available.map((emp) => ({
              value: emp.uid,
              label: `${emp.full_name} (${emp.designation})`,
            }))}
          />
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default QuickAssignModal;
