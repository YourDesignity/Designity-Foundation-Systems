import React, { useState, useEffect } from 'react';
import {
  Modal, Descriptions, Tag, Button, Tabs,
  Table, Empty, message, Statistic, Row, Col, Card, Spin,
} from 'antd';
import {
  FileTextOutlined, EnvironmentOutlined, TeamOutlined,
  UserOutlined, PlusOutlined,
} from '@ant-design/icons';
import { fetchWithAuth } from '../../services/apiService';
import { useNavigate } from 'react-router-dom';

const ProjectDetailsModal = ({ visible, project, onCancel, onUpdate }) => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [details, setDetails] = useState(null);

  useEffect(() => {
    if (visible && project) {
      fetchProjectDetails();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visible, project]);

  const fetchProjectDetails = async () => {
    setLoading(true);
    try {
      const data = await fetchWithAuth(`/projects/${project.uid}`);
      setDetails(data);
    } catch (error) {
      console.error('Error fetching project details:', error);
      message.error('Error fetching project details');
    } finally {
      setLoading(false);
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

  const contractColumns = [
    {
      title: 'Contract Code',
      dataIndex: 'contract_code',
      key: 'contract_code',
      render: (text) => <strong>{text}</strong>,
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
  ];

  const siteColumns = [
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
      title: 'Manager',
      dataIndex: 'assigned_manager_name',
      key: 'assigned_manager_name',
      render: (name) => name || <Tag>Unassigned</Tag>,
    },
    {
      title: 'Workers',
      key: 'workers',
      render: (_, record) => (
        <span>
          {record.assigned_workers || 0} / {record.required_workers || 0}
        </span>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status) => <Tag color={getStatusColor(status)}>{status}</Tag>,
    },
  ];

  const assignmentColumns = [
    { title: 'Employee', dataIndex: 'employee_name', key: 'employee_name' },
    { title: 'Site', dataIndex: 'site_name', key: 'site_name' },
    { title: 'Manager', dataIndex: 'manager_name', key: 'manager_name' },
    { title: 'Start Date', dataIndex: 'assignment_start', key: 'assignment_start' },
    { title: 'End Date', dataIndex: 'assignment_end', key: 'assignment_end' },
  ];

  const tabItems = [
    {
      key: '1',
      label: (
        <span>
          <FileTextOutlined /> Contracts ({details?.contracts?.length || 0})
        </span>
      ),
      children: (
        <Table
          columns={contractColumns}
          dataSource={details?.contracts || []}
          rowKey="uid"
          pagination={false}
          locale={{
            emptyText: (
              <Empty description="No contracts yet">
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={() => {
                    onCancel();
                    navigate(`/project-workflow/${project?.uid}/contracts`);
                  }}
                >
                  Add Contract
                </Button>
              </Empty>
            ),
          }}
        />
      ),
    },
    {
      key: '2',
      label: (
        <span>
          <EnvironmentOutlined /> Sites ({details?.sites?.length || 0})
        </span>
      ),
      children: (
        <Table
          columns={siteColumns}
          dataSource={details?.sites || []}
          rowKey="uid"
          pagination={false}
          locale={{
            emptyText: (
              <Empty description="No sites yet">
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={() => {
                    onCancel();
                    navigate(`/project-workflow/${project?.uid}/sites`);
                  }}
                >
                  Add Site
                </Button>
              </Empty>
            ),
          }}
        />
      ),
    },
    {
      key: '3',
      label: (
        <span>
          <TeamOutlined /> Assignments ({details?.active_assignments?.length || 0})
        </span>
      ),
      children: (
        <Table
          dataSource={details?.active_assignments || []}
          rowKey="uid"
          pagination={false}
          columns={assignmentColumns}
          locale={{
            emptyText: <Empty description="No employee assignments yet" />,
          }}
        />
      ),
    },
  ];

  return (
    <Modal
      title={`Project Details: ${project?.project_code}`}
      open={visible}
      onCancel={onCancel}
      footer={
        <Button
          type="primary"
          onClick={() => {
            onCancel();
            navigate(`/project-workflow/${project?.uid}/contracts`);
          }}
        >
          Manage Contracts & Sites
        </Button>
      }
      width={1000}
    >
      {loading ? (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin size="large" />
        </div>
      ) : details ? (
        <>
          <Descriptions bordered column={2} style={{ marginBottom: 24 }}>
            <Descriptions.Item label="Project Code" span={1}>
              <strong>{details.project?.project_code}</strong>
            </Descriptions.Item>
            <Descriptions.Item label="Status" span={1}>
              <Tag color={getStatusColor(details.project?.status)}>
                {details.project?.status}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Project Name" span={2}>
              {details.project?.project_name}
            </Descriptions.Item>
            <Descriptions.Item label="Client Name" span={1}>
              {details.project?.client_name}
            </Descriptions.Item>
            <Descriptions.Item label="Client Contact" span={1}>
              {details.project?.client_contact || 'N/A'}
            </Descriptions.Item>
            <Descriptions.Item label="Client Email" span={2}>
              {details.project?.client_email || 'N/A'}
            </Descriptions.Item>
            {details.project?.description && (
              <Descriptions.Item label="Description" span={2}>
                {details.project.description}
              </Descriptions.Item>
            )}
          </Descriptions>

          <Row gutter={16} style={{ marginBottom: 24 }}>
            <Col span={8}>
              <Card>
                <Statistic
                  title="Total Sites"
                  value={details.project?.total_sites || 0}
                  prefix={<EnvironmentOutlined />}
                />
              </Card>
            </Col>
            <Col span={8}>
              <Card>
                <Statistic
                  title="Assigned Employees"
                  value={details.project?.total_assigned_employees || 0}
                  prefix={<TeamOutlined />}
                />
              </Card>
            </Col>
            <Col span={8}>
              <Card>
                <Statistic
                  title="Managers"
                  value={details.project?.total_assigned_managers || 0}
                  prefix={<UserOutlined />}
                />
              </Card>
            </Col>
          </Row>

          <Tabs defaultActiveKey="1" items={tabItems} />
        </>
      ) : null}
    </Modal>
  );
};

export default ProjectDetailsModal;
