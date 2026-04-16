import React, { useMemo, useState } from 'react';
import {
  Breadcrumb,
  Button,
  Card,
  Col,
  DatePicker,
  Row,
  Select,
  Space,
  Statistic,
  Table,
  Tag,
  Typography,
  message,
  Progress,
  Result,
} from 'antd';
import dayjs from 'dayjs';
import { DualAxes } from '@ant-design/charts';
import { useAuth } from '../../context/AuthContext';
import { getMonthlyRoleCostReport, getRoleContractsList } from '../../services/roleContractsService';
import CostBreakdownChart from '../../components/role-contracts/CostBreakdownChart';
import FulfillmentCalendar from '../../components/role-contracts/FulfillmentCalendar';

const { Title, Text } = Typography;

const downloadCsv = (dailyBreakdown) => {
  const header = ['Date', 'Total Required', 'Total Filled', 'Fulfillment %', 'Daily Cost', 'Unfilled Slots'];
  const rows = dailyBreakdown.map((row) => [
    row.date,
    row.total_required,
    row.total_filled,
    Math.round((row.total_filled / Math.max(row.total_required, 1)) * 100),
    row.total_cost,
    row.unfilled_slots?.length || 0,
  ]);
  const csv = [header, ...rows].map((line) => line.join(',')).join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = `monthly-role-report-${dayjs().format('YYYYMMDD-HHmmss')}.csv`;
  link.click();
};

const MonthlyReportDashboard = () => {
  const { user } = useAuth();
  const canAccess = ['Site Manager', 'Admin', 'SuperAdmin'].includes(user?.role);

  const [contracts, setContracts] = useState([]);
  const [contractId, setContractId] = useState();
  const [monthYear, setMonthYear] = useState(dayjs());
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);

  React.useEffect(() => {
    if (!canAccess) return;
    getRoleContractsList()
      .then((list) => {
        setContracts(list || []);
        if (!contractId && list?.length) setContractId(list[0].contract_id);
      })
      .catch((error) => message.error(`Failed to load contracts: ${error.message}`));
  }, [canAccess, contractId]);

  const generate = async () => {
    if (!contractId) return message.warning('Select a contract');
    setLoading(true);
    try {
      const response = await getMonthlyRoleCostReport(contractId, monthYear.month() + 1, monthYear.year());
      setReport(response);
    } catch (error) {
      message.error(`Failed to generate report: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const trendData = useMemo(() => {
    return (report?.daily_breakdown || []).map((row) => ({
      date: dayjs(row.date).format('DD MMM'),
      fulfillmentRate: Math.round((row.total_filled / Math.max(row.total_required, 1)) * 100),
      dailyCost: Number(row.total_cost || 0),
      unfilled: row.unfilled_slots?.length || 0,
    }));
  }, [report]);

  const trendConfig = {
    data: [trendData, trendData],
    xField: 'date',
    yField: ['fulfillmentRate', 'dailyCost'],
    geometryOptions: [{ geometry: 'line', color: '#3B82F6' }, { geometry: 'column', color: '#10B981' }],
    yAxis: {
      fulfillmentRate: { max: 100 },
    },
  };

  const columns = [
    { title: 'Date', dataIndex: 'date', key: 'date' },
    { title: 'Total Required', dataIndex: 'total_required', key: 'total_required' },
    { title: 'Total Filled', dataIndex: 'total_filled', key: 'total_filled' },
    { title: 'Fulfillment %', key: 'rate', render: (_, row) => `${Math.round((row.total_filled / Math.max(row.total_required, 1)) * 100)}%` },
    { title: 'Daily Cost', key: 'total_cost', render: (_, row) => `KD ${Number(row.total_cost || 0).toFixed(2)}` },
    { title: 'Unfilled Slots', key: 'unfilled_slots', render: (_, row) => <Tag color={row.unfilled_slots?.length ? 'red' : 'green'}>{row.unfilled_slots?.length || 0}</Tag> },
    { title: 'Actions', key: 'actions', render: (_, row) => <Button type="link" onClick={() => message.info(`Details for ${row.date}`)}>View Details</Button> },
  ];

  if (!canAccess) {
    return <Result status="403" title="Access Denied" subTitle="You do not have permission to view monthly role reports." />;
  }

  return (
    <Space orientation="vertical" size={16} style={{ width: '100%' }}>
      <Breadcrumb items={[{ title: 'Home' }, { title: 'Role Contracts' }, { title: 'Monthly Report' }]} />
      <Title level={3} style={{ marginBottom: 0 }}>Monthly Cost Report Dashboard</Title>

      <Card>
        <Row gutter={[12, 12]}>
          <Col xs={24} md={8}>
            <Select
              style={{ width: '100%' }}
              value={contractId}
              onChange={setContractId}
              placeholder="Select contract"
              options={contracts.map((item) => ({ value: item.contract_id, label: item.contract_code }))}
            />
          </Col>
          <Col xs={24} md={6}>
            <DatePicker picker="month" style={{ width: '100%' }} value={monthYear} onChange={(value) => setMonthYear(value || dayjs())} />
          </Col>
          <Col xs={24} md={4}>
            <Button type="primary" loading={loading} onClick={generate} block>Generate Report</Button>
          </Col>
        </Row>
      </Card>

      {report && (
        <>
          <Row gutter={[12, 12]}>
            <Col xs={12} md={4}><Card><Statistic title="Days Recorded" value={report.total_days_recorded} /></Card></Col>
            <Col xs={12} md={4}><Card><Statistic title="Roles Required" value={report.total_roles_required} /></Card></Col>
            <Col xs={12} md={4}><Card><Statistic title="Roles Filled" value={report.total_roles_filled} /></Card></Col>
            <Col xs={24} md={4}><Card><Statistic title="Total Cost" value={report.total_cost} precision={2} prefix="KD" /></Card></Col>
            <Col xs={24} md={4}><Card><Statistic title="Shortage Impact" value={report.shortage_cost_impact} precision={2} prefix="KD" /></Card></Col>
            <Col xs={24} md={4}>
              <Card>
                <Text type="secondary">Fulfillment Rate</Text>
                <Progress percent={Math.round((report.fulfillment_rate || 0) * 100)} />
              </Card>
            </Col>
          </Row>

          <Row gutter={[12, 12]}>
            <Col xs={24} lg={10}><Card title="Cost Breakdown by Designation"><CostBreakdownChart costByDesignation={report.cost_by_designation} /></Card></Col>
            <Col xs={24} lg={14}><Card title="Daily Fulfillment Trend"><DualAxes {...trendConfig} height={300} /></Card></Col>
          </Row>

          <Card title="Fulfillment Calendar"><FulfillmentCalendar dailyBreakdown={report.daily_breakdown || []} /></Card>

          <Card title="Daily Breakdown Table">
            <Table rowKey="date" dataSource={report.daily_breakdown || []} columns={columns} pagination={{ pageSize: 10 }} scroll={{ x: 900 }} />
          </Card>

          <Space>
            <Button onClick={() => downloadCsv(report.daily_breakdown || [])}>Export CSV</Button>
            <Button onClick={() => window.print()}>Export PDF</Button>
            <Button onClick={() => window.print()}>Print Report</Button>
          </Space>
        </>
      )}

      {!report && <Card><Text type="secondary">Select filters and click Generate Report.</Text></Card>}
    </Space>
  );
};

export default MonthlyReportDashboard;
