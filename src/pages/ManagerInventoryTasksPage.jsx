/**
 * ManagerInventoryTasksPage.jsx
 *
 * Manager-facing page for handling inventory/material tasks assigned
 * to their contracts — similar to how managers handle employee attendance.
 *
 * Managers can:
 * 1. View materials assigned to their contracts
 * 2. Record material usage (OUT movements) for their contract
 * 3. View material usage history
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Card, Row, Col, Table, Button, Select, InputNumber, Input, Space, Tag,
  Typography, Modal, Form, message, Spin, Empty, Divider, Statistic,
  Descriptions, Tabs, Badge,
} from 'antd';
import {
  ReloadOutlined, PlusOutlined, HistoryOutlined, BoxPlotOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import apiClient from '../services/base/apiClient';
import { useAuth } from '../context/AuthContext';
import { managerSiteService } from '../services';
import SiteSwitcher from '../components/manager/SiteSwitcher';
import SiteInfoCard from '../components/manager/SiteInfoCard';

const { Title, Text } = Typography;
const { Option } = Select;
const { TextArea } = Input;

// ─── Helpers ─────────────────────────────────────────────────────────────────

const formatDateTime = (dt) => {
  if (!dt) return '—';
  try {
    return new Date(dt).toLocaleString('en-KW', { dateStyle: 'medium', timeStyle: 'short' });
  } catch {
    return dt;
  }
};

// ─── Record Usage Modal ───────────────────────────────────────────────────────

const RecordUsageModal = ({ open, contract, materials, onClose, onSuccess }) => {
  const [form] = Form.useForm();
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);

      await apiClient.post('/materials/use-on-contract', {
        material_id: values.material_id,
        quantity: values.quantity,
        contract_id: contract?.uid,
        contract_code: contract?.contract_code,
        notes: values.notes,
      });

      message.success('Material usage recorded successfully');
      form.resetFields();
      onSuccess?.();
      onClose?.();
    } catch (err) {
      if (err.errorFields) return; // form validation
      message.error(err?.response?.data?.detail || 'Failed to record usage');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal
      open={open}
      onCancel={onClose}
      title={<Space><BoxPlotOutlined /> Record Material Usage</Space>}
      footer={[
        <Button key="cancel" onClick={onClose}>Cancel</Button>,
        <Button key="submit" type="primary" loading={submitting} onClick={handleSubmit}>
          Record Usage
        </Button>,
      ]}
    >
      {contract && (
        <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
          Contract: <strong>{contract.contract_code}</strong> – {contract.contract_name}
        </Text>
      )}
      <Form form={form} layout="vertical">
        <Form.Item
          name="material_id"
          label="Material"
          rules={[{ required: true, message: 'Please select a material' }]}
        >
          <Select placeholder="Select material" showSearch optionFilterProp="children">
            {materials.map((m) => (
              <Option key={m.uid} value={m.uid}>
                {m.name} ({m.unit_of_measure}) — Stock: {m.current_stock}
              </Option>
            ))}
          </Select>
        </Form.Item>

        <Form.Item
          name="quantity"
          label="Quantity Used"
          rules={[{ required: true, message: 'Please enter quantity' }]}
        >
          <InputNumber min={0.01} step={0.5} style={{ width: '100%' }} placeholder="e.g. 5.0" />
        </Form.Item>

        <Form.Item name="notes" label="Notes">
          <TextArea rows={2} placeholder="Optional: describe the usage context" />
        </Form.Item>
      </Form>
    </Modal>
  );
};

// ─── Usage History Table ──────────────────────────────────────────────────────

const UsageHistoryTable = ({ contractId, loading }) => {
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  useEffect(() => {
    if (!contractId) return;
    const fetchHistory = async () => {
      setHistoryLoading(true);
      try {
        const data = await apiClient.get(`/materials/contract/${contractId}/usage`);
        setHistory(Array.isArray(data) ? data : []);
      } catch {
        setHistory([]);
      } finally {
        setHistoryLoading(false);
      }
    };
    fetchHistory();
  }, [contractId]);

  const columns = [
    {
      title: 'Date',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (v) => <Text style={{ fontSize: 12 }}>{formatDateTime(v)}</Text>,
    },
    {
      title: 'Material',
      dataIndex: 'material_name',
      key: 'material_name',
    },
    {
      title: 'Type',
      dataIndex: 'movement_type',
      key: 'movement_type',
      render: (v) => <Tag color={v === 'OUT' ? 'red' : 'green'}>{v}</Tag>,
    },
    {
      title: 'Quantity',
      dataIndex: 'quantity',
      key: 'quantity',
    },
    {
      title: 'Notes',
      dataIndex: 'notes',
      key: 'notes',
      ellipsis: true,
    },
  ];

  return (
    <Table
      rowKey={(r) => r.uid || r.created_at}
      dataSource={history}
      columns={columns}
      loading={historyLoading}
      size="small"
      pagination={{ pageSize: 10, showSizeChanger: false }}
      locale={{ emptyText: <Empty description="No material usage recorded yet" /> }}
    />
  );
};

// ─── Main Page ────────────────────────────────────────────────────────────────

const ManagerInventoryTasksPage = () => {
  const { user } = useAuth();
  const managerId = user?.id;

  const [sites, setSites] = useState([]);
  const [selectedSiteId, setSelectedSiteId] = useState(null);
  const [selectedSite, setSelectedSite] = useState(null);

  const [contracts, setContracts] = useState([]);
  const [selectedContractId, setSelectedContractId] = useState(null);
  const [selectedContract, setSelectedContract] = useState(null);

  const [materials, setMaterials] = useState([]);
  const [contractMaterials, setContractMaterials] = useState([]);

  const [loadingSites, setLoadingSites] = useState(false);
  const [loadingContracts, setLoadingContracts] = useState(false);
  const [loadingMaterials, setLoadingMaterials] = useState(false);

  const [usageModalOpen, setUsageModalOpen] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  // Load manager's sites
  useEffect(() => {
    if (!managerId) return;
    const fetchSites = async () => {
      setLoadingSites(true);
      try {
        const data = await managerSiteService.getManagerSites(managerId);
        const siteList = data?.sites ?? [];
        setSites(siteList);
        if (siteList.length > 0 && !selectedSiteId) {
          setSelectedSiteId(siteList[0].uid);
          setSelectedSite(siteList[0]);
        }
      } catch (err) {
        console.error('Failed to load sites:', err);
      } finally {
        setLoadingSites(false);
      }
    };
    fetchSites();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [managerId]);

  // Load contracts with inventory module enabled
  useEffect(() => {
    const fetchContracts = async () => {
      setLoadingContracts(true);
      try {
        const res = await apiClient.get('/api/contracts/', { params: { module: 'inventory', page_size: 100 } });
        const list = res?.items ?? [];
        setContracts(list);
        if (list.length > 0 && !selectedContractId) {
          setSelectedContractId(list[0].uid);
          setSelectedContract(list[0]);
        }
      } catch {
        setContracts([]);
      } finally {
        setLoadingContracts(false);
      }
    };
    fetchContracts();
  }, []);

  // Load all materials
  useEffect(() => {
    const fetchMaterials = async () => {
      setLoadingMaterials(true);
      try {
        const data = await apiClient.get('/materials/');
        setMaterials(Array.isArray(data) ? data : []);
      } catch {
        setMaterials([]);
      } finally {
        setLoadingMaterials(false);
      }
    };
    fetchMaterials();
  }, []);

  const handleContractChange = useCallback((contractId) => {
    setSelectedContractId(contractId);
    setSelectedContract(contracts.find((c) => c.uid === contractId) || null);
  }, [contracts]);

  const handleRecordSuccess = useCallback(() => {
    setRefreshKey((k) => k + 1);
  }, []);

  return (
    <div style={{ padding: '24px' }}>
      <Row justify="space-between" align="middle" style={{ marginBottom: 20 }}>
        <Col>
          <Title level={3} style={{ margin: 0 }}>
            <BoxPlotOutlined /> Inventory Tasks
          </Title>
          <Text type="secondary">Record and track material usage for your contracts</Text>
        </Col>
        <Col>
          <Button
            icon={<ReloadOutlined />}
            onClick={() => setRefreshKey((k) => k + 1)}
          >
            Refresh
          </Button>
        </Col>
      </Row>

      {sites.length > 1 && (
        <div style={{ marginBottom: 16 }}>
          <SiteSwitcher
            sites={sites}
            selectedSiteId={selectedSiteId}
            onSiteChange={(id) => {
              setSelectedSiteId(id);
              setSelectedSite(sites.find((s) => s.uid === id) || null);
            }}
          />
        </div>
      )}

      {selectedSite && (
        <div style={{ marginBottom: 16 }}>
          <SiteInfoCard site={selectedSite} />
        </div>
      )}

      <Row gutter={[16, 16]}>
        {/* Contract Selector */}
        <Col span={24}>
          <Card size="small" title="Select Contract">
            <Space>
              <Text>Contract with Inventory Module:</Text>
              <Select
                style={{ width: 320 }}
                placeholder="Select a contract"
                value={selectedContractId}
                onChange={handleContractChange}
                loading={loadingContracts}
                showSearch
                optionFilterProp="children"
              >
                {contracts.map((c) => (
                  <Option key={c.uid} value={c.uid}>
                    {c.contract_code} – {c.contract_name || 'Unnamed'}
                  </Option>
                ))}
              </Select>
              {selectedContract && (
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={() => setUsageModalOpen(true)}
                  disabled={loadingMaterials}
                >
                  Record Material Usage
                </Button>
              )}
            </Space>
          </Card>
        </Col>

        {/* Materials Available */}
        <Col span={24}>
          <Card
            size="small"
            title={<Space><BoxPlotOutlined /> Available Materials</Space>}
          >
            <Table
              rowKey="uid"
              dataSource={materials}
              loading={loadingMaterials}
              size="small"
              pagination={{ pageSize: 8, showSizeChanger: false }}
              columns={[
                { title: 'Name', dataIndex: 'name', key: 'name' },
                { title: 'Category', dataIndex: 'category', key: 'category' },
                {
                  title: 'Current Stock',
                  dataIndex: 'current_stock',
                  key: 'current_stock',
                  render: (v, row) => (
                    <Tag color={v <= (row.minimum_stock || 0) ? 'red' : 'green'}>
                      {v} {row.unit_of_measure}
                    </Tag>
                  ),
                },
                {
                  title: 'Min Stock',
                  dataIndex: 'minimum_stock',
                  key: 'minimum_stock',
                  render: (v, row) => `${v} ${row.unit_of_measure}`,
                },
                {
                  title: 'Status',
                  key: 'status',
                  render: (_, row) => {
                    const isLow = row.current_stock <= (row.minimum_stock || 0);
                    return <Tag color={isLow ? 'error' : 'success'}>{isLow ? 'Low Stock' : 'Adequate'}</Tag>;
                  },
                },
              ]}
              locale={{ emptyText: <Empty description="No materials found" /> }}
            />
          </Card>
        </Col>

        {/* Usage History */}
        {selectedContract && (
          <Col span={24}>
            <Card
              size="small"
              title={
                <Space>
                  <HistoryOutlined />
                  Material Usage History — {selectedContract.contract_code}
                </Space>
              }
            >
              <UsageHistoryTable
                contractId={selectedContractId}
                key={refreshKey}
              />
            </Card>
          </Col>
        )}
      </Row>

      <RecordUsageModal
        open={usageModalOpen}
        contract={selectedContract}
        materials={materials}
        onClose={() => setUsageModalOpen(false)}
        onSuccess={handleRecordSuccess}
      />
    </div>
  );
};

export default ManagerInventoryTasksPage;
