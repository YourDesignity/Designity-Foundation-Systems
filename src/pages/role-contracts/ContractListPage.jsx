/**
 * ContractListPage.jsx
 *
 * Displays all modular contracts with filters, search, sorting, and
 * pagination. Supports grid (card) and table views.
 */

import React, { useState, useCallback, useEffect } from 'react';
import {
  Row, Col, Button, Space, Typography, Table, Tag, Tooltip,
  Breadcrumb, Card, Dropdown, Menu, Popconfirm, message, Spin,
  Badge, Switch,
} from 'antd';
import {
  PlusOutlined, EyeOutlined, EditOutlined, DeleteOutlined,
  CopyOutlined, TableOutlined, AppstoreOutlined, ReloadOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import ContractFilters from '../../components/role-contracts/ContractFilters';
import ContractCard from '../../components/role-contracts/ContractCard';
import { WorkflowStateBadge, ModuleBadges } from '../../components/role-contracts/WorkflowStatus';
import {
  getContracts, deleteContract, cloneContract,
} from '../../services/contractService';
import '../../styles/contract-pages.css';

const { Title, Text } = Typography;

const DEFAULT_FILTERS = {
  search: '',
  status: '',
  contract_type: '',
  module: '',
  start_date: '',
  end_date: '',
};

const formatDate = (dt) => {
  if (!dt) return '—';
  try {
    return new Date(dt).toLocaleDateString('en-KW', { day: '2-digit', month: 'short', year: 'numeric' });
  } catch {
    return dt;
  }
};

const formatCurrency = (amount) =>
  typeof amount === 'number'
    ? `KD ${amount.toLocaleString('en-KW', { minimumFractionDigits: 2 })}`
    : '—';

const ContractListPage = () => {
  const navigate = useNavigate();
  const { user } = useAuth();

  const [contracts, setContracts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 20, total: 0 });
  const [viewMode, setViewMode] = useState('table'); // 'table' | 'grid'

  const canManage = ['SuperAdmin', 'Admin'].includes(user?.role);

  const fetchContracts = useCallback(async (page = 1) => {
    setLoading(true);
    try {
      const params = {
        ...filters,
        page,
        page_size: pagination.pageSize,
      };
      // Remove empty params
      Object.keys(params).forEach((k) => { if (!params[k]) delete params[k]; });

      const data = await getContracts(params);
      const list = Array.isArray(data) ? data : data?.contracts || data?.items || [];
      const total = data?.total ?? list.length;

      setContracts(list);
      setPagination((prev) => ({ ...prev, current: page, total }));
    } catch {
      message.error('Failed to load contracts');
    } finally {
      setLoading(false);
    }
  }, [filters, pagination.pageSize]);

  useEffect(() => {
    fetchContracts(1);
  }, [filters]);

  const handleDelete = async (uid) => {
    try {
      await deleteContract(uid);
      message.success('Contract deleted');
      fetchContracts(pagination.current);
    } catch {
      message.error('Failed to delete contract');
    }
  };

  const handleClone = async (uid) => {
    try {
      const cloned = await cloneContract(uid);
      message.success('Contract cloned successfully');
      fetchContracts(1);
    } catch {
      message.error('Failed to clone contract');
    }
  };

  const handleFiltersChange = (newFilters) => {
    setFilters(newFilters);
  };

  const handleFiltersReset = () => {
    setFilters(DEFAULT_FILTERS);
  };

  const columns = [
    {
      title: 'Code',
      dataIndex: 'contract_code',
      key: 'contract_code',
      width: 130,
      render: (code, record) => (
        <Button
          type="link"
          style={{ padding: 0, fontFamily: 'monospace', fontSize: 12 }}
          onClick={() => navigate(`/contracts/${record.uid}`)}
        >
          {code}
        </Button>
      ),
    },
    {
      title: 'Name',
      dataIndex: 'contract_name',
      key: 'contract_name',
      ellipsis: true,
      render: (name, record) => (
        <Text style={{ fontSize: 13 }}>{name || record.contract_code}</Text>
      ),
    },
    {
      title: 'Client',
      dataIndex: 'client_name',
      key: 'client_name',
      ellipsis: true,
      width: 140,
      render: (v) => <Text style={{ fontSize: 13 }}>{v || '—'}</Text>,
    },
    {
      title: 'Type',
      dataIndex: 'contract_type',
      key: 'contract_type',
      width: 120,
      render: (v) => <Tag style={{ fontSize: 11 }}>{v}</Tag>,
    },
    {
      title: 'Status',
      dataIndex: 'workflow_state',
      key: 'workflow_state',
      width: 140,
      render: (state) => <WorkflowStateBadge state={state} />,
    },
    {
      title: 'Start',
      dataIndex: 'start_date',
      key: 'start_date',
      width: 100,
      render: (v) => <Text style={{ fontSize: 12 }}>{formatDate(v)}</Text>,
    },
    {
      title: 'End',
      dataIndex: 'end_date',
      key: 'end_date',
      width: 100,
      render: (v) => <Text style={{ fontSize: 12 }}>{formatDate(v)}</Text>,
    },
    {
      title: 'Value',
      dataIndex: 'contract_value',
      key: 'contract_value',
      width: 110,
      align: 'right',
      render: (v) => <Text style={{ fontSize: 12 }}>{formatCurrency(v)}</Text>,
    },
    {
      title: 'Modules',
      dataIndex: 'enabled_modules',
      key: 'enabled_modules',
      width: 160,
      render: (modules) => <ModuleBadges modules={modules || []} />,
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 130,
      fixed: 'right',
      render: (_, record) => (
        <Space size={4}>
          <Tooltip title="View Details">
            <Button
              type="text"
              icon={<EyeOutlined />}
              size="small"
              onClick={() => navigate(`/contracts/${record.uid}`)}
            />
          </Tooltip>
          {canManage && (
            <>
              <Tooltip title="Edit">
                <Button
                  type="text"
                  icon={<EditOutlined />}
                  size="small"
                  onClick={() => navigate(`/contracts/${record.uid}/edit`)}
                />
              </Tooltip>
              <Tooltip title="Clone">
                <Button
                  type="text"
                  icon={<CopyOutlined />}
                  size="small"
                  onClick={() => handleClone(record.uid)}
                />
              </Tooltip>
              <Tooltip title="Delete">
                <Popconfirm
                  title="Delete this contract?"
                  description="This action cannot be undone."
                  onConfirm={() => handleDelete(record.uid)}
                  okType="danger"
                  okText="Delete"
                >
                  <Button type="text" icon={<DeleteOutlined />} size="small" danger />
                </Popconfirm>
              </Tooltip>
            </>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div className="contract-page">
      {/* Header */}
      <div className="page-header">
        <Breadcrumb
          items={[{ title: 'Home' }, { title: 'Contracts' }]}
          style={{ marginBottom: 8 }}
        />
        <Row justify="space-between" align="middle">
          <Col>
            <div className="page-title">Contracts</div>
            <div className="page-subtitle">Manage modular contract workflow system</div>
          </Col>
          <Col>
            <Space>
              <Button
                icon={viewMode === 'table' ? <AppstoreOutlined /> : <TableOutlined />}
                onClick={() => setViewMode((v) => (v === 'table' ? 'grid' : 'table'))}
              >
                {viewMode === 'table' ? 'Grid View' : 'Table View'}
              </Button>
              <Button
                icon={<ReloadOutlined />}
                onClick={() => fetchContracts(pagination.current)}
                loading={loading}
              />
              {canManage && (
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={() => navigate('/contracts/new')}
                >
                  New Contract
                </Button>
              )}
            </Space>
          </Col>
        </Row>
      </div>

      {/* Filters */}
      <ContractFilters
        filters={filters}
        onChange={handleFiltersChange}
        onReset={handleFiltersReset}
        loading={loading}
      />

      {/* Stats */}
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }} className="contract-stats-row">
        {[
          { label: 'Total', value: pagination.total, color: '#1890ff' },
          {
            label: 'Active',
            value: contracts.filter((c) => c.workflow_state === 'ACTIVE').length,
            color: '#52c41a',
          },
          {
            label: 'Pending Approval',
            value: contracts.filter((c) => c.workflow_state === 'PENDING_APPROVAL').length,
            color: '#fa8c16',
          },
          {
            label: 'Expiring Soon',
            value: contracts.filter((c) => c.is_expiring_soon).length,
            color: '#ff4d4f',
          },
        ].map(({ label, value, color }) => (
          <Col key={label} xs={12} sm={6}>
            <Card size="small" className="stat-card">
              <Text style={{ fontSize: 12, color: '#888' }}>{label}</Text>
              <div style={{ fontSize: 22, fontWeight: 700, color }}>{value}</div>
            </Card>
          </Col>
        ))}
      </Row>

      {/* Content */}
      {viewMode === 'table' ? (
        <Card bodyStyle={{ padding: 0 }}>
          <Table
            dataSource={contracts}
            columns={columns}
            rowKey={(r) => r.uid ?? r.contract_code}
            loading={loading}
            pagination={{
              ...pagination,
              showSizeChanger: true,
              pageSizeOptions: ['10', '20', '50'],
              showTotal: (total) => `${total} contracts`,
              onChange: (page, pageSize) => {
                setPagination((p) => ({ ...p, pageSize }));
                fetchContracts(page);
              },
            }}
            scroll={{ x: 1200 }}
            size="middle"
          />
        </Card>
      ) : (
        <Spin spinning={loading}>
          <Row gutter={[16, 16]}>
            {contracts.map((contract) => (
              <Col key={contract.uid} xs={24} sm={12} md={8} lg={6}>
                <ContractCard contract={contract} />
              </Col>
            ))}
            {!loading && contracts.length === 0 && (
              <Col span={24} style={{ textAlign: 'center', padding: '48px 0' }}>
                <Text type="secondary">No contracts found for the current filters.</Text>
              </Col>
            )}
          </Row>
        </Spin>
      )}
    </div>
  );
};

export default ContractListPage;
