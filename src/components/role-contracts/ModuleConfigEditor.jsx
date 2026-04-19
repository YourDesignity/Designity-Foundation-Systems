/**
 * ModuleConfigEditor.jsx
 *
 * JSON config editor for contract modules.
 * Renders a Monaco-like textarea with validation, preview, and save.
 */

import React, { useState, useEffect } from 'react';
import { Card, Button, Space, Typography, Alert, Input, Tooltip, Tag } from 'antd';
import {
  SaveOutlined, ReloadOutlined, FullscreenOutlined, InfoCircleOutlined,
} from '@ant-design/icons';

const { Text, Paragraph } = Typography;
const { TextArea } = Input;

const MODULE_DEFAULTS = {
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
};

const ModuleConfigEditor = ({
  moduleType,
  config = {},
  onChange,
  onSave,
  readOnly = false,
  loading = false,
}) => {
  const [jsonText, setJsonText] = useState('');
  const [parseError, setParseError] = useState(null);
  const [isDirty, setIsDirty] = useState(false);

  useEffect(() => {
    const value = Object.keys(config).length > 0 ? config : MODULE_DEFAULTS[moduleType] || {};
    setJsonText(JSON.stringify(value, null, 2));
    setIsDirty(false);
    setParseError(null);
  }, [config, moduleType]);

  const handleChange = (e) => {
    const text = e.target.value;
    setJsonText(text);
    setIsDirty(true);
    try {
      const parsed = JSON.parse(text);
      setParseError(null);
      onChange?.(parsed);
    } catch {
      setParseError('Invalid JSON – please fix before saving');
    }
  };

  const handleReset = () => {
    const value = MODULE_DEFAULTS[moduleType] || {};
    setJsonText(JSON.stringify(value, null, 2));
    setIsDirty(true);
    setParseError(null);
    onChange?.(value);
  };

  const handleSave = () => {
    if (parseError) return;
    try {
      const parsed = JSON.parse(jsonText);
      onSave?.(parsed);
      setIsDirty(false);
    } catch {
      setParseError('Cannot save – invalid JSON');
    }
  };

  return (
    <div className="module-config-editor">
      {parseError && (
        <Alert
          type="error"
          message={parseError}
          style={{ marginBottom: 8 }}
          showIcon
        />
      )}

      <TextArea
        value={jsonText}
        onChange={handleChange}
        rows={12}
        readOnly={readOnly}
        style={{
          fontFamily: "'Courier New', Courier, monospace",
          fontSize: 13,
          lineHeight: 1.6,
          background: readOnly ? '#fafafa' : '#fff',
        }}
      />

      {!readOnly && (
        <Space style={{ marginTop: 8 }} wrap>
          <Button
            type="primary"
            icon={<SaveOutlined />}
            onClick={handleSave}
            loading={loading}
            disabled={!!parseError || !isDirty}
            size="small"
          >
            Save Config
          </Button>
          <Tooltip title="Reset to module defaults">
            <Button
              icon={<ReloadOutlined />}
              onClick={handleReset}
              size="small"
            >
              Reset Defaults
            </Button>
          </Tooltip>
          {isDirty && !parseError && (
            <Tag color="warning" style={{ fontSize: 11 }}>Unsaved changes</Tag>
          )}
        </Space>
      )}
    </div>
  );
};

export default ModuleConfigEditor;
