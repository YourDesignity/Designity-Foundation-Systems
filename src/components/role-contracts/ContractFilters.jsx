/**
 * ContractFilters.jsx
 *
 * Filter bar for the contract list.  Provides status, type, module, and
 * search controls and calls back with the current filter state on change.
 */

import React from 'react';
import { Row, Col, Input, Select, DatePicker, Button, Space } from 'antd';
import { SearchOutlined, FilterOutlined, ReloadOutlined } from '@ant-design/icons';

const { RangePicker } = DatePicker;
const { Option } = Select;

const STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'DRAFT', label: 'Draft' },
  { value: 'PENDING_APPROVAL', label: 'Pending Approval' },
  { value: 'ACTIVE', label: 'Active' },
  { value: 'SUSPENDED', label: 'Suspended' },
  { value: 'COMPLETED', label: 'Completed' },
  { value: 'CANCELLED', label: 'Cancelled' },
];

const TYPE_OPTIONS = [
  { value: '', label: 'All Types' },
  { value: 'Labour', label: 'Labour' },
  { value: 'Goods Supply', label: 'Goods Supply' },
  { value: 'Equipment Rental', label: 'Equipment Rental' },
  { value: 'Role-Based', label: 'Role-Based' },
  { value: 'Hybrid', label: 'Hybrid' },
];

const MODULE_OPTIONS = [
  { value: '', label: 'All Modules' },
  { value: 'employee', label: 'Employee' },
  { value: 'inventory', label: 'Inventory' },
  { value: 'vehicle', label: 'Vehicle' },
];

const ContractFilters = ({ filters = {}, onChange, onReset, loading = false }) => {
  const handleChange = (field) => (value) => {
    onChange?.({ ...filters, [field]: value });
  };

  const handleSearch = (e) => {
    onChange?.({ ...filters, search: e.target.value });
  };

  const handleDateRange = (dates) => {
    onChange?.({
      ...filters,
      start_date: dates?.[0]?.toISOString() || '',
      end_date: dates?.[1]?.toISOString() || '',
    });
  };

  return (
    <div className="contract-filters">
      <Row gutter={[12, 12]} align="middle">
        <Col xs={24} sm={24} md={8} lg={7}>
          <Input
            prefix={<SearchOutlined />}
            placeholder="Search by code or name…"
            value={filters.search || ''}
            onChange={handleSearch}
            allowClear
          />
        </Col>

        <Col xs={12} sm={8} md={4} lg={4}>
          <Select
            style={{ width: '100%' }}
            value={filters.status || ''}
            onChange={handleChange('status')}
            options={STATUS_OPTIONS}
          />
        </Col>

        <Col xs={12} sm={8} md={4} lg={3}>
          <Select
            style={{ width: '100%' }}
            value={filters.contract_type || ''}
            onChange={handleChange('contract_type')}
            options={TYPE_OPTIONS}
          />
        </Col>

        <Col xs={12} sm={8} md={4} lg={3}>
          <Select
            style={{ width: '100%' }}
            value={filters.module || ''}
            onChange={handleChange('module')}
            options={MODULE_OPTIONS}
          />
        </Col>

        <Col xs={24} sm={16} md={8} lg={5}>
          <RangePicker
            style={{ width: '100%' }}
            placeholder={['Start date', 'End date']}
            onChange={handleDateRange}
          />
        </Col>

        <Col xs={24} sm={8} md={24} lg={2}>
          <Button
            icon={<ReloadOutlined />}
            onClick={onReset}
            loading={loading}
            style={{ width: '100%' }}
          >
            Reset
          </Button>
        </Col>
      </Row>
    </div>
  );
};

export default ContractFilters;
