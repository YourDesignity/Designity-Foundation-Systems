import React from 'react';
import { Select, Input, DatePicker, Row, Col } from 'antd';
import { CONTRACT_TYPE_OPTIONS } from '../../constants/contractTypes';

const { Option } = Select;

const ContractFilters = ({ filters, onChange }) => {
  const handleChange = (field) => (value) => {
    onChange({ ...filters, [field]: value });
  };

  return (
    <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
      <Col xs={24} sm={12} md={6}>
        <Select
          allowClear
          placeholder="Filter by type"
          style={{ width: '100%' }}
          value={filters.contract_type || undefined}
          onChange={handleChange('contract_type')}
        >
          {CONTRACT_TYPE_OPTIONS.map(opt => (
            <Option key={opt.value} value={opt.value}>{opt.label}</Option>
          ))}
        </Select>
      </Col>
      <Col xs={24} sm={12} md={6}>
        <Select
          allowClear
          placeholder="Filter by status"
          style={{ width: '100%' }}
          value={filters.status || undefined}
          onChange={handleChange('status')}
        >
          {['Active', 'Expired', 'Completed', 'Terminated', 'On Hold'].map(s => (
            <Option key={s} value={s}>{s}</Option>
          ))}
        </Select>
      </Col>
      <Col xs={24} sm={12} md={8}>
        <Input
          placeholder="Search by name or code..."
          value={filters.search || ''}
          onChange={(e) => handleChange('search')(e.target.value)}
          allowClear
        />
      </Col>
    </Row>
  );
};

export default ContractFilters;
