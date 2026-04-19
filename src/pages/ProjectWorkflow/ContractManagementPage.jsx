import React, { useState, useEffect, useCallback } from 'react';
import {
  Card, Table, Tag, Button, Space, Empty, message,
  Breadcrumb, Statistic, Row, Col, Popconfirm,
} from 'antd';
import {
  PlusOutlined, ArrowLeftOutlined, FileTextOutlined,
  DeleteOutlined, EnvironmentOutlined,
} from '@ant-design/icons';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { fetchWithAuth } from '../../services/apiService';
import CreateContractModal from '../../components/ProjectWorkflow/CreateContractModal';

const ContractManagementPage = () => {
  const { projectId } = useParams();
  const navigate = useNavigate();

  const [project, setProject] = useState(null);
  const [contracts, setContracts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [createModalVisible, setCreateModalVisible] = useState(false);

  const fetchProjectAndContracts = useCallback(async () => {
    setLoading(true);
    try {
      const [projectData, contractsData] = await Promise.all([
        fetchWithAuth(`/projects/${projectId}`),
        fetchWithAuth(`/workflow/contracts/?project_id=${projectId}`),
      ]);
      setProject(projectData?.project || projectData);
      setContracts(Array.isArray(contractsData) ? contractsData : []);
    } catch (error) {
      console.error('Error fetching data:', error);
      message.error('Error loading project data');
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    if (projectId) {
      fetchProjectAndContracts();
    }
  }, [projectId, fetchProjectAndContracts]);

  const handleDeleteContract = async (contractId) => {
    try {
      await fetchWithAuth(`/workflow/contracts/${contractId}`, { method: 'DELETE' });
      message.success('Contract deleted successfully');
      fetchProjectAndContracts();
    } catch (error) {
      message.error(error.message || 'Error deleting contract');
    }
  };

  const getStatusColor = (status) => {
    const colors = {
      Active: 'green',
      Completed: 'blue',
      'On Hold': 'orange',
      Cancelled: 'red',
      Expired: 'red',
    };
    return colors[status] || 'default';
  };

  const columns = [
    {
      title: 'Contract Code',
      dataIndex: 'contract_code',
      key: 'contract_code',
      render: (text) => <strong>{text}</strong>,
    },
    {
      title: 'Contract Name',
      dataIndex: 'contract_name',
      key: 'contract_name',
      render: (text) => text || '—',
    },
    {
      title: 'Start Date',
      dataIndex: 'start_date',
      key: 'start_date',
    },
    {
      title: 'End Date',
      dataIndex: 'end_date',
      key: 'end_date',
    },
    {
      title: 'Value (KD)',
      dataIndex: 'contract_value',
      key: 'contract_value',
      render: (value) => (value != null ? Number(value).toLocaleString() : '—'),
    },
    {
      title: 'Days Remaining',
      dataIndex: 'days_remaining',
      key: 'days_remaining',
      render: (days, record) => (
        <span style={{ color: record.is_expiring_soon ? 'red' : 'inherit' }}>
          {days != null ? days : '—'} {record.is_expiring_soon && '⚠️'}
        </span>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status) => <Tag color={getStatusColor(status)}>{status}</Tag>,
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            onClick={() => navigate(`/project-workflow/contracts/${record.uid}/details`)}
          >
            Details
          </Button>
          <Button
            type="link"
            icon={<EnvironmentOutlined />}
            onClick={() => navigate(`/project-workflow/${projectId}/sites?contract=${record.uid}`)}
          >
            Sites
          </Button>
          <Popconfirm
            title="Delete this contract?"
            description="This will only work if no active sites exist."
            onConfirm={() => handleDeleteContract(record.uid)}
            okText="Delete"
            okButtonProps={{ danger: true }}
          >
            <Button type="link" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const totalValue = contracts.reduce((sum, c) => sum + (c.contract_value || 0), 0);
  const activeContracts = contracts.filter((c) => c.status === 'Active').length;

  return (
    <div style={{ padding: 24, background: '#f0f2f5', minHeight: 'calc(100vh - 64px)' }}>
      <Breadcrumb
        style={{ marginBottom: 16 }}
        items={[
          { title: <Link to="/project-workflow">Projects</Link> },
          { title: project?.project_code || `Project ${projectId}` },
          { title: 'Contracts' },
        ]}
      />

      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          background: 'white',
          padding: '16px 24px',
          borderRadius: 8,
          marginBottom: 24,
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <Button
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate('/project-workflow')}
          />
          <div>
            <h2 style={{ margin: 0, color: '#1890ff' }}>
              <FileTextOutlined /> Contract Management
            </h2>
            <p style={{ margin: 0, color: '#666' }}>
              {project?.project_name} ({project?.project_code})
            </p>
          </div>
        </div>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => setCreateModalVisible(true)}
        >
          Add Contract
        </Button>
      </div>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="Total Contracts"
              value={contracts.length}
              prefix={<FileTextOutlined />}
              styles={{ content: { color: '#1890ff' } }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="Active Contracts"
              value={activeContracts}
              styles={{ content: { color: '#52c41a' } }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="Total Value (KD)"
              value={totalValue.toLocaleString()}
              styles={{ content: { color: '#722ed1' } }}
            />
          </Card>
        </Col>
      </Row>

      <Card>
        <Table
          columns={columns}
          dataSource={contracts}
          loading={loading}
          rowKey="uid"
          pagination={{ pageSize: 10 }}
          locale={{
            emptyText: (
              <Empty description="No contracts yet">
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={() => setCreateModalVisible(true)}
                >
                  Add First Contract
                </Button>
              </Empty>
            ),
          }}
        />
      </Card>

      <CreateContractModal
        visible={createModalVisible}
        projectId={Number(projectId)}
        onCancel={() => setCreateModalVisible(false)}
        onSuccess={() => {
          setCreateModalVisible(false);
          fetchProjectAndContracts();
        }}
      />
    </div>
  );
};

export default ContractManagementPage;
