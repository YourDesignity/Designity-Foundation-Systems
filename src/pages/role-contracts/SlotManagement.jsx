import React, { useMemo, useState } from 'react';
import {
  Alert,
  Breadcrumb,
  Button,
  Card,
  Col,
  DatePicker,
  Descriptions,
  Empty,
  Row,
  Select,
  Space,
  Tag,
  Typography,
  message,
  Result,
} from 'antd';
import dayjs from 'dayjs';
import { useAuth } from '../../context/AuthContext';
import { useEmployees } from '../../hooks/useEmployees';
import { useRoleContracts, useAssignEmployeeToSlot, useSwapEmployeeInSlot } from '../../hooks/useRoleContracts';
import { dailyFulfillmentService } from '../../services';
import SlotAssignmentModal from '../../components/role-contracts/SlotAssignmentModal';
import EmployeeSwapModal from '../../components/role-contracts/EmployeeSwapModal';

const { Title, Text } = Typography;

const SlotManagement = () => {
  const { user } = useAuth();
  const canAccess = ['Site Manager', 'Admin', 'SuperAdmin'].includes(user?.role);

  const [contractId, setContractId] = useState();
  const [date, setDate] = useState(dayjs());
  const [record, setRecord] = useState(null);
  const [loading, setLoading] = useState(false);

  const [assignSlot, setAssignSlot] = useState(null);
  const [swapSlot, setSwapSlot] = useState(null);

  // React Query hooks
  const { data: contracts = [] } = useRoleContracts();
  const { data: employees = [] } = useEmployees();
  const assignMutation = useAssignEmployeeToSlot();
  const swapMutation = useSwapEmployeeInSlot();

  React.useEffect(() => {
    if (!canAccess || contracts.length === 0) return;
    if (!contractId) setContractId(contracts[0]?.contract_id);
  }, [canAccess, contracts, contractId]);

  const loadRecord = async () => {
    if (!contractId) return message.warning('Select a contract first.');
    setLoading(true);
    try {
      const response = await dailyFulfillmentService.getDailyFulfillmentRecord(contractId, date.format('YYYY-MM-DD'));
      setRecord(response);
    } catch (error) {
      setRecord(null);
      message.error(`Failed to load fulfillment record: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const assignedEmployeeIds = useMemo(() => {
    return (record?.role_fulfillments || [])
      .filter((slot) => slot.is_filled && slot.employee_id)
      .map((slot) => slot.employee_id);
  }, [record]);

  const refreshRecord = async () => {
    if (!record?.contract_id) return;
    try {
      const updated = await dailyFulfillmentService.getDailyFulfillmentRecord(record.contract_id, dayjs(record.date).format('YYYY-MM-DD'));
      setRecord(updated);
    } catch (error) {
      message.error(`Refresh failed: ${error.message}`);
    }
  };

  const handleAssign = async (values) => {
    if (!record?.uid || !assignSlot) return;
    const employee = employees.find((emp) => emp.uid === values.employee_id);
    if (!employee || employee.designation !== assignSlot.designation) {
      return message.error('Selected employee designation does not match slot designation.');
    }

    assignMutation.mutate(
      {
        fulfillmentId: record.uid,
        payload: {
          slot_id: assignSlot.slot_id,
          employee_id: employee.uid,
          employee_name: employee.name,
          attendance_status: values.attendance_status,
          notes: values.notes || null,
        },
      },
      {
        onSuccess: () => {
          setAssignSlot(null);
          refreshRecord();
        },
      }
    );
  };

  const handleSwap = async (values) => {
    if (!record?.uid || !swapSlot) return;
    const employee = employees.find((emp) => emp.uid === values.new_employee_id);
    if (!employee || employee.designation !== swapSlot.designation) {
      return message.error('Selected replacement designation does not match slot.');
    }

    swapMutation.mutate(
      {
        fulfillmentId: record.uid,
        payload: {
          slot_id: swapSlot.slot_id,
          new_employee_id: employee.uid,
          new_employee_name: employee.name,
          reason: values.reason === 'Other' ? values.custom_reason : values.reason,
        },
      },
      {
        onSuccess: () => {
          setSwapSlot(null);
          refreshRecord();
        },
      }
    );
  };

  if (!canAccess) {
    return <Result status="403" title="Access Denied" subTitle="You do not have permission to manage role slots." />;
  }

  return (
    <Space orientation="vertical" size={16} style={{ width: '100%' }}>
      <Breadcrumb items={[{ title: 'Home' }, { title: 'Role Contracts' }, { title: 'Manage Slots' }]} />
      <Title level={3} style={{ marginBottom: 0 }}>Slot Assignment / Swap</Title>

      <Card>
        <Row gutter={[12, 12]}>
          <Col xs={24} md={8}>
            <Select
              style={{ width: '100%' }}
              value={contractId}
              onChange={setContractId}
              options={contracts.map((item) => ({ value: item.contract_id, label: item.contract_code }))}
              placeholder="Select Contract"
            />
          </Col>
          <Col xs={24} md={6}>
            <DatePicker style={{ width: '100%' }} value={date} onChange={(value) => setDate(value || dayjs())} />
          </Col>
          <Col xs={24} md={4}>
            <Button type="primary" loading={loading} onClick={loadRecord} block>Load Record</Button>
          </Col>
        </Row>
      </Card>

      {record && (
        <Card>
          <Descriptions size="small" column={{ xs: 1, md: 3 }}>
            <Descriptions.Item label="Fulfillment UID">{record.uid}</Descriptions.Item>
            <Descriptions.Item label="Date">{dayjs(record.date).format('YYYY-MM-DD')}</Descriptions.Item>
            <Descriptions.Item label="Filled / Required">{record.total_roles_filled} / {record.total_roles_required}</Descriptions.Item>
            <Descriptions.Item label="Total Cost">KD {Number(record.total_daily_cost || 0).toFixed(2)}</Descriptions.Item>
            <Descriptions.Item label="Unfilled Slots"><Tag color={record.unfilled_slots?.length ? 'red' : 'green'}>{record.unfilled_slots?.length || 0}</Tag></Descriptions.Item>
          </Descriptions>
        </Card>
      )}

      {!record ? (
        <Empty description="Load a fulfillment record to manage slots" />
      ) : (
        <Row gutter={[12, 12]}>
          {(record.role_fulfillments || []).map((slot, index) => (
            <Col xs={24} md={12} lg={8} key={slot.slot_id || `slot-${index}`}>
              <Card
                title={`${slot.slot_id} (${slot.designation})`}
                extra={<Tag color={slot.is_filled ? '#10B981' : '#EF4444'}>{slot.is_filled ? 'Filled' : 'Unfilled'}</Tag>}
              >
                <Space orientation="vertical" style={{ width: '100%' }}>
                  <Text>Rate: KD {Number(slot.daily_rate || 0).toFixed(2)}</Text>
                  <Text>Employee: {slot.employee_name || '—'}</Text>
                  <Text>Attendance: {slot.attendance_status || '—'}</Text>
                  <Text>Cost Applied: KD {Number(slot.cost_applied || 0).toFixed(2)}</Text>
                  {slot.replacement_employee_name && (
                    <Alert
                      type="info"
                      message={`Replaced from ${slot.replacement_employee_name}`}
                      description={slot.replacement_reason || 'No reason provided'}
                    />
                  )}
                  {slot.is_filled ? (
                    <Button onClick={() => setSwapSlot(slot)}>Swap Employee</Button>
                  ) : (
                    <Button type="primary" onClick={() => setAssignSlot(slot)}>Assign Employee</Button>
                  )}
                </Space>
              </Card>
            </Col>
          ))}
        </Row>
      )}

      <SlotAssignmentModal
        open={Boolean(assignSlot)}
        slot={assignSlot}
        employees={employees}
        loading={assignMutation.isPending}
        assignedEmployeeIds={assignedEmployeeIds}
        onCancel={() => setAssignSlot(null)}
        onSubmit={handleAssign}
      />

      <EmployeeSwapModal
        open={Boolean(swapSlot)}
        slot={swapSlot}
        employees={employees}
        loading={swapMutation.isPending}
        assignedEmployeeIds={assignedEmployeeIds}
        onCancel={() => setSwapSlot(null)}
        onSubmit={handleSwap}
      />
    </Space>
  );
};

export default SlotManagement;
