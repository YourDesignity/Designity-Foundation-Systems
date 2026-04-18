import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Card, Row, Col, Table, DatePicker, Button, Tag, Typography, Modal,
  Form, Select, TimePicker, Input, message, Space, Tooltip,
} from 'antd';
import {
  ReloadOutlined, CalendarOutlined, EditOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { getManagerAttendanceAll, overrideManagerAttendance } from '../services/apiService';

const { Title, Text } = Typography;
const { Option } = Select;
const { TextArea } = Input;

const STATUS_COLORS = {
  'on_time':         'green',
  'late':            'orange',
  'missed':          'red',
  'admin_override':  'blue',
  'disabled':        'default',
  'pending':         'default',
  'absent':          'red',
};

const STATUS_LABELS = {
  'on_time':        'On Time',
  'late':           'Late',
  'missed':         'Missed',
  'admin_override': 'Admin Override',
  'disabled':       'Disabled',
  'pending':        'Pending',
  'absent':         'Absent',
};

const DAY_STATUS_COLORS = {
  'full_day': 'green',
  'partial':  'orange',
  'absent':   'red',
  'pending':  'default',
};

function StatusTag({ status }) {
  if (!status) return <Tag color="default">—</Tag>;
  const key = status.toLowerCase();
  return <Tag color={STATUS_COLORS[key] ?? 'default'}>{STATUS_LABELS[key] ?? status}</Tag>;
}

function SegmentCell({ segment, managerName, managerDate, segmentLabel, onOverride }) {
  if (!segment) return <Text type="secondary">—</Text>;
  const isMissed = segment.status?.toLowerCase() === 'missed';
  return (
    <Space orientation="vertical" size={2}>
      <StatusTag status={segment.status} />
      {segment.time && <Text type="secondary" style={{ fontSize: 12 }}>{segment.time}</Text>}
      {isMissed && (
        <Button
          size="small"
          icon={<EditOutlined />}
          onClick={() => onOverride({ managerName, date: managerDate, segment: segmentLabel, segment_key: segment.key })}
        >
          Override
        </Button>
      )}
    </Space>
  );
}

function ManagerAttendanceAdminPage() {
  const [searchParams] = useSearchParams();
  const [selectedDate, setSelectedDate] = useState(dayjs());
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(false);

  // Override modal state
  const [overrideTarget, setOverrideTarget] = useState(null);
  const [overrideForm] = Form.useForm();
  const [overrideSubmitting, setOverrideSubmitting] = useState(false);

  const fetchAttendance = useCallback(async (date) => {
    setLoading(true);
    try {
      const dateStr = (date ?? selectedDate).format('YYYY-MM-DD');
      const data = await getManagerAttendanceAll(dateStr);
      setRecords(Array.isArray(data) ? data : []);
    } catch (err) {
      message.error('Failed to load attendance: ' + err.message);
    } finally {
      setLoading(false);
    }
  }, [selectedDate]);

  useEffect(() => {
    fetchAttendance(selectedDate);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleDateChange = (date) => {
    setSelectedDate(date);
    if (date) fetchAttendance(date);
  };

  const openOverride = (info) => {
    setOverrideTarget(info);
    overrideForm.resetFields();
  };

  const handleOverrideSave = async () => {
    try {
      const values = await overrideForm.validateFields();
      setOverrideSubmitting(true);
      const payload = {
        manager_name: overrideTarget.managerName,
        date: overrideTarget.date,
        segment: overrideTarget.segment_key,
        status: values.status,
        check_in_time: values.check_in_time
          ? values.check_in_time.format('HH:mm')
          : null,
        reason: values.reason,
      };
      await overrideManagerAttendance(payload);
      message.success('Attendance override saved');
      setOverrideTarget(null);
      fetchAttendance(selectedDate);
    } catch (err) {
      if (err?.errorFields) return;
      message.error('Failed to save override: ' + (err?.message ?? 'Unknown error'));
    } finally {
      setOverrideSubmitting(false);
    }
  };

  const columns = [
    {
      title: 'Manager',
      dataIndex: 'manager_name',
      key: 'manager_name',
      render: (name) => <Text strong>{name}</Text>,
    },
    {
      title: 'Morning',
      dataIndex: 'morning',
      key: 'morning',
      render: (seg, record) => (
        <SegmentCell
          segment={seg}
          managerName={record.manager_name}
          managerDate={selectedDate.format('YYYY-MM-DD')}
          segmentLabel="Morning Check-in"
          onOverride={openOverride}
        />
      ),
    },
    {
      title: 'Afternoon',
      dataIndex: 'afternoon',
      key: 'afternoon',
      render: (seg, record) => (
        <SegmentCell
          segment={seg}
          managerName={record.manager_name}
          managerDate={selectedDate.format('YYYY-MM-DD')}
          segmentLabel="Afternoon Check-in"
          onOverride={openOverride}
        />
      ),
    },
    {
      title: 'Evening',
      dataIndex: 'evening',
      key: 'evening',
      render: (seg, record) => (
        <SegmentCell
          segment={seg}
          managerName={record.manager_name}
          managerDate={selectedDate.format('YYYY-MM-DD')}
          segmentLabel="Evening Check-out"
          onOverride={openOverride}
        />
      ),
    },
    {
      title: 'Day Status',
      dataIndex: 'day_status',
      key: 'day_status',
      render: (status) => {
        const key = status?.toLowerCase();
        const label = key === 'full_day' ? 'Full Day'
          : key === 'partial' ? 'Partial'
          : key === 'absent' ? 'Absent'
          : 'Pending';
        return <Tag color={DAY_STATUS_COLORS[key] ?? 'default'}>{label}</Tag>;
      },
    },
  ];

  return (
    <div className="layout-content">
      <Card variant="borderless" className="criclebox mb-24" style={{ marginBottom: 24 }}>
        <Row align="middle" justify="space-between" wrap={false}>
          <Col>
            <Title level={4} style={{ margin: 0 }}>
              <CalendarOutlined style={{ marginRight: 8 }} />
              Manager Attendance
            </Title>
            <Text type="secondary">Monitor and override daily manager attendance</Text>
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
                  onClick={() => fetchAttendance(selectedDate)}
                  loading={loading}
                />
              </Tooltip>
            </Space>
          </Col>
        </Row>
      </Card>

      <Row gutter={[24, 0]}>
        <Col xs={24}>
          <Card variant="borderless" className="criclebox tablespace mb-24">
            <div className="table-responsive">
              <Table
                columns={columns}
                dataSource={records}
                rowKey={(r, i) => r.manager_id ?? r.manager_name ?? i}
                loading={loading}
                pagination={{ pageSize: 20 }}
                className="ant-border-space"
                scroll={{ x: 800 }}
              />
            </div>
          </Card>
        </Col>
      </Row>

      {/* Override Modal */}
      <Modal
        title="Admin Attendance Override"
        open={!!overrideTarget}
        onOk={handleOverrideSave}
        onCancel={() => setOverrideTarget(null)}
        confirmLoading={overrideSubmitting}
        okText="Save Override"
        width={480}
      >
        {overrideTarget && (
          <div style={{ marginBottom: 16 }}>
            <Text type="secondary">Manager: </Text>
            <Text strong>{overrideTarget.managerName}</Text>
            <br />
            <Text type="secondary">Date: </Text>
            <Text>{overrideTarget.date}</Text>
            <br />
            <Text type="secondary">Segment: </Text>
            <Text>{overrideTarget.segment}</Text>
          </div>
        )}
        <Form form={overrideForm} layout="vertical">
          <Form.Item
            name="status"
            label="Override Status"
            rules={[{ required: true, message: 'Please select a status' }]}
          >
            <Select placeholder="Select status">
              <Option value="admin_override">Mark as Present (Admin Override)</Option>
              <Option value="on_time">On Time</Option>
              <Option value="late">Late</Option>
              <Option value="absent">Absent / Leave</Option>
            </Select>
          </Form.Item>
          <Form.Item name="check_in_time" label="Check-in Time (optional)">
            <TimePicker format="HH:mm" style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item
            name="reason"
            label="Reason"
            rules={[{ required: true, message: 'Reason is required' }]}
          >
            <TextArea rows={3} placeholder="Explain the reason for this override" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

export default ManagerAttendanceAdminPage;
