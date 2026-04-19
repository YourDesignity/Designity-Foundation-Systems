/**
 * ContractFormPage.jsx
 *
 * Create / Edit contract form with tabbed sections:
 * - Basic Info
 * - Module Configuration
 * - Module Settings (per-module JSON config)
 * - Terms & Conditions
 */

import React, { useState, useEffect } from 'react';
import {
  Form, Input, Select, DatePicker, InputNumber, Tabs, Button,
  Space, Typography, Card, Row, Col, Switch, Breadcrumb,
  message, Spin, Divider, Alert,
} from 'antd';
import {
  SaveOutlined, ArrowLeftOutlined, FileTextOutlined,
  SettingOutlined, TeamOutlined, CarOutlined, ShoppingOutlined,
} from '@ant-design/icons';
import { useNavigate, useParams } from 'react-router-dom';
import dayjs from 'dayjs';
import { toast } from 'react-toastify';
import { useAuth } from '../../context/AuthContext';
import ModuleConfigEditor from '../../components/role-contracts/ModuleConfigEditor';
import {
  getContractById, createContract, updateContract,
} from '../../services/contractService';
import { projectService } from '../../services';
import '../../styles/contract-pages.css';
import { CONTRACT_TYPE_OPTIONS, normaliseContractType } from '../../constants/contractTypes';

const { Title, Text } = Typography;
const { TextArea } = Input;
const { RangePicker } = DatePicker;

// CONTRACT_TYPES is imported from constants/contractTypes.js

const WORKFLOW_STATES = [
  'DRAFT', 'PENDING_APPROVAL', 'ACTIVE', 'SUSPENDED', 'COMPLETED', 'CANCELLED',
];

const MODULES = [
  {
    key: 'employee',
    label: 'Employee Module',
    icon: <TeamOutlined />,
    description: 'Track employee assignments, attendance, and payroll',
  },
  {
    key: 'inventory',
    label: 'Inventory Module',
    icon: <ShoppingOutlined />,
    description: 'Manage material allocations and stock movements',
  },
  {
    key: 'vehicle',
    label: 'Vehicle Module',
    icon: <CarOutlined />,
    description: 'Assign vehicles, track mileage and fuel usage',
  },
];

const ContractFormPage = () => {
  const navigate = useNavigate();
  const { id } = useParams();
  const { user } = useAuth();
  const [form] = Form.useForm();
  const isEditing = !!id;

  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [activeTab, setActiveTab] = useState('basic');
  const [enabledModules, setEnabledModules] = useState([]);
  const [moduleConfigs, setModuleConfigs] = useState({});
  const [projects, setProjects] = useState([]);
  const [projectsLoading, setProjectsLoading] = useState(false);

  // Load projects for the project selector
  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    setProjectsLoading(true);
    try {
      const data = await projectService.getAll();
      setProjects(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Failed to load projects:', err);
    } finally {
      setProjectsLoading(false);
    }
  };

  // Load contract data when editing
  useEffect(() => {
    if (isEditing) {
      loadContract();
    }
  }, [id]);

  const loadContract = async () => {
    setLoading(true);
    try {
      const data = await getContractById(id);
      const contract = data?.contract || data;

      form.setFieldsValue({
        contract_code: contract.contract_code,
        contract_name: contract.contract_name,
        client_name: contract.client_name,
        contract_type: normaliseContractType(contract.contract_type),
        contract_value: contract.contract_value,
        payment_terms: contract.payment_terms,
        notes: contract.notes,
        contract_terms: contract.contract_terms,
        project_id: contract.project_id,
        date_range: [
          contract.start_date ? dayjs(contract.start_date) : null,
          contract.end_date ? dayjs(contract.end_date) : null,
        ],
      });

      setEnabledModules(contract.enabled_modules || []);
      setModuleConfigs(contract.module_config || {});
    } catch {
      message.error('Failed to load contract');
    } finally {
      setLoading(false);
    }
  };

  const toggleModule = (moduleKey) => {
    setEnabledModules((prev) =>
      prev.includes(moduleKey)
        ? prev.filter((m) => m !== moduleKey)
        : [...prev, moduleKey]
    );
  };

  const handleModuleConfigChange = (moduleKey, config) => {
    setModuleConfigs((prev) => ({ ...prev, [moduleKey]: config }));
  };

  const handleSubmit = async (saveAsDraft = false) => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);

      const [startDate, endDate] = values.date_range || [];
      const selectedProject = projects.find((p) => p.uid === values.project_id);
      const payload = {
        project_id: values.project_id,
        project_name: selectedProject?.project_name || null,
        contract_code: values.contract_code,
        contract_name: values.contract_name,
        client_name: values.client_name,
        contract_type: values.contract_type || 'DEDICATED_STAFF',
        contract_value: values.contract_value || 0,
        payment_terms: values.payment_terms,
        notes: values.notes,
        contract_terms: values.contract_terms,
        start_date: startDate?.toISOString(),
        end_date: endDate?.toISOString(),
        enabled_modules: enabledModules,
        module_config: moduleConfigs,
        workflow_state: saveAsDraft ? 'DRAFT' : 'DRAFT',
      };

      if (isEditing) {
        await updateContract(id, payload);
        toast.success('Contract updated successfully');
      } else {
        const created = await createContract(payload);
        toast.success('Contract created successfully');
        const newId = created?.uid ?? created?.id;
        if (newId) {
          navigate(`/contracts/${newId}`);
          return;
        }
      }

      navigate('/contracts');
    } catch (err) {
      if (err?.errorFields) {
        setActiveTab('basic');
        return;
      }
      toast.error(isEditing ? 'Failed to update contract' : 'Failed to create contract');
    } finally {
      setSubmitting(false);
    }
  };

  const tabItems = [
    {
      key: 'basic',
      label: (
        <Space>
          <FileTextOutlined />
          Basic Info
        </Space>
      ),
      children: (
        <Row gutter={[16, 0]}>
          <Col xs={24} md={12}>
            <Form.Item
              name="project_id"
              label="Project"
              rules={[{ required: true, message: 'Project is required' }]}
            >
              <Select
                showSearch
                loading={projectsLoading}
                placeholder="Select a project"
                optionFilterProp="label"
                options={projects.map((p) => ({
                  value: p.uid,
                  label: `${p.project_code} — ${p.project_name}`,
                }))}
              />
            </Form.Item>
          </Col>
          <Col xs={24} md={12}>
            <Form.Item
              name="contract_code"
              label="Contract Code"
              rules={[{ required: true, message: 'Contract code is required' }]}
            >
              <Input placeholder="e.g. CNT-2024-001" />
            </Form.Item>
          </Col>
          <Col xs={24} md={12}>
            <Form.Item name="contract_name" label="Contract Name">
              <Input placeholder="Descriptive name for this contract" />
            </Form.Item>
          </Col>
          <Col xs={24} md={12}>
            <Form.Item name="client_name" label="Client Name">
              <Input placeholder="Client or company name" />
            </Form.Item>
          </Col>
          <Col xs={24} md={12}>
            <Form.Item name="contract_type" label="Contract Type">
              <Select
                options={CONTRACT_TYPES.map((t) => ({ value: t, label: t }))}
                placeholder="Select type"
              />
            </Form.Item>
          </Col>
          <Col xs={24} md={12}>
            <Form.Item
              name="date_range"
              label="Contract Period"
              rules={[{ required: true, message: 'Start and end dates are required' }]}
            >
              <RangePicker style={{ width: '100%' }} />
            </Form.Item>
          </Col>
          <Col xs={24} md={12}>
            <Form.Item name="contract_value" label="Contract Value (KD)">
              <InputNumber
                style={{ width: '100%' }}
                min={0}
                precision={2}
                formatter={(v) => v?.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                placeholder="0.00"
              />
            </Form.Item>
          </Col>
          <Col xs={24} md={12}>
            <Form.Item name="payment_terms" label="Payment Terms">
              <Input placeholder="e.g. Net 30, Monthly, Upon completion" />
            </Form.Item>
          </Col>
          <Col xs={24}>
            <Form.Item name="notes" label="Notes">
              <TextArea rows={3} placeholder="Internal notes about this contract…" />
            </Form.Item>
          </Col>
        </Row>
      ),
    },
    {
      key: 'modules',
      label: (
        <Space>
          <SettingOutlined />
          Modules
        </Space>
      ),
      children: (
        <div>
          <Alert
            type="info"
            title="Enable modules to track employees, inventory, and vehicles against this contract."
            style={{ marginBottom: 16 }}
            showIcon
          />
          <Row gutter={[16, 16]}>
            {MODULES.map((mod) => {
              const isEnabled = enabledModules.includes(mod.key);
              return (
                <Col key={mod.key} xs={24} md={8}>
                  <Card
                    className={`module-toggle-card${isEnabled ? ' enabled' : ''}`}
                    onClick={() => toggleModule(mod.key)}
                    hoverable
                  >
                    <Space align="start">
                      <div style={{ fontSize: 24, color: isEnabled ? '#1890ff' : '#ccc' }}>
                        {mod.icon}
                      </div>
                      <div>
                        <div style={{ fontWeight: 600, marginBottom: 4 }}>{mod.label}</div>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {mod.description}
                        </Text>
                      </div>
                    </Space>
                    <div style={{ marginTop: 12 }}>
                      <Switch
                        checked={isEnabled}
                        onChange={(checked, event) => {
                          if (event) event.stopPropagation();
                          toggleModule(mod.key);
                        }}
                      />
                      <Text style={{ marginLeft: 8, fontSize: 12 }}>
                        {isEnabled ? 'Enabled' : 'Disabled'}
                      </Text>
                    </div>
                  </Card>
                </Col>
              );
            })}
          </Row>
        </div>
      ),
    },
    {
      key: 'module-settings',
      label: 'Module Settings',
      disabled: enabledModules.length === 0,
      children: (
        <div>
          {enabledModules.length === 0 ? (
            <Alert
              type="warning"
              title="Enable at least one module in the Modules tab to configure settings."
              showIcon
            />
          ) : (
            <Tabs
              tabPlacement="left"
              items={enabledModules.map((mod) => ({
                key: mod,
                label: mod.charAt(0).toUpperCase() + mod.slice(1),
                children: (
                  <ModuleConfigEditor
                    moduleType={mod}
                    config={moduleConfigs[mod] || {}}
                    onChange={(config) => handleModuleConfigChange(mod, config)}
                  />
                ),
              }))}
            />
          )}
        </div>
      ),
    },
    {
      key: 'terms',
      label: 'Terms & Conditions',
      children: (
        <Form.Item name="contract_terms" label="Contract Terms & Conditions">
          <TextArea
            rows={12}
            placeholder="Enter full terms and conditions for this contract…"
          />
        </Form.Item>
      ),
    },
  ];

  return (
    <div className="contract-page">
      <Breadcrumb
        items={[
          { title: 'Home' },
          { title: <a onClick={() => navigate('/contracts')}>Contracts</a> },
          { title: isEditing ? 'Edit Contract' : 'New Contract' },
        ]}
        style={{ marginBottom: 16 }}
      />

      <div className="page-header">
        <Row justify="space-between" align="middle">
          <Col>
            <Space>
              <Button
                icon={<ArrowLeftOutlined />}
                onClick={() => navigate(isEditing ? `/contracts/${id}` : '/contracts')}
              />
              <div>
                <div className="page-title">
                  {isEditing ? 'Edit Contract' : 'Create New Contract'}
                </div>
                <div className="page-subtitle">
                  {isEditing
                    ? 'Update contract details, modules, and settings'
                    : 'Fill in the details to create a new modular contract'}
                </div>
              </div>
            </Space>
          </Col>
          <Col>
            <Space>
              <Button
                onClick={() => handleSubmit(true)}
                loading={submitting}
              >
                Save as Draft
              </Button>
              <Button
                type="primary"
                icon={<SaveOutlined />}
                onClick={() => handleSubmit(false)}
                loading={submitting}
              >
                {isEditing ? 'Save Changes' : 'Create Contract'}
              </Button>
            </Space>
          </Col>
        </Row>
      </div>

      <Spin spinning={loading}>
        <Card>
          <Form form={form} layout="vertical" className="contract-form-tabs">
            <Tabs
              activeKey={activeTab}
              onChange={setActiveTab}
              items={tabItems}
            />
          </Form>
        </Card>
      </Spin>
    </div>
  );
};

export default ContractFormPage;
