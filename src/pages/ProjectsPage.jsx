import React, { useState, useEffect } from 'react';
import '../styles/projectsPage.css';
import {
  Button, message, Tag, Card, Row, Col, Statistic, Table, Badge, Empty, Space, Typography,
} from 'antd';
import { PlusOutlined, ApartmentOutlined, EnvironmentOutlined, TeamOutlined } from '@ant-design/icons';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { projectService } from '../services';
import CreateProjectModal from '../components/ProjectWorkflow/CreateProjectModal';

const { Title } = Typography;

const STATUS_COLORS = {
  Active: 'green',
  Completed: 'blue',
  'On Hold': 'orange',
  Cancelled: 'red',
};

const ONGOING_STATUSES = new Set(['Active', 'On Hold']);

const ProjectsPage = () => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('ongoing');
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(false);
  const { isAdmin } = useAuth();
  const [isModalOpen, setIsModalOpen] = useState(false);

  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    setLoading(true);
    try {
      const data = await projectService.getAll();
      setProjects(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('Failed to fetch projects:', error);
      message.error('Failed to load projects');
    } finally {
      setLoading(false);
    }
  };

  // isAdmin from useAuth() — no manual jwtDecode needed

  const ongoingProjects = projects.filter(p => ONGOING_STATUSES.has(p.status));
  const allProjects = projects;

  const totalProjects = projects.length;
  const activeCount = projects.filter(p => p.status === 'Active').length;
  const totalSites = projects.reduce((sum, p) => sum + (p.total_sites || 0), 0);
  const totalEmployees = projects.reduce((sum, p) => sum + (p.total_assigned_employees || 0), 0);

  const renderProjectCard = (item) => (
    <div key={item.uid} className="project-card labour-border">
      <div className="card-top">
        <h3>{item.project_name}</h3>
        <Tag color={STATUS_COLORS[item.status] || 'default'}>{item.status}</Tag>
      </div>
      <div className="contract-meta">
        <p className="client-value">{item.client_name}</p>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          <span className="contract-value-tag">Code: {item.project_code}</span>
          <span className="contract-value-tag">
            <EnvironmentOutlined style={{ marginRight: 4 }} />{item.total_sites || 0} Sites
          </span>
          <span className="contract-value-tag">
            <TeamOutlined style={{ marginRight: 4 }} />{item.total_assigned_employees || 0} Workers
          </span>
        </div>
      </div>
      <div style={{ marginTop: 'auto', paddingTop: 16 }}>
        <button
          className="btn-primary-modern"
          style={{ width: '100%' }}
          onClick={() => navigate(`/project-workflow/${item.uid}/contracts`)}
        >
          <ApartmentOutlined style={{ marginRight: 6 }} /> Manage
        </button>
      </div>
    </div>
  );

  const registryColumns = [
    { title: 'Code', dataIndex: 'project_code', key: 'project_code', render: (t) => <strong>{t}</strong> },
    { title: 'Project', dataIndex: 'project_name', key: 'project_name' },
    { title: 'Client', dataIndex: 'client_name', key: 'client_name' },
    { title: 'Sites', dataIndex: 'total_sites', key: 'total_sites', align: 'center',
      render: (v) => <Badge count={v || 0} showZero style={{ backgroundColor: '#1890ff' }} /> },
    { title: 'Employees', dataIndex: 'total_assigned_employees', key: 'total_assigned_employees', align: 'center',
      render: (v) => <Badge count={v || 0} showZero style={{ backgroundColor: '#52c41a' }} /> },
    { title: 'Status', dataIndex: 'status', key: 'status',
      render: (s) => <Tag color={STATUS_COLORS[s] || 'default'}>{s}</Tag> },
    { title: 'Actions', key: 'actions',
      render: (_, record) => (
        <Button type="link" onClick={() => navigate(`/project-workflow/${record.uid}/contracts`)}>
          Manage
        </Button>
      ) },
  ];

  return (
    <div className="projects-container">
      <div className="projects-header">
        <Title level={2} style={{ margin: 0 }}>Montreal Intl. Projects</Title>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <div className="project-tabs">
            <button className={`tab-btn ${activeTab === 'ongoing' ? 'active' : ''}`} onClick={() => setActiveTab('ongoing')}>
              Ongoing ({ongoingProjects.length})
            </button>
            <button className={`tab-btn ${activeTab === 'registry' ? 'active' : ''}`} onClick={() => setActiveTab('registry')}>
              Registry ({allProjects.length})
            </button>
          </div>
          {isAdmin && (
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setIsModalOpen(true)}
              style={{ height: 45, borderRadius: 10, background: '#22c55e', border: 'none' }}
            >
              Launch Project
            </Button>
          )}
        </div>
      </div>

      <Row gutter={[16, 16]} style={{ marginBottom: '24px', marginTop: 20 }}>
        <Col xs={24} sm={6}>
          <Card variant="borderless" className="summary-stat-card">
            <Statistic title="Total Projects" value={totalProjects} />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card variant="borderless" className="summary-stat-card">
            <Statistic title="Active" value={activeCount} styles={{ content: { color: '#3f8600' } }} />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card variant="borderless" className="summary-stat-card">
            <Statistic title="Total Sites" value={totalSites} />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card variant="borderless" className="summary-stat-card">
            <Statistic title="Assigned Workers" value={totalEmployees} />
          </Card>
        </Col>
      </Row>

      <div className="projects-content">
        {activeTab === 'ongoing' ? (
          <div className="grid-view">
            {ongoingProjects.length > 0 ? (
              ongoingProjects.map(renderProjectCard)
            ) : (
              <div style={{ gridColumn: '1 / -1' }}>
                <Empty description="No ongoing projects" image={Empty.PRESENTED_IMAGE_SIMPLE}>
                  {isAdmin && (
                    <Button type="primary" icon={<PlusOutlined />} onClick={() => setIsModalOpen(true)}>
                      Launch First Project
                    </Button>
                  )}
                </Empty>
              </div>
            )}
          </div>
        ) : (
          <Card variant="borderless" style={{ borderRadius: 16 }}>
            <Table
              dataSource={allProjects}
              rowKey="uid"
              columns={registryColumns}
              loading={loading}
              pagination={{ pageSize: 10 }}
              locale={{ emptyText: <Empty description="No projects yet" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
            />
          </Card>
        )}
      </div>

      <CreateProjectModal
        visible={isModalOpen}
        onCancel={() => setIsModalOpen(false)}
        onSuccess={() => {
          setIsModalOpen(false);
          fetchProjects();
        }}
      />
    </div>
  );
};

export default ProjectsPage;