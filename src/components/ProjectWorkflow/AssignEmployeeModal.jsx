import React, { useState, useEffect } from 'react';
import { Modal, Select, DatePicker, message, Spin, Space, Badge, Typography } from 'antd';
import { TeamOutlined } from '@ant-design/icons';
import { fetchWithAuth } from '../../services/apiService';
import dayjs from 'dayjs';

const { RangePicker } = DatePicker;
const { Text } = Typography;

/**
 * AssignEmployeeModal – assign one or more company employees to a site.
 *
 * Props:
 *   visible        {boolean}
 *   site           {object}  – site record (must have uid, name, required_workers, assigned_workers)
 *   onCancel       {function}
 *   onSuccess      {function}
 */
const AssignEmployeeModal = ({ visible, site, onCancel, onSuccess }) => {
  const [loading, setLoading] = useState(false);
  const [fetchingEmployees, setFetchingEmployees] = useState(false);
  const [availableEmployees, setAvailableEmployees] = useState([]);
  const [selectedEmployeeIds, setSelectedEmployeeIds] = useState([]);
  const [dateRange, setDateRange] = useState([dayjs(), null]);

  useEffect(() => {
    if (visible) {
      fetchAvailableEmployees();
      setSelectedEmployeeIds([]);
      setDateRange([dayjs(), null]);
    }
  }, [visible]);

  const fetchAvailableEmployees = async () => {
    setFetchingEmployees(true);
    try {
      const data = await fetchWithAuth('/assignments/available/employees');
      setAvailableEmployees(data.employees || []);
    } catch (error) {
      console.error('Error fetching available employees:', error);
      message.error('Could not load available employees');
    } finally {
      setFetchingEmployees(false);
    }
  };

  const handleAssign = async () => {
    if (selectedEmployeeIds.length === 0) {
      message.warning('Please select at least one employee');
      return;
    }
    if (!dateRange[0]) {
      message.warning('Please select an assignment start date');
      return;
    }

    setLoading(true);
    try {
      const payload = {
        employee_ids: selectedEmployeeIds,
        assignment_start: dateRange[0].format('YYYY-MM-DD'),
        assignment_end: dateRange[1] ? dateRange[1].format('YYYY-MM-DD') : null,
      };

      const data = await fetchWithAuth(`/workflow/sites/${site.uid}/assign-employees`, {
        method: 'POST',
        body: JSON.stringify(payload),
      });

      const msg = data.message || `${data.created_count} employee(s) assigned successfully`;
      if (data.failed_count > 0) {
        message.warning(`${msg}. ${data.failed_count} failed.`);
      } else {
        message.success(msg);
      }
      onSuccess(data);
    } catch (error) {
      console.error('Error assigning employees:', error);
      message.error(error.message || 'Error assigning employees');
    } finally {
      setLoading(false);
    }
  };

  const availableSlots = site
    ? Math.max(0, site.required_workers - (site.assigned_workers || 0))
    : 0;

  return (
    <Modal
      title={
        <span>
          <TeamOutlined style={{ marginRight: 8 }} />
          Assign Employees – {site?.site_code || site?.name || ''}
        </span>
      }
      open={visible}
      onOk={handleAssign}
      onCancel={onCancel}
      okText={`Assign ${selectedEmployeeIds.length > 0 ? `(${selectedEmployeeIds.length})` : ''}`}
      confirmLoading={loading}
      okButtonProps={{ disabled: selectedEmployeeIds.length === 0 }}
      width={600}
    >
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        <div>
          <Text type="secondary">Site: </Text>
          <Text strong>{site?.name}</Text>
          {'  '}
          <Text type="secondary">Required: </Text>
          <Text strong>{site?.required_workers}</Text>
          {'  '}
          <Text type="secondary">Available slots: </Text>
          <Text strong style={{ color: availableSlots > 0 ? '#52c41a' : '#ff4d4f' }}>
            {availableSlots}
          </Text>
        </div>

        <div>
          <p style={{ marginBottom: 8 }}>
            <strong>Assignment Period:</strong>
          </p>
          <RangePicker
            style={{ width: '100%' }}
            value={dateRange}
            onChange={setDateRange}
            placeholder={['Start Date', 'End Date (Optional)']}
            allowEmpty={[false, true]}
          />
        </div>

        <div>
          <p style={{ marginBottom: 8 }}>
            <strong>Select Company Employees:</strong>
            <Badge
              count={selectedEmployeeIds.length}
              style={{ marginLeft: 8, backgroundColor: '#1890ff' }}
            />
          </p>
          {fetchingEmployees ? (
            <Spin />
          ) : (
            <Select
              mode="multiple"
              style={{ width: '100%' }}
              placeholder="Select employees to assign to this site"
              value={selectedEmployeeIds}
              onChange={setSelectedEmployeeIds}
              showSearch
              optionFilterProp="label"
              options={availableEmployees.map((emp) => ({
                value: emp.uid,
                label: `${emp.name} – ${emp.designation || 'N/A'}`,
              }))}
            />
          )}
          <p style={{ marginTop: 6, color: '#888', fontSize: 12 }}>
            {availableEmployees.length} employee(s) available for assignment
          </p>
        </div>
      </Space>
    </Modal>
  );
};

export default AssignEmployeeModal;
