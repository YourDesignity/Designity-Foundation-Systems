import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Breadcrumb,
  Button,
  Card,
  Col,
  DatePicker,
  Form,
  Input,
  InputNumber,
  Row,
  Select,
  Space,
  Steps,
  Switch,
  Table,
  Tag,
  Typography,
  message,
  Result,
} from 'antd';
import dayjs from 'dayjs';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { getEmployees } from '../../services/apiService';
import { getContractRoleConfiguration, getRoleContractsList, recordDailyFulfillment } from '../../services/roleContractsService';

const { Title, Text } = Typography;
const attendanceOptions = ['Present', 'Absent', 'Half-Day', 'Leave'];

const calcCost = (slot, row) => {
  if (!row.is_filled) return 0;
  if (row.attendance_status === 'Half-Day') return Number(slot.daily_rate || 0) / 2;
  if (row.attendance_status === 'Present') return Number(slot.daily_rate || 0);
  return 0;
};

const DailyFulfillmentRecord = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [contracts, setContracts] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [selectedContractId, setSelectedContractId] = useState(Number(searchParams.get('contract')) || undefined);
  const [selectedDate, setSelectedDate] = useState(dayjs());
  const [contractDetails, setContractDetails] = useState(null);
  const [rows, setRows] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [loading, setLoading] = useState(false);

  const canAccess = ['Site Manager', 'Admin', 'SuperAdmin'].includes(user?.role);

  const loadBase = useCallback(async () => {
    setLoading(true);
    try {
      const [contractList, employeeList] = await Promise.all([getRoleContractsList(), getEmployees()]);
      setContracts(contractList || []);
      setEmployees(employeeList || []);
    } catch (error) {
      message.error(`Failed to load setup data: ${error.message}`);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (canAccess) loadBase();
  }, [canAccess, loadBase]);

  useEffect(() => {
    const fetchContractDetails = async () => {
      if (!selectedContractId) return;
      try {
        const details = await getContractRoleConfiguration(selectedContractId);
        setContractDetails(details);
        setRows((details.role_slots || []).map((slot) => ({
          slot_id: slot.slot_id,
          designation: slot.designation,
          daily_rate: Number(slot.daily_rate || 0),
          employee_id: null,
          attendance_status: 'Present',
          is_filled: false,
          notes: '',
        })));
      } catch (error) {
        setContractDetails(null);
        setRows([]);
        message.error(`Failed to load role slots: ${error.message}`);
      }
    };

    fetchContractDetails();
  }, [selectedContractId]);

  const contractOptions = useMemo(() => contracts.map((contract) => ({ value: contract.contract_id, label: `${contract.contract_code} (${contract.total_role_slots || 0} slots)` })), [contracts]);

  const duplicateEmployeeIds = useMemo(() => {
    const ids = rows.filter((row) => row.is_filled && row.employee_id).map((row) => row.employee_id);
    return ids.filter((id, index) => ids.indexOf(id) !== index);
  }, [rows]);

  const validationErrors = useMemo(() => {
    const errors = [];
    if (selectedDate.isAfter(dayjs(), 'day')) {
      errors.push('Date cannot be in the future.');
    }
    rows.forEach((row) => {
      const emp = employees.find((employee) => employee.uid === row.employee_id);
      if (row.is_filled && !row.employee_id) {
        errors.push(`Employee is required for slot ${row.slot_id}.`);
      }
      if (row.employee_id && emp && emp.designation !== row.designation) {
        errors.push(`Designation mismatch for slot ${row.slot_id}.`);
      }
    });
    if (duplicateEmployeeIds.length) {
      errors.push('Double-booking detected: same employee assigned to multiple slots.');
    }
    return errors;
  }, [duplicateEmployeeIds.length, employees, rows, selectedDate]);

  const summary = useMemo(() => {
    const total = rows.length;
    const filled = rows.filter((row) => row.is_filled && row.employee_id).length;
    const totalCost = rows.reduce((sum, row) => sum + calcCost(row, row), 0);
    return {
      total,
      filled,
      unfilled: Math.max(total - filled, 0),
      totalCost,
    };
  }, [rows]);

  const handleRowChange = (slotId, patch) => {
    setRows((prev) => prev.map((row) => row.slot_id === slotId ? { ...row, ...patch } : row));
  };

  const submit = async () => {
    if (!selectedContractId || !contractDetails) {
      message.warning('Please select a contract first.');
      return;
    }
    if (validationErrors.length) {
      message.error('Please fix validation issues before submission.');
      return;
    }

    const payload = {
      contract_id: selectedContractId,
      site_id: Number((contracts.find((c) => c.contract_id === selectedContractId)?.site_ids || [])[0] || 1),
      date: selectedDate.format('YYYY-MM-DD'),
      recorded_by_manager_id: Number(user?.uid || user?.id || 1),
      role_fulfillments: rows.map((row) => {
        const employee = employees.find((emp) => emp.uid === row.employee_id);
        const apiAttendance = row.attendance_status === 'Half-Day' ? 'Late' : row.attendance_status;
        return {
          slot_id: row.slot_id,
          designation: row.designation,
          daily_rate: row.daily_rate,
          employee_id: row.employee_id || null,
          employee_name: employee?.name || null,
          is_filled: Boolean(row.is_filled && row.employee_id),
          attendance_status: apiAttendance,
          cost_applied: calcCost(row, row),
          payment_status: 'Pending',
          notes: row.notes || null,
        };
      }),
    };

    setSubmitting(true);
    try {
      const response = await recordDailyFulfillment(payload);
      message.success(`Fulfillment recorded (UID: ${response.uid || response.fulfillment_uid || 'created'})`);
    } catch (error) {
      message.error(`Submission failed: ${error.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  const columns = [
    { title: 'Slot ID', dataIndex: 'slot_id', key: 'slot_id' },
    { title: 'Designation', dataIndex: 'designation', key: 'designation' },
    { title: 'Daily Rate', dataIndex: 'daily_rate', key: 'daily_rate', render: (value) => `KD ${Number(value).toFixed(2)}` },
    {
      title: 'Employee',
      key: 'employee_id',
      render: (_, row) => (
        <Select
          allowClear
          style={{ width: 220 }}
          value={row.employee_id}
          onChange={(value) => handleRowChange(row.slot_id, { employee_id: value })}
          options={employees
            .filter((employee) => employee.designation === row.designation)
            .map((employee) => ({ value: employee.uid, label: employee.name }))}
        />
      ),
    },
    {
      title: 'Attendance',
      key: 'attendance_status',
      render: (_, row) => (
        <Select
          style={{ width: 140 }}
          value={row.attendance_status}
          onChange={(value) => handleRowChange(row.slot_id, { attendance_status: value })}
          options={attendanceOptions.map((item) => ({ value: item, label: item }))}
        />
      ),
    },
    {
      title: 'Filled',
      key: 'is_filled',
      render: (_, row) => (
        <Switch
          checked={row.is_filled}
          onChange={(value) => handleRowChange(row.slot_id, { is_filled: value })}
        />
      ),
    },
    {
      title: 'Notes',
      key: 'notes',
      render: (_, row) => (
        <Input
          placeholder="Optional"
          value={row.notes}
          onChange={(event) => handleRowChange(row.slot_id, { notes: event.target.value })}
        />
      ),
    },
    {
      title: 'Cost Preview',
      key: 'cost_preview',
      render: (_, row) => `KD ${calcCost(row, row).toFixed(2)}`,
    },
  ];

  if (!canAccess) {
    return <Result status="403" title="Access Denied" subTitle="You do not have permission to record daily fulfillment." />;
  }

  return (
    <Space orientation="vertical" size={16} style={{ width: '100%' }}>
      <Breadcrumb items={[{ title: 'Home' }, { title: 'Role Contracts' }, { title: 'Record Daily' }]} />
      <Title level={3} style={{ marginBottom: 0 }}>Daily Fulfillment Recording</Title>

      <Steps
        current={contractDetails ? 2 : selectedContractId ? 1 : 0}
        items={[
          { title: 'Select Contract & Date' },
          { title: 'Fill Role Slots' },
          { title: 'Validation & Preview' },
          { title: 'Submit' },
        ]}
      />

      <Card loading={loading}>
        <Form layout="vertical">
          <Row gutter={12}>
            <Col xs={24} md={10}>
              <Form.Item label="Contract" required>
                <Select
                  showSearch
                  value={selectedContractId}
                  onChange={setSelectedContractId}
                  options={contractOptions}
                  placeholder="Select labour contract"
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item label="Date" required>
                <DatePicker
                  style={{ width: '100%' }}
                  value={selectedDate}
                  onChange={(date) => setSelectedDate(date || dayjs())}
                  disabledDate={(current) => current && current > dayjs().endOf('day')}
                />
              </Form.Item>
            </Col>
          </Row>
        </Form>

        {contractDetails && (
          <Alert
            type="info"
            showIcon
            message={`${contractDetails.contract_code} • ${contractDetails.total_role_slots} slots • KD ${Number(contractDetails.total_daily_cost || 0).toFixed(2)} daily`}
            style={{ marginBottom: 12 }}
          />
        )}

        <Table rowKey="slot_id" dataSource={rows} columns={columns} pagination={false} scroll={{ x: 1000 }} />
      </Card>

      <Card title="Validation & Preview">
        {validationErrors.length ? (
          <Space orientation="vertical" style={{ width: '100%' }}>
            {validationErrors.map((error) => <Tag color="red" key={error}>{error}</Tag>)}
          </Space>
        ) : (
          <Alert type="success" title="All validations passed." />
        )}
        <Row gutter={[12, 12]} style={{ marginTop: 12 }}>
          <Col xs={12} md={6}><Text>Total Slots: {summary.total}</Text></Col>
          <Col xs={12} md={6}><Text>Filled Slots: {summary.filled}</Text></Col>
          <Col xs={12} md={6}><Text>Unfilled Slots: {summary.unfilled}</Text></Col>
          <Col xs={12} md={6}><Text strong>Total Daily Cost: KD {summary.totalCost.toFixed(2)}</Text></Col>
        </Row>
      </Card>

      <Space>
        <Button type="primary" loading={submitting} onClick={submit}>Submit Fulfillment</Button>
        <Button onClick={() => window.location.reload()}>Record Another Day</Button>
        <Button onClick={() => navigate('/role-contracts/monthly-report')}>View Report</Button>
      </Space>
    </Space>
  );
};

export default DailyFulfillmentRecord;
