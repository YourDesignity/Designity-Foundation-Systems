// src/pages/ProjectWorkflow/TempWorkerManagement.jsx
import React, { useState, useEffect, useCallback } from 'react';
import {
    Card, Row, Col, Button, Table, Tag, Tabs, Statistic,
    message, Modal, Space, Typography, Empty, Progress, Badge,
    Tooltip
} from 'antd';
import {
    UserAddOutlined, TeamOutlined, DollarOutlined,
    EnvironmentOutlined, StopOutlined, ReloadOutlined,
    PieChartOutlined,
} from '@ant-design/icons';
import { useParams } from 'react-router-dom';
import { fetchWithAuth } from '../../services/apiService';
import {
    getTempWorkersAtSite,
    endTempAssignment,
    getCostSummary,
} from '../../services/tempWorkerService';
import AssignTempWorkersModal from './AssignTempWorkersModal';
import RegisterTempWorkerModal from './RegisterTempWorkerModal';
import dayjs from 'dayjs';

const { Text, Title } = Typography;

const TempWorkerManagement = () => {
    const { siteId } = useParams();

    const [site, setSite] = useState(null);
    const [companyEmployees, setCompanyEmployees] = useState([]);
    const [companyAssignments, setCompanyAssignments] = useState([]);
    const [tempWorkers, setTempWorkers] = useState([]);
    const [costSummary, setCostSummary] = useState(null);

    const [loadingCompany, setLoadingCompany] = useState(false);
    const [loadingTemp, setLoadingTemp] = useState(false);
    const [loadingSummary, setLoadingSummary] = useState(false);

    const [assignModalVisible, setAssignModalVisible] = useState(false);
    const [registerModalVisible, setRegisterModalVisible] = useState(false);
    const [activeTab, setActiveTab] = useState('company');

    const fetchCompanyEmployees = useCallback(async () => {
        setLoadingCompany(true);
        try {
            const data = await fetchWithAuth(`/assignments/site/${siteId}/employees`);
            setSite(data.site);
            setCompanyEmployees(data.employees || []);
            setCompanyAssignments(data.assignments || []);
        } catch (err) {
            message.error('Failed to load company employees');
        } finally {
            setLoadingCompany(false);
        }
    }, [siteId]);

    const fetchTempWorkers = useCallback(async () => {
        setLoadingTemp(true);
        try {
            const data = await getTempWorkersAtSite(siteId);
            setTempWorkers(data.assignments || []);
        } catch (err) {
            message.error('Failed to load temporary workers');
        } finally {
            setLoadingTemp(false);
        }
    }, [siteId]);

    const fetchCostSummary = useCallback(async () => {
        setLoadingSummary(true);
        try {
            const data = await getCostSummary({ site_id: parseInt(siteId, 10) });
            setCostSummary(data);
        } catch (err) {
            console.error('Cost summary error:', err);
        } finally {
            setLoadingSummary(false);
        }
    }, [siteId]);

    const fetchAll = useCallback(() => {
        fetchCompanyEmployees();
        fetchTempWorkers();
        fetchCostSummary();
    }, [fetchCompanyEmployees, fetchTempWorkers, fetchCostSummary]);

    useEffect(() => {
        if (siteId) {
            fetchAll();
        }
    }, [siteId, fetchAll]);

    // ── Company Employees ──────────────────────────────────────────────

    const handleUnassignCompany = (assignmentId, employeeName) => {
        Modal.confirm({
            title: 'Remove Employee from Site',
            content: `Remove ${employeeName} from this site?`,
            okText: 'Remove',
            okType: 'danger',
            onOk: async () => {
                try {
                    await fetchWithAuth(`/assignments/${assignmentId}`, { method: 'DELETE' });
                    message.success(`${employeeName} removed from site`);
                    fetchCompanyEmployees();
                    fetchCostSummary();
                } catch (err) {
                    message.error('Failed to remove employee');
                }
            },
        });
    };

    const getCompanyAssignmentId = (empId) =>
        companyAssignments.find(a => a.employee_id === empId)?.uid;

    // ── Temp Workers ───────────────────────────────────────────────────

    const handleEndAssignment = (assignmentId, workerName) => {
        Modal.confirm({
            title: 'End Assignment',
            content: `End the assignment of ${workerName}? The final cost will be calculated as of today.`,
            okText: 'End Assignment',
            okType: 'danger',
            onOk: async () => {
                try {
                    const result = await endTempAssignment(assignmentId);
                    message.success(
                        `Assignment ended. Final cost: ${result.final_cost?.toFixed(3)} KD`
                    );
                    fetchTempWorkers();
                    fetchCostSummary();
                } catch (err) {
                    message.error(err.message || 'Failed to end assignment');
                }
            },
        });
    };

    // ── Company Employees Columns ──────────────────────────────────────
    const companyColumns = [
        {
            title: 'Name',
            dataIndex: 'name',
            key: 'name',
            render: (name, record) => (
                <Space>
                    <Badge color="blue" />
                    <div>
                        <div style={{ fontWeight: 500 }}>{name}</div>
                        <Text type="secondary" style={{ fontSize: 12 }}>{record.designation}</Text>
                    </div>
                </Space>
            ),
        },
        {
            title: 'Phone',
            dataIndex: 'phone_kuwait',
            key: 'phone_kuwait',
            render: v => v || '—',
        },
        {
            title: 'Status',
            dataIndex: 'status',
            key: 'status',
            render: status => (
                <Tag color={status === 'Active' ? 'blue' : 'default'}>{status}</Tag>
            ),
        },
        {
            title: 'Monthly Cost',
            key: 'cost',
            render: (_, record) => (
                <Text>{((record.basic_salary || 0) + (record.allowance || 0)).toFixed(3)} KD</Text>
            ),
        },
        {
            title: 'Actions',
            key: 'actions',
            render: (_, record) => (
                <Tooltip title="Remove from site">
                    <Button
                        type="link"
                        danger
                        icon={<StopOutlined />}
                        onClick={() =>
                            handleUnassignCompany(
                                getCompanyAssignmentId(record.uid),
                                record.name
                            )
                        }
                    >
                        Remove
                    </Button>
                </Tooltip>
            ),
        },
    ];

    // ── Temp Workers Columns ───────────────────────────────────────────
    const tempColumns = [
        {
            title: 'Name',
            dataIndex: 'employee_name',
            key: 'employee_name',
            render: (name, record) => (
                <Space>
                    <Badge color="orange" />
                    <div>
                        <div style={{ fontWeight: 500 }}>{name}</div>
                        <Text type="secondary" style={{ fontSize: 12 }}>{record.designation || '—'}</Text>
                    </div>
                </Space>
            ),
        },
        {
            title: 'Period',
            key: 'period',
            render: (_, record) => (
                <div>
                    <div>{dayjs(record.start_date).format('DD/MM/YYYY')}</div>
                    <div style={{ color: '#999' }}>→ {dayjs(record.end_date).format('DD/MM/YYYY')}</div>
                </div>
            ),
        },
        {
            title: 'Days',
            dataIndex: 'total_days',
            key: 'total_days',
            render: d => <Tag color="blue">{d}d</Tag>,
        },
        {
            title: 'Rate Type',
            dataIndex: 'rate_type',
            key: 'rate_type',
            render: rt => (
                <Tag color={rt === 'Daily' ? 'orange' : 'purple'}>{rt}</Tag>
            ),
        },
        {
            title: 'Rate',
            dataIndex: 'rate',
            key: 'rate',
            render: (r, record) => (
                <span>{r?.toFixed(3)} KD/{record.rate_type === 'Daily' ? 'd' : 'hr'}</span>
            ),
        },
        {
            title: 'Est. Cost',
            dataIndex: 'estimated_cost',
            key: 'estimated_cost',
            render: cost => (
                <Text strong style={{ color: '#fa8c16' }}>
                    {cost?.toFixed(3)} KD
                </Text>
            ),
        },
        {
            title: 'Reason',
            dataIndex: 'replacement_reason',
            key: 'replacement_reason',
            render: r => r ? <Tag>{r}</Tag> : '—',
        },
        {
            title: 'Actions',
            key: 'actions',
            render: (_, record) => (
                <Button
                    type="link"
                    danger
                    icon={<StopOutlined />}
                    onClick={() => handleEndAssignment(record.assignment_id, record.employee_name)}
                >
                    End
                </Button>
            ),
        },
    ];

    const totalTempCost = tempWorkers.reduce((s, w) => s + (w.estimated_cost || 0), 0);
    const totalCompanyCost = companyEmployees.reduce(
        (s, e) => s + (e.basic_salary || 0) + (e.allowance || 0),
        0
    );
    const totalLaborCost = totalCompanyCost + totalTempCost;
    const externalPct = totalLaborCost > 0
        ? Math.round((totalTempCost / totalLaborCost) * 100)
        : 0;

    const capacityPct = site
        ? Math.round((site.assigned_workers / (site.required_workers || 1)) * 100)
        : 0;

    const tabItems = [
        {
            key: 'company',
            label: (
                <span>
                    <TeamOutlined />
                    Company Employees
                    <Badge
                        count={companyEmployees.length}
                        style={{ marginLeft: 8, backgroundColor: '#1890ff' }}
                    />
                </span>
            ),
            children: (
                <Table
                    columns={companyColumns}
                    dataSource={companyEmployees}
                    rowKey="uid"
                    loading={loadingCompany}
                    pagination={{ pageSize: 10 }}
                    locale={{
                        emptyText: (
                            <Empty description="No company employees assigned to this site" />
                        ),
                    }}
                    summary={() =>
                        companyEmployees.length > 0 ? (
                            <Table.Summary.Row>
                                <Table.Summary.Cell colSpan={3}>
                                    <Text strong>Total Monthly Cost</Text>
                                </Table.Summary.Cell>
                                <Table.Summary.Cell>
                                    <Text strong style={{ color: '#1890ff' }}>
                                        {totalCompanyCost.toFixed(3)} KD
                                    </Text>
                                </Table.Summary.Cell>
                                <Table.Summary.Cell />
                            </Table.Summary.Row>
                        ) : null
                    }
                />
            ),
        },
        {
            key: 'external',
            label: (
                <span>
                    <UserAddOutlined />
                    External Workers
                    <Badge
                        count={tempWorkers.length}
                        style={{ marginLeft: 8, backgroundColor: '#fa8c16' }}
                    />
                </span>
            ),
            children: (
                <>
                    <div style={{ marginBottom: 16, textAlign: 'right' }}>
                        <Button
                            type="primary"
                            icon={<UserAddOutlined />}
                            onClick={() => setAssignModalVisible(true)}
                            style={{ background: '#fa8c16', borderColor: '#fa8c16' }}
                        >
                            Assign Temp Workers
                        </Button>
                    </div>
                    <Table
                        columns={tempColumns}
                        dataSource={tempWorkers}
                        rowKey="assignment_id"
                        loading={loadingTemp}
                        pagination={{ pageSize: 10 }}
                        locale={{
                            emptyText: (
                                <Empty description="No temporary workers assigned to this site">
                                    <Button
                                        type="primary"
                                        onClick={() => setAssignModalVisible(true)}
                                        style={{ background: '#fa8c16', borderColor: '#fa8c16' }}
                                    >
                                        Assign Now
                                    </Button>
                                </Empty>
                            ),
                        }}
                        summary={() =>
                            tempWorkers.length > 0 ? (
                                <Table.Summary.Row>
                                    <Table.Summary.Cell colSpan={5}>
                                        <Text strong>Total External Cost</Text>
                                    </Table.Summary.Cell>
                                    <Table.Summary.Cell>
                                        <Text strong style={{ color: '#fa8c16' }}>
                                            {totalTempCost.toFixed(3)} KD
                                        </Text>
                                    </Table.Summary.Cell>
                                    <Table.Summary.Cell colSpan={2} />
                                </Table.Summary.Row>
                            ) : null
                        }
                    />
                </>
            ),
        },
        {
            key: 'summary',
            label: (
                <span>
                    <PieChartOutlined />
                    Summary
                </span>
            ),
            children: (
                <Row gutter={[24, 24]}>
                    <Col xs={24} sm={12} md={6}>
                        <Card>
                            <Statistic
                                title="Company Employees"
                                value={companyEmployees.length}
                                prefix={<TeamOutlined style={{ color: '#1890ff' }} />}
                                styles={{ content: { color: '#1890ff' } }}
                            />
                            <div style={{ marginTop: 8 }}>
                                <Text type="secondary">Monthly Cost: </Text>
                                <Text strong>{totalCompanyCost.toFixed(3)} KD</Text>
                            </div>
                        </Card>
                    </Col>
                    <Col xs={24} sm={12} md={6}>
                        <Card>
                            <Statistic
                                title="External Workers"
                                value={tempWorkers.length}
                                prefix={<UserAddOutlined style={{ color: '#fa8c16' }} />}
                                styles={{ content: { color: '#fa8c16' } }}
                            />
                            <div style={{ marginTop: 8 }}>
                                <Text type="secondary">Total Cost: </Text>
                                <Text strong style={{ color: '#fa8c16' }}>
                                    {totalTempCost.toFixed(3)} KD
                                </Text>
                            </div>
                        </Card>
                    </Col>
                    <Col xs={24} sm={12} md={6}>
                        <Card>
                            <Statistic
                                title="Total Labor Cost"
                                value={totalLaborCost.toFixed(3)}
                                suffix="KD"
                                prefix={<DollarOutlined />}
                                styles={{ content: { color: '#52c41a' } }}
                            />
                        </Card>
                    </Col>
                    <Col xs={24} sm={12} md={6}>
                        <Card>
                            <div style={{ marginBottom: 8 }}>
                                <Text type="secondary">External Labor %</Text>
                            </div>
                            <Progress
                                type="circle"
                                percent={externalPct}
                                strokeColor="#fa8c16"
                                size={80}
                            />
                            <div style={{ marginTop: 8 }}>
                                <Text type="secondary" style={{ fontSize: 12 }}>
                                    of total labor cost
                                </Text>
                            </div>
                        </Card>
                    </Col>

                    {/* Cost breakdown */}
                    {costSummary && costSummary.external_cost_breakdown?.length > 0 && (
                        <Col xs={24}>
                            <Card title="External Worker Cost Breakdown" loading={loadingSummary}>
                                <Table
                                    dataSource={costSummary.external_cost_breakdown}
                                    rowKey="assignment_id"
                                    size="small"
                                    pagination={false}
                                    columns={[
                                        { title: 'Worker', dataIndex: 'worker_name', key: 'worker_name' },
                                        { title: 'Rate Type', dataIndex: 'rate_type', key: 'rate_type', render: rt => <Tag>{rt}</Tag> },
                                        { title: 'Rate (KD)', dataIndex: 'rate', key: 'rate', render: r => r?.toFixed(3) },
                                        { title: 'Days', dataIndex: 'total_days', key: 'total_days' },
                                        {
                                            title: 'Cost (KD)',
                                            dataIndex: 'cost',
                                            key: 'cost',
                                            render: c => <Text strong style={{ color: '#fa8c16' }}>{c?.toFixed(3)}</Text>
                                        },
                                    ]}
                                />
                            </Card>
                        </Col>
                    )}
                </Row>
            ),
        },
    ];

    return (
        <div style={{ padding: '24px' }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 }}>
                <div>
                    <Title level={3} style={{ margin: 0 }}>
                        <TeamOutlined /> Workforce Management
                    </Title>
                    <Text type="secondary">
                        {site ? `${site.name} — ${site.location || ''}` : `Site #${siteId}`}
                    </Text>
                </div>
                <Space>
                    <Button
                        icon={<ReloadOutlined />}
                        onClick={fetchAll}
                    >
                        Refresh
                    </Button>
                    <Button
                        type="primary"
                        icon={<UserAddOutlined />}
                        onClick={() => {
                            setActiveTab('external');
                            setAssignModalVisible(true);
                        }}
                        style={{ background: '#fa8c16', borderColor: '#fa8c16' }}
                    >
                        Assign Temp Workers
                    </Button>
                </Space>
            </div>

            {/* Site capacity stats */}
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
                                value={site.required_workers || 0}
                            />
                        </Card>
                    </Col>
                    <Col xs={24} sm={12} md={6}>
                        <Card>
                            <Statistic
                                title="Assigned Workers"
                                value={site.assigned_workers || 0}
                                styles={{ content: {
                                    color: (site.assigned_workers || 0) >= (site.required_workers || 0)
                                        ? '#52c41a' : '#fa8c16'
                                } }}
                            />
                        </Card>
                    </Col>
                    <Col xs={24} sm={12} md={6}>
                        <Card>
                            <div style={{ marginBottom: 8 }}>
                                <Text type="secondary">Capacity</Text>
                            </div>
                            <Progress
                                percent={Math.min(capacityPct, 100)}
                                status={capacityPct >= 100 ? 'success' : 'active'}
                                format={pct => `${pct}%`}
                            />
                        </Card>
                    </Col>
                </Row>
            )}

            {/* Main Tabs */}
            <Card>
                <Tabs
                    activeKey={activeTab}
                    onChange={setActiveTab}
                    items={tabItems}
                />
            </Card>

            {/* Modals */}
            <AssignTempWorkersModal
                visible={assignModalVisible}
                site={site}
                onCancel={() => setAssignModalVisible(false)}
                onSuccess={() => {
                    setAssignModalVisible(false);
                    fetchTempWorkers();
                    fetchCostSummary();
                }}
                onRegisterNew={() => {
                    setAssignModalVisible(false);
                    setRegisterModalVisible(true);
                }}
            />

            <RegisterTempWorkerModal
                visible={registerModalVisible}
                onCancel={() => setRegisterModalVisible(false)}
                onSuccess={() => {
                    setRegisterModalVisible(false);
                    setAssignModalVisible(true);
                }}
            />
        </div>
    );
};

export default TempWorkerManagement;
