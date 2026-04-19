import React, { useState, useEffect } from 'react';
import {
  Card, Row, Col, Button, Table, Tag, Space, Statistic,
  Empty, message, Tabs, Badge,
} from 'antd';
import {
  PlusOutlined, ProjectOutlined, EnvironmentOutlined,
  TeamOutlined, CheckCircleOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { fetchWithAuth } from '../../services/apiService';
import CreateProjectModal from '../../components/ProjectWorkflow/CreateProjectModal';
import ProjectDetailsModal from '../../components/ProjectWorkflow/ProjectDetailsModal';
import './ProjectDashboard.css';

const ProjectDashboard = () => {
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(false);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [selectedProject, setSelectedProject] = useState(null);
  const [detailsModalVisible, setDetailsModalVisible] = useState(false);
  const [activeTab, setActiveTab] = useState('all');

  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async (status = null) => {
    setLoading(true);
    try {
      const url = status ? `/projects/?status=${status}` : '/projects/';
      const data = await fetchWithAuth(url);
      setProjects(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('Error fetching projects:', error);
      message.error('Error fetching projects');
    } finally {
      setLoading(false);
    }
  };

  const handleTabChange = (key) => {
    setActiveTab(key);
    const statusMap = {
      all: null,
      active: 'Active',
      completed: 'Completed',
      onhold: 'On Hold',
    };
    fetchProjects(statusMap[key]);
  };

  const handleCreateProject = () => {
    setCreateModalVisible(true);
  };

  const handleProjectCreated = () => {
    setCreateModalVisible(false);
    fetchProjects();
    message.success('Project created successfully!');
  };

  const handleViewDetails = (project) => {
    setSelectedProject(project);
    setDetailsModalVisible(true);
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
      title: 'Project Code',
      dataIndex: 'project_code',
      key: 'project_code',
      render: (text) => <strong>{text}</strong>,
    },
    {
      title: 'Project Name',
      dataIndex: 'project_name',
      key: 'project_name',
    },
    {
      title: 'Client',
      dataIndex: 'client_name',
      key: 'client_name',
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status) => <Tag color={getStatusColor(status)}>{status}</Tag>,
    },
    {
      title: 'Sites',
      dataIndex: 'total_sites',
      key: 'total_sites',
      align: 'center',
      render: (count) => (
        <Badge count={count} showZero style={{ backgroundColor: '#1890ff' }} />
      ),
    },
    {
      title: 'Employees',
      dataIndex: 'total_assigned_employees',
      key: 'total_assigned_employees',
      align: 'center',
      render: (count) => (
        <Badge count={count} showZero style={{ backgroundColor: '#52c41a' }} />
      ),
    },
    {
      title: 'Managers',
      dataIndex: 'total_assigned_managers',
      key: 'total_assigned_managers',
      align: 'center',
      render: (count) => (
        <Badge count={count} showZero style={{ backgroundColor: '#722ed1' }} />
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button type="link" onClick={() => handleViewDetails(record)}>
            View Details
          </Button>
          <Button
            type="link"
            onClick={() => navigate(`/project-workflow/${record.uid}/details`)}
          >
            Full Details
          </Button>
          <Button
            type="link"
            onClick={() => navigate(`/project-workflow/${record.uid}/contracts`)}
          >
            Manage Contracts
          </Button>
        </Space>
      ),
    },
  ];

  const stats = {
    total: projects.length,
    active: projects.filter((p) => p.status === 'Active').length,
    completed: projects.filter((p) => p.status === 'Completed').length,
    totalSites: projects.reduce((sum, p) => sum + (p.total_sites || 0), 0),
    totalEmployees: projects.reduce((sum, p) => sum + (p.total_assigned_employees || 0), 0),
  };

  const tabItems = [
    { key: 'all', label: 'All Projects' },
    { key: 'active', label: 'Active' },
    { key: 'completed', label: 'Completed' },
    { key: 'onhold', label: 'On Hold' },
  ];

  return (
    <div className="project-dashboard">
      <div className="dashboard-header">
        <div>
          <h1>
            <ProjectOutlined /> Project Workflow Management
          </h1>
          <p style={{ color: '#666', marginTop: 8 }}>
            Manage projects, contracts, sites, and workforce assignments
          </p>
        </div>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          size="large"
          onClick={handleCreateProject}
        >
          Create New Project
        </Button>
      </div>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={6} lg={4}>
          <Card>
            <Statistic
              title="Total Projects"
              value={stats.total}
              prefix={<ProjectOutlined />}
              styles={{ content: { color: '#1890ff' } }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6} lg={4}>
          <Card>
            <Statistic
              title="Active Projects"
              value={stats.active}
              prefix={<CheckCircleOutlined />}
              styles={{ content: { color: '#52c41a' } }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6} lg={4}>
          <Card>
            <Statistic
              title="Completed"
              value={stats.completed}
              prefix={<CheckCircleOutlined />}
              styles={{ content: { color: '#1890ff' } }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6} lg={4}>
          <Card>
            <Statistic
              title="Total Sites"
              value={stats.totalSites}
              prefix={<EnvironmentOutlined />}
              styles={{ content: { color: '#722ed1' } }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6} lg={4}>
          <Card>
            <Statistic
              title="Assigned Workers"
              value={stats.totalEmployees}
              prefix={<TeamOutlined />}
              styles={{ content: { color: '#fa8c16' } }}
            />
          </Card>
        </Col>
      </Row>

      <Card>
        <Tabs activeKey={activeTab} onChange={handleTabChange} items={tabItems} />

        <Table
          columns={columns}
          dataSource={projects}
          loading={loading}
          rowKey="uid"
          pagination={{ pageSize: 10 }}
          locale={{
            emptyText: (
              <Empty
                description="No projects found"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              >
                <Button type="primary" onClick={handleCreateProject}>
                  Create Your First Project
                </Button>
              </Empty>
            ),
          }}
        />
      </Card>

      <CreateProjectModal
        visible={createModalVisible}
        onCancel={() => setCreateModalVisible(false)}
        onSuccess={handleProjectCreated}
      />

      {selectedProject && (
        <ProjectDetailsModal
          visible={detailsModalVisible}
          project={selectedProject}
          onCancel={() => setDetailsModalVisible(false)}
          onUpdate={fetchProjects}
        />
      )}
    </div>
  );
};

export default ProjectDashboard;
