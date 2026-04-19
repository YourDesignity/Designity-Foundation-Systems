/**
 * DesignationManagement.jsx
 * 
 * Standalone company master list for designations.
 * Admin can create, edit, and deactivate designations.
 * These are used across Dedicated Staff and Shift-Based contracts
 * for role-slot matching.
 */

import React, { useState, useEffect } from 'react';
import {
  Table, Button, Modal, Form, Input, Tag, Space, Typography,
  Popconfirm, message, Card, Row, Col, Statistic, Badge, Tooltip,
} from 'antd';
import {
  PlusOutlined, EditOutlined, DeleteOutlined, TagsOutlined, TeamOutlined,
} from '@ant-design/icons';
import { useAuth } from '../context/AuthContext';
import { getDesignations, addDesignation, deleteDesignation, getEmployees } from '../services/apiService';

const { Title, Text } = Typography;

const DesignationManagement = () => {
  const { isAdmin } = useAuth();
  const [designations, setDesignations]     = useState([]);
  const [employeeCounts, setEmployeeCounts] = useState({});
  const [loading, setLoading]               = useState(true);
  const [modalOpen, setModalOpen]           = useState(false);
  const [submitting, setSubmitting]         = useState(false);
  const [form] = Form.useForm();

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [desData, empData] = await Promise.all([getDesignations(), getEmployees()]);
      setDesignations(Array.isArray(desData) ? desData : []);

      // Build employee count per designation
      const counts = {};
      if (Array.isArray(empData)) {
        empData.forEach(emp => {
          if (emp.designation) {
            counts[emp.designation] = (counts[emp.designation] || 0) + 1;
          }
        });
      }
      setEmployeeCounts(counts);
    } catch (err) {
      console.error(err);
      message.error('Could not load designations.');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (values) => {
    try {
      setSubmitting(true);
      await addDesignation({ title: values.name });
      message.success(`Designation "${values.name}" created.`);
      form.resetFields();
      setModalOpen(false);
      fetchData();
    } catch (err) {
      message.error(err?.response?.data?.detail || 'Failed to create designation.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (uid) => {
    try {
      await deleteDesignation(uid);
      message.success('Designation deleted.');
      fetchData();
    } catch (err) {
      message.error(err?.response?.data?.detail || 'Failed to delete designation.');
    }
  };

  const totalDesignations  = designations.length;
  const totalWithEmployees = designations.filter(d => (employeeCounts[d.title] || 0) > 0).length;

  const columns = [
    {
      title: '#',
      width: 60,
      render: (_, __, i) => <Text type="secondary">{i + 1}</Text>,
    },
    {
      title: 'Designation',
      dataIndex: 'title',
      key: 'title',
      render: (title) => (
        <Space>
          <TagsOutlined style={{ color: '#1677ff' }} />
          <Text strong>{title}</Text>
        </Space>
      ),
    },
    {
      title: 'Employees',
      key: 'employees',
      render: (_, record) => {
        const count = employeeCounts[record.title] || 0;
        return (
          <Badge
            count={count}
            showZero
            style={{ backgroundColor: count > 0 ? '#52c41a' : '#d9d9d9' }}
          >
            <TeamOutlined style={{ fontSize: 16, paddingRight: 8 }} />
          </Badge>
        );
      },
    },
    {
      title: 'Status',
      key: 'status',
      render: (_, record) => {
        const count = employeeCounts[record.title] || 0;
        return count > 0
          ? <Tag color="green">In Use</Tag>
          : <Tag color="default">Unused</Tag>;
      },
    },
    ...(isAdmin ? [{
      title: 'Actions',
      key: 'actions',
      width: 100,
      render: (_, record) => {
        const count = employeeCounts[record.title] || 0;
        return (
          <Popconfirm
            title="Delete this designation?"
            description={count > 0
              ? `${count} employee(s) use this designation. Deleting it won't unassign them.`
              : 'This designation has no assigned employees.'}
            onConfirm={() => handleDelete(record.uid)}
            okText="Delete"
            cancelText="Cancel"
            okButtonProps={{ danger: true }}
          >
            <Tooltip title="Delete">
              <Button danger icon={<DeleteOutlined />} size="small" type="text" />
            </Tooltip>
          </Popconfirm>
        );
      },
    }] : []),
  ];

  return (
    <div style={{ padding: '24px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 }}>
        <div>
          <Title level={3} style={{ margin: 0 }}>Designations</Title>
          <Text type="secondary">
            Company master list of job designations. Used for employee profiles and contract role slots.
          </Text>
        </div>
        {isAdmin && (
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
            Add Designation
          </Button>
        )}
      </div>

      {/* Stats */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={6}>
          <Card size="small" variant="borderless" style={{ background: '#f0f5ff' }}>
            <Statistic title="Total Designations" value={totalDesignations} prefix={<TagsOutlined />} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small" variant="borderless" style={{ background: '#f6ffed' }}>
            <Statistic title="In Use" value={totalWithEmployees} prefix={<TeamOutlined />} />
          </Card>
        </Col>
      </Row>

      {/* Table */}
      <Card variant="borderless" styles={{ body: { padding: 0 } }}>
        <Table
          columns={columns}
          dataSource={designations}
          rowKey="uid"
          loading={loading}
          pagination={{ pageSize: 20, showSizeChanger: false }}
          locale={{ emptyText: 'No designations yet. Add one to get started.' }}
        />
      </Card>

      {/* Create Modal */}
      <Modal
        title="Add New Designation"
        open={modalOpen}
        onCancel={() => { setModalOpen(false); form.resetFields(); }}
        footer={null}
        destroyOnHidden
      >
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item
            name="name"
            label="Designation Name"
            rules={[
              { required: true, message: 'Please enter a designation name' },
              { min: 2, message: 'Must be at least 2 characters' },
              { max: 60, message: 'Must be 60 characters or less' },
            ]}
          >
            <Input
              placeholder="e.g. Driver, Carpenter, Site Supervisor"
              autoFocus
            />
          </Form.Item>
          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Space>
              <Button onClick={() => { setModalOpen(false); form.resetFields(); }}>
                Cancel
              </Button>
              <Button type="primary" htmlType="submit" loading={submitting}>
                Create Designation
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default DesignationManagement;
