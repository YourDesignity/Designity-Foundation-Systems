// src/pages/ManagerSiteAttendancePage.jsx
// Manager's attendance interface for their assigned sites with multi-site support.

import React, { useState, useEffect, useCallback } from 'react';
import {
  Card, Row, Col, Table, DatePicker, Button, Tag, Typography,
  Modal, Form, Select, Input, message, Space, Tooltip, Spin, Alert,
} from 'antd';
import {
  ReloadOutlined, CalendarOutlined, CheckCircleOutlined,
  CloseCircleOutlined, ClockCircleOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { useAuth } from '../context/AuthContext';
import { managerSiteService } from '../services';
import SiteSwitcher from '../components/manager/SiteSwitcher';
import SiteInfoCard from '../components/manager/SiteInfoCard';

const { Title, Text } = Typography;
const { Option } = Select;
const { TextArea } = Input;

const ATTENDANCE_STATUSES = ['Present', 'Absent', 'Late', 'Half Day', 'On Leave'];

const STATUS_COLORS = {
  present:  'green',
  absent:   'red',
  late:     'orange',
  'half day': 'gold',
  'on leave': 'blue',
};

function StatusTag({ status }) {
  if (!status) return <Tag color="default">—</Tag>;
  const key = status.toLowerCase();
  return <Tag color={STATUS_COLORS[key] ?? 'default'}>{status}</Tag>;
}

function ManagerSiteAttendancePage() {
  const { user } = useAuth();
  const managerId = user?.id;

  const [sites, setSites] = useState([]);
  const [selectedSiteId, setSelectedSiteId] = useState(null);
  const [selectedSite, setSelectedSite] = useState(null);
  const [employees, setEmployees] = useState([]);
  const [attendanceMap, setAttendanceMap] = useState({});
  const [selectedDate, setSelectedDate] = useState(dayjs());

  const [loadingSites, setLoadingSites] = useState(false);
  const [loadingEmployees, setLoadingEmployees] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [sitesError, setSitesError] = useState(null);

  // Edit attendance modal
  const [editTarget, setEditTarget] = useState(null);
  const [editForm] = Form.useForm();

  // ── Load manager's sites ───────────────────────────────────────────────────
  useEffect(() => {
    if (!managerId) return;
    const fetchSites = async () => {
      setLoadingSites(true);
      setSitesError(null);
      try {
        const data = await managerSiteService.getManagerSites(managerId);
        const siteList = data?.sites ?? [];
        setSites(siteList);
        if (siteList.length > 0 && !selectedSiteId) {
          setSelectedSiteId(siteList[0].uid);
          setSelectedSite(siteList[0]);
        }
      } catch (err) {
        setSitesError(err?.message ?? 'Failed to load sites');
      } finally {
        setLoadingSites(false);
      }
    };
    fetchSites();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [managerId]);

  // ── Load employees when site or date changes ───────────────────────────────
  const fetchEmployees = useCallback(
    async (siteId, date) => {
      if (!managerId || !siteId) return;
      setLoadingEmployees(true);
      try {
        const empData = await managerSiteService.getSiteEmployees(managerId, siteId);
        const allEmps = [
          ...(empData?.company_employees ?? []),
          ...(empData?.substitutes ?? []).map((s) => ({ employee: s, assignment: null })),
        ];
        setEmployees(allEmps);

        // Fetch existing attendance for the date
        const dateStr = (date ?? selectedDate).format('YYYY-MM-DD');
        const attData = await managerSiteService.getAttendance(managerId, siteId, dateStr);
        const map = {};
        (attData?.records ?? []).forEach((r) => {
          map[r.employee_uid] = r;
        });
        setAttendanceMap(map);
      } catch (err) {
        message.error('Failed to load employees: ' + (err?.message ?? 'Unknown error'));
      } finally {
        setLoadingEmployees(false);
      }
    },
    [managerId, selectedDate],
  );

  useEffect(() => {
    if (selectedSiteId) {
      fetchEmployees(selectedSiteId, selectedDate);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedSiteId, selectedDate]);

  // ── Site switcher handler ──────────────────────────────────────────────────
  const handleSiteChange = (siteId) => {
    setSelectedSiteId(siteId);
    const site = sites.find((s) => s.uid === siteId);
    setSelectedSite(site ?? null);
    setAttendanceMap({});
  };

  // ── Date change handler ────────────────────────────────────────────────────
  const handleDateChange = (date) => {
    setSelectedDate(date);
  };

  // ── Open edit modal ────────────────────────────────────────────────────────
  const openEdit = (record) => {
    const existing = attendanceMap[record.employee.uid];
    setEditTarget(record);
    editForm.setFieldsValue({
      status: existing?.status ?? 'Present',
      shift: existing?.shift ?? 'Morning',
      overtime_hours: existing?.overtime_hours ?? 0,
      notes: existing?.notes ?? '',
    });
  };

  // ── Submit single attendance record ───────────────────────────────────────
  const handleEditSave = async () => {
    try {
      const values = await editForm.validateFields();
      setSubmitting(true);
      const payload = {
        site_id: selectedSiteId,
        date: selectedDate.format('YYYY-MM-DD'),
        records: [
          {
            employee_uid: editTarget.employee.uid,
            status: values.status,
            shift: values.shift ?? 'Morning',
            overtime_hours: values.overtime_hours ?? 0,
            notes: values.notes ?? '',
          },
        ],
      };
      await managerSiteService.recordAttendance(managerId, selectedSiteId, payload);
      message.success('Attendance saved');
      setEditTarget(null);
      fetchEmployees(selectedSiteId, selectedDate);
    } catch (err) {
      if (err?.errorFields) return;
      message.error('Failed to save: ' + (err?.message ?? 'Unknown error'));
    } finally {
      setSubmitting(false);
    }
  };

  // ── Mark all present ───────────────────────────────────────────────────────
  const handleMarkAllPresent = async () => {
    if (!employees.length) return;
    setSubmitting(true);
    try {
      const records = employees.map(({ employee }) => ({
        employee_uid: employee.uid,
        status: 'Present',
        shift: 'Morning',
        overtime_hours: 0,
      }));
      const payload = {
        site_id: selectedSiteId,
        date: selectedDate.format('YYYY-MM-DD'),
        records,
      };
      await managerSiteService.recordAttendance(managerId, selectedSiteId, payload);
      message.success(`Marked ${records.length} employees as Present`);
      fetchEmployees(selectedSiteId, selectedDate);
    } catch (err) {
      message.error('Failed to mark attendance: ' + (err?.message ?? 'Unknown error'));
    } finally {
      setSubmitting(false);
    }
  };

  // ── Table columns ──────────────────────────────────────────────────────────
  const columns = [
    {
      title: 'Employee',
      dataIndex: ['employee', 'name'],
      key: 'name',
      render: (name, record) => (
        <Space orientation="vertical" size={0}>
          <Text strong>{name}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.employee?.designation}
          </Text>
        </Space>
      ),
    },
    {
      title: 'Site',
      key: 'site',
      render: (_, record) => {
        const siteCode = record.assignment?.site_name ?? selectedSite?.name;
        return siteCode ? <Tag>{siteCode}</Tag> : <Text type="secondary">—</Text>;
      },
    },
    {
      title: 'Manager',
      key: 'manager',
      render: (_, record) => (
        <Text>{record.assignment?.manager_name ?? selectedSite?.assigned_manager_name ?? '—'}</Text>
      ),
    },
    {
      title: 'Status',
      key: 'status',
      render: (_, record) => {
        const att = attendanceMap[record.employee.uid];
        return att ? <StatusTag status={att.status} /> : <Tag color="default">Not Recorded</Tag>;
      },
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Button size="small" onClick={() => openEdit(record)}>
          {attendanceMap[record.employee.uid] ? 'Edit' : 'Record'}
        </Button>
      ),
    },
  ];

  // ── Render ─────────────────────────────────────────────────────────────────
  if (!managerId) {
    return <Alert type="warning" title="Manager identity not found. Please log in again." />;
  }

  return (
    <div className="layout-content">
      {/* Header */}
      <Card variant="borderless" className="criclebox mb-24" style={{ marginBottom: 24 }}>
        <Row align="middle" justify="space-between" wrap={false}>
          <Col>
            <Title level={4} style={{ margin: 0 }}>
              <CalendarOutlined style={{ marginRight: 8 }} />
              Site Attendance
            </Title>
            <Text type="secondary">Record and review attendance for your assigned sites</Text>
          </Col>
          <Col>
            <Space>
              <DatePicker
                value={selectedDate}
                onChange={handleDateChange}
                allowClear={false}
                format="DD/MM/YYYY"
              />
              <Tooltip title="Refresh">
                <Button
                  icon={<ReloadOutlined />}
                  onClick={() => fetchEmployees(selectedSiteId, selectedDate)}
                  loading={loadingEmployees}
                />
              </Tooltip>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Error loading sites */}
      {sitesError && (
        <Alert type="error" title={sitesError} style={{ marginBottom: 16 }} />
      )}

      {/* Loading sites spinner */}
      {loadingSites && (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin tip="Loading your sites…" />
        </div>
      )}

      {!loadingSites && (
        <>
          {/* Site Switcher — only visible when manager has multiple sites */}
          {sites.length > 1 && (
            <SiteSwitcher
              selectedSiteId={selectedSiteId}
              sites={sites}
              onSiteChange={handleSiteChange}
            />
          )}

          {/* Site Info Card */}
          {selectedSite && <SiteInfoCard site={selectedSite} />}

          {/* No sites message */}
          {sites.length === 0 && (
            <Alert
              type="info"
              title="No sites assigned"
              description="You have no sites assigned to you. Please contact your administrator."
              style={{ marginBottom: 16 }}
            />
          )}

          {/* Employee Attendance Table */}
          {selectedSiteId && (
            <Card
              variant="borderless"
              className="criclebox tablespace mb-24"
              extra={
                <Space>
                  <Button
                    type="primary"
                    icon={<CheckCircleOutlined />}
                    loading={submitting}
                    onClick={handleMarkAllPresent}
                    disabled={!employees.length}
                  >
                    Mark All Present
                  </Button>
                </Space>
              }
            >
              <div className="table-responsive">
                <Table
                  columns={columns}
                  dataSource={employees}
                  rowKey={(r, idx) => r.employee?.uid ?? `row-${idx}`}
                  loading={loadingEmployees}
                  pagination={{ pageSize: 20 }}
                  className="ant-border-space"
                  scroll={{ x: 800 }}
                />
              </div>
            </Card>
          )}
        </>
      )}

      {/* Edit Attendance Modal */}
      <Modal
        title="Record Attendance"
        open={!!editTarget}
        onOk={handleEditSave}
        onCancel={() => setEditTarget(null)}
        confirmLoading={submitting}
        okText="Save"
        width={440}
      >
        {editTarget && (
          <div style={{ marginBottom: 16 }}>
            <Text type="secondary">Employee: </Text>
            <Text strong>{editTarget.employee?.name}</Text>
          </div>
        )}
        <Form form={editForm} layout="vertical">
          <Form.Item
            name="status"
            label="Attendance Status"
            rules={[{ required: true, message: 'Please select a status' }]}
          >
            <Select placeholder="Select status">
              {ATTENDANCE_STATUSES.map((s) => (
                <Option key={s} value={s}>{s}</Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="shift" label="Shift">
            <Select>
              <Option value="Morning">Morning</Option>
              <Option value="Afternoon">Afternoon</Option>
              <Option value="Evening">Evening</Option>
              <Option value="Night">Night</Option>
            </Select>
          </Form.Item>
          <Form.Item name="overtime_hours" label="Overtime Hours">
            <Input type="number" min={0} step={0.5} />
          </Form.Item>
          <Form.Item name="notes" label="Notes">
            <TextArea rows={2} placeholder="Optional notes" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

export default ManagerSiteAttendancePage;
