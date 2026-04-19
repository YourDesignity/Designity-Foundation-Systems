/**
 * ModuleSettingsPage.jsx
 *
 * Global module configuration for the system.
 * Enables / disables modules system-wide and provides default configs.
 */

import React, { useState, useEffect } from 'react';
import {
  Row, Col, Card, Switch, Typography, Space, Button, Alert,
  Breadcrumb, Divider, Tag, Spin, message,
} from 'antd';
import {
  TeamOutlined, CarOutlined, ShoppingOutlined, SettingOutlined,
  SaveOutlined, ReloadOutlined,
} from '@ant-design/icons';
import { toast } from 'react-toastify';
import { useAuth } from '../../context/AuthContext';
import ModuleConfigEditor from '../../components/role-contracts/ModuleConfigEditor';
import {
  getGlobalModuleSettings, updateGlobalModuleSettings,
} from '../../services/contractService';
import '../../styles/contract-pages.css';

const { Title, Text, Paragraph } = Typography;

const MODULE_DEFS = [
  {
    key: 'employee',
    label: 'Employee Module',
    icon: <TeamOutlined />,
    color: '#1890ff',
    description:
      'Track employee assignments, attendance records, and payroll calculations for contracts.',
    features: ['Multi-employee assignment', 'Role-based access', 'Attendance tracking', 'Salary calculation'],
  },
  {
    key: 'inventory',
    label: 'Inventory Module',
    icon: <ShoppingOutlined />,
    color: '#fa8c16',
    description:
      'Manage material allocations, stock movements, and return tracking for contracts.',
    features: ['Material allocation', 'Stock movement logs', 'Return tracking', 'Low-stock alerts'],
  },
  {
    key: 'vehicle',
    label: 'Vehicle Module',
    icon: <CarOutlined />,
    color: '#722ed1',
    description:
      'Assign fleet vehicles, track mileage and fuel consumption, and schedule maintenance.',
    features: ['Fleet assignment', 'Driver management', 'Mileage tracking', 'Maintenance alerts'],
  },
];

const DEFAULT_GLOBAL_SETTINGS = {
  modules_enabled: {
    employee: true,
    inventory: true,
    vehicle: true,
  },
  default_configs: {
    employee: {
      max_employees: 50,
      require_role_assignment: true,
      track_attendance: true,
      allow_overtime: false,
      salary_calculation: 'monthly',
    },
    inventory: {
      track_movements: true,
      require_return_date: true,
      alert_low_stock: true,
      auto_deduct: false,
    },
    vehicle: {
      track_mileage: true,
      require_driver_assignment: true,
      maintenance_alerts: true,
      fuel_tracking: false,
    },
  },
};

const ModuleSettingsPage = () => {
  const { user } = useAuth();
  const canManage = ['SuperAdmin', 'Admin'].includes(user?.role);

  const [settings, setSettings] = useState(DEFAULT_GLOBAL_SETTINGS);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [isDirty, setIsDirty] = useState(false);
  const [activeModule, setActiveModule] = useState('employee');

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    setLoading(true);
    try {
      const data = await getGlobalModuleSettings();
      setSettings(data || DEFAULT_GLOBAL_SETTINGS);
    } catch {
      // Use defaults if API not available yet
      setSettings(DEFAULT_GLOBAL_SETTINGS);
    } finally {
      setLoading(false);
    }
  };

  const toggleModule = (moduleKey) => {
    setSettings((prev) => ({
      ...prev,
      modules_enabled: {
        ...prev.modules_enabled,
        [moduleKey]: !prev.modules_enabled?.[moduleKey],
      },
    }));
    setIsDirty(true);
  };

  const updateDefaultConfig = (moduleKey, config) => {
    setSettings((prev) => ({
      ...prev,
      default_configs: {
        ...prev.default_configs,
        [moduleKey]: config,
      },
    }));
    setIsDirty(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await updateGlobalModuleSettings(settings);
      toast.success('Global module settings saved successfully');
      setIsDirty(false);
    } catch {
      toast.error('Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="contract-page">
      <Breadcrumb
        items={[{ title: 'Home' }, { title: 'Contracts' }, { title: 'Module Settings' }]}
        style={{ marginBottom: 12 }}
      />

      <div className="page-header">
        <Row justify="space-between" align="middle">
          <Col>
            <div className="page-title">Module Settings</div>
            <div className="page-subtitle">
              Configure system-wide defaults for contract modules
            </div>
          </Col>
          {canManage && (
            <Col>
              <Space>
                <Button icon={<ReloadOutlined />} onClick={loadSettings} loading={loading}>
                  Refresh
                </Button>
                <Button
                  type="primary"
                  icon={<SaveOutlined />}
                  onClick={handleSave}
                  loading={saving}
                  disabled={!isDirty}
                >
                  Save Changes
                </Button>
              </Space>
            </Col>
          )}
        </Row>
      </div>

      {!canManage && (
        <Alert
          type="warning"
          message="You have read-only access. Admin permissions required to modify settings."
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      {isDirty && (
        <Alert
          type="warning"
          message="You have unsaved changes. Click 'Save Changes' to apply."
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      <Spin spinning={loading}>
        <Row gutter={[16, 16]}>
          {/* Module Toggle Cards */}
          {MODULE_DEFS.map((mod) => {
            const isEnabled = settings.modules_enabled?.[mod.key] !== false;
            return (
              <Col key={mod.key} xs={24} md={8}>
                <Card
                  className={`module-toggle-card${isEnabled ? ' enabled' : ''}`}
                  style={{ height: '100%' }}
                >
                  <Space align="start" style={{ width: '100%' }}>
                    <div
                      style={{
                        fontSize: 28,
                        color: isEnabled ? mod.color : '#ccc',
                        lineHeight: 1,
                      }}
                    >
                      {mod.icon}
                    </div>
                    <div style={{ flex: 1 }}>
                      <Row justify="space-between" align="middle">
                        <Col>
                          <Text strong style={{ fontSize: 15 }}>{mod.label}</Text>
                        </Col>
                        <Col>
                          <Switch
                            checked={isEnabled}
                            onChange={() => canManage && toggleModule(mod.key)}
                            disabled={!canManage}
                            checkedChildren="ON"
                            unCheckedChildren="OFF"
                          />
                        </Col>
                      </Row>
                      <Paragraph
                        type="secondary"
                        style={{ fontSize: 12, marginTop: 6, marginBottom: 10 }}
                      >
                        {mod.description}
                      </Paragraph>
                      <Space wrap size={4}>
                        {mod.features.map((f) => (
                          <Tag key={f} style={{ fontSize: 11 }}>{f}</Tag>
                        ))}
                      </Space>
                    </div>
                  </Space>
                </Card>
              </Col>
            );
          })}
        </Row>

        <Divider style={{ margin: '24px 0 20px' }}>Default Module Configurations</Divider>

        <Row gutter={[16, 0]}>
          {/* Module selector */}
          <Col xs={24} md={6}>
            <Card size="small">
              <Space orientation="vertical" style={{ width: '100%' }}>
                {MODULE_DEFS.map((mod) => (
                  <Button
                    key={mod.key}
                    type={activeModule === mod.key ? 'primary' : 'text'}
                    icon={mod.icon}
                    onClick={() => setActiveModule(mod.key)}
                    style={{ width: '100%', textAlign: 'left', justifyContent: 'flex-start' }}
                    disabled={settings.modules_enabled?.[mod.key] === false}
                  >
                    {mod.label.replace(' Module', '')}
                  </Button>
                ))}
              </Space>
            </Card>
          </Col>

          {/* Config editor */}
          <Col xs={24} md={18}>
            <Card
              title={
                <Space>
                  <SettingOutlined />
                  Default Config — {MODULE_DEFS.find((m) => m.key === activeModule)?.label}
                </Space>
              }
              size="small"
            >
              <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 12 }}>
                These defaults are applied when the module is first enabled on a new contract.
                Individual contracts can override these settings.
              </Text>
              <ModuleConfigEditor
                moduleType={activeModule}
                config={settings.default_configs?.[activeModule] || {}}
                onChange={(config) => updateDefaultConfig(activeModule, config)}
                readOnly={!canManage}
              />
            </Card>
          </Col>
        </Row>
      </Spin>
    </div>
  );
};

export default ModuleSettingsPage;
