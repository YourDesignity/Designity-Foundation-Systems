import React, { useState, useEffect } from 'react';
import { 
  Row, Col, Card, Table, Tag, Button, Typography, Space, Modal, Form, 
  Input, Select, DatePicker, Tabs, message, Badge, InputNumber, Avatar, Divider, Statistic, List
} from 'antd';
import { 
  CarOutlined, ToolOutlined, HistoryOutlined, PlusOutlined, 
  FireOutlined, DashboardOutlined, ReloadOutlined, 
  SearchOutlined, WarningOutlined, EnvironmentOutlined,
  CalendarOutlined, UserOutlined, WalletOutlined, CheckCircleOutlined,
  ArrowRightOutlined, DollarOutlined, RiseOutlined
} from '@ant-design/icons';
import dayjs from 'dayjs';

// Custom CSS for better UI (Injected via JS for this example, but keep in your .css file)
const uiStyles = {
  headerCard: {
    background: 'linear-gradient(135deg, #1890ff 0%, #096dd9 100%)',
    borderRadius: '12px',
    padding: '24px',
    marginBottom: '24px',
    color: 'white'
  },
  actionCard: {
    borderRadius: '12px',
    boxShadow: '0 4px 12px rgba(0,0,0,0.05)',
    border: '1px solid #f0f0f0'
  },
  statusTag: {
    borderRadius: '20px',
    padding: '0 12px',
    fontWeight: 500
  }
};

import { 
  getVehicles, addVehicle, getTrips, startTrip, endTrip, 
  getMaintenanceLogs, addMaintenanceLog, getFuelLogs, addFuelLog,
  getExpenses, addExpense 
} from '../services/apiService';

const { Title, Text } = Typography;
const { Option } = Select;

function VehicleManagementPage() {
  const [activeTab, setActiveTab] = useState('1');
  const [loading, setLoading] = useState(true);
  const [refreshKey, setRefreshKey] = useState(0); 
  const [searchText, setSearchText] = useState('');

  // Data
  const [vehicles, setVehicles] = useState([]);
  const [trips, setTrips] = useState([]);
  const [maintenance, setMaintenance] = useState([]);
  const [fuelLogs, setFuelLogs] = useState([]);
  const [expenses, setExpenses] = useState([]);

  // Modals
  const [modals, setModals] = useState({ 
    vehicle: false, tripStart: false, tripEnd: false, 
    maintenance: false, fuel: false, expense: false 
  });
  const [selectedTripId, setSelectedTripId] = useState(null);

  // Forms
  const [vehicleForm] = Form.useForm();
  const [tripForm] = Form.useForm();
  const [endTripForm] = Form.useForm();
  const [maintForm] = Form.useForm();
  const [fuelForm] = Form.useForm();
  const [expenseForm] = Form.useForm();

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const [v, t, m, f, e] = await Promise.all([
          getVehicles(), getTrips(), getMaintenanceLogs(), getFuelLogs(), getExpenses()
        ]);
        setVehicles(Array.isArray(v) ? v : []);
        setTrips(Array.isArray(t) ? t : []);
        setMaintenance(Array.isArray(m) ? m : []);
        setFuelLogs(Array.isArray(f) ? f : []);
        setExpenses(Array.isArray(e) ? e : []);
      } catch (err) {
        message.error("System failed to sync vehicle data.");
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [refreshKey]);

  const refreshData = () => { setLoading(true); setRefreshKey(prev => prev + 1); };
  const formatCurrency = (val) => val ? `$${val.toLocaleString(undefined, {minimumFractionDigits: 2})}` : '$0.00';

  // Stats for the top row
  const totalFleetValue = maintenance.reduce((sum, item) => sum + item.cost, 0);
  const activeTripsCount = trips.filter(t => t.status === 'Ongoing').length;

  // --- HANDLERS ---
  const handleAddVehicle = async () => {
    try {
        const values = await vehicleForm.validateFields();
        await addVehicle({
            ...values,
            registration_expiry: values.registration_expiry?.format('YYYY-MM-DD'),
            insurance_expiry: values.insurance_expiry?.format('YYYY-MM-DD'),
        });
        message.success('Vehicle registered to fleet'); setModals({...modals, vehicle:false}); vehicleForm.resetFields(); refreshData();
    } catch(e) { message.error(e.message || 'Operation failed'); }
  };

  const handleStartTrip = async () => { 
    try { 
        const values = await tripForm.validateFields();
        await startTrip(values); 
        message.success('Trip sequence started'); setModals({...modals, tripStart:false}); tripForm.resetFields(); refreshData(); 
    } catch(e){ message.error('Ensure all driver details are filled'); } 
  };

  const handleEndTrip = async () => { 
    try { 
        const v = await endTripForm.validateFields();
        await endTrip(selectedTripId, v.end_mileage, v.end_condition); 
        message.success('Trip completed & logged'); setModals({...modals, tripEnd:false}); endTripForm.resetFields(); refreshData(); 
    } catch(e){ message.error('Trip closure failed'); } 
  };

  const handleAddFuel = async () => {
    try {
        const v = await fuelForm.validateFields();
        await addFuelLog({...v, date: v.date.format('YYYY-MM-DD HH:mm')});
        message.success('Fuel entry saved'); setModals({...modals, fuel:false}); fuelForm.resetFields(); refreshData();
    } catch(e){ message.error('Fuel log failed'); }
  };

  const handleAddMaintenance = async () => {
    try {
        const v = await maintForm.validateFields();
        await addMaintenanceLog({...v, service_date: v.service_date.format('YYYY-MM-DD')});
        message.success('Maintenance record added'); setModals({...modals, maintenance:false}); maintForm.resetFields(); refreshData();
    } catch(e){ message.error('Maintenance log failed'); }
  };

  const handleAddExpense = async () => {
    try {
        const v = await expenseForm.validateFields();
        await addExpense({...v, date: dayjs().format('YYYY-MM-DD HH:mm')});
        message.success('Digital expense logged successfully'); setModals({...modals, expense:false}); expenseForm.resetFields(); refreshData();
    } catch(e){ message.error('Expense tracking failed'); }
  };

  // --- TABLE COLUMNS ---
  const vehicleColumns = [
    { 
      title: 'Vehicle Details', 
      key: 'v', 
      render: (_, r) => (
        <Space size="middle">
          <Avatar size={44} style={{ backgroundColor: '#e6f7ff', color: '#1890ff' }} icon={<CarOutlined/>} />
          <div>
            <Text strong style={{ fontSize: 16 }}>{r.model}</Text><br/>
            <Text type="secondary"><Tag color="blue" style={{margin:0}}>{r.plate}</Tag></Text>
          </div>
        </Space>
      ) 
    },
    { 
      title: 'Operating Status', 
      dataIndex: 'status', 
      render: s => (
        <Tag color={s==='Available'?'green':'processing'} style={uiStyles.statusTag}>
          {s==='Available' ? <CheckCircleOutlined /> : <ReloadOutlined spin />} {s}
        </Tag>
      ) 
    },
    { 
      title: 'Odometer Reading', 
      dataIndex: 'current_mileage', 
      render: v => <Text strong><DashboardOutlined /> {v?.toLocaleString()} km</Text> 
    }
  ];

  const tripColumns = [
    { title: 'Vehicle / Plate', dataIndex: 'vehicle_plate', render: t => <Text strong>{t}</Text> },
    { title: 'Assigned Driver', dataIndex: 'driver_name', render: d => <Space><UserOutlined style={{color:'#1890ff'}}/>{d}</Space> },
    { title: 'Departure Condition', dataIndex: 'start_condition', render: c => <Tag color="cyan">{c}</Tag> },
    { 
      title: 'Action', 
      key: 'act', 
      render: (_,r) => r.status === 'Ongoing' ? 
        <Button size="small" type="primary" danger shape="round" icon={<ArrowRightOutlined />} onClick={()=>{setSelectedTripId(r.uid); setModals({...modals, tripEnd:true})}}>End Trip</Button> : 
        <Tag color="success">Trip Finished</Tag> 
    }
  ];

  return (
    <div style={{ padding: '24px', background: '#f9f9f9', minHeight: '100vh' }}>
      
      {/* --- HERO HEADER --- */}
      <div style={uiStyles.headerCard}>
        <Row align="middle" gutter={24}>
          <Col flex="auto">
            <Title level={2} style={{ color: 'white', margin: 0 }}>Fleet Operations Dashboard</Title>
            <Text style={{ color: 'rgba(255,255,255,0.85)' }}>Real-time vehicle tracking, condition reporting, and expense auditing.</Text>
          </Col>
          <Col>
            <Button ghost size="large" icon={<ReloadOutlined spin={loading} />} onClick={refreshData}>Sync System</Button>
          </Col>
        </Row>
      </div>

      {/* --- QUICK STATS --- */}
      <Row gutter={[24, 24]} style={{ marginBottom: '24px' }}>
        <Col xs={24} sm={8}>
          <Card variant="borderless" style={uiStyles.actionCard}>
            <Statistic title="Active Fleet" value={vehicles.length} prefix={<CarOutlined style={{color: '#1890ff'}} />} />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card variant="borderless" style={uiStyles.actionCard}>
            <Statistic title="Live Trips" value={activeTripsCount} styles={{ content: { color: '#3f8600' } }} prefix={<RiseOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card variant="borderless" style={uiStyles.actionCard}>
            <Statistic title="Total Maintenance" value={totalFleetValue} precision={2} prefix={<DollarOutlined />} />
          </Card>
        </Col>
      </Row>

      <Row gutter={[24, 24]}>
        <Col xs={24} lg={17}>
          <Card variant="borderless" style={uiStyles.actionCard}>
            <Tabs 
              defaultActiveKey="1"
              type="line"
              items={[
                { key: '1', label: <span><CarOutlined />Fleet Registry</span>, children: <Table loading={loading} columns={vehicleColumns} dataSource={vehicles} rowKey="uid" pagination={{pageSize: 6}} /> },
                { key: '2', label: <span><HistoryOutlined />Trip Logs</span>, children: <Table loading={loading} columns={tripColumns} dataSource={trips} rowKey="uid" /> },
                { key: '3', label: <span><WalletOutlined />Daily Expenses</span>, children: <Table loading={loading} columns={[
                    { title: 'Date/Time', dataIndex: 'date', render: d => <Text type="secondary">{d}</Text> },
                    { title: 'Category', dataIndex: 'category', render: c => <Tag color="gold" style={{borderRadius:'10px'}}>{c}</Tag> },
                    { title: 'Amount', dataIndex: 'amount', render: v => <Text strong style={{color:'#cf1322'}}>{formatCurrency(v)}</Text> },
                    { title: 'Recorded By', dataIndex: 'driver_name', render: d => <Text>{d}</Text> }
                ]} dataSource={expenses} rowKey="uid" /> },
                { key: '4', label: <span><ToolOutlined />Maintenance</span>, children: <Table loading={loading} columns={[
                    { title: 'Service Date', dataIndex: 'service_date' },
                    { title: 'Vehicle', dataIndex: 'vehicle_plate' },
                    { title: 'Type', dataIndex: 'service_type', render: t => <Tag color="magenta">{t}</Tag> },
                    { title: 'Cost', dataIndex: 'cost', render: formatCurrency }
                ]} dataSource={maintenance} rowKey="uid" /> },
                { key: '5', label: <span><FireOutlined />Fuel Records</span>, children: <Table loading={loading} columns={[
                    { title: 'Refuel Date', dataIndex: 'date' },
                    { title: 'Vehicle', dataIndex: 'vehicle_plate' },
                    { title: 'Liters', dataIndex: 'liters', render: l => `${l}L` },
                    { title: 'Total Cost', dataIndex: 'cost', render: formatCurrency }
                ]} dataSource={fuelLogs} rowKey="uid" /> },
            ]} />
          </Card>
        </Col>

        {/* --- SIDEBAR ACTIONS --- */}
        <Col xs={24} lg={7}>
          <Card title={<Text strong><PlusOutlined /> Quick Operations</Text>} variant="borderless" style={uiStyles.actionCard}>
             <Space orientation="vertical" style={{ width: '100%' }} size="middle">
                <Button type="primary" size="large" block icon={<HistoryOutlined />} style={{ height: '50px', borderRadius: '8px' }} onClick={()=>setModals({...modals, tripStart:true})}>Start Daily Trip</Button>
                <Button size="large" block icon={<WalletOutlined />} style={{ height: '50px', borderRadius: '8px', color: '#d46b08', borderColor: '#ffd591', background: '#fff7e6' }} onClick={()=>setModals({...modals, expense:true})}>Log Toll/Parking</Button>
                <Button size="large" block icon={<FireOutlined />} style={{ height: '50px', borderRadius: '8px', color: '#389e0d', borderColor: '#b7eb8f', background: '#f6ffed' }} onClick={()=>setModals({...modals, fuel:true})}>Refuel Entry</Button>
                <Button size="large" block icon={<ToolOutlined />} style={{ height: '50px', borderRadius: '8px', color: '#cf1322', borderColor: '#ffa39e', background: '#fff1f0' }} onClick={()=>setModals({...modals, maintenance:true})}>Record Maintenance</Button>
                <Divider style={{ margin: '12px 0' }} />
                <Button type="dashed" size="large" block icon={<PlusOutlined />} style={{ height: '50px', borderRadius: '8px' }} onClick={()=>setModals({...modals, vehicle:true})}>Register New Vehicle</Button>
             </Space>
          </Card>

          <Card style={{ ...uiStyles.actionCard, marginTop: '24px' }} title={<Text strong><WarningOutlined style={{color:'#faad14'}}/> System Alerts</Text>}>
              <List
                size="small"
                dataSource={vehicles.filter(v => v.current_mileage > 10000)} // Example alert logic
                renderItem={item => (
                    <List.Item>
                        <Badge status="warning" text={`${item.plate} is due for check-up`} />
                    </List.Item>
                )}
              />
          </Card>
        </Col>
      </Row>

      {/* --- ALL MODALS --- */}
      
      {/* Modal: Add Vehicle */}
      <Modal title={<span><PlusOutlined /> Register Vehicle to Fleet</span>} open={modals.vehicle} onCancel={()=>setModals({...modals, vehicle:false})} onOk={handleAddVehicle} okText="Add Vehicle">
         <Form form={vehicleForm} layout="vertical">
            <Form.Item name="model" label="Vehicle Model" rules={[{required:true}]}><Input placeholder="e.g. Toyota HiAce 2024"/></Form.Item>
            <Form.Item name="plate" label="License Plate Number" rules={[{required:true}]}><Input placeholder="ABC-1234"/></Form.Item>
            <Form.Item name="type" label="Vehicle Classification"><Select placeholder="Select Type"><Option value="Van">Van / Passenger</Option><Option value="Truck">Truck / Logistics</Option><Option value="Car">Sedan / SUV</Option></Select></Form.Item>
            <Row gutter={16}><Col span={12}><Form.Item name="registration_expiry" label="Reg. Expiry"><DatePicker style={{width:'100%'}}/></Form.Item></Col><Col span={12}><Form.Item name="insurance_expiry" label="Insurance Expiry"><DatePicker style={{width:'100%'}}/></Form.Item></Col></Row>
         </Form>
      </Modal>

      {/* Modal: Start Trip */}
      <Modal title={<span><HistoryOutlined /> Start Trip Report</span>} open={modals.tripStart} onCancel={()=>setModals({...modals, tripStart:false})} onOk={handleStartTrip}>
         <Form form={tripForm} layout="vertical">
            <Form.Item name="vehicle_uid" label="Select Available Vehicle" rules={[{required:true}]}><Select options={vehicles.filter(v=>v.status==='Available').map(v=>({value:v.uid, label:v.plate}))}/></Form.Item>
            <Form.Item name="driver_name" label="Driver in Charge" rules={[{required:true}]}><Input prefix={<UserOutlined/>} placeholder="Full name"/></Form.Item>
            <Form.Item name="start_condition" label="Vehicle Condition Statement" initialValue="Good Condition"><Select><Option value="Good Condition">Clean & No Damage</Option><Option value="Minor Scratches">Minor Exterior Damage</Option><Option value="Interior Dirty">Interior Needs Cleaning</Option></Select></Form.Item>
            <Form.Item name="purpose" label="Trip Objective" rules={[{required:true}]}><Input placeholder="e.g. Delivery to Site A"/></Form.Item>
         </Form>
      </Modal>

      {/* Modal: Fuel */}
      <Modal title={<span><FireOutlined /> Refuel Entry</span>} open={modals.fuel} onCancel={()=>setModals({...modals, fuel:false})} onOk={handleAddFuel}>
         <Form form={fuelForm} layout="vertical">
            <Form.Item name="vehicle_uid" label="Vehicle" rules={[{required:true}]}><Select options={vehicles.map(v=>({value:v.uid, label:v.plate}))}/></Form.Item>
            <Row gutter={16}><Col span={12}><Form.Item name="liters" label="Volume (Liters)" rules={[{required:true}]}><InputNumber style={{width:'100%'}}/></Form.Item></Col><Col span={12}><Form.Item name="cost" label="Total Bill Cost" rules={[{required:true}]}><InputNumber style={{width:'100%'}} prefix="$"/></Form.Item></Col></Row>
            <Row gutter={16}><Col span={12}><Form.Item name="odometer" label="Current Odometer (km)" rules={[{required:true}]}><InputNumber style={{width:'100%'}}/></Form.Item></Col><Col span={12}><Form.Item name="date" label="Refuel Date/Time" rules={[{required:true}]}><DatePicker showTime style={{width:'100%'}}/></Form.Item></Col></Row>
         </Form>
      </Modal>

      {/* Modal: Maintenance */}
      <Modal title={<span><ToolOutlined /> Service & Maintenance Record</span>} open={modals.maintenance} onCancel={()=>setModals({...modals, maintenance:false})} onOk={handleAddMaintenance}>
         <Form form={maintForm} layout="vertical">
            <Form.Item name="vehicle_uid" label="Vehicle" rules={[{required:true}]}><Select options={vehicles.map(v=>({value:v.uid, label:v.plate}))}/></Form.Item>
            <Form.Item name="service_type" label="Service Category" rules={[{required:true}]}><Select><Option value="Oil Change">Oil Change</Option><Option value="Brake Pad Replace">Brake Systems</Option><Option value="Tire Rotation">Tire Maintenance</Option><Option value="Full Service">Major Service</Option></Select></Form.Item>
            <Row gutter={16}><Col span={12}><Form.Item name="cost" label="Service Cost" rules={[{required:true}]}><InputNumber style={{width:'100%'}} prefix="$"/></Form.Item></Col><Col span={12}><Form.Item name="service_date" label="Service Date" rules={[{required:true}]}><DatePicker style={{width:'100%'}}/></Form.Item></Col></Row>
         </Form>
      </Modal>

      {/* Modal: Expenses */}
      <Modal title={<span><WalletOutlined /> Digital Expense Log</span>} open={modals.expense} onCancel={()=>setModals({...modals, expense:false})} onOk={handleAddExpense}>
         <Form form={expenseForm} layout="vertical">
            <Form.Item name="vehicle_uid" label="Associated Vehicle" rules={[{required:true}]}><Select options={vehicles.map(v=>({value:v.uid, label:v.plate}))}/></Form.Item>
            <Form.Item name="driver_name" label="Staff Member Name" rules={[{required:true}]}><Input/></Form.Item>
            <Row gutter={16}><Col span={12}><Form.Item name="category" label="Expense Type"><Select><Option value="Toll">Salik / Toll Fee</Option><Option value="Parking">Public Parking</Option><Option value="Cleaning">Car Wash / Cleaning</Option><Option value="Fine">Traffic Violation Fine</Option></Select></Form.Item></Col><Col span={12}><Form.Item name="amount" label="Amount Paid" rules={[{required:true}]}><InputNumber style={{width:'100%'}} prefix="$"/></Form.Item></Col></Row>
         </Form>
      </Modal>

      {/* Modal: End Trip */}
      <Modal title={<span><CheckCircleOutlined /> Finalize Trip Record</span>} open={modals.tripEnd} onCancel={()=>setModals({...modals, tripEnd:false})} onOk={handleEndTrip}>
         <Form form={endTripForm} layout="vertical">
            <Form.Item name="end_mileage" label="Arrival Odometer Reading (km)" rules={[{required:true}]}><InputNumber style={{width:'100%'}}/></Form.Item>
            <Form.Item name="end_condition" label="Final Vehicle Status" initialValue="No Changes"><Select><Option value="No Changes">No Changes (Same as Start)</Option><Option value="Minor Damage">New Minor Damage</Option><Option value="Needs Cleaning">Interior Needs Cleaning</Option><Option value="Major Issue">Mechanical Issue Found</Option></Select></Form.Item>
         </Form>
      </Modal>

    </div>
  );
}

export default VehicleManagementPage;