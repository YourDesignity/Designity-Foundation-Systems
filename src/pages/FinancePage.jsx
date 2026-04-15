import React, { useState, useEffect, useCallback } from 'react';
import {
    Row, Col, Card, Statistic, Typography, Spin, Tag,
    Result, Button, Alert, Space
} from 'antd';
import {
    ArrowUpOutlined, ArrowDownOutlined, DollarOutlined,
    BarChartOutlined, RiseOutlined, WarningOutlined,
    FileExcelOutlined, ReloadOutlined
} from '@ant-design/icons';
import { Line, Column, Pie, Bar, Gauge, Waterfall } from '@ant-design/charts';
import ExcelJS from 'exceljs';
import '../styles/FinancePage.css';
import { getAdvancedFinancialSummary } from '../services/apiService';
import { useAuth } from '../context/AuthContext';
import { usePermission } from '../hooks/usePermission';
import { PERMISSIONS } from '../constants/permissions';

const { Title, Text } = Typography;

// ── Excel export helper ───────────────────────────────────────────────────────
const exportToExcel = async (data) => {
    try {
        const wb = new ExcelJS.Workbook();
        wb.creator = 'Montreal Finance';
        wb.created = new Date();

        // Sheet 1 – Overview
        const ws1 = wb.addWorksheet('Overview');
        ws1.columns = [
            { header: 'Metric', key: 'metric', width: 30 },
            { header: 'Value (KWD)', key: 'value', width: 20 },
        ];
        const ov = data.overview;
        ws1.addRows([
            { metric: 'Total Revenue', value: ov.total_revenue },
            { metric: 'Total Costs', value: ov.total_costs },
            { metric: 'Net Profit', value: ov.net_profit },
            { metric: 'Profit Margin (%)', value: ov.profit_margin },
            { metric: 'YTD Growth (%)', value: ov.ytd_growth },
            { metric: 'MoM Change (%)', value: ov.mom_change },
        ]);

        // Sheet 2 – Monthly Trends
        const ws2 = wb.addWorksheet('Monthly Trends');
        ws2.columns = [
            { header: 'Month', key: 'month', width: 12 },
            { header: 'Revenue', key: 'revenue', width: 16 },
            { header: 'Costs', key: 'costs', width: 16 },
            { header: 'Profit', key: 'profit', width: 16 },
            { header: 'Margin (%)', key: 'margin', width: 14 },
        ];
        ws2.addRows(data.monthly_trend);

        // Sheet 3 – Contracts
        const ws3 = wb.addWorksheet('Contracts');
        ws3.columns = [
            { header: 'Contract', key: 'contract_name', width: 30 },
            { header: 'Revenue', key: 'revenue', width: 16 },
            { header: 'Costs', key: 'costs', width: 16 },
            { header: 'Profit', key: 'profit', width: 16 },
            { header: 'Margin (%)', key: 'margin', width: 14 },
            { header: 'Status', key: 'status', width: 14 },
        ];
        ws3.addRows(data.contract_profitability);

        // Sheet 4 – Cash Flow
        const ws4 = wb.addWorksheet('Cash Flow');
        ws4.columns = [
            { header: 'Category', key: 'category', width: 24 },
            { header: 'Amount (KWD)', key: 'amount', width: 18 },
            { header: 'Type', key: 'type', width: 12 },
        ];
        ws4.addRows(data.cash_flow.breakdown);

        const buffer = await wb.xlsx.writeBuffer();
        const blob = new Blob([buffer], {
            type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `Financial_Report_${new Date().toISOString().slice(0, 10)}.xlsx`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
    } catch (err) {
        console.error('Export failed:', err);
    }
};

// ── Trend indicator ───────────────────────────────────────────────────────────
const TrendBadge = ({ value }) => {
    if (value == null) return null;
    const up = value >= 0;
    return (
        <span className={`trend-indicator ${up ? 'trend-up' : 'trend-down'}`}>
            {up ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
            {Math.abs(value).toFixed(1)}%
        </span>
    );
};

// ── Main component ────────────────────────────────────────────────────────────
const FinancePage = () => {
    const { user } = useAuth();
    const { hasPermission } = usePermission();
    const [loading, setLoading] = useState(true);
    const [data, setData] = useState(null);
    const [error, setError] = useState(null);

    const canViewFinance = hasPermission(PERMISSIONS.FINANCE_VIEW);

    const loadData = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const result = await getAdvancedFinancialSummary();
            setData(result);
        } catch (e) {
            setError(e.message || 'Failed to load financial data.');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        if (canViewFinance) loadData();
    }, [canViewFinance, loadData]);

    if (!canViewFinance) {
        return (
            <Result
                status="403"
                title="Access Denied"
                subTitle="You do not have permission to view financial data."
                extra={<Button type="primary" href="/dashboard">Back to Dashboard</Button>}
            />
        );
    }

    if (loading) {
        return (
            <div className="finance-loading">
                <Spin size="large" tip="Loading Confidential Financial Data..." />
            </div>
        );
    }

    if (error) {
        return (
            <div className="finance-container">
                <Alert
                    type="error"
                    message="Failed to Load Financial Data"
                    description={error}
                    action={<Button onClick={loadData} icon={<ReloadOutlined />}>Retry</Button>}
                />
            </div>
        );
    }

    const ov = data?.overview || {};
    const monthly = data?.monthly_trend || [];
    const cb = data?.cost_breakdown || {};
    const contracts = data?.contract_profitability || [];
    const atRisk = data?.at_risk_contracts || [];
    const cf = data?.cash_flow || {};
    const eff = data?.efficiency_metrics || {};

    // ── Chart configs ─────────────────────────────────────────────────────────

    // 1. Revenue vs Costs Line chart
    const lineData = monthly.flatMap(m => [
        { month: m.month, value: m.revenue, category: 'Revenue' },
        { month: m.month, value: m.costs, category: 'Costs' },
        { month: m.month, value: m.profit, category: 'Profit' },
    ]);
    const lineConfig = {
        data: lineData,
        xField: 'month',
        yField: 'value',
        colorField: 'category',
        smooth: true,
        point: { shapeField: 'circle', sizeField: 4 },
        color: ['#52c41a', '#ff4d4f', '#1890ff'],
        legend: { position: 'top' },
        tooltip: { formatter: (d) => ({ name: d.category, value: `${d.value?.toLocaleString()} KWD` }) },
        yAxis: { label: { formatter: (v) => `${(v / 1000).toFixed(0)}K` } },
        interactions: [{ type: 'brush-x' }],
    };

    // 2. Cost distribution donut
    const donutData = [
        { type: 'Employee Salaries', value: cb.employee_salaries || 0 },
        { type: 'External Workers', value: cb.external_workers || 0 },
        { type: 'Fleet Fuel', value: cb.fleet_fuel || 0 },
        { type: 'Fleet Maintenance', value: cb.fleet_maintenance || 0 },
        { type: 'Project Materials', value: cb.project_materials || 0 },
        { type: 'Overhead', value: cb.overhead || 0 },
    ].filter(d => d.value > 0);

    const donutConfig = {
        data: donutData,
        angleField: 'value',
        colorField: 'type',
        radius: 0.85,
        innerRadius: 0.65,
        color: ['#1890ff', '#52c41a', '#fa8c16', '#f5222d', '#722ed1', '#13c2c2'],
        label: {
            type: 'inner',
            offset: '-30%',
            content: ({ percent }) => `${(percent * 100).toFixed(1)}%`,
            style: { fill: '#fff', fontSize: 11, fontWeight: 600 },
        },
        legend: { position: 'bottom', layout: 'horizontal' },
        statistic: {
            title: { content: 'Total\nCosts' },
            content: { content: `${((ov.total_costs || 0) / 1000).toFixed(1)}K KWD` },
        },
        interactions: [{ type: 'element-active' }],
        tooltip: { formatter: (d) => ({ name: d.type, value: `${d.value?.toLocaleString()} KWD` }) },
    };

    // 3. Stacked column – monthly cost breakdown
    const stackData = monthly.flatMap(m => [
        { month: m.month, value: m.employee_costs || 0, category: 'Employee' },
        { month: m.month, value: m.external_costs || 0, category: 'External' },
        { month: m.month, value: m.fleet_costs || 0, category: 'Fleet' },
        { month: m.month, value: m.project_costs || 0, category: 'Projects' },
    ]);
    const stackConfig = {
        data: stackData,
        xField: 'month',
        yField: 'value',
        colorField: 'category',
        stack: true,
        color: ['#1890ff', '#52c41a', '#fa8c16', '#722ed1'],
        legend: { position: 'top' },
        tooltip: { formatter: (d) => ({ name: d.category, value: `${d.value?.toLocaleString()} KWD` }) },
    };

    // 4. Contract profitability horizontal bar
    const barData = contracts.slice(0, 10).map(c => ({
        contract: c.contract_name.length > 20 ? c.contract_name.slice(0, 20) + '…' : c.contract_name,
        profit: c.profit,
        status: c.status,
        margin: c.margin,
    }));
    const barConfig = {
        data: barData,
        xField: 'profit',
        yField: 'contract',
        colorField: 'status',
        color: ({ status }) => status === 'profitable' ? '#52c41a' : status === 'at-risk' ? '#faad14' : '#ff4d4f',
        label: {
            position: 'right',
            formatter: (d) => `${d.margin}%`,
            style: { fontSize: 11 },
        },
        tooltip: {
            formatter: (d) => ({
                name: d.contract,
                value: `Profit: ${d.profit?.toLocaleString()} KWD | Margin: ${d.margin}%`,
            }),
        },
    };

    // 5. Gauges
    const marginGaugeConfig = {
        data: { target: Math.max(0, Math.min(100, ov.profit_margin || 0)), total: 100, name: 'Profit Margin' },
        legend: false,
        range: { color: ['#ff4d4f', '#faad14', '#52c41a'], width: 12 },
        gauge: {
            type: 'meter',
            steps: 50,
            stepRatio: 0.6,
        },
        statistic: {
            content: {
                formatter: ({ percent }) => `${(percent * 100).toFixed(1)}%`,
                style: { fontSize: '20px', fontWeight: 700 },
            },
        },
    };

    const utilizationGaugeConfig = {
        data: { target: Math.max(0, Math.min(100, eff.utilization_rate || 0)), total: 100, name: 'Utilization' },
        legend: false,
        range: { color: ['#ff4d4f', '#faad14', '#52c41a'], width: 12 },
        gauge: { type: 'meter', steps: 50, stepRatio: 0.6 },
        statistic: {
            content: {
                formatter: ({ percent }) => `${(percent * 100).toFixed(1)}%`,
                style: { fontSize: '20px', fontWeight: 700 },
            },
        },
    };

    const burnRateMax = Math.max((eff.burn_rate_daily || 0) * 2, 1);
    const burnGaugeConfig = {
        data: { target: Math.min(eff.burn_rate_daily || 0, burnRateMax), total: burnRateMax, name: 'Burn Rate' },
        legend: false,
        range: { color: ['#52c41a', '#faad14', '#ff4d4f'], width: 12 },
        gauge: { type: 'meter', steps: 50, stepRatio: 0.6 },
        statistic: {
            content: {
                formatter: () => `${(eff.burn_rate_daily || 0).toFixed(0)} KWD/d`,
                style: { fontSize: '18px', fontWeight: 700 },
            },
        },
    };

    // 6. Waterfall (cash flow)
    const waterfallData = [
        { label: 'Opening', value: cf.starting_balance || 0, isTotal: false },
        ...((cf.breakdown || []).map(b => ({
            label: b.category,
            value: b.type === 'inflow' ? b.amount : -b.amount,
            isTotal: false,
        }))),
        { label: 'Closing', value: cf.ending_balance || 0, isTotal: true },
    ];
    const waterfallConfig = {
        data: waterfallData,
        xField: 'label',
        yField: 'value',
        risingFill: '#52c41a',
        fallingFill: '#ff4d4f',
        total: { label: 'Closing Balance', style: { fill: '#1890ff' } },
        label: {
            formatter: (d) => `${(d.value / 1000).toFixed(1)}K`,
            style: { fontSize: 10 },
        },
        tooltip: { formatter: (d) => ({ name: d.label, value: `${d.value?.toLocaleString()} KWD` }) },
    };

    const profitPositive = (ov.net_profit || 0) >= 0;

    return (
        <div className="finance-container">
            {/* ── Header ─────────────────────────────────────────────────────── */}
            <div className="finance-header-row">
                <div>
                    <Title level={2} style={{ margin: 0 }}>
                        <BarChartOutlined /> Financial Dashboard
                    </Title>
                    <Text type="secondary">Profit &amp; Loss Analytics — Confidential</Text>
                </div>
                <Space>
                    <Button icon={<ReloadOutlined />} onClick={loadData}>Refresh</Button>
                    <Button
                        type="primary"
                        icon={<FileExcelOutlined />}
                        className="export-excel-btn"
                        onClick={() => exportToExcel(data)}
                    >
                        Export to Excel
                    </Button>
                </Space>
            </div>

            {/* ── KPI Cards ──────────────────────────────────────────────────── */}
            <Row gutter={[20, 20]} style={{ marginTop: 24, marginBottom: 24 }}>
                <Col xs={24} sm={12} md={6}>
                    <Card variant="borderless" className="fin-stat-card revenue-glow">
                        <Statistic
                            title="Total Revenue"
                            value={ov.total_revenue}
                            precision={2}
                            suffix="KWD"
                            prefix={<DollarOutlined />}
                        />
                        <div className="kpi-sub">
                            YTD <TrendBadge value={ov.ytd_growth} />
                        </div>
                    </Card>
                </Col>
                <Col xs={24} sm={12} md={6}>
                    <Card variant="borderless" className="fin-stat-card expense-glow">
                        <Statistic
                            title="Total Costs"
                            value={ov.total_costs}
                            precision={2}
                            suffix="KWD"
                            valueStyle={{ color: '#cf1322' }}
                        />
                        <div className="kpi-sub">
                            MoM <TrendBadge value={typeof ov.mom_change === 'number' ? -ov.mom_change : null} />
                        </div>
                    </Card>
                </Col>
                <Col xs={24} sm={12} md={6}>
                    <Card variant="borderless" className="fin-stat-card profit-glow">
                        <Statistic
                            title="Net Profit"
                            value={ov.net_profit}
                            precision={2}
                            suffix="KWD"
                            valueStyle={{ color: profitPositive ? '#3f8600' : '#cf1322' }}
                        />
                        <div className="kpi-sub">
                            <TrendBadge value={ov.mom_change} />
                        </div>
                    </Card>
                </Col>
                <Col xs={24} sm={12} md={6}>
                    <Card variant="borderless" className="fin-stat-card info-glow">
                        <Statistic
                            title="Profit Margin"
                            value={ov.profit_margin}
                            precision={1}
                            suffix="%"
                            prefix={<RiseOutlined />}
                        />
                        <div className="kpi-sub">
                            <Tag color={
                                (ov.profit_margin || 0) >= 20 ? 'success' :
                                (ov.profit_margin || 0) >= 10 ? 'warning' : 'error'
                            }>
                                {(ov.profit_margin || 0) >= 20 ? 'Healthy' :
                                 (ov.profit_margin || 0) >= 10 ? 'At-Risk' : 'Critical'}
                            </Tag>
                        </div>
                    </Card>
                </Col>
            </Row>

            {/* ── Row 2: Line + Donut ────────────────────────────────────────── */}
            <Row gutter={[24, 24]} style={{ marginBottom: 24 }}>
                <Col xs={24} lg={14}>
                    <Card title="Revenue vs Costs Trend (6 Months)" className="finance-chart-card">
                        {monthly.length > 0
                            ? <Line {...lineConfig} height={280} />
                            : <div className="chart-empty">No trend data available.</div>
                        }
                    </Card>
                </Col>
                <Col xs={24} lg={10}>
                    <Card title="Cost Distribution" className="finance-chart-card">
                        {donutData.length > 0
                            ? <Pie {...donutConfig} height={280} />
                            : <div className="chart-empty">No cost data available.</div>
                        }
                    </Card>
                </Col>
            </Row>

            {/* ── Row 3: Stacked Column ─────────────────────────────────────── */}
            <Row gutter={[24, 24]} style={{ marginBottom: 24 }}>
                <Col xs={24}>
                    <Card title="Monthly Cost Breakdown by Category" className="finance-chart-card">
                        {monthly.length > 0
                            ? <Column {...stackConfig} height={260} />
                            : <div className="chart-empty">No monthly data available.</div>
                        }
                    </Card>
                </Col>
            </Row>

            {/* ── Row 4: Bar + At-Risk ──────────────────────────────────────── */}
            <Row gutter={[24, 24]} style={{ marginBottom: 24 }}>
                <Col xs={24} lg={14}>
                    <Card title="Contract Profitability" className="finance-chart-card">
                        {barData.length > 0
                            ? <Bar {...barConfig} height={300} />
                            : <div className="chart-empty">No contract data available.</div>
                        }
                    </Card>
                </Col>
                <Col xs={24} lg={10}>
                    <Card
                        title={
                            <span>
                                <WarningOutlined style={{ color: '#faad14', marginRight: 8 }} />
                                At-Risk Contracts
                            </span>
                        }
                        className="finance-chart-card"
                    >
                        {atRisk.length === 0 ? (
                            <Alert type="success" message="All contracts are operating profitably." showIcon />
                        ) : (
                            <div className="at-risk-list">
                                {atRisk.map(c => (
                                    <div
                                        key={c.contract_id}
                                        className={`risk-alert-card ${c.risk_level === 'high' ? 'high-risk' : ''}`}
                                    >
                                        <div className="risk-header">
                                            <Text strong>{c.contract_name}</Text>
                                            <Tag color={c.risk_level === 'high' ? 'red' : 'orange'}>
                                                {c.risk_level === 'high' ? '🔴 High' : '🟠 Medium'}
                                            </Tag>
                                        </div>
                                        <div className="risk-metrics">
                                            <span>Margin: <strong>{c.margin}%</strong></span>
                                            <span>Profit: <strong>{c.profit?.toLocaleString()} KWD</strong></span>
                                        </div>
                                        <Text type="secondary" style={{ fontSize: 12 }}>
                                            {c.recommendation}
                                        </Text>
                                    </div>
                                ))}
                            </div>
                        )}
                    </Card>
                </Col>
            </Row>

            {/* ── Row 5: Gauges ─────────────────────────────────────────────── */}
            <Row gutter={[24, 24]} style={{ marginBottom: 24 }}>
                <Col xs={24} sm={8}>
                    <Card title="Profit Margin" className="finance-chart-card gauge-card">
                        <Gauge {...marginGaugeConfig} height={200} />
                        <div className="gauge-label">Target: 20%+</div>
                    </Card>
                </Col>
                <Col xs={24} sm={8}>
                    <Card title="Workforce Utilization" className="finance-chart-card gauge-card">
                        <Gauge {...utilizationGaugeConfig} height={200} />
                        <div className="gauge-label">
                            {eff.utilization_rate?.toFixed(1)}% of employees assigned
                        </div>
                    </Card>
                </Col>
                <Col xs={24} sm={8}>
                    <Card title="Daily Burn Rate" className="finance-chart-card gauge-card">
                        <Gauge {...burnGaugeConfig} height={200} />
                        <div className="gauge-label">
                            Runway: ~{eff.runway_days} days
                        </div>
                    </Card>
                </Col>
            </Row>

            {/* ── Row 6: Waterfall ──────────────────────────────────────────── */}
            <Row gutter={[24, 24]} style={{ marginBottom: 24 }}>
                <Col xs={24}>
                    <Card title="Cash Flow Analysis (Waterfall)" className="finance-chart-card">
                        {cf.breakdown?.length > 0
                            ? <Waterfall {...waterfallConfig} height={280} />
                            : <div className="chart-empty">No cash flow data available.</div>
                        }
                    </Card>
                </Col>
            </Row>

            {/* ── Row 7: Efficiency summary ─────────────────────────────────── */}
            <Row gutter={[24, 24]} style={{ marginBottom: 24 }}>
                <Col xs={24}>
                    <Card title="Efficiency Metrics Summary" className="finance-chart-card">
                        <Row gutter={[20, 12]}>
                            {[
                                { label: 'Profit / Employee', value: `${(eff.profit_per_employee || 0).toLocaleString()} KWD` },
                                { label: 'Revenue / Employee', value: `${(eff.revenue_per_employee || 0).toLocaleString()} KWD` },
                                { label: 'Cost / Employee', value: `${(eff.cost_per_employee || 0).toLocaleString()} KWD` },
                                { label: 'Profit / Hour', value: `${(eff.profit_per_hour || 0).toFixed(2)} KWD` },
                                { label: 'Daily Burn Rate', value: `${(eff.burn_rate_daily || 0).toFixed(0)} KWD/day` },
                                { label: 'Cash Runway', value: `${eff.runway_days || 0} days` },
                            ].map(m => (
                                <Col xs={12} sm={8} md={4} key={m.label}>
                                    <div className="eff-metric">
                                        <Text type="secondary" style={{ fontSize: 12 }}>{m.label}</Text>
                                        <div className="eff-value">{m.value}</div>
                                    </div>
                                </Col>
                            ))}
                        </Row>
                    </Card>
                </Col>
            </Row>
        </div>
    );
};

export default FinancePage;