// src/components/manager/SiteSwitcher.jsx

import React from 'react';
import { Select, Space, Tag, Typography } from 'antd';

const { Text } = Typography;
const { Option } = Select;

/**
 * Dropdown selector for managers with multiple sites.
 * Shows site code, name, employee count, and understaffed warnings.
 *
 * @param {number|string} selectedSiteId - Currently selected site UID
 * @param {Array}         sites          - Array of site summary objects from API
 * @param {Function}      onSiteChange   - Called with the new site UID when selection changes
 */
const SiteSwitcher = ({ selectedSiteId, sites = [], onSiteChange }) => {
  if (!sites || sites.length <= 1) return null;

  return (
    <Select
      style={{ width: '100%', maxWidth: 480, marginBottom: 16 }}
      value={selectedSiteId}
      onChange={onSiteChange}
      placeholder="Select a site"
      optionLabelProp="label"
    >
      {sites.map((site) => (
        <Option
          key={site.uid}
          value={site.uid}
          label={`${site.site_code || site.uid} - ${site.name}`}
        >
          <Space direction="vertical" size={0}>
            <Text strong>
              {site.site_code || `Site ${site.uid}`} — {site.name}
            </Text>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {site.active_employees ?? 0}/{site.required_workers ?? 0} workers
              {site.is_understaffed && (
                <Tag color="red" style={{ marginLeft: 8 }}>
                  Understaffed
                </Tag>
              )}
            </Text>
          </Space>
        </Option>
      ))}
    </Select>
  );
};

export default SiteSwitcher;
