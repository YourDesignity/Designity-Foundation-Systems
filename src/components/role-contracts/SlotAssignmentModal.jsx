import React, { useMemo } from 'react';
import { Modal, Form, Select, Input, Alert } from 'antd';

const SlotAssignmentModal = ({ open, slot, employees = [], loading, onCancel, onSubmit, assignedEmployeeIds = [] }) => {
  const [form] = Form.useForm();
  const filteredEmployees = useMemo(() => employees.filter((emp) => emp.designation === slot?.designation), [employees, slot]);

  return (
    <Modal
      title={`Assign Employee: ${slot?.slot_id || ''}`}
      open={open}
      onCancel={onCancel}
      onOk={() => form.submit()}
      confirmLoading={loading}
      destroyOnHidden
    >
      {slot && assignedEmployeeIds.length > 0 && (
        <Alert type="info" title="Already-assigned employees are hidden from the picker to prevent double-booking." style={{ marginBottom: 12 }} />
      )}
      <Form
        form={form}
        layout="vertical"
        initialValues={{ attendance_status: 'Present' }}
        onFinish={onSubmit}
      >
        <Form.Item name="employee_id" label="Employee" rules={[{ required: true, message: 'Please select an employee' }]}>
          <Select
            showSearch
            options={filteredEmployees
              .filter((emp) => !assignedEmployeeIds.includes(emp.uid))
              .map((emp) => ({ value: emp.uid, label: `${emp.name} (${emp.designation})` }))}
          />
        </Form.Item>
        <Form.Item name="attendance_status" label="Attendance">
          <Select options={['Present', 'Absent', 'Leave', 'Late'].map((value) => ({ value, label: value }))} />
        </Form.Item>
        <Form.Item name="notes" label="Notes">
          <Input.TextArea rows={3} maxLength={240} />
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default SlotAssignmentModal;
