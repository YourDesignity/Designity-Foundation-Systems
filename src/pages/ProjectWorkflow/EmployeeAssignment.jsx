import React, { useState, useEffect } from 'react';
import {
  Card, Row, Col, Button, Table, Tag, Space, Select,
  message, Modal, DatePicker, Statistic, Progress,
  Empty, Badge
} from 'antd';
import {
  UserAddOutlined, TeamOutlined, EnvironmentOutlined,
  CheckCircleOutlined
} from '@ant-design/icons';
import { useParams } from 'react-router-dom';
import { fetchWithAuth } from '../../services/apiService';
import dayjs from 'dayjs';
import './EmployeeAssignment.css';

const { RangePicker } = DatePicker;

const EmployeeAssignment = () => {
  const { siteId } = useParams();

  const [loading, setLoading] = useState(false);
  const [site, setSite] = useState(null);
  const [assignedEmployees, setAssignedEmployees] = useState([]);
  const [availableEmployees, setAvailableEmployees] = useState([]);
  const [selectedEmployees, setSelectedEmployees] = useState([]);
  const [assignModalVisible, setAssignModalVisible] = useState(false);
  const [dateRange, setDateRange] = useState([dayjs(), null]);
  const [assignments, setAssignments] = useState([]);

  useEffect(() => {
    if (siteId) {
      fetchSiteData();
      fetchAvailableEmployees();
    }
  }, [siteId]);

  const fetchSiteData = async () => {
    setLoading(true);
    try {
      const data = await fetchWithAuth(`/assignments/site/${siteId}/employees`);
      setSite(data.site);
      setAssignedEmployees(data.employees || []);
      setAssignments(data.assignments || []);
    } catch (error) {
      console.error('Error:', error);
      message.error('Error fetching site data');
    } finally {
      setLoading(false);
    }
  };

  const fetchAvailableEmployees = async () => {
    try {
      const data = await fetchWithAuth('/assignments/available/employees');
      setAvailableEmployees(data.employees || []);
    } catch (error) {
      console.error('Error fetching available employees:', error);
    }
  };

  const handleBulkAssign = async () => {
    if (selectedEmployees.length === 0) {
      message.warning('Please select at least one employee');
      return;
    }

    if (!dateRange[0]) {
      message.warning('Please select start date');
      return;
    }

    setLoading(true);
    try {
      const data = await fetchWithAuth('/assignments/assign-employees', {
        method: 'POST',
        body: JSON.stringify({
          site_id: parseInt(siteId),
          employee_ids: selectedEmployees,
          assignment_start: dateRange[0].format('YYYY-MM-DD'),
          assignment_end: dateRange[1] ? dateRange[1].format('YYYY-MM-DD') : null
        })
      });

      message.success(data.message);
      setAssignModalVisible(false);
      setSelectedEmployees([]);
      setDateRange([dayjs(), null]);
      fetchSiteData();
      fetchAvailableEmployees();
    } catch (error) {
      console.error('Error:', error);
      message.error(error.message || 'Error assigning employees');
    } finally {
      setLoading(false);
    }
  };

  const handleUnassign = (assignmentId, employeeName) => {
    Modal.confirm({
      title: 'Unassign Employee',
      content: `Are you sure you want to unassign ${employeeName} from this site?`,
      okText: 'Yes, Unassign',
      okType: 'danger',
      onOk: async () => {
        try {
          await fetchWithAuth(`/assignments/${assignmentId}`, {
            method: 'DELETE'
          });

          message.success('Employee unassigned successfully');
          fetchSiteData();
          fetchAvailableEmployees();
        } catch (error) {
          console.error('Error:', error);
          message.error(error.message || 'Error unassigning employee');
        }
      }
    });
  };

  const getAssignmentId = (employeeId) => {
    const assignment = assignments.find(a => a.employee_id === employeeId);
    return assignment?.uid;
  };

  const assignedColumns = [
    {
      title: 'Employee ID',
      dataIndex: 'uid',
      key: 'uid',
      width: 100,
    },
    {
      title: 'Full Name',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: 'Designation',
      dataIndex: 'designation',
      key: 'designation',
    },
    {
      title: 'Phone',
      dataIndex: 'phone_kuwait',
      key: 'phone_kuwait',
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Tag color={status === 'Active' ? 'green' : 'default'}>
          {status}
        </Tag>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Button
          type="link"
          danger
          onClick={() => handleUnassign(getAssignmentId(record.uid), record.name)}
        >
          Unassign
        </Button>
      ),
    },
  ];

  const capacityPercentage = site
    ? (site.assigned_workers / site.required_workers * 100)
    : 0;

  return (
    <div className="employee-assignment-page">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1><TeamOutlined /> Employee Assignment</h1>
          <p style={{ color: '#666', marginTop: 8 }}>
            Assign company employees to {site?.name || 'site'}
          </p>
        </div>
        <Button
          type="primary"
          icon={<UserAddOutlined />}
          size="large"
          onClick={() => setAssignModalVisible(true)}
        >
          Assign Employees
        </Button>
      </div>

      {/* Site Info & Capacity */}
      {site && (
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="Site"
                value={site.name}
                prefix={<EnvironmentOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="Required Workers"
                value={site.required_workers}
                prefix={<TeamOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="Assigned Workers"
                value={site.assigned_workers}
                styles={{ content: { color: site.assigned_workers >= site.required_workers ? '#52c41a' : '#fa8c16' } }}
                prefix={<CheckCircleOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <div style={{ marginBottom: 8 }}>
                <span style={{ fontSize: 14, color: '#666' }}>Capacity</span>
              </div>
              <Progress
                percent={Math.round(capacityPercentage)}
                status={capacityPercentage >= 100 ? 'success' : 'active'}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* Assigned Employees Table */}
      <Card title={`Assigned Employees (${assignedEmployees.length})`}>
        <Table
          columns={assignedColumns}
          dataSource={assignedEmployees}
          rowKey="uid"
          loading={loading}
          pagination={{ pageSize: 10 }}
          locale={{
            emptyText: (
              <Empty description="No employees assigned yet">
                <Button
                  type="primary"
                  onClick={() => setAssignModalVisible(true)}
                >
                  Assign Employees
                </Button>
              </Empty>
            ),
          }}
        />
      </Card>

      {/* Assign Employees Modal */}
      <Modal
        title="Assign Employees to Site"
        open={assignModalVisible}
        onCancel={() => {
          setAssignModalVisible(false);
          setSelectedEmployees([]);
          setDateRange([dayjs(), null]);
        }}
        onOk={handleBulkAssign}
        okText={`Assign ${selectedEmployees.length} Employee${selectedEmployees.length !== 1 ? 's' : ''}`}
        width={800}
        confirmLoading={loading}
        okButtonProps={{ disabled: selectedEmployees.length === 0 }}
      >
        <Space orientation="vertical" style={{ width: '100%' }} size="large">
          <div>
            <p><strong>Site:</strong> {site?.name}</p>
            <p><strong>Available Slots:</strong> {site ? site.required_workers - site.assigned_workers : 0}</p>
          </div>

          <div>
            <p style={{ marginBottom: 8 }}><strong>Assignment Period:</strong></p>
            <RangePicker
              style={{ width: '100%' }}
              value={dateRange}
              onChange={setDateRange}
              placeholder={['Start Date', 'End Date (Optional)']}
            />
          </div>

          <div>
            <p style={{ marginBottom: 8 }}>
              <strong>Select Employees:</strong>
              <Badge
                count={selectedEmployees.length}
                style={{ marginLeft: 8, backgroundColor: '#1890ff' }}
              />
            </p>
            <Select
              mode="multiple"
              style={{ width: '100%' }}
              placeholder="Select employees to assign"
              value={selectedEmployees}
              onChange={setSelectedEmployees}
              showSearch
              filterOption={(input, option) =>
                option.children.toLowerCase().includes(input.toLowerCase())
              }
            >
              {availableEmployees.map(emp => (
                <Select.Option key={emp.uid} value={emp.uid}>
                  {emp.name} - {emp.designation}
                </Select.Option>
              ))}
            </Select>
            <p style={{ marginTop: 8, color: '#666', fontSize: 12 }}>
              {availableEmployees.length} employees available for assignment
            </p>
          </div>
        </Space>
      </Modal>
    </div>
  );
};

export default EmployeeAssignment;
