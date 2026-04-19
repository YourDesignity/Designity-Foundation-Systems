/**
 * DailyMusterPage.jsx
 *
 * Phase 6 — Renamed from DailyFulfillmentRecord.
 * Accessible via /projects/:projectId/contracts/:contractId/muster
 * and /projects/:projectId/contracts/:contractId/muster/:date
 *
 * Manager logs who filled each shift slot today.
 * Admin sees costs — manager does NOT.
 */

import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert, Breadcrumb, Button, Card, Col, DatePicker,
  Form, InputNumber, Row, Select, Space, Table, Tag,
  Typography, Result, Spin, message, Divider,
} from 'antd';
import { CheckCircleOutlined, SaveOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { useNavigate, useParams, Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useEmployees } from '../../hooks/useEmployees';
import { useRoleContract, useRecordDailyFulfillment } from '../../hooks/useRoleContracts';
import { fetchWithAuth } from '../../services/apiService';

const { Title, Text } = Typography;
const { Option } = Select;

const ATTENDANCE_OPTIONS = ['Present', 'Absent', 'Half-Day', 'Leave'];

const DailyMusterPage = () => {
  const { projectId, contractId, date: dateParam } = useParams();
  const navigate  = useNavigate();
  const { user, isAdmin, isSiteManager } = useAuth();

  const [selectedDate, setSelectedDate] = useState(
    dateParam ? dayjs(dateParam) : dayjs()
  );
  const [rows, setRows]         = useState([]);
  const [contract, setContract] = useState(null);
  const [project, setProject]   = useState(null);
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading]   = useState(false);

  const canAccess = isAdmin || isSiteManager;

  // Hooks
  const { data: employeeList = [] } = useEmployees();
  const { data: contractDetails, isLoading: loadingContract } = useRoleContract(contractId);
  const recordMutation = useRecordDailyFulfillment();

  // Fetch contract + project info
  useEffect(() => {
    if (!contractId) return;
    Promise.all([
      fetchWithAuth(`/api/contracts/${contractId}`).catch(() => null),
      projectId ? fetchWithAuth(`/projects/${projectId}`).catch(() => null) : Promise.resolve(null),
    ]).then(([cd, pd]) => {
      setContract(cd?.contract || cd);
      setProject(pd?.project || pd);
    });
  }, [contractId, projectId]);

  // Initialise rows from contract role slots
  useEffect(() => {
    if (!contractDetails) { setRows([]); return; }
    setRows((contractDetails.role_slots || []).map(slot => ({
      slot_id: slot.slot_id,
      designation: slot.designation,
      daily_rate: Number(slot.daily_rate || 0),
      employee_id: slot.current_employee_id || null,
      attendance_status: 'Present',
      is_filled: !!slot.current_employee_id,
      notes: '',
    })));
  }, [contractDetails]);

  // Employees matching designation for each slot
  const employeesByDesignation = useMemo(() => {
    const map = {};
    (employeeList || []).forEach(emp => {
      const d = emp.designation || '';
      if (!map[d]) map[d] = [];
      map[d].push(emp);
    });
    return map;
  }, [employeeList]);

  const updateRow = (slotId, field, value) => {
    setRows(prev => prev.map(r => {
      if (r.slot_id !== slotId) return r;
      const updated = { ...r, [field]: value };
      if (field === 'employee_id') {
        updated.is_filled = !!value;
        if (!value) updated.attendance_status = 'Absent';
      }
      if (field === 'attendance_status') {
        updated.is_filled = value === 'Present' || value === 'Half-Day';
      }
      return updated;
    }));
  };

  const handleSubmit = async () => {
    try {
      setLoading(true);
      const payload = {
        contract_id: Number(contractId),
        date: selectedDate.format('YYYY-MM-DD'),
        submitted_by_manager_id: user?.uid,
        is_submitted: true,
        slot_records: rows.map(r => ({
          slot_id: r.slot_id,
          designation: r.designation,
          employee_id: r.employee_id,
          is_filled: r.is_filled,
          attendance_status: r.attendance_status,
          notes: r.notes,
          // daily_rate intentionally NOT sent — admin calculates cost
        })),
      };
      await recordMutation.mutateAsync(payload);
      setSubmitted(true);
    } catch {
      message.error('Failed to submit muster. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (!canAccess) {
    return <Result status="403" title="Access Denied" subTitle="You don't have permission to record muster." />;
  }

  if (loadingContract) {
    return <div style={{ padding: 24, textAlign: 'center' }}><Spin /></div>;
  }

  if (submitted) {
    return (
      <div style={{ padding: 24 }}>
        <Result
          status="success"
          title="Muster Submitted!"
          subTitle={`Daily muster for ${selectedDate.format('DD MMM YYYY')} has been recorded.`}
          extra={[
            <Button key="back" onClick={() => navigate(`/projects/${projectId}/contracts/${contractId}`)}>
              Back to Contract
            </Button>,
            <Button key="new" type="primary" onClick={() => setSubmitted(false)}>
              Record Another Day
            </Button>,
          ]}
        />
      </div>
    );
  }

  const filledCount = rows.filter(r => r.is_filled).length;
  const totalCount  = rows.length;

  const columns = [
    {
      title: 'Slot', dataIndex: 'slot_id', key: 'slot_id', width: 110,
      render: id => <Text code style={{ fontSize: 12 }}>{id}</Text>,
    },
    {
      title: 'Designation', dataIndex: 'designation', key: 'designation', width: 150,
      render: d => <Tag color="blue">{d}</Tag>,
    },
    {
      title: 'Employee',
      key: 'employee',
      render: (_, row) => {
        const options = employeesByDesignation[row.designation] || [];
        return (
          <Select
            style={{ width: 200 }}
            placeholder="Select employee..."
            value={row.employee_id || undefined}
            onChange={val => updateRow(row.slot_id, 'employee_id', val)}
            allowClear
            showSearch
            optionFilterProp="children"
          >
            {options.map(emp => (
              <Option key={emp.uid} value={emp.uid}>{emp.name}</Option>
            ))}
          </Select>
        );
      },
    },
    {
      title: 'Attendance',
      key: 'attendance',
      width: 150,
      render: (_, row) => (
        <Select
          style={{ width: 130 }}
          value={row.attendance_status}
          onChange={val => updateRow(row.slot_id, 'attendance_status', val)}
        >
          {ATTENDANCE_OPTIONS.map(o => (
            <Option key={o} value={o}>{o}</Option>
          ))}
        </Select>
      ),
    },
    {
      title: 'Status', key: 'status', width: 100,
      render: (_, row) => row.is_filled
        ? <Tag color="green" icon={<CheckCircleOutlined />}>Filled</Tag>
        : <Tag color="red">Unfilled</Tag>,
    },
    {
      title: 'Notes', key: 'notes',
      render: (_, row) => (
        <input
          style={{ border: '1px solid #d9d9d9', borderRadius: 6, padding: '4px 8px', width: '100%', fontSize: 13 }}
          placeholder="Optional note..."
          value={row.notes}
          onChange={e => updateRow(row.slot_id, 'notes', e.target.value)}
        />
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      {/* Breadcrumb */}
      <Breadcrumb style={{ marginBottom: 16 }} items={[
        { title: <Link to="/projects">Projects</Link> },
        { title: <Link to={`/projects/${projectId}`}>{project?.project_name || `Project`}</Link> },
        { title: <Link to={`/projects/${projectId}/contracts/${contractId}`}>{contract?.contract_code || 'Contract'}</Link> },
        { title: 'Daily Muster' },
      ]} />

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} type="text"
            onClick={() => navigate(`/projects/${projectId}/contracts/${contractId}`)} />
          <Title level={3} style={{ margin: 0 }}>Daily Muster</Title>
          {contract && <Text type="secondary">{contract.contract_name || contract.contract_code}</Text>}
        </Space>
        <DatePicker
          value={selectedDate}
          onChange={d => d && setSelectedDate(d)}
          format="DD MMM YYYY"
          disabledDate={d => d && d.isAfter(dayjs())}
        />
      </div>

      {/* Summary bar */}
      <Row gutter={16} style={{ marginBottom: 20 }}>
        <Col xs={12} sm={6}>
          <Card size="small" variant="borderless" style={{ background: '#f0f5ff' }}>
            <Text strong>{totalCount}</Text> <Text type="secondary">Total Slots</Text>
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small" variant="borderless" style={{ background: filledCount === totalCount ? '#f6ffed' : '#fff7e6' }}>
            <Text strong>{filledCount}</Text> <Text type="secondary">Filled</Text>
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small" variant="borderless" style={{ background: totalCount - filledCount > 0 ? '#fff1f0' : '#f5f5f5' }}>
            <Text strong>{totalCount - filledCount}</Text> <Text type="secondary">Unfilled</Text>
          </Card>
        </Col>
      </Row>

      {/* Admin info note */}
      {isAdmin && (
        <Alert
          style={{ marginBottom: 16 }}
          title="Admin View"
          description="Cost calculation is triggered separately after reviewing submissions. Managers cannot see rates or costs."
          type="info"
          showIcon
          closable
        />
      )}

      {/* Muster Table */}
      <Card variant="borderless" styles={{ body: { padding: 0 } }}>
        <Table
          columns={columns}
          dataSource={rows}
          rowKey="slot_id"
          pagination={false}
          size="middle"
          locale={{ emptyText: 'No role slots defined for this contract.' }}
        />
      </Card>

      {/* Submit */}
      {rows.length > 0 && (
        <div style={{ textAlign: 'right', marginTop: 20 }}>
          <Space>
            <Text type="secondary">{filledCount} / {totalCount} slots filled</Text>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              onClick={handleSubmit}
              loading={loading}
              size="large"
            >
              Submit Muster for {selectedDate.format('DD MMM YYYY')}
            </Button>
          </Space>
        </div>
      )}
    </div>
  );
};

export default DailyMusterPage;
