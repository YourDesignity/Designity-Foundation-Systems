// src/pages/ProjectWorkflow/AssignTempWorkersModal.jsx
import React, { useState, useEffect } from 'react';
import {
    Modal, Form, Select, DatePicker, Row, Col,
    Tag, Table, Statistic, message, Divider, Button,
    Empty, Space, Typography
} from 'antd';
import {
    UserAddOutlined, DollarOutlined, CalendarOutlined
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { getAvailableTempWorkers, assignTempWorkers } from '../../services/tempWorkerService';

const { Option } = Select;
const { Text } = Typography;
const { RangePicker } = DatePicker;

const REASONS = [
    'Sick Leave Coverage',
    'Vacation Coverage',
    'Peak Demand',
    'Emergency',
    'Project Requirement',
    'Additional Coverage',
];

const AssignTempWorkersModal = ({ visible, site, onCancel, onSuccess, onRegisterNew }) => {
    const [availableWorkers, setAvailableWorkers] = useState([]);
    const [selectedWorkerIds, setSelectedWorkerIds] = useState([]);
    const [workerDateRanges, setWorkerDateRanges] = useState({});
    const [reason, setReason] = useState(null);
    const [loading, setLoading] = useState(false);
    const [fetching, setFetching] = useState(false);

    useEffect(() => {
        if (visible) {
            loadAvailableWorkers();
        }
    }, [visible]);

    const loadAvailableWorkers = async () => {
        setFetching(true);
        try {
            const data = await getAvailableTempWorkers();
            setAvailableWorkers(data.workers || []);
        } catch (err) {
            message.error('Failed to load available workers');
        } finally {
            setFetching(false);
        }
    };

    const handleWorkerSelect = (ids) => {
        setSelectedWorkerIds(ids);
        // Initialize date range for newly selected workers
        const updatedRanges = { ...workerDateRanges };
        ids.forEach(id => {
            if (!updatedRanges[id]) {
                updatedRanges[id] = [dayjs(), dayjs().add(7, 'day')];
            }
        });
        // Remove de-selected workers
        Object.keys(updatedRanges).forEach(id => {
            if (!ids.includes(Number(id))) {
                delete updatedRanges[id];
            }
        });
        setWorkerDateRanges(updatedRanges);
    };

    const handleDateChange = (workerId, dates) => {
        setWorkerDateRanges(prev => ({ ...prev, [workerId]: dates }));
    };

    const calculateWorkerCost = (worker, dates) => {
        if (!dates || !dates[0] || !dates[1]) return 0;
        const days = dates[1].diff(dates[0], 'day') + 1;
        return days * (worker.daily_rate || 0);
    };

    const totalEstimatedCost = selectedWorkerIds.reduce((sum, id) => {
        const worker = availableWorkers.find(w => w.id === id);
        const dates = workerDateRanges[id];
        return sum + calculateWorkerCost(worker, dates);
    }, 0);

    const handleAssign = async () => {
        if (selectedWorkerIds.length === 0) {
            message.warning('Please select at least one worker');
            return;
        }

        const invalidWorker = selectedWorkerIds.find(id => {
            const dates = workerDateRanges[id];
            return !dates || !dates[0] || !dates[1];
        });
        if (invalidWorker) {
            message.warning('Please set start and end dates for all selected workers');
            return;
        }

        setLoading(true);
        try {
            const workers = selectedWorkerIds.map(id => {
                const worker = availableWorkers.find(w => w.id === id);
                const dates = workerDateRanges[id];
                return {
                    employee_id: id,
                    start_date: dates[0].format('YYYY-MM-DD'),
                    end_date: dates[1].format('YYYY-MM-DD'),
                    rate_type: 'Daily',
                    daily_rate: worker?.daily_rate || 0,
                    hourly_rate: worker?.hourly_rate || 0,
                };
            });

            const result = await assignTempWorkers(site.uid || site.id, workers, reason);
            message.success(
                `${result.created_count} worker(s) assigned. Estimated cost: ${result.total_estimated_cost?.toFixed(3)} KD`
            );
            handleClose();
            onSuccess(result);
        } catch (err) {
            message.error(err.message || 'Failed to assign workers');
        } finally {
            setLoading(false);
        }
    };

    const handleClose = () => {
        setSelectedWorkerIds([]);
        setWorkerDateRanges({});
        setReason(null);
        onCancel();
    };

    const selectedWorkerRows = selectedWorkerIds.map(id => {
        const worker = availableWorkers.find(w => w.id === id);
        const dates = workerDateRanges[id];
        const days = dates && dates[0] && dates[1] ? dates[1].diff(dates[0], 'day') + 1 : 0;
        const cost = calculateWorkerCost(worker, dates);
        return { ...worker, dates, days, cost };
    });

    const workerColumns = [
        {
            title: 'Worker',
            dataIndex: 'name',
            key: 'name',
            render: (name, record) => (
                <div>
                    <div style={{ fontWeight: 500 }}>{name}</div>
                    <Text type="secondary" style={{ fontSize: 12 }}>{record.designation}</Text>
                </div>
            ),
        },
        {
            title: 'Dates',
            key: 'dates',
            width: 260,
            render: (_, record) => (
                <RangePicker
                    size="small"
                    value={workerDateRanges[record.id]}
                    onChange={(dates) => handleDateChange(record.id, dates)}
                    disabledDate={(d) => d && d < dayjs().startOf('day')}
                    format="DD/MM/YYYY"
                />
            ),
        },
        {
            title: 'Days',
            dataIndex: 'days',
            key: 'days',
            width: 60,
            render: days => <Tag color="blue">{days}d</Tag>,
        },
        {
            title: 'Rate',
            key: 'rate',
            width: 100,
            render: (_, record) => (
                <span>{(record.daily_rate || 0).toFixed(3)} KD/d</span>
            ),
        },
        {
            title: 'Cost',
            dataIndex: 'cost',
            key: 'cost',
            width: 100,
            render: cost => (
                <Text strong style={{ color: '#fa8c16' }}>
                    {cost.toFixed(3)} KD
                </Text>
            ),
        },
    ];

    return (
        <Modal
            title={
                <Space>
                    <UserAddOutlined style={{ color: '#fa8c16' }} />
                    <span>Assign Temporary Workers</span>
                    {site && <Tag color="blue">{site.name}</Tag>}
                </Space>
            }
            open={visible}
            onCancel={handleClose}
            onOk={handleAssign}
            okText={`Assign ${selectedWorkerIds.length} Worker${selectedWorkerIds.length !== 1 ? 's' : ''}`}
            okButtonProps={{
                disabled: selectedWorkerIds.length === 0,
                style: { background: '#fa8c16', borderColor: '#fa8c16' }
            }}
            width={860}
            confirmLoading={loading}
            destroyOnHidden
        >
            {/* Site Info */}
            {site && (
                <div style={{ background: '#fafafa', padding: '12px 16px', borderRadius: 8, marginBottom: 16 }}>
                    <Row gutter={24}>
                        <Col span={8}>
                            <Text type="secondary">Site</Text>
                            <div style={{ fontWeight: 600 }}>{site.name}</div>
                        </Col>
                        <Col span={8}>
                            <Text type="secondary">Location</Text>
                            <div>{site.location || '—'}</div>
                        </Col>
                        <Col span={8}>
                            <Text type="secondary">Available Workers</Text>
                            <div style={{ fontWeight: 600 }}>{availableWorkers.length}</div>
                        </Col>
                    </Row>
                </div>
            )}

            {/* Reason */}
            <Form layout="vertical">
                <Form.Item label="Reason for Assignment">
                    <Select
                        placeholder="Select reason (optional)"
                        value={reason}
                        onChange={setReason}
                        allowClear
                        style={{ width: '100%' }}
                    >
                        {REASONS.map(r => (
                            <Option key={r} value={r}>{r}</Option>
                        ))}
                    </Select>
                </Form.Item>

                {/* Worker multi-select */}
                <Form.Item label="Select Workers">
                    <Select
                        mode="multiple"
                        style={{ width: '100%' }}
                        placeholder={fetching ? 'Loading workers...' : 'Select workers to assign'}
                        value={selectedWorkerIds}
                        onChange={handleWorkerSelect}
                        loading={fetching}
                        showSearch
                        optionFilterProp="label"
                        notFoundContent={
                            <Empty
                                description={
                                    <span>
                                        No available workers.{' '}
                                        <Button type="link" size="small" onClick={onRegisterNew}>
                                            Register New
                                        </Button>
                                    </span>
                                }
                            />
                        }
                    >
                        {availableWorkers.map(w => (
                            <Option key={w.id} value={w.id} label={w.name}>
                                <Space>
                                    <span>{w.name}</span>
                                    <Tag color="orange" style={{ marginRight: 0 }}>{w.designation}</Tag>
                                    {w.agency_name && (
                                        <Text type="secondary" style={{ fontSize: 11 }}>({w.agency_name})</Text>
                                    )}
                                    <Text type="secondary" style={{ fontSize: 11 }}>
                                        {(w.daily_rate || 0).toFixed(3)} KD/d
                                    </Text>
                                </Space>
                            </Option>
                        ))}
                    </Select>
                    <div style={{ marginTop: 4 }}>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                            {availableWorkers.length} workers available ·{' '}
                        </Text>
                        <Button type="link" size="small" style={{ padding: 0, fontSize: 12 }} onClick={onRegisterNew}>
                            + Register New Worker
                        </Button>
                    </div>
                </Form.Item>
            </Form>

            {/* Per-worker date ranges */}
            {selectedWorkerRows.length > 0 && (
                <>
                    <Divider style={{ margin: '12px 0' }}>Assignment Details</Divider>
                    <Table
                        dataSource={selectedWorkerRows}
                        columns={workerColumns}
                        rowKey="id"
                        pagination={false}
                        size="small"
                        style={{ marginBottom: 16 }}
                    />
                </>
            )}

            {/* Cost summary */}
            {selectedWorkerIds.length > 0 && (
                <div style={{
                    background: '#fff7e6',
                    border: '1px solid #ffd591',
                    borderRadius: 8,
                    padding: '12px 20px',
                }}>
                    <Row gutter={24} align="middle">
                        <Col span={8}>
                            <Statistic
                                title="Workers Selected"
                                value={selectedWorkerIds.length}
                                prefix={<UserAddOutlined />}
                            />
                        </Col>
                        <Col span={8}>
                            <Statistic
                                title="Total Estimated Cost"
                                value={totalEstimatedCost.toFixed(3)}
                                suffix="KD"
                                prefix={<DollarOutlined />}
                                styles={{ content: { color: '#fa8c16', fontWeight: 700 } }}
                            />
                        </Col>
                        <Col span={8}>
                            <Statistic
                                title="Avg. Cost / Worker"
                                value={(totalEstimatedCost / selectedWorkerIds.length).toFixed(3)}
                                suffix="KD"
                                prefix={<CalendarOutlined />}
                            />
                        </Col>
                    </Row>
                </div>
            )}
        </Modal>
    );
};

export default AssignTempWorkersModal;
