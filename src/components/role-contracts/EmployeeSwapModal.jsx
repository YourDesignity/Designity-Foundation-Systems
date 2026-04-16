import React, { useMemo } from 'react';
import { Modal, Form, Select, Input, Descriptions } from 'antd';

const reasons = ['Employee absent', 'Employee on leave', 'Performance issue', 'Other'];

const EmployeeSwapModal = ({ open, slot, employees = [], loading, onCancel, onSubmit, assignedEmployeeIds = [] }) => {
  const [form] = Form.useForm();
  const filteredEmployees = useMemo(() => employees.filter((emp) => emp.designation === slot?.designation), [employees, slot]);

  return (
    <Modal
      title={`Swap Employee: ${slot?.slot_id || ''}`}
      open={open}
      onCancel={onCancel}
      onOk={() => form.submit()}
      confirmLoading={loading}
      destroyOnHidden
    >
      {slot && (
        <Descriptions size="small" column={1} style={{ marginBottom: 12 }}>
          <Descriptions.Item label="Current Employee">{slot.employee_name || '—'}</Descriptions.Item>
          <Descriptions.Item label="Current Attendance">{slot.attendance_status || '—'}</Descriptions.Item>
        </Descriptions>
      )}
      <Form
        form={form}
        layout="vertical"
        onFinish={onSubmit}
        initialValues={{ reason: 'Employee absent' }}
      >
        <Form.Item name="new_employee_id" label="New Employee" rules={[{ required: true, message: 'Please select replacement employee' }]}>
          <Select
            showSearch
            options={filteredEmployees
              .filter((emp) => !assignedEmployeeIds.includes(emp.uid) || emp.uid === slot?.employee_id)
              .map((emp) => ({ value: emp.uid, label: `${emp.name} (${emp.designation})` }))}
          />
        </Form.Item>
        <Form.Item name="reason" label="Reason" rules={[{ required: true, message: 'Swap reason is required' }]}>
          <Select options={reasons.map((value) => ({ value, label: value }))} />
        </Form.Item>
        <Form.Item shouldUpdate noStyle>
          {({ getFieldValue }) => getFieldValue('reason') === 'Other' ? (
            <Form.Item name="custom_reason" label="Custom Reason" rules={[{ required: true, message: 'Please provide reason' }]}>
              <Input.TextArea rows={3} maxLength={240} />
            </Form.Item>
          ) : null}
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default EmployeeSwapModal;
