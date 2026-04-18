import React, { useState, useEffect, useMemo } from 'react';
import { 
  Card, Row, Col, Checkbox, Avatar, Typography, Button, Input, 
  Modal, Form, Select, DatePicker, message, Spin, Space, Tag, Table, Badge, Popconfirm, Divider
} from 'antd';
import { 
  SearchOutlined, EyeOutlined, DeleteOutlined, CheckCircleOutlined, UserOutlined 
} from '@ant-design/icons';
import dayjs from 'dayjs'; 
import '../styles/DutyList.css';

// --- Services ---
import { employeeService, siteService, managerService, dutyListService } from '../services';

const { Title, Text } = Typography;
const { Option } = Select;
const { RangePicker } = DatePicker;

// Fallback for direct deletion - now using service
const deleteDutyManual = async (id) => {
    return dutyListService.deleteById(id);
};

const DutyListPage = () => {
    const [form] = Form.useForm();
    
    const [employees, setEmployees] = useState([]);
    const [sites, setSites] = useState([]);
    const [managers, setManagers] = useState([]);
    const [loading, setLoading] = useState(true);
    
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedEmployees, setSelectedEmployees] = useState([]);
    const [assignedIdsToday, setAssignedIdsToday] = useState([]); 
    
    const [isModalOpen, setIsModalOpen] = useState(false); 
    const [isSubmitting, setIsSubmitting] = useState(false);

    const [isViewModalOpen, setIsViewModalOpen] = useState(false);
    const [viewDate, setViewDate] = useState(dayjs()); 
    const [dutyListRecords, setDutyListRecords] = useState([]);
    const [loadingDuty, setLoadingDuty] = useState(false);

    // --- 1. Load Data ---
    useEffect(() => {
        fetchInitialData();
        refreshAssignedList();
    }, []);

    const fetchInitialData = async () => {
        try {
            setLoading(true);
            const [empData, siteData, adminData] = await Promise.all([
                employeeService.getAll(), siteService.getAll(), managerService.getAll()
            ]);
            setEmployees(Array.isArray(empData) ? empData : []);
            setSites(Array.isArray(siteData) ? siteData : []);
            setManagers(Array.isArray(adminData) ? adminData : []);
        } catch (err) {
            message.error("Failed to load workforce data");
        } finally {
            setLoading(false);
        }
    };

    const refreshAssignedList = async (date = dayjs()) => {
        try {
            const data = await dutyListService.getByDate(date.format('YYYY-MM-DD'));
            setAssignedIdsToday((data || []).map(d => d.employee_id));
        } catch (e) { console.error("Sync error"); }
    };

    // --- 2. Filter Logic (This fixes your ReferenceError) ---
    const filteredEmployees = useMemo(() => {
        return employees.filter(emp =>
            emp.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
            emp.designation?.toLowerCase().includes(searchTerm.toLowerCase())
        );
    }, [employees, searchTerm]);

    // O(1) manager lookup map
    const managerMap = useMemo(() => {
        return new Map(managers.map(m => [m.id, m]));
    }, [managers]);

    // --- 3. Duty List View Logic ---
    const fetchDutyRecords = async () => {
        try {
            setLoadingDuty(true);
            const dateStr = viewDate.format('YYYY-MM-DD');
            const data = await dutyListService.getByDate(dateStr);
            const mappedData = (data || []).map((record) => {
                const emp = employees.find(e => e.id === record.employee_id);
                const site = sites.find(s => s.id === record.site_id);
                const mgr = managerMap.get(record.manager_id);
                return {
                    id: record._id || record.id,
                    employee_name: emp ? emp.name : 'Unknown',
                    designation: emp ? emp.designation : '-',
                    site_name: site ? site.name : 'Unknown',
                    manager_name: mgr ? mgr.full_name : 'Assigned Manager',
                    start_date: record.start_date,
                    end_date: record.end_date
                };
            });
            setDutyListRecords(mappedData);
        } catch (error) { setDutyListRecords([]); }
        finally { setLoadingDuty(false); }
    };

    useEffect(() => {
        if (isViewModalOpen) fetchDutyRecords();
    }, [isViewModalOpen, viewDate]);

    // --- 4. Selection Handlers ---
    const handleSelectEmployee = (id) => {
        if (assignedIdsToday.includes(id)) return; 
        setSelectedEmployees(prev => 
            prev.includes(id) ? prev.filter(item => item !== id) : [...prev, id]
        );
    };

    const handleSubmitAssignment = async () => {
        try {
            const values = await form.validateFields();
            setIsSubmitting(true);

            const payload = selectedEmployees.map(eid => ({ 
                employee_id: eid, 
                site_id: parseInt(values.site_id), 
                manager_id: parseInt(values.manager_id),
                start_date: values.dateRange[0].format('YYYY-MM-DD'),
                end_date: values.dateRange[1].format('YYYY-MM-DD')
            }));

            await dutyListService.save(payload);
            message.success("Duty assigned to employees successfully");
            setIsModalOpen(false);
            setSelectedEmployees([]);
            form.resetFields();
            refreshAssignedList();
        } catch (err) { 
            message.error("Deployment failed"); 
        } finally { 
            setIsSubmitting(false); 
        }
    };

    const handleDeleteDuty = async (id) => {
        try {
            await deleteDutyManual(id);
            message.success("Duty removed");
            fetchDutyRecords();
            refreshAssignedList(viewDate);
        } catch (e) { message.error("Delete failed"); }
    };

    if (loading) return <Spin fullscreen description="Syncing Workforce Database..." />;

    return (
        <div className="layout-content">
            <Card variant="borderless" className="duty-header-card" style={{ marginBottom: 24 }}>
                <Row align="middle" justify="space-between">
                    <Col>
                        <Title level={3} style={{margin:0}}>Workforce Assignment</Title>
                        <Text type="secondary">Select employees to assign duty for the selected period.</Text>
                    </Col>
                    <Col>
                        <Space>
                            <Input 
                                placeholder="Search employees..." 
                                prefix={<SearchOutlined />} 
                                onChange={e => setSearchTerm(e.target.value)} 
                            />
                            <Button type="primary" ghost icon={<EyeOutlined />} onClick={() => setIsViewModalOpen(true)}>
                                View Records
                            </Button>
                        </Space>
                    </Col>
                </Row>
                
                <Divider />

                <Row justify="space-between" align="middle">
                    <Checkbox 
                        onChange={(e) => {
                            const available = filteredEmployees.filter(emp => !assignedIdsToday.includes(emp.id));
                            setSelectedEmployees(e.target.checked ? available.map(emp => emp.id) : []);
                        }}
                        checked={selectedEmployees.length > 0 && selectedEmployees.length === filteredEmployees.filter(emp => !assignedIdsToday.includes(emp.id)).length}
                    >
                        Select All Available ({filteredEmployees.filter(emp => !assignedIdsToday.includes(emp.id)).length})
                    </Checkbox>
                    
                    <Space>
                        <Button 
                            type="primary" 
                            icon={<UserOutlined />}
                            disabled={selectedEmployees.length === 0} 
                            onClick={() => setIsModalOpen(true)} 
                            style={{ background: '#2a9d8f', border: 'none', height: 40, borderRadius: 8 }}
                        >
                            Assign Duty ({selectedEmployees.length})
                        </Button>
                    </Space>
                </Row>
            </Card>

            <Row gutter={[20, 20]}>
                {filteredEmployees.map(emp => {
                    const isAssigned = assignedIdsToday.includes(emp.id);
                    const isSelected = selectedEmployees.includes(emp.id);
                    const assignedManager = emp.manager_id ? managerMap.get(emp.manager_id) : null;
                    return (
                        <Col key={emp.id} xs={24} sm={12} md={8} lg={6}>
                            <Card 
                                variant="borderless"
                                className={`employee-card ${isAssigned ? 'assigned-blur' : ''} ${isSelected ? 'selected-card' : ''}`}
                                onClick={() => handleSelectEmployee(emp.id)}
                                style={{ cursor: isAssigned ? 'not-allowed' : 'pointer', position: 'relative' }}
                            >
                                {assignedManager && (
                                    <Tag
                                        color="blue"
                                        style={{
                                            position: 'absolute',
                                            top: 8,
                                            right: 8,
                                            fontSize: '11px',
                                            fontWeight: 'bold',
                                            zIndex: 1
                                        }}
                                    >
                                        {assignedManager.full_name.charAt(0)}
                                    </Tag>
                                )}
                                <div className="card-inner">
                                    <Avatar size={50} src={emp.image} style={{ backgroundColor: isAssigned ? '#bfbfbf' : '#2a9d8f' }}>{emp.name?.charAt(0)}</Avatar>
                                    <div className="emp-info">
                                        <Text strong>{emp.name}</Text>
                                        <Text type="secondary" style={{fontSize:12}}>{emp.designation}</Text>
                                        {isAssigned ? <Badge status="error" text="Assigned" /> : <Badge status="success" text="Available" />}
                                    </div>
                                    {!isAssigned && <Checkbox checked={isSelected} className="card-checkbox" />}
                                    {isAssigned && <CheckCircleOutlined style={{color:'#f5222d'}} />}
                                </div>
                            </Card>
                        </Col>
                    );
                })}
            </Row>

            {/* MODAL: ASSIGN TO MANAGER */}
            <Modal 
                title="Workforce Assignment" 
                open={isModalOpen} 
                onOk={handleSubmitAssignment} 
                onCancel={() => setIsModalOpen(false)} 
                confirmLoading={isSubmitting}
                okText="Assign Duty"
                destroyOnHidden
            >
                <Form form={form} layout="vertical" initialValues={{ dateRange: [dayjs(), dayjs().add(7, 'days')] }}>
                    <Form.Item 
                        name="manager_id" 
                        label="Responsible Manager" 
                        rules={[{ required: true, message: 'Select a manager' }]}
                    >
                        <Select placeholder="Select Manager">
                            {managers.map(m => (
                                <Option key={m.id} value={m.id}>{m.full_name} (Manager)</Option>
                            ))}
                        </Select>
                    </Form.Item>

                    <Form.Item name="site_id" label="Project Site" rules={[{ required: true }]}>
                        <Select placeholder="Select Site">
                            {sites.map(s => <Option key={s.id} value={s.id}>{s.name}</Option>)}
                        </Select>
                    </Form.Item>

                    <Form.Item
                        name="dateRange"
                        label="Assignment Period"
                        rules={[{ required: true, message: 'Select start and end dates' }]}
                    >
                        <RangePicker
                            style={{ width: '100%' }}
                            format="DD/MM/YYYY"
                            placeholder={['Start Date', 'End Date']}
                        />
                    </Form.Item>
                </Form>
            </Modal>

            {/* MODAL: VIEW RECORDS */}
            <Modal title="Daily Records" open={isViewModalOpen} onCancel={() => setIsViewModalOpen(false)} footer={null} width={800}>
                <div style={{marginBottom:20}}>
                    <DatePicker value={viewDate} onChange={setViewDate} format="DD/MM/YYYY" allowClear={false} />
                </div>
                <Table 
                    columns={[
                        { title: 'Employee', dataIndex: 'employee_name' },
                        { title: 'Location', dataIndex: 'site_name', render: t => <Tag color="blue">{t}</Tag> },
                        { title: 'Manager', dataIndex: 'manager_name', render: t => <Tag color="green">{t}</Tag> },
                        { title: 'Start Date', dataIndex: 'start_date' },
                        { title: 'End Date', dataIndex: 'end_date' },
                        { title: 'Action', render: (_, r) => (
                            <Popconfirm title="Remove assignment?" onConfirm={() => handleDeleteDuty(r.id)}>
                                <Button type="text" danger icon={<DeleteOutlined />} />
                            </Popconfirm>
                        )}
                    ]} 
                    dataSource={dutyListRecords} 
                    rowKey="id"
                    loading={loadingDuty} 
                />
            </Modal>
        </div>
    );
};

export default DutyListPage;