// src/components/DashboardPage.jsx

import React, { useState, useEffect, useMemo } from 'react';
import { 
  Card, Col, Row, Typography, message, Button, 
  Select, Table, Modal, Input, Form, Space, Avatar, Tag, Skeleton, InputNumber 
} from "antd";
import { 
  UserOutlined, DollarOutlined, SolutionOutlined, TeamOutlined, 
  EditOutlined, DeleteOutlined 
} from "@ant-design/icons";
import ReactApexChart from "react-apexcharts";

import { getEmployees, createPayslips, updateEmployee, deleteEmployee, getDesignations } from '../services/apiService';

const { Title, Text } = Typography;
const { Option } = Select;

function DashboardPage() {
  const [employees, setEmployees] = useState([]);
  const [designationOptions, setDesignationOptions] = useState([]);
  const [loading, setLoading] = useState(true);
  
  const [selectedDesignation, setSelectedDesignation] = useState('all');
  const [selectedEmployees, setSelectedEmployees] = useState([]);
  
  const [isPayslipModalVisible, setIsPayslipModalVisible] = useState(false);
  const [isCreatingPayslip, setIsCreatingPayslip] = useState(false);
  const [isEditModalVisible, setIsEditModalVisible] = useState(false);
  const [editingEmployee, setEditingEmployee] = useState(null);
  
  const [form] = Form.useForm();

  useEffect(() => {
    let isMounted = true;
    
    const loadInitialData = async () => {
      try {
        const [empData, desData] = await Promise.all([
            getEmployees(),
            getDesignations()
        ]);
        if (isMounted) {
          setEmployees(Array.isArray(empData) ? empData : []);
          setDesignationOptions(Array.isArray(desData) ? desData : []);
        }
      } catch (e) {
        console.error("Error loading data:", e);
      } finally {
        if (isMounted) setLoading(false);
      }
    };
    loadInitialData();

    return () => { isMounted = false; };
  }, []);

  const totalEmployees = employees.length;
  const totalBasicSalary = employees.reduce((sum, emp) => sum + (parseFloat(emp.basic_salary) || 0), 0);
  
  const filteredEmployees = useMemo(() => 
    employees.filter(e => selectedDesignation === 'all' || e.designation === selectedDesignation),
  [employees, selectedDesignation]);

  const handleDesignationChange = (value) => { setSelectedDesignation(value); setSelectedEmployees([]); };
  
  const confirmAndCreatePayslips = async () => {
    if (selectedEmployees.length === 0) return;
    setIsCreatingPayslip(true);
    try {
      await createPayslips(selectedEmployees);
      message.success('Payslips created successfully!');
      setSelectedEmployees([]);
      setIsPayslipModalVisible(false);
    } catch (err) { message.error(err.message); } finally { setIsCreatingPayslip(false); }
  };

  const openEditModal = (record) => {
    setEditingEmployee(record);
    form.setFieldsValue(record);
    setIsEditModalVisible(true);
  };

  const handleSaveEdit = async () => {
    try {
        const values = await form.validateFields();
        const payload = { 
            ...values, 
            basic_salary: parseFloat(values.basic_salary) || 0, 
            allowance: parseFloat(values.allowance) || 0, 
            standard_work_days: parseInt(values.standard_work_days) || 0 
        };
        await updateEmployee(editingEmployee.id, payload);
        message.success("Updated successfully");
        setIsEditModalVisible(false);
        setEditingEmployee(null);
    } catch (error) { message.error("Update failed"); }
  };

  const handleDeleteEmployee = async (id) => {
    Modal.confirm({
        title: 'Delete Employee?', content: 'Cannot be undone.', okText: 'Yes', okType: 'danger', cancelText: 'No',
        onOk: async () => {
            try { await deleteEmployee(id); message.success("Deleted"); } catch (error) { message.error("Failed"); }
        },
    });
  };

  const showLoading = loading && employees.length === 0;

  // --- EXISTING CHARTS ---
  const chartOptions = useMemo(() => ({
    chart: { type: "bar", toolbar: { show: false }, animations: { enabled: false } },
    plotOptions: { bar: { borderRadius: 5 } },
    dataLabels: { enabled: false },
    stroke: { show: true, width: 1, colors: ["transparent"] },
    xaxis: { categories: ["Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct"], labels: { style: { colors: "#8c8c8c" } } },
    yaxis: { labels: { style: { colors: "#8c8c8c" } } },
    grid: { borderColor: "#f0f0f0" },
    tooltip: { theme: "light" },
  }), []);

  const chartSeries = useMemo(() => [{ name: "Salary", data: [450, 200, 100, 220, 500, 100, 400, 230, 500] }], []);

  const lineChartOptions = useMemo(() => ({
    chart: { type: "area", toolbar: { show: false }, animations: { enabled: false } },
    dataLabels: { enabled: false },
    stroke: { curve: "smooth" },
    xaxis: { categories: ["Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct"], labels: { style: { colors: "#8c8c8c" } } },
    yaxis: { labels: { style: { colors: "#8c8c8c" } } },
    grid: { borderColor: "#f0f0f0" },
  }), []);

  const lineChartSeries = useMemo(() => [
    { name: "Active", data: [50, 40, 300, 220, 500, 250, 400, 230, 500] }
  ], []);

  // --- NEW VEHICLE CHART OPTIONS (PROFIT & LOSS / EXPENSES) ---
  const vehicleChartOptions = useMemo(() => ({
    chart: { type: "bar", stacked: true, toolbar: { show: false } },
    colors: ['#52c41a', '#f5222d'], // Green for Income/Usage Value, Red for Expenses
    plotOptions: { bar: { horizontal: false, columnWidth: '40%', borderRadius: 4 } },
    dataLabels: { enabled: false },
    xaxis: { 
        categories: ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
        labels: { style: { colors: "#8c8c8c" } } 
    },
    yaxis: { title: { text: '$ Amount' } },
    legend: { position: 'top', horizontalAlign: 'right' },
    fill: { opacity: 1 }
  }), []);

  const vehicleChartSeries = useMemo(() => [
    { name: 'Value/Usage', data: [5000, 5200, 4800, 6100, 5900, 6500] },
    { name: 'Expenses (Fuel/Maint)', data: [-1200, -1350, -2100, -1100, -900, -1450] }
  ], []);

  const columns = [
    {
      title: 'EMPLOYEE', dataIndex: 'name', key: 'name', width: '30%',
      render: (text, record) => (
        <div className="avatar-info" style={{display: 'flex', alignItems: 'center'}}>
           <Avatar style={{ backgroundColor: '#1890ff', marginRight: '10px' }} size={40} shape="square">
             {text ? text.charAt(0).toUpperCase() : 'U'}
           </Avatar>
           <div><Title level={5} style={{margin: 0}}>{text}</Title><Text type="secondary">{record.designation}</Text></div>
        </div>
      ),
    },
    {
      title: 'FINANCIALS', key: 'financials',
      render: (_, record) => (
        <div>
            <div className="semibold">Basic: ${parseFloat(record.basic_salary || 0).toFixed(2)}</div>
            <div className="text-sm text-muted">Allow: ${parseFloat(record.allowance || 0).toFixed(2)}</div>
        </div>
      ),
    },
    { title: 'STATUS', key: 'status', render: () => <Tag color="blue">ACTIVE</Tag> },
    {
      title: 'ACTIONS', key: 'action',
      render: (_, record) => (
        <Space size="middle">
          <Button type="text" icon={<EditOutlined />} onClick={() => openEditModal(record)} />
          <Button type="text" danger icon={<DeleteOutlined />} onClick={() => handleDeleteEmployee(record.id)} />
        </Space>
      ),
    },
  ];

  return (
    <div className="layout-content">
      <Row className="rowgap-vbox" gutter={[24, 0]}>
        {[
          { title: "Total Employees", value: totalEmployees, icon: <UserOutlined />, color: "#1890ff" },
          { title: "Total Basic Salary", value: `$${totalBasicSalary.toLocaleString(undefined, {minimumFractionDigits: 2})}`, icon: <DollarOutlined />, color: "#52c41a" },
          { title: "Designations", value: designationOptions.length, icon: <SolutionOutlined />, color: "#faad14" },
          { title: "Active Staff", value: totalEmployees, icon: <TeamOutlined />, color: "#f5222d" }
        ].map((stat, index) => (
          <Col key={index} xs={24} sm={24} md={12} lg={6} xl={6} className="mb-24">
            {/* FIX: variant="borderless" instead of bordered={false} */}
            <Card variant="borderless" className="criclebox">
              <div className="number">
                <Row align="middle" gutter={[24, 0]}>
                  <Col xs={18}>
                    <span>{stat.title}</span>
                    <div style={{ minHeight: '32px', display: 'flex', alignItems: 'center' }}>
                      {showLoading ? 
                        <Skeleton.Input active size="small" style={{ width: 80, height: 20 }} /> : 
                        <Title level={3} style={{ margin: 0 }}>{stat.value}</Title>
                      }
                    </div>
                  </Col>
                  <Col xs={6}>
                    <div className="icon-box" style={{background: stat.color, color: '#fff', display: 'flex', justifyContent: 'center', alignItems: 'center', borderRadius: 8, width: 48, height: 48}}>
                      {React.cloneElement(stat.icon, { style: { fontSize: 24 } })}
                    </div>
                  </Col>
                </Row>
              </div>
            </Card>
          </Col>
        ))}
      </Row>

      <Row gutter={[24, 0]}>
        <Col xs={24} sm={24} md={12} lg={12} xl={10} className="mb-24">
          <Card variant="borderless" className="criclebox h-full">
            <div className="chart-vistior">
              <Title level={5}>Salary Overview</Title>
              <Text type="secondary">Monthly trends</Text>
            </div>
            <div style={{ height: 220, overflow: 'hidden' }}>
                {showLoading ? 
                  <Skeleton active paragraph={{ rows: 4 }} /> : 
                  <ReactApexChart options={chartOptions} series={chartSeries} type="bar" height={200} />
                }
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={24} md={12} lg={12} xl={14} className="mb-24">
          <Card variant="borderless" className="criclebox h-full">
            <div className="linechart">
              <div><Title level={5}>Staff Activity</Title><Text type="secondary">Active vs Inactive</Text></div>
            </div>
            <div style={{ height: 370, overflow: 'hidden' }}>
                {showLoading ? 
                  <Skeleton active paragraph={{ rows: 4 }} /> : 
                  <ReactApexChart options={lineChartOptions} series={lineChartSeries} type="area" height={350} />
                }
            </div>
          </Card>
        </Col>
      </Row>

      {/* --- NEW SECTION: VEHICLE MANAGEMENT GRAPH --- */}
      <Row gutter={[24, 0]}>
        <Col span={24} className="mb-24">
            <Card variant="borderless" className="criclebox h-full">
                <div className="chart-vistior">
                    <Title level={5}>Vehicle Profit & Loss</Title>
                    <Text type="secondary">Operational Value vs Maintenance Expenses</Text>
                </div>
                <div style={{ height: 300, marginTop: 20 }}>
                    <ReactApexChart options={vehicleChartOptions} series={vehicleChartSeries} type="bar" height={280} />
                </div>
            </Card>
        </Col>
      </Row>
      {/* --------------------------------------------- */}

      <Row gutter={[24, 0]}>
        <Col xs={24} xl={24} className="mb-24">
          <Card variant="borderless" className="criclebox tablespace mb-24" title="Employees List" 
            extra={
              <Space>
                <Select value={selectedDesignation} onChange={handleDesignationChange} style={{ width: 200 }} disabled={showLoading}>
                    <Option value="all">All Designations</Option>
                    {designationOptions.map(r => <Option key={r.id} value={r.title || r.name}>{r.title || r.name}</Option>)}
                </Select>
                <Button type="primary" onClick={() => setIsPayslipModalVisible(true)} disabled={showLoading || selectedEmployees.length === 0}>Create Payslip</Button>
              </Space>
            }
          >
            <div className="table-responsive">
              <Table
                loading={showLoading}
                rowSelection={{ type: 'checkbox', selectedRowKeys: selectedEmployees, onChange: setSelectedEmployees }}
                columns={columns}
                dataSource={filteredEmployees}
                pagination={{ pageSize: 5 }}
                className="ant-border-space"
                rowKey="id"
                scroll={{ x: true }} 
              />
            </div>
          </Card>
        </Col>
      </Row>

      <Modal title="Confirm Payslip Creation" open={isPayslipModalVisible} onOk={confirmAndCreatePayslips} confirmLoading={isCreatingPayslip} onCancel={() => setIsPayslipModalVisible(false)}>
        <p>Create payslips for <b>{selectedEmployees.length}</b> employees?</p>
      </Modal>

      <Modal title="Edit Employee" open={isEditModalVisible} onOk={handleSaveEdit} onCancel={() => setIsEditModalVisible(false)}>
        <Form form={form} layout="vertical">
            <Form.Item name="name" label="Name" rules={[{ required: true }]}><Input /></Form.Item>
            <Form.Item name="designation" label="Designation"><Select>{designationOptions.map(r => <Option key={r.id} value={r.title || r.name}>{r.title || r.name}</Option>)}</Select></Form.Item>
            <Row gutter={16}>
                {/* Fixed: Use InputNumber */}
                <Col span={12}><Form.Item name="basic_salary" label="Basic Salary"><InputNumber style={{width: '100%'}} /></Form.Item></Col>
                <Col span={12}><Form.Item name="allowance" label="Allowance"><InputNumber style={{width: '100%'}} /></Form.Item></Col>
            </Row>
            <Form.Item name="standard_work_days" label="Work Days"><InputNumber style={{width: '100%'}} /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

export default DashboardPage;