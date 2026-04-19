import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Card, Row, Col, Typography, Tag, Button, Statistic, Table, Badge,
  Calendar, Tooltip, Modal, Space, Progress, Alert, Spin, Collapse,
  message,
} from 'antd';
import {
  SunOutlined, ClockCircleOutlined, MoonOutlined, CheckCircleOutlined,
  WarningOutlined, CloseCircleOutlined, LeftOutlined, RightOutlined,
  SettingOutlined, CalendarOutlined, HistoryOutlined, BarChartOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import {
  getMyAttendanceConfig,
  getMyTodayAttendance,
  getMyAttendanceHistory,
  checkInSegment,
} from '../services/apiService';

const { Title, Text } = Typography;

const timeToMinutes = (timeStr) => {
  if (!timeStr) return 0;
  const parts = timeStr.split(':');
  return parseInt(parts[0], 10) * 60 + parseInt(parts[1], 10);
};

const formatTime12 = (timeStr) => {
  if (!timeStr) return '--';
  const d = dayjs(`2000-01-01T${timeStr}`);
  return d.isValid() ? d.format('h:mm A') : timeStr;
};

const formatCountdown = (minutes) => {
  if (minutes <= 0) return '0m remaining';
  const hrs = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return hrs > 0 ? `${hrs}h ${mins}m remaining` : `${mins}m remaining`;
};

const SEGMENT_META = {
  morning: { label: 'Morning', icon: <SunOutlined />, configKey: 'morning' },
  afternoon: { label: 'Afternoon', icon: <ClockCircleOutlined />, configKey: 'afternoon' },
  evening: { label: 'Evening', icon: <MoonOutlined />, configKey: 'evening' },
};

const DAY_STATUS_COLORS = {
  full_day: 'success',
  partial: 'warning',
  absent: 'error',
  pending: 'default',
};

const DAY_STATUS_LABELS = {
  full_day: 'Full Day',
  partial: 'Partial',
  absent: 'Absent',
  pending: 'Pending',
};

const SEG_STATUS_COLORS = {
  on_time: 'success',
  late: 'warning',
  missed: 'error',
  admin_override: 'processing',
  disabled: 'default',
  pending: 'default',
  open: 'processing',
};

const SEG_STATUS_LABELS = {
  on_time: 'On Time',
  late: 'Late',
  missed: 'Missed',
  admin_override: 'Admin Override',
  disabled: 'Disabled',
  pending: 'Pending',
  open: 'Window Open',
};

// Derive segment UI state from config + attendance + current time
const getSegmentStatus = (config, attendance, segment, nowMinutes) => {
  if (!config) return { status: 'pending', label: 'Loading…', color: 'default', canCheckIn: false };

  const enabled = config[`${segment}_enabled`];
  const windowStart = config[`${segment}_window_start`];
  const windowEnd = config[`${segment}_window_end`];
  const checkIn = attendance?.[`${segment}_check_in`];
  const segStatus = attendance?.[`${segment}_status`];

  if (!enabled) {
    return { status: 'disabled', label: 'Disabled', color: 'default', canCheckIn: false };
  }

  if (checkIn) {
    const statusKey = (segStatus || 'on_time').toLowerCase().replace(' ', '_');
    return {
      status: 'completed',
      label: SEG_STATUS_LABELS[statusKey] || segStatus,
      color: SEG_STATUS_COLORS[statusKey] || 'default',
      canCheckIn: false,
      time: formatTime12(checkIn.includes('T') ? checkIn.split('T')[1] : checkIn),
    };
  }

  if (!windowStart || !windowEnd) {
    return { status: 'pending', label: 'Not Configured', color: 'default', canCheckIn: false };
  }

  const startMin = timeToMinutes(windowStart);
  const endMin = timeToMinutes(windowEnd);

  if (nowMinutes < startMin) {
    return {
      status: 'pending',
      label: 'Not Started',
      color: 'default',
      canCheckIn: false,
      message: `Opens at ${formatTime12(windowStart)}`,
    };
  }

  if (nowMinutes >= startMin && nowMinutes <= endMin) {
    return {
      status: 'open',
      label: 'Window Open',
      color: 'processing',
      canCheckIn: true,
      countdown: endMin - nowMinutes,
    };
  }

  return { status: 'missed', label: 'Missed', color: 'error', canCheckIn: false };
};

// ---------- SegmentCard component ----------

function SegmentCard({ segment, config, attendance, onCheckIn, checkingIn }) {
  const meta = SEGMENT_META[segment];
  const now = new Date();
  const nowMinutes = now.getHours() * 60 + now.getMinutes();
  const segStatus = getSegmentStatus(config, attendance, segment, nowMinutes);

  const isOpen = segStatus.status === 'open';
  const cardStyle = {
    border: isOpen ? '2px solid #52c41a' : '1px solid #d9d9d9',
    background: isOpen ? '#f6ffed' : 'white',
    borderRadius: 8,
    height: '100%',
  };

  return (
    <Card style={cardStyle} styles={{ body: { padding: '16px' } }}>
      <Space orientation="vertical" style={{ width: '100%' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Space>
            {meta.icon}
            <Text strong>{meta.label}</Text>
          </Space>
          <Tag color={segStatus.color}>{segStatus.label}</Tag>
        </div>

        {config && config[`${segment}_window_start`] && (
          <Text type="secondary" style={{ fontSize: 12 }}>
            {formatTime12(config[`${segment}_window_start`])} – {formatTime12(config[`${segment}_window_end`])}
          </Text>
        )}

        {segStatus.canCheckIn && (
          <>
            <Button
              type="primary"
              size="large"
              block
              onClick={() => onCheckIn(segment)}
              loading={checkingIn === segment}
              icon={<CheckCircleOutlined />}
            >
              Check In Now
            </Button>
            <Text type="secondary" style={{ fontSize: 12 }}>
              <ClockCircleOutlined style={{ marginRight: 4 }} />
              {formatCountdown(segStatus.countdown)}
            </Text>
          </>
        )}

        {segStatus.time && (
          <Text style={{ color: '#52c41a' }}>
            <CheckCircleOutlined style={{ marginRight: 4 }} />
            Checked in at {segStatus.time}
          </Text>
        )}

        {segStatus.message && (
          <Text type="secondary" style={{ fontSize: 12 }}>{segStatus.message}</Text>
        )}
      </Space>
    </Card>
  );
}

// ---------- Main Page ----------

function ManagerMyAttendancePage() {
  const [config, setConfig] = useState(null);
  const [todayAttendance, setTodayAttendance] = useState(null);
  const [historyRecords, setHistoryRecords] = useState([]);
  const [summary, setSummary] = useState(null);
  const [currentMonth, setCurrentMonth] = useState(dayjs());
  const [selectedDay, setSelectedDay] = useState(null);
  const [dayModalVisible, setDayModalVisible] = useState(false);
  const [checkingIn, setCheckingIn] = useState(null); // segment name or null
  const [loadingConfig, setLoadingConfig] = useState(true);
  const [loadingToday, setLoadingToday] = useState(true);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [showFullHistory, setShowFullHistory] = useState(false);
  const timerRef = useRef(null);

  // Fetch config once on mount
  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const data = await getMyAttendanceConfig();
        setConfig(data);
      } catch (err) {
        console.error('Failed to load config:', err);
      } finally {
        setLoadingConfig(false);
      }
    };
    fetchConfig();
  }, []);

  // Fetch today's attendance
  const fetchToday = useCallback(async () => {
    try {
      setLoadingToday(true);
      const data = await getMyTodayAttendance();
      setTodayAttendance(data);
    } catch (err) {
      console.error('Failed to load today attendance:', err);
    } finally {
      setLoadingToday(false);
    }
  }, []);

  useEffect(() => {
    fetchToday();
    // Auto-refresh every 30 seconds
    timerRef.current = setInterval(fetchToday, 30000);
    return () => clearInterval(timerRef.current);
  }, [fetchToday]);

  // Fetch history when month changes
  const fetchHistory = useCallback(async (month) => {
    setLoadingHistory(true);
    try {
      const startDate = month.startOf('month').format('YYYY-MM-DD');
      const endDate = month.endOf('month').format('YYYY-MM-DD');
      const data = await getMyAttendanceHistory(startDate, endDate);
      setHistoryRecords(Array.isArray(data?.records) ? data.records : Array.isArray(data) ? data : []);
      if (data?.summary) setSummary(data.summary);
    } catch (err) {
      console.error('Failed to load history:', err);
    } finally {
      setLoadingHistory(false);
    }
  }, []);

  useEffect(() => {
    fetchHistory(currentMonth);
  }, [currentMonth, fetchHistory]);

  const handleCheckIn = async (segment) => {
    try {
      setCheckingIn(segment);
      await checkInSegment(segment);
      message.success(`${SEGMENT_META[segment].label} check-in successful!`);
      fetchToday();
    } catch (err) {
      const detail = err.message || '';
      if (detail.toLowerCase().includes('window closed') || detail.toLowerCase().includes('window has closed')) {
        Modal.warning({
          title: 'Check-in Window Closed',
          content: (
            <div>
              <p>{detail}</p>
              <p>Please contact your administrator if you need this check-in to be recorded.</p>
            </div>
          ),
        });
      } else if (detail.toLowerCase().includes('already checked in')) {
        message.info('You have already checked in for this segment.');
      } else {
        message.error(detail || 'Check-in failed. Please try again.');
      }
    } finally {
      setCheckingIn(null);
    }
  };

  // ---------- Overall day status ----------
  const getDayStatusConfig = (status) => {
    const key = (status || 'pending').toLowerCase().replace(' ', '_');
    const configs = {
      full_day: { type: 'success', icon: <CheckCircleOutlined />, text: 'Full Day Completed' },
      partial: { type: 'warning', icon: <WarningOutlined />, text: 'Partial Attendance' },
      absent: { type: 'error', icon: <CloseCircleOutlined />, text: 'Absent' },
      pending: { type: 'info', icon: <ClockCircleOutlined />, text: 'Pending Check-ins' },
    };
    return configs[key] || configs.pending;
  };

  const todayDayStatus = todayAttendance?.day_status || 'pending';
  const dayStatusCfg = getDayStatusConfig(todayDayStatus);

  // ---------- Calendar ----------
  const getRecordForDate = (date) =>
    historyRecords.find((r) => dayjs(r.date).isSame(date, 'day'));

  const dateCellRender = (date) => {
    if (!date.isSame(currentMonth, 'month')) return null;
    const record = getRecordForDate(date);
    if (!record) return null;
    const statusKey = (record.day_status || '').toLowerCase().replace(' ', '_');
    const badgeStatus = statusKey === 'full_day' ? 'success'
      : statusKey === 'partial' ? 'warning'
      : statusKey === 'absent' ? 'error'
      : 'default';
    return (
      <Tooltip title={`${DAY_STATUS_LABELS[statusKey] || record.day_status} – click for details`}>
        <Badge status={badgeStatus} style={{ position: 'absolute', bottom: 4, right: 4 }} />
      </Tooltip>
    );
  };

  const handleDateSelect = (date) => {
    const record = getRecordForDate(date);
    if (record) {
      setSelectedDay(record);
      setDayModalVisible(true);
    }
  };

  // ---------- Stats ----------
  const workingDays = historyRecords.filter((r) => r.day_status !== null).length;
  const fullDays = historyRecords.filter((r) => (r.day_status || '').toLowerCase().replace(' ', '_') === 'full_day').length;
  const partialDays = historyRecords.filter((r) => (r.day_status || '').toLowerCase().replace(' ', '_') === 'partial').length;
  const absentDays = historyRecords.filter((r) => (r.day_status || '').toLowerCase().replace(' ', '_') === 'absent').length;

  const totalCheckIns = historyRecords.reduce((acc, r) => {
    ['morning', 'afternoon', 'evening'].forEach((seg) => {
      if (r[`${seg}_check_in`]) acc.total++;
      if ((r[`${seg}_status`] || '').toLowerCase().replace(' ', '_') === 'on_time') acc.onTime++;
    });
    return acc;
  }, { total: 0, onTime: 0 });
  const onTimeRate = totalCheckIns.total > 0 ? Math.round((totalCheckIns.onTime / totalCheckIns.total) * 100) : 0;

  // ---------- History table ----------
  const recentRecords = [...historyRecords]
    .sort((a, b) => dayjs(b.date).diff(dayjs(a.date)))
    .slice(0, showFullHistory ? undefined : 10);

  const renderSegCell = (record, seg) => {
    const checkIn = record[`${seg}_check_in`];
    const status = record[`${seg}_status`];
    if (!checkIn && !status) return <Text type="secondary">–</Text>;
    const statusKey = (status || '').toLowerCase().replace(' ', '_');
    return (
      <Space orientation="vertical" size={0}>
        {checkIn && <Text style={{ fontSize: 12 }}>{formatTime12(checkIn.includes('T') ? checkIn.split('T')[1] : checkIn)}</Text>}
        {status && <Tag color={SEG_STATUS_COLORS[statusKey] || 'default'} style={{ fontSize: 11 }}>{SEG_STATUS_LABELS[statusKey] || status}</Tag>}
      </Space>
    );
  };

  const historyColumns = [
    {
      title: 'Date',
      dataIndex: 'date',
      key: 'date',
      render: (d) => dayjs(d).format('ddd, MMM D'),
    },
    {
      title: 'Status',
      dataIndex: 'day_status',
      key: 'day_status',
      render: (s) => {
        const key = (s || 'pending').toLowerCase().replace(' ', '_');
        return <Tag color={DAY_STATUS_COLORS[key] || 'default'}>{DAY_STATUS_LABELS[key] || s}</Tag>;
      },
    },
    {
      title: 'Morning',
      key: 'morning',
      render: (_, record) => renderSegCell(record, 'morning'),
    },
    {
      title: 'Afternoon',
      key: 'afternoon',
      render: (_, record) => renderSegCell(record, 'afternoon'),
    },
    {
      title: 'Evening',
      key: 'evening',
      render: (_, record) => renderSegCell(record, 'evening'),
    },
    {
      title: '',
      key: 'override',
      width: 40,
      render: (_, record) =>
        record.is_overridden ? (
          <Tooltip title="Admin override applied">
            <WarningOutlined style={{ color: '#1890ff' }} />
          </Tooltip>
        ) : null,
    },
  ];

  // ---------- Config display ----------
  const renderConfigValue = (enabled, start, end) => {
    if (!enabled) return <Tag color="default">Disabled</Tag>;
    if (!start) return <Text type="secondary">Not configured</Text>;
    return <Text>{formatTime12(start)} – {formatTime12(end)}</Text>;
  };

  // ---------- Render ----------
  return (
    <div className="layout-content">
      {/* Header */}
      <Card variant="borderless" className="criclebox mb-24" style={{ marginBottom: 24 }}>
        <Row align="middle" justify="space-between">
          <Col>
            <Title level={4} style={{ margin: 0 }}>
              <ClockCircleOutlined style={{ marginRight: 8 }} />
              My Attendance
            </Title>
            <Text type="secondary">Manage your daily check-ins and view attendance history</Text>
          </Col>
          <Col>
            <Text type="secondary">{dayjs().format('dddd, MMMM D, YYYY')}</Text>
          </Col>
        </Row>
      </Card>

      {/* ── Section 1: Today's Check-in Widget ── */}
      <Card
        title={<><CalendarOutlined style={{ marginRight: 8 }} />Today's Check-in</>}
        className="criclebox mb-24"
        style={{ marginBottom: 24 }}
        extra={
          loadingToday ? <Spin size="small" /> : (
            <Alert
              type={dayStatusCfg.type}
              title={<Space>{dayStatusCfg.icon}<span>{dayStatusCfg.text}</span></Space>}
              style={{ padding: '2px 10px', marginBottom: 0 }}
            />
          )
        }
      >
        {loadingConfig || loadingToday ? (
          <Row gutter={[16, 16]}>
            {['morning', 'afternoon', 'evening'].map((seg) => (
              <Col xs={24} sm={8} key={seg}>
                <Card loading style={{ height: 160 }} />
              </Col>
            ))}
          </Row>
        ) : (
          <Row gutter={[16, 16]}>
            {['morning', 'afternoon', 'evening'].map((seg) => (
              <Col xs={24} sm={8} key={seg}>
                <SegmentCard
                  segment={seg}
                  config={config}
                  attendance={todayAttendance}
                  onCheckIn={handleCheckIn}
                  checkingIn={checkingIn}
                />
              </Col>
            ))}
          </Row>
        )}
      </Card>

      {/* ── Section 3: Stats (shown before calendar so stats are visible) ── */}
      <Card
        title={<><BarChartOutlined style={{ marginRight: 8 }} />Monthly Summary — {currentMonth.format('MMMM YYYY')}</>}
        className="criclebox mb-24"
        style={{ marginBottom: 24 }}
        loading={loadingHistory}
      >
        <Row gutter={[16, 16]}>
          <Col xs={12} sm={6}>
            <Card variant="borderless" style={{ textAlign: 'center', background: '#f6ffed' }}>
              <Statistic
                title="Full Days"
                value={fullDays}
                suffix={workingDays > 0 ? `/ ${workingDays}` : ''}
                styles={{ content: { color: '#52c41a' } }}
                prefix={<CheckCircleOutlined />}
              />
              {workingDays > 0 && (
                <Progress
                  percent={Math.round((fullDays / workingDays) * 100)}
                  strokeColor="#52c41a"
                  showInfo={false}
                  size="small"
                />
              )}
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card variant="borderless" style={{ textAlign: 'center', background: '#fffbe6' }}>
              <Statistic
                title="Partial Days"
                value={partialDays}
                suffix={workingDays > 0 ? `/ ${workingDays}` : ''}
                styles={{ content: { color: '#faad14' } }}
                prefix={<WarningOutlined />}
              />
              {workingDays > 0 && (
                <Progress
                  percent={Math.round((partialDays / workingDays) * 100)}
                  strokeColor="#faad14"
                  showInfo={false}
                  size="small"
                />
              )}
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card variant="borderless" style={{ textAlign: 'center', background: '#fff2f0' }}>
              <Statistic
                title="Absent Days"
                value={absentDays}
                suffix={workingDays > 0 ? `/ ${workingDays}` : ''}
                styles={{ content: { color: '#ff4d4f' } }}
                prefix={<CloseCircleOutlined />}
              />
              {workingDays > 0 && (
                <Progress
                  percent={Math.round((absentDays / workingDays) * 100)}
                  strokeColor="#ff4d4f"
                  showInfo={false}
                  size="small"
                />
              )}
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card variant="borderless" style={{ textAlign: 'center', background: '#e6f7ff' }}>
              <Statistic
                title="On-Time Rate"
                value={onTimeRate}
                suffix="%"
                styles={{ content: { color: '#1890ff' } }}
                prefix={<ClockCircleOutlined />}
              />
              <Progress
                percent={onTimeRate}
                strokeColor="#1890ff"
                showInfo={false}
                size="small"
              />
            </Card>
          </Col>
        </Row>
      </Card>

      {/* ── Section 2: Monthly Calendar ── */}
      <Card
        title={<><CalendarOutlined style={{ marginRight: 8 }} />Monthly Calendar</>}
        className="criclebox mb-24"
        style={{ marginBottom: 24 }}
        extra={
          <Space>
            <Button
              icon={<LeftOutlined />}
              size="small"
              onClick={() => setCurrentMonth(currentMonth.subtract(1, 'month'))}
            />
            <Text strong>{currentMonth.format('MMMM YYYY')}</Text>
            <Button
              icon={<RightOutlined />}
              size="small"
              onClick={() => setCurrentMonth(currentMonth.add(1, 'month'))}
              disabled={currentMonth.isSame(dayjs(), 'month')}
            />
          </Space>
        }
      >
        <Spin spinning={loadingHistory}>
          <Calendar
            value={currentMonth}
            onSelect={handleDateSelect}
            dateCellRender={dateCellRender}
            headerRender={() => null}
            style={{ border: 'none' }}
          />
        </Spin>
      </Card>

      {/* ── Section 4: Recent History Table ── */}
      <Card
        title={<><HistoryOutlined style={{ marginRight: 8 }} />Recent History</>}
        className="criclebox mb-24"
        style={{ marginBottom: 24 }}
        extra={
          <Button
            type="link"
            onClick={() => setShowFullHistory(!showFullHistory)}
          >
            {showFullHistory ? 'Show Less' : 'View More'}
          </Button>
        }
      >
        <Table
          dataSource={recentRecords}
          columns={historyColumns}
          rowKey={(r) => r.date || r.id}
          pagination={false}
          loading={loadingHistory}
          size="small"
          scroll={{ x: 600 }}
        />
      </Card>

      {/* ── Section 5: My Configuration ── */}
      <Card className="criclebox mb-24" style={{ marginBottom: 24 }}>
        <Collapse
          ghost
          items={[{
            key: 'config',
            label: (
              <Space>
                <SettingOutlined />
                <Text strong>My Attendance Configuration</Text>
              </Space>
            ),
            children: loadingConfig ? (
              <Spin />
            ) : config ? (
              <Space orientation="vertical" style={{ width: '100%' }}>
                <Row gutter={[16, 8]}>
                  <Col xs={24} sm={8}>
                    <Text type="secondary">Morning Window</Text>
                    <div>{renderConfigValue(config.morning_enabled, config.morning_window_start, config.morning_window_end)}</div>
                  </Col>
                  <Col xs={24} sm={8}>
                    <Text type="secondary">Afternoon Window</Text>
                    <div>{renderConfigValue(config.afternoon_enabled, config.afternoon_window_start, config.afternoon_window_end)}</div>
                  </Col>
                  <Col xs={24} sm={8}>
                    <Text type="secondary">Evening Window</Text>
                    <div>{renderConfigValue(config.evening_enabled, config.evening_window_start, config.evening_window_end)}</div>
                  </Col>
                </Row>
                <Alert
                  type="info"
                  icon={<SettingOutlined />}
                  showIcon
                  title="⚠️ Only admins can modify your time windows."
                  style={{ marginTop: 8 }}
                />
              </Space>
            ) : (
              <Text type="secondary">Configuration not available.</Text>
            ),
          }]}
        />
      </Card>

      {/* Day detail modal */}
      <Modal
        title={selectedDay ? dayjs(selectedDay.date).format('dddd, MMMM D, YYYY') : ''}
        open={dayModalVisible}
        onCancel={() => setDayModalVisible(false)}
        footer={null}
      >
        {selectedDay && (
          <Space orientation="vertical" style={{ width: '100%' }}>
            <div>
              <Text type="secondary">Day Status: </Text>
              {(() => {
                const key = (selectedDay.day_status || 'pending').toLowerCase().replace(' ', '_');
                return <Tag color={DAY_STATUS_COLORS[key] || 'default'}>{DAY_STATUS_LABELS[key] || selectedDay.day_status}</Tag>;
              })()}
              {selectedDay.is_overridden && (
                <Tag color="blue" style={{ marginLeft: 8 }}>Admin Override</Tag>
              )}
            </div>
            {['morning', 'afternoon', 'evening'].map((seg) => (
              <Row key={seg} gutter={8} align="middle">
                <Col span={8}>
                  <Space>
                    {SEGMENT_META[seg].icon}
                    <Text strong>{SEGMENT_META[seg].label}</Text>
                  </Space>
                </Col>
                <Col span={16}>
                  {renderSegCell(selectedDay, seg)}
                </Col>
              </Row>
            ))}
            {selectedDay.notes && (
              <div>
                <Text type="secondary">Notes: </Text>
                <Text>{selectedDay.notes}</Text>
              </div>
            )}
          </Space>
        )}
      </Modal>
    </div>
  );
}

export default ManagerMyAttendancePage;
