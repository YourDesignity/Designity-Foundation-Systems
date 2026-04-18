// src/pages/ManagerDashboard.jsx

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Button, Space, Typography, Spin, Alert } from 'antd';
import {
  SunOutlined, ClockCircleOutlined, MoonOutlined, CheckCircleOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import ContentHeader from '../components/ContentHeader';
import { FaEllipsisV } from 'react-icons/fa';
import '../styles/dashboard.css';
import { getEmployees, getMyAttendanceConfig, getMyTodayAttendance } from '../services/apiService';

const { Text } = Typography;

// --- Quick attendance widget helpers ---

const timeToMinutes = (timeStr) => {
  if (!timeStr) return 0;
  const parts = timeStr.split(':');
  return parseInt(parts[0], 10) * 60 + parseInt(parts[1], 10);
};

const formatTime12 = (timeStr) => {
  if (!timeStr) return '--';
  const [h, m] = timeStr.split(':').map(Number);
  const ampm = h >= 12 ? 'PM' : 'AM';
  const hour = h % 12 || 12;
  return `${hour}:${String(m).padStart(2, '0')} ${ampm}`;
};

const SEGMENT_META = {
  morning: { label: 'Morning', icon: <SunOutlined /> },
  afternoon: { label: 'Afternoon', icon: <ClockCircleOutlined /> },
  evening: { label: 'Evening', icon: <MoonOutlined /> },
};

function QuickSegmentStatus({ segment, config, attendance }) {
  const now = new Date();
  const nowMin = now.getHours() * 60 + now.getMinutes();
  const enabled = config?.[`${segment}_enabled`];
  const windowStart = config?.[`${segment}_window_start`];
  const windowEnd = config?.[`${segment}_window_end`];
  const checkIn = attendance?.[`${segment}_check_in`];
  const status = attendance?.[`${segment}_status`];

  if (!enabled) return null;

  let tagColor, tagText;
  if (checkIn) {
    const key = (status || 'on_time').toLowerCase().replace(' ', '_');
    tagColor = key === 'on_time' ? 'success' : 'warning';
    tagText = key === 'on_time' ? 'On Time ✓' : 'Late ⏰';
  } else if (!windowStart) {
    return null;
  } else {
    const startMin = timeToMinutes(windowStart);
    const endMin = timeToMinutes(windowEnd);
    if (nowMin < startMin) {
      tagColor = 'default';
      tagText = `Opens ${formatTime12(windowStart)}`;
    } else if (nowMin <= endMin) {
      tagColor = 'processing';
      tagText = 'Window Open';
    } else {
      tagColor = 'error';
      tagText = 'Missed';
    }
  }

  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 0' }}>
      <Space size={4}>
        {SEGMENT_META[segment].icon}
        <Text style={{ fontSize: 13 }}>{SEGMENT_META[segment].label}</Text>
      </Space>
      <span className={`ant-tag ant-tag-${tagColor}`}>{tagText}</span>
    </div>
  );
}

function AttendanceQuickWidget() {
  const navigate = useNavigate();
  const [config, setConfig] = useState(null);
  const [today, setToday] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      try {
        const [cfg, att] = await Promise.all([getMyAttendanceConfig(), getMyTodayAttendance()]);
        if (mounted) { setConfig(cfg); setToday(att); }
      } catch (_) {
        // silently fail — widget is supplementary
      } finally {
        if (mounted) setLoading(false);
      }
    };
    load();
    return () => { mounted = false; };
  }, []);

  const dayStatusKey = (today?.day_status || 'pending').toLowerCase().replace(' ', '_');
  const dayAlertType = dayStatusKey === 'full_day' ? 'success'
    : dayStatusKey === 'partial' ? 'warning'
    : dayStatusKey === 'absent' ? 'error'
    : 'info';
  const dayLabel = {
    full_day: 'Full Day ✓',
    partial: 'Partial Attendance',
    absent: 'Absent',
    pending: 'Pending Check-ins',
  }[dayStatusKey] || 'Pending';

  return (
    <Card
      title={<Space><ClockCircleOutlined />Today's Attendance</Space>}
      size="small"
      extra={<Button type="link" size="small" onClick={() => navigate('/my-attendance')}>View Full →</Button>}
      style={{ marginBottom: 24 }}
    >
      {loading ? (
        <div style={{ textAlign: 'center', padding: 16 }}><Spin size="small" /></div>
      ) : (
        <Space orientation="vertical" style={{ width: '100%' }}>
          <Alert type={dayAlertType} title={dayLabel} style={{ padding: '4px 12px' }} />
          {['morning', 'afternoon', 'evening'].map((seg) => (
            <QuickSegmentStatus key={seg} segment={seg} config={config} attendance={today} />
          ))}
        </Space>
      )}
    </Card>
  );
}

// --- Main Dashboard ---

const ManagerDashboardPage = () => {
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [reconnectMessage, setReconnectMessage] = useState(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        const data = await getEmployees();
        setEmployees(Array.isArray(data) ? data : []);
      } catch (e) {
        console.error("Failed to load employee data:", e);
        setError(e.message);
      } finally {
        setLoading(false);
      }
    };
    loadData();

    try {
        // websocketService.register(setEmployees, setReconnectMessage);
        // websocketService.connect();
    } catch (wsError) {
        console.error("WebSocket connection failed:", wsError);
        setReconnectMessage("Real-time updates are unavailable.");
    }

    return () => {
        // websocketService.unregister();
    };
  }, []);

  const SkeletonCard = () => ( <div className="card skeleton"><div className="skeleton-icon"></div><div className="skeleton-text skeleton-text-medium"></div></div> );
  const SkeletonEmployee = () => ( <li className="employee-item skeleton"><div className="skeleton-avatar"></div><div className="employee-details"><div className="employee-info"><div className="skeleton-text skeleton-text-short"></div><div className="skeleton-text skeleton-text-long"></div></div></div><div className="skeleton-text skeleton-text-medium"></div></li> );

  if (loading) {
    return (
        <div className="dashboard-page-main">
            <ContentHeader />
            <div className="cards">
                <SkeletonCard /><SkeletonCard />
            </div>
            <div className="employees-section">
                <div className="employees-header"><h3 className="employees-title">Loading Team Members...</h3></div>
                <ul className="employee-list">{Array.from({ length: 5 }).map((_, index) => <SkeletonEmployee key={index} />)}</ul>
            </div>
        </div>
    );
  }

  if (error) return <div className="error-message">Error: {error}</div>;

  return (
    <div className="dashboard-page-main">
      <ContentHeader />

      {/* Quick Attendance Widget — shown at the top for easy access */}
      <AttendanceQuickWidget />

      <div className="cards">
        {/* ... (cards content remains the same) ... */}
      </div>

      <div className="employees-section">
        <div className="employees-header">
          <h3 className="employees-title">Your Team Members</h3>
          {reconnectMessage && <div className="reconnect-message">{reconnectMessage}</div>}
        </div>
        <ul className="employee-list">
          {employees.map(employee => (
              <li key={employee.id} className="employee-item">
                <div className="employee-details">
                  <div className="employee-avatar-placeholder">{employee.name?.charAt(0).toUpperCase() ?? '?'}</div>
                  <div className="employee-info">
                    <span className="employee-name">{employee.name ?? 'No Name'}</span>
                    <span className="employee-designation">{employee.designation ?? 'No Designation'}</span>
                  </div>
                </div>
                <div className="employee-pay">
                  Status: {employee.status || 'Active'}
                </div>
                <span className="employee-options"><FaEllipsisV /></span>
              </li>
            ))}
        </ul>
      </div>
    </div>
  );
};

export default ManagerDashboardPage;
