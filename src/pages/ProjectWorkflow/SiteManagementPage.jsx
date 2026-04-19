import React, { useState, useEffect, useCallback } from 'react';
import {
  Card, Table, Tag, Button, Space, Empty, message,
  Breadcrumb, Statistic, Row, Col, Popconfirm, Tooltip,
} from 'antd';
import {
  PlusOutlined, ArrowLeftOutlined, EnvironmentOutlined,
  DeleteOutlined, UserAddOutlined, UserDeleteOutlined, TeamOutlined,
} from '@ant-design/icons';
import { useParams, useNavigate, useSearchParams, Link } from 'react-router-dom';
import { fetchWithAuth } from '../../services/apiService';
import CreateSiteModal from '../../components/ProjectWorkflow/CreateSiteModal';
import AssignManagerModal from '../../components/ProjectWorkflow/AssignManagerModal';
import AssignEmployeeModal from '../../components/ProjectWorkflow/AssignEmployeeModal';

const SiteManagementPage = () => {
  const { projectId } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const [project, setProject] = useState(null);
  const [contracts, setContracts] = useState([]);
  const [sites, setSites] = useState([]);
  const [loading, setLoading] = useState(false);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [assignManagerModal, setAssignManagerModal] = useState({ visible: false, site: null });
  const [assignEmployeeModal, setAssignEmployeeModal] = useState({ visible: false, site: null });

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [projectData, contractsData, sitesData] = await Promise.all([
        fetchWithAuth(`/projects/${projectId}`),
        fetchWithAuth(`/workflow/contracts/?project_id=${projectId}`),
        fetchWithAuth(`/workflow/sites/?project_id=${projectId}`),
      ]);
      setProject(projectData?.project || projectData);
      setContracts(Array.isArray(contractsData) ? contractsData : []);
      setSites(Array.isArray(sitesData) ? sitesData : []);
    } catch (error) {
      console.error('Error fetching data:', error);
      message.error('Error loading site data');
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    if (projectId) {
      fetchData();
    }
  }, [projectId, fetchData]);

  const handleDeleteSite = async (siteId) => {
    try {
      await fetchWithAuth(`/workflow/sites/${siteId}`, { method: 'DELETE' });
      message.success('Site deleted successfully');
      fetchData();
    } catch (error) {
      message.error(error.message || 'Error deleting site');
    }
  };

  const handleManagerAssigned = () => {
    setAssignManagerModal({ visible: false, site: null });
    fetchData();
  };

  const handleEmployeeAssigned = () => {
    setAssignEmployeeModal({ visible: false, site: null });
    fetchData();
  };

  const getStatusColor = (status) => {
    const colors = {
      Active: 'green',
      Completed: 'blue',
      'On Hold': 'orange',
      Cancelled: 'red',
    };
    return colors[status] || 'default';
  };

  const columns = [
    {
      title: 'Site Code',
      dataIndex: 'site_code',
      key: 'site_code',
      render: (text) => <strong>{text}</strong>,
    },
    {
      title: 'Site Name',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: 'Location',
      dataIndex: 'location',
      key: 'location',
    },
    {
      title: 'Contract',
      dataIndex: 'contract_code',
      key: 'contract_code',
      render: (code) => code ? <Tag>{code}</Tag> : '—',
    },
    {
      title: 'Manager',
      dataIndex: 'assigned_manager_name',
      key: 'assigned_manager_name',
      render: (name) =>
        name ? (
          <Tag color="blue">{name}</Tag>
        ) : (
          <Tag color="orange">Unassigned</Tag>
        ),
    },
    {
      title: 'Workers',
      key: 'workers',
      render: (_, record) => {
        const assigned = record.assigned_workers || 0;
        const required = record.required_workers || 0;
        const isFull = assigned >= required && required > 0;
        return (
          <span style={{ color: isFull ? '#52c41a' : '#fa8c16' }}>
            {assigned} / {required}
          </span>
        );
      },
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
            onClick={() => navigate(`/project-workflow/sites/${record.uid}/details`)}
          >
            Details
          </Button>
          <Tooltip title={record.assigned_manager_name ? 'Change Manager' : 'Assign Manager'}>
            <Button
              type="link"
              icon={<UserAddOutlined />}
              onClick={() => setAssignManagerModal({ visible: true, site: record })}
            >
              {record.assigned_manager_name ? 'Change' : 'Assign'} Manager
            </Button>
          </Tooltip>
          <Tooltip title="Assign Employees to this Site">
            <Button
              type="link"
              icon={<TeamOutlined />}
              onClick={() => setAssignEmployeeModal({ visible: true, site: record })}
            >
              Assign Employees
            </Button>
          </Tooltip>
          <Popconfirm
            title="Delete this site?"
            description="This will only work if no active assignments exist."
            onConfirm={() => handleDeleteSite(record.uid)}
            okText="Delete"
            okButtonProps={{ danger: true }}
          >
            <Button type="link" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const assignedSites = sites.filter((s) => s.assigned_manager_id).length;
  const totalRequired = sites.reduce((sum, s) => sum + (s.required_workers || 0), 0);
  const totalAssigned = sites.reduce((sum, s) => sum + (s.assigned_workers || 0), 0);

  return (
    <div style={{ padding: 24, background: '#f0f2f5', minHeight: 'calc(100vh - 64px)' }}>
      <Breadcrumb
        style={{ marginBottom: 16 }}
        items={[
          { title: <Link to="/project-workflow">Projects</Link> },
          { title: <Link to={`/project-workflow/${projectId}/contracts`}>{project?.project_code || `Project ${projectId}`}</Link> },
          { title: 'Sites' },
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
            onClick={() => navigate(`/project-workflow/${projectId}/contracts`)}
          />
          <div>
            <h2 style={{ margin: 0, color: '#1890ff' }}>
              <EnvironmentOutlined /> Site Management
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
          Add Site
        </Button>
      </div>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="Total Sites"
              value={sites.length}
              prefix={<EnvironmentOutlined />}
              styles={{ content: { color: '#1890ff' } }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="Sites with Managers"
              value={assignedSites}
              suffix={`/ ${sites.length}`}
              styles={{ content: { color: '#52c41a' } }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="Worker Fulfillment"
              value={totalAssigned}
              suffix={`/ ${totalRequired}`}
              styles={{ content: { color: '#722ed1' } }}
            />
          </Card>
        </Col>
      </Row>

      <Card>
        <Table
          columns={columns}
          dataSource={sites}
          loading={loading}
          rowKey="uid"
          pagination={{ pageSize: 10 }}
          locale={{
            emptyText: (
              <Empty description="No sites yet">
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={() => setCreateModalVisible(true)}
                >
                  Add First Site
                </Button>
              </Empty>
            ),
          }}
        />
      </Card>

      <CreateSiteModal
        visible={createModalVisible}
        projectId={Number(projectId)}
        contracts={contracts}
        onCancel={() => setCreateModalVisible(false)}
        onSuccess={() => {
          setCreateModalVisible(false);
          fetchData();
        }}
      />

      {assignManagerModal.site && (
        <AssignManagerModal
          visible={assignManagerModal.visible}
          site={assignManagerModal.site}
          onCancel={() => setAssignManagerModal({ visible: false, site: null })}
          onSuccess={handleManagerAssigned}
        />
      )}

      {assignEmployeeModal.site && (
        <AssignEmployeeModal
          visible={assignEmployeeModal.visible}
          site={assignEmployeeModal.site}
          onCancel={() => setAssignEmployeeModal({ visible: false, site: null })}
          onSuccess={handleEmployeeAssigned}
        />
      )}
    </div>
  );
};

export default SiteManagementPage;
