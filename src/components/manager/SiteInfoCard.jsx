// src/components/manager/SiteInfoCard.jsx

import React from 'react';
import { Card, Col, Row, Statistic, Typography } from 'antd';

const { Text } = Typography;

/**
 * Displays key information about a site: code, name, worker counts, and managers.
 *
 * @param {Object} site - Site summary object from API
 */
const SiteInfoCard = ({ site }) => {
  if (!site) return null;

  const activeEmployees = site.active_employees ?? site.assigned_workers ?? 0;
  const required = site.required_workers ?? 0;
  const isUnderstaffed = required > 0 && activeEmployees < required;

  // Support both multi-manager list and legacy single-manager field
  const managerNames =
    Array.isArray(site.assigned_manager_names) && site.assigned_manager_names.length > 0
      ? site.assigned_manager_names.join(', ')
      : site.assigned_manager_name || '—';

  return (
    <Card style={{ marginBottom: 16 }}>
      <Row gutter={16}>
        <Col xs={24} sm={8}>
          <Statistic title="Site Code" value={site.site_code || `Site ${site.uid}`} />
          <Text type="secondary">{site.name}</Text>
        </Col>
        <Col xs={24} sm={8}>
          <Statistic
            title="Workers"
            value={`${activeEmployees}/${required}`}
            valueStyle={{ color: isUnderstaffed ? '#cf1322' : '#3f8600' }}
          />
          {isUnderstaffed && (
            <Text type="danger" style={{ fontSize: 12 }}>
              {required - activeEmployees} worker(s) short
            </Text>
          )}
        </Col>
        <Col xs={24} sm={8}>
          <Statistic
            title={site.assigned_manager_ids?.length > 1 ? 'Managers' : 'Manager'}
            value={managerNames}
            valueStyle={{ fontSize: 14 }}
          />
        </Col>
      </Row>
    </Card>
  );
};

export default SiteInfoCard;
