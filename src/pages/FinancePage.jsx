/**
 * FinancePage.jsx — Complete rewrite
 *
 * Features:
 * - Date range picker for all charts (tweakable by any period)
 * - Revenue vs Costs line chart (real invoice data)
 * - Cost breakdown donut — all 6 categories, graceful empty state
 * - Monthly stacked bar — employee / fleet / external / overhead
 * - Contract profitability horizontal bar
 * - Cash flow waterfall — NaN-safe, all values validated
 * - Efficiency gauges — profit margin, utilization, burn rate
 * - Invoice summary table
 * - Excel export of all data
 * - Tally-equivalent: P&L, receivables, payables, cash position
 */

import React, { useState, useCallback, useEffect } from 'react';
import {
  Row, Col, Card, Statistic, Typography, Spin, Tag,
  Result, Button, Alert, Space, Table, DatePicker,
  Divider, Tooltip, Badge, Progress,
} from 'antd';
import {
  ArrowUpOutlined, ArrowDownOutlined, ReloadOutlined,
  FileExcelOutlined, BarChartOutlined, WarningOutlined,
  CheckCircleOutlined, DollarOutlined, RiseOutlined,
  FallOutlined, TeamOutlined, CalendarOutlined,
} from '@ant-design/icons';
import { Line, Column, Pie, Bar, Gauge, Waterfall } from '@ant-design/charts';
import ExcelJS from 'exceljs';
import dayjs from 'dayjs';
import '../styles/FinancePage.css';
import { financeService } from '../services';
import { useAuth } from '../context/AuthContext';
import { usePermission } from '../hooks/usePermission';
import { PERMISSIONS } from '../constants/permissions';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;

// ── Safe number ────────────────────────────────────────────────────────────────
const n = (v, decimals = 2) => {
  const f = parseFloat(v ?? 0);
  return isNaN(f) ? 0 : parseFloat(f.toFixed(decimals));
};

const kwd = (v) => {
  const f = n(v, 3);
  return `${f < 0 ? '-' : ''}${Math.abs(f).toLocaleString('en-KW', { minimumFractionDigits: 2 })} KWD`;
};

const pct = (v) => `${n(v, 1)}%`;

// ── KPI Card ──────────────────────────────────────────────────────────────────
const KpiCard = ({ title, value, sub, trend, color, icon, prefix }) => (
  <Card size="small" style={{ borderTop: `3px solid ${color}`, height: '100%' }}>
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
      <div>
        <Text type="secondary" style={{ fontSize: 12 }}>{title}</Text>
        <div style={{ fontSize: 22, fontWeight: 800, color, marginTop: 4, lineHeight: 1.2 }}>
          {prefix}{value}
        </div>
        {sub && <Text type="secondary" style={{ fontSize: 11, marginTop: 4, display: 'block' }}>{sub}</Text>}
        {trend != null && (
          <span style={{ fontSize: 12, color: trend >= 0 ? '#52c41a' : '#ff4d4f', marginTop: 4, display: 'inline-flex', alignItems: 'center', gap: 3 }}>
            {trend >= 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />} {Math.abs(n(trend, 1))}%
          </span>
        )}
      </div>
      <div style={{ fontSize: 28, color, opacity: 0.15 }}>{icon}</div>
    </div>
  </Card>
);

// ── Empty chart placeholder ────────────────────────────────────────────────────
const EmptyChart = ({ label }) => (
  <div style={{ height: 220, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: '#bfbfbf' }}>
    <BarChartOutlined style={{ fontSize: 36, marginBottom: 8 }} />
    <Text type="secondary">{label || 'No data available'}</Text>
  </div>
);

// ── Main component ─────────────────────────────────────────────────────────────
const FinancePage = () => {
  const { user } = useAuth();
  const { hasPermission } = usePermission();
  const [loading, setLoading]   = useState(true);
  const [data, setData]         = useState(null);
  const [error, setError]       = useState(null);
  const [dateRange, setDateRange] = useState(null); // [dayjs, dayjs] | null

  const canView = hasPermission(PERMISSIONS.FINANCE_VIEW);

  const loadData = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const params = {};
      if (dateRange?.[0]) params.date_from = dateRange[0].format('YYYY-MM-DD');
      if (dateRange?.[1]) params.date_to   = dateRange[1].format('YYYY-MM-DD');

      const qs = new URLSearchParams(params).toString();
      const result = await financeService.getAdvancedSummary(qs ? `?${qs}` : '');
      setData(result);
    } catch (e) {
      setError(e.message || 'Failed to load financial data.');
    } finally {
      setLoading(false);
    }
  }, [dateRange]);

  useEffect(() => { if (canView) loadData(); }, [canView, loadData]);

  // ── Export ────────────────────────────────────────────────────────────────
  const exportToExcel = async () => {
    if (!data) return;
    const wb = new ExcelJS.Workbook();
    wb.creator = 'Designity Finance';

    const addSheet = (name, cols, rows) => {
      const ws = wb.addWorksheet(name);
      ws.columns = cols;
      ws.addRows(rows);
      ws.getRow(1).font = { bold: true };
    };

    const ov = data.overview || {};
    addSheet('Overview',
      [{ header: 'Metric', key: 'm', width: 30 }, { header: 'Value (KWD)', key: 'v', width: 20 }],
      [
        { m: 'Total Revenue (Received)', v: n(ov.total_revenue) },
        { m: 'Total Billed', v: n(ov.total_billed) },
        { m: 'Outstanding', v: n(ov.outstanding) },
        { m: 'Total Costs', v: n(ov.total_costs) },
        { m: 'Net Profit', v: n(ov.net_profit) },
        { m: 'Profit Margin (%)', v: n(ov.profit_margin) },
        { m: 'MoM Change (%)', v: n(ov.mom_change) },
      ]
    );

    addSheet('Monthly Trend',
      ['month', 'revenue', 'costs', 'profit', 'margin', 'employee_costs', 'fleet_costs', 'overhead'].map(k => ({
        header: k.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()), key: k, width: 16,
      })),
      (data.monthly_trend || []).map(m => ({
        month: m.month, revenue: n(m.revenue), costs: n(m.costs), profit: n(m.profit),
        margin: n(m.margin), employee_costs: n(m.employee_costs),
        fleet_costs: n(m.fleet_costs), overhead: n(m.overhead),
      }))
    );

    addSheet('Contract P&L',
      ['contract_name', 'revenue', 'costs', 'profit', 'margin', 'status'].map(k => ({
        header: k.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()), key: k, width: 20,
      })),
      (data.contract_profitability || []).map(c => ({
        contract_name: c.contract_name, revenue: n(c.revenue), costs: n(c.costs),
        profit: n(c.profit), margin: n(c.margin), status: c.status,
      }))
    );

    const buf = await wb.xlsx.writeBuffer();
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([buf], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }));
    a.download = `Finance_${dayjs().format('YYYY-MM-DD')}.xlsx`;
    a.click(); a.remove();
  };

  // ── Access guard ──────────────────────────────────────────────────────────
  if (!canView) return (
    <Result status="403" title="Access Denied"
      subTitle="You do not have permission to view financial data."
      extra={<Button type="primary" href="/dashboard">Back to Dashboard</Button>} />
  );

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '60vh' }}>
      <Spin size="large" />
    </div>
  );

  if (error) return (
    <div style={{ padding: 24 }}>
      <Alert type="error" title="Failed to Load Financial Data" description={error}
        action={<Button onClick={loadData} icon={<ReloadOutlined />}>Retry</Button>} />
    </div>
  );

  const ov       = data?.overview || {};
  const monthly  = data?.monthly_trend || [];
  const cb       = data?.cost_breakdown || {};
  const contracts = data?.contract_profitability || [];
  const atRisk   = data?.at_risk_contracts || [];
  const cf       = data?.cash_flow || {};
  const eff      = data?.efficiency_metrics || {};
  const invSum   = data?.invoice_summary || {};

  const profitPositive = n(ov.net_profit) >= 0;

  // ── Chart data ─────────────────────────────────────────────────────────────

  // 1. Revenue vs Costs line
  const lineData = monthly.flatMap(m => [
    { month: m.month, value: n(m.revenue), category: 'Revenue' },
    { month: m.month, value: n(m.costs),   category: 'Costs' },
    { month: m.month, value: n(m.profit),  category: 'Profit' },
  ]);

  const lineConfig = {
    data: lineData, xField: 'month', yField: 'value', colorField: 'category',
    smooth: true,
    point: { shapeField: 'circle', sizeField: 4 },
    color: ['#52c41a', '#ff4d4f', '#1677ff'],
    legend: { position: 'top' },
    tooltip: { formatter: d => ({ name: d.category, value: kwd(d.value) }) },
    yAxis: { label: { formatter: v => `${(n(v) / 1000).toFixed(0)}K` } },
  };

  // 2. Cost breakdown donut
  const donutRaw = [
    { type: 'Employee Salaries', value: n(cb.employee_salaries) },
    { type: 'Overtime',          value: n(cb.overtime) },
    { type: 'External Workers',  value: n(cb.external_workers) },
    { type: 'Fleet Fuel',        value: n(cb.fleet_fuel) },
    { type: 'Fleet Maintenance', value: n(cb.fleet_maintenance) },
    { type: 'Overhead',          value: n(cb.overhead) },
  ];
  const donutData = donutRaw.filter(d => d.value > 0);
  const hasDonut  = donutData.length > 0;

  const donutConfig = {
    data: donutData, angleField: 'value', colorField: 'type',
    radius: 0.85, innerRadius: 0.62,
    color: ['#1677ff', '#faad14', '#52c41a', '#fa8c16', '#f5222d', '#13c2c2'],
    label: {
      type: 'inner', offset: '-30%',
      content: ({ percent }) => `${(percent * 100).toFixed(0)}%`,
      style: { fill: '#fff', fontSize: 11, fontWeight: 600 },
    },
    legend: { position: 'bottom', layout: 'horizontal' },
    statistic: {
      title: { content: 'Total\nCosts' },
      content: { content: kwd(ov.total_costs) },
    },
    tooltip: { formatter: d => ({ name: d.type, value: kwd(d.value) }) },
  };

  // 3. Stacked monthly cost column
  const stackData = monthly.flatMap(m => [
    { month: m.month, value: n(m.employee_costs), category: 'Employee' },
    { month: m.month, value: n(m.fleet_costs),    category: 'Fleet' },
    { month: m.month, value: n(m.external_costs), category: 'External' },
    { month: m.month, value: n(m.overhead),        category: 'Overhead' },
  ]);
  const stackConfig = {
    data: stackData, xField: 'month', yField: 'value', colorField: 'category',
    stack: true,
    color: ['#1677ff', '#fa8c16', '#52c41a', '#bfbfbf'],
    legend: { position: 'top' },
    tooltip: { formatter: d => ({ name: d.category, value: kwd(d.value) }) },
    yAxis: { label: { formatter: v => `${(n(v) / 1000).toFixed(0)}K` } },
  };

  // 4. Contract profitability bar
  const barData = contracts.slice(0, 12).map(c => ({
    contract: c.contract_name?.length > 22 ? c.contract_name.slice(0, 22) + '…' : c.contract_name,
    profit: n(c.profit), status: c.status, margin: n(c.margin),
  }));
  const hasBar = barData.length > 0;
  const barConfig = {
    data: barData, xField: 'profit', yField: 'contract',
    colorField: 'status',
    color: ({ status }) => status === 'profitable' ? '#52c41a' : status === 'at-risk' ? '#faad14' : '#ff4d4f',
    label: { position: 'right', formatter: d => `${d.margin}%`, style: { fontSize: 11 } },
    tooltip: { formatter: d => ({ name: d.contract, value: `Profit: ${kwd(d.profit)} | Margin: ${d.margin}%` }) },
  };

  // 5. Waterfall — NaN-safe
  const wfData = [
    { label: 'Opening',  value: n(cf.starting_balance), isTotal: false },
    ...((cf.breakdown || []).map(b => ({
      label:   b.category,
      value:   b.type === 'inflow' ? n(b.amount) : -n(b.amount),
      isTotal: false,
    }))),
    { label: 'Closing',  value: n(cf.ending_balance), isTotal: true },
  ].filter(d => !isNaN(d.value));

  const wfConfig = {
    data: wfData, xField: 'label', yField: 'value',
    risingFill: '#52c41a', fallingFill: '#ff4d4f',
    total: { label: 'Closing Balance', style: { fill: '#1677ff' } },
    label: { formatter: d => `${(n(d.value) / 1000).toFixed(1)}K`, style: { fontSize: 10 } },
    tooltip: { formatter: d => ({ name: d.label, value: kwd(d.value) }) },
  };

  // 6. Gauge configs
  const makeGauge = (target, total, content, colorScheme) => ({
    data: { target: Math.max(0, Math.min(n(target), n(total))), total: Math.max(n(total), 1), name: '' },
    legend: false,
    range: { color: colorScheme, width: 12 },
    gauge: { type: 'meter', steps: 50, stepRatio: 0.6 },
    statistic: { content: { formatter: () => content, style: { fontSize: '16px', fontWeight: 700 } } },
  });

  const marginGauge = makeGauge(
    Math.max(0, n(ov.profit_margin)), 100,
    pct(ov.profit_margin),
    ['#ff4d4f', '#faad14', '#52c41a']
  );
  const utilGauge = makeGauge(
    n(eff.utilization_rate), 100,
    pct(eff.utilization_rate),
    ['#ff4d4f', '#faad14', '#52c41a']
  );
  const burnMax = Math.max(n(eff.burn_rate_daily) * 2, 1);
  const burnGauge = makeGauge(
    n(eff.burn_rate_daily), burnMax,
    `${n(eff.burn_rate_daily, 0)} KWD/d`,
    ['#52c41a', '#faad14', '#ff4d4f']
  );

  // ── Invoice table ─────────────────────────────────────────────────────────
  const invCols = [
    { title: 'Metric', dataIndex: 'm', key: 'm', width: 200 },
    { title: 'Value', dataIndex: 'v', key: 'v', align: 'right' },
  ];
  const invRows = [
    { m: 'Total Billed',   v: kwd(invSum.total_billed) },
    { m: 'Total Received', v: <Text style={{ color: '#52c41a', fontWeight: 600 }}>{kwd(invSum.total_received)}</Text> },
    { m: 'Outstanding',    v: <Text style={{ color: n(invSum.total_pending) > 0 ? '#fa8c16' : '#666' }}>{kwd(invSum.total_pending)}</Text> },
    { m: 'Total Invoices', v: invSum.invoice_count ?? 0 },
    { m: 'Paid',           v: <Tag color="green">{invSum.paid_count ?? 0}</Tag> },
    { m: 'Overdue',        v: <Tag color={invSum.overdue_count > 0 ? 'red' : 'default'}>{invSum.overdue_count ?? 0}</Tag> },
  ];

  return (
    <div className="finance-container">

      {/* ── Header ───────────────────────────────────────────────────────── */}
      <div className="finance-header-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24, flexWrap: 'wrap', gap: 12 }}>
        <div>
          <Title level={2} style={{ margin: 0 }}>
            <BarChartOutlined style={{ marginRight: 10 }} />Financial Dashboard
          </Title>
          <Text type="secondary">Profit & Loss Analytics — Confidential</Text>
        </div>
        <Space wrap>
          <RangePicker
            value={dateRange}
            onChange={setDateRange}
            format="MMM YYYY"
            picker="month"
            placeholder={['From month', 'To month']}
            style={{ borderRadius: 8 }}
          />
          <Button icon={<ReloadOutlined />} onClick={loadData} loading={loading}>Refresh</Button>
          <Button icon={<FileExcelOutlined />} onClick={exportToExcel} style={{ background: '#217346', color: '#fff', border: 'none' }}>
            Export Excel
          </Button>
        </Space>
      </div>

      {/* ── KPI Row ───────────────────────────────────────────────────────── */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={6}>
          <KpiCard title="Total Revenue" value={kwd(ov.total_revenue)}
            sub={`Billed: ${kwd(ov.total_billed)}`} trend={ov.ytd_growth}
            color="#52c41a" icon={<DollarOutlined />} />
        </Col>
        <Col xs={24} sm={12} md={6}>
          <KpiCard title="Total Costs" value={kwd(ov.total_costs)}
            sub={`Outstanding: ${kwd(ov.outstanding)}`}
            color="#ff4d4f" icon={<FallOutlined />} />
        </Col>
        <Col xs={24} sm={12} md={6}>
          <KpiCard title="Net Profit" value={kwd(ov.net_profit)}
            trend={ov.mom_change} sub="Month-on-Month"
            color={profitPositive ? '#1677ff' : '#ff4d4f'} icon={<RiseOutlined />} />
        </Col>
        <Col xs={24} sm={12} md={6}>
          <KpiCard title="Profit Margin" value={pct(ov.profit_margin)}
            sub={`Burn: ${kwd(eff.burn_rate_daily)}/day`}
            color={n(ov.profit_margin) > 15 ? '#52c41a' : n(ov.profit_margin) > 0 ? '#faad14' : '#ff4d4f'}
            icon={<BarChartOutlined />} />
        </Col>
      </Row>

      {/* ── Revenue vs Costs + Cost Donut ────────────────────────────────── */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={15}>
          <Card title="Revenue vs Costs Trend (6 Months)" size="small">
            {lineData.length > 0
              ? <Line {...lineConfig} height={240} />
              : <EmptyChart label="No revenue data — run seed script or log invoices" />}
          </Card>
        </Col>
        <Col xs={24} lg={9}>
          <Card title="Cost Distribution" size="small">
            {hasDonut
              ? <Pie {...donutConfig} height={240} />
              : <EmptyChart label="No cost data available yet" />}
          </Card>
        </Col>
      </Row>

      {/* ── Monthly Cost Breakdown + Invoice Summary ─────────────────────── */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={15}>
          <Card title="Monthly Cost Breakdown by Category" size="small">
            {stackData.length > 0
              ? <Column {...stackConfig} height={240} />
              : <EmptyChart label="No cost data available" />}
          </Card>
        </Col>
        <Col xs={24} lg={9}>
          <Card title="Invoice Summary" size="small">
            <Table dataSource={invRows} columns={invCols} rowKey="m"
              pagination={false} size="small"
              showHeader={false} style={{ marginTop: 4 }} />
            <Divider style={{ margin: '12px 0' }} />
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <Text type="secondary" style={{ fontSize: 12 }}>Collection Rate</Text>
              <Text strong style={{ fontSize: 12 }}>
                {invSum.total_billed > 0
                  ? pct((invSum.total_received / invSum.total_billed) * 100)
                  : '—'}
              </Text>
            </div>
            <Progress
              percent={invSum.total_billed > 0 ? n((invSum.total_received / invSum.total_billed) * 100, 1) : 0}
              strokeColor="#52c41a" size="small" style={{ marginTop: 6 }} />
          </Card>
        </Col>
      </Row>

      {/* ── Contract Profitability ────────────────────────────────────────── */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={16}>
          <Card title="Contract Profitability" size="small">
            {hasBar
              ? <Bar {...barConfig} height={Math.max(200, barData.length * 32)} />
              : <EmptyChart label="No contracts with financial data" />}
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="At-Risk Contracts" size="small" style={{ height: '100%' }}>
            {atRisk.length === 0 ? (
              <div style={{ padding: '16px 0', textAlign: 'center' }}>
                <CheckCircleOutlined style={{ fontSize: 24, color: '#52c41a', marginBottom: 8 }} />
                <div><Text type="secondary">All contracts operating profitably.</Text></div>
              </div>
            ) : (
              atRisk.map(c => (
                <div key={c.contract_id} style={{ marginBottom: 12, padding: '10px 12px', background: c.risk_level === 'high' ? '#fff1f0' : '#fffbe6', borderRadius: 8, border: `1px solid ${c.risk_level === 'high' ? '#ffccc7' : '#ffe58f'}` }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <Text strong style={{ fontSize: 13 }}>{c.contract_name}</Text>
                    <Tag color={c.risk_level === 'high' ? 'red' : 'orange'}>
                      {c.risk_level === 'high' ? 'LOSS' : 'AT RISK'}
                    </Tag>
                  </div>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    Margin: {pct(c.margin)} · {kwd(c.profit)}
                  </Text>
                </div>
              ))
            )}
          </Card>
        </Col>
      </Row>

      {/* ── Cash Flow Waterfall ───────────────────────────────────────────── */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={24}>
          <Card title="Cash Flow Analysis (Waterfall)" size="small">
            {wfData.length > 2
              ? <Waterfall {...wfConfig} height={260} />
              : <EmptyChart label="Insufficient cash flow data" />}
          </Card>
        </Col>
      </Row>

      {/* ── Efficiency Gauges ─────────────────────────────────────────────── */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        {[
          { title: 'Profit Margin', config: marginGauge, sub: 'Target: 20%+' },
          { title: 'Workforce Utilization', config: utilGauge, sub: `${pct(eff.utilization_rate)} of employees assigned` },
          { title: 'Cash Runway', config: burnGauge, sub: `Runway: ~${eff.cash_runway_days ?? 0} days` },
        ].map(({ title, config, sub }) => (
          <Col xs={24} sm={8} key={title}>
            <Card title={title} size="small">
              <Gauge {...config} height={180} />
              <div style={{ textAlign: 'center', marginTop: 8 }}>
                <Text type="secondary" style={{ fontSize: 12 }}>{sub}</Text>
              </div>
            </Card>
          </Col>
        ))}
      </Row>

      {/* ── Efficiency Metrics Summary ────────────────────────────────────── */}
      <Card title="Efficiency Metrics Summary" size="small" style={{ marginBottom: 24 }}>
        <Row gutter={[16, 16]}>
          {[
            { label: 'Profit / Employee',   value: kwd(eff.profit_per_employee) },
            { label: 'Revenue / Employee',  value: kwd(eff.revenue_per_employee) },
            { label: 'Cost / Employee',     value: kwd(eff.cost_per_employee) },
            { label: 'Profit / Hour',       value: kwd(eff.profit_per_hour) },
            { label: 'Daily Burn Rate',     value: `${kwd(eff.burn_rate_daily)}/day` },
            { label: 'Cash Runway',         value: `${eff.cash_runway_days ?? 0} days` },
          ].map(m => (
            <Col xs={12} sm={8} md={4} key={m.label}>
              <div style={{ textAlign: 'center', padding: '12px 8px', background: '#fafafa', borderRadius: 8 }}>
                <div style={{ fontSize: 16, fontWeight: 700, color: '#1E3A5F' }}>{m.value}</div>
                <div style={{ fontSize: 11, color: '#888', marginTop: 4 }}>{m.label}</div>
              </div>
            </Col>
          ))}
        </Row>
      </Card>

    </div>
  );
};

export default FinancePage;
