import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Badge,
  Breadcrumb,
  Button,
  Card,
  Col,
  Empty,
  Input,
  Row,
  Select,
  Space,
  Spin,
  Statistic,
  Typography,
  message,
  Result,
} from 'antd';
import { useNavigate } from 'react-router-dom';
import { SearchOutlined } from '@ant-design/icons';
import { useAuth } from '../../context/AuthContext';
import { getSites } from '../../services/apiService';
import { getRoleContractsList, getUnfilledRoleSlots } from '../../services/roleContractsService';
import ContractRoleCard from '../../components/role-contracts/ContractRoleCard';
import UnfilledSlotsAlert from '../../components/role-contracts/UnfilledSlotsAlert';

const { Title, Text } = Typography;

const RoleContractFulfillmentOverview = () => {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [contracts, setContracts] = useState([]);
  const [sites, setSites] = useState([]);
  const [unfilledRecords, setUnfilledRecords] = useState([]);
  const [loading, setLoading] = useState(false);

  const [search, setSearch] = useState('');
  const [siteFilter, setSiteFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');

  const canAccess = ['Site Manager', 'Admin', 'SuperAdmin'].includes(user?.role);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [contractList, unfilled, siteList] = await Promise.all([
        getRoleContractsList(),
        getUnfilledRoleSlots().catch(() => []),
        getSites().catch(() => []),
      ]);
      setContracts(contractList || []);
      setUnfilledRecords(Array.isArray(unfilled) ? unfilled : []);
      setSites(Array.isArray(siteList) ? siteList : []);
    } catch (error) {
      message.error(`Failed to load role contracts: ${error.message}`);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (canAccess) loadData();
  }, [canAccess, loadData]);

  const siteNameById = useMemo(() => {
    return (sites || []).reduce((acc, site) => {
      acc[site.uid] = site.name || site.site_name || site.site_code || `Site ${site.uid}`;
      return acc;
    }, {});
  }, [sites]);

  const allowedSiteIds = useMemo(() => {
    if (user?.role !== 'Site Manager') return null;
    const rawSites = user?.sites || user?.site_ids || [];
    return new Set(rawSites.map((item) => Number(item?.uid ?? item)));
  }, [user]);

  const recordsByContract = useMemo(() => {
    return unfilledRecords.reduce((acc, record) => {
      const current = acc[record.contract_id] || { required: 0, filled: 0 };
      current.required += Number(record.total_roles_required || 0);
      current.filled += Number(record.total_roles_filled || 0);
      acc[record.contract_id] = current;
      return acc;
    }, {});
  }, [unfilledRecords]);

  const visibleContracts = useMemo(() => {
    return contracts
      .filter((contract) => contract.contract_type === 'Labour' || contract.contract_type === undefined)
      .filter((contract) => {
        if (!allowedSiteIds) return true;
        const ids = (contract.site_ids || []).map(Number);
        return ids.some((id) => allowedSiteIds.has(id));
      })
      .filter((contract) => {
        const text = search.trim().toLowerCase();
        return !text || contract.contract_code?.toLowerCase().includes(text);
      })
      .filter((contract) => {
        if (siteFilter === 'all') return true;
        return (contract.site_ids || []).map(String).includes(siteFilter);
      })
      .filter((contract) => {
        if (statusFilter === 'all') return true;
        const { required, filled } = recordsByContract[contract.contract_id] || { required: contract.total_role_slots || 0, filled: contract.total_role_slots || 0 };
        if (!required) return statusFilter === 'unfilled';
        const ratio = filled / required;
        if (statusFilter === 'full') return ratio === 1;
        if (statusFilter === 'partial') return ratio > 0 && ratio < 1;
        return ratio < 0.6;
      });
  }, [contracts, allowedSiteIds, search, siteFilter, statusFilter, recordsByContract]);

  const stats = useMemo(() => {
    const totalContracts = visibleContracts.length;
    const totalRoleSlots = visibleContracts.reduce((sum, c) => sum + Number(c.total_role_slots || 0), 0);
    const totalDailyCost = visibleContracts.reduce((sum, c) => sum + Number(c.total_daily_cost || 0), 0);
    const totalFilled = visibleContracts.reduce((sum, c) => {
      const record = recordsByContract[c.contract_id];
      return sum + Number(record?.filled ?? c.total_role_slots ?? 0);
    }, 0);
    const totalRequired = visibleContracts.reduce((sum, c) => {
      const record = recordsByContract[c.contract_id];
      return sum + Number(record?.required ?? c.total_role_slots ?? 0);
    }, 0);

    return {
      totalContracts,
      totalRoleSlots,
      totalDailyCost,
      unfilledCount: unfilledRecords.reduce((sum, row) => sum + (row.unfilled_slots?.length || 0), 0),
      overallRate: totalRequired ? Math.round((totalFilled / totalRequired) * 100) : 0,
    };
  }, [recordsByContract, visibleContracts, unfilledRecords]);

  if (!canAccess) {
    return (
      <Result
        status="403"
        title="Access Denied"
        subTitle="You do not have permission to access role contract fulfillment."
      />
    );
  }

  return (
    <Space orientation="vertical" size={16} style={{ width: '100%' }}>
      <Breadcrumb items={[{ title: 'Home' }, { title: 'Role Contracts' }]} />
      <div>
        <Title level={3} style={{ marginBottom: 0 }}>Role-Contract Fulfillment Overview</Title>
        <Text type="secondary">Monitor labour role slot fulfillment and jump into daily actions quickly.</Text>
      </div>

      <UnfilledSlotsAlert count={stats.unfilledCount} />

      <Row gutter={[12, 12]}>
        <Col xs={12} md={4}><Card><Statistic title="Contracts" value={stats.totalContracts} /></Card></Col>
        <Col xs={12} md={5}><Card><Statistic title="Role Slots" value={stats.totalRoleSlots} /></Card></Col>
        <Col xs={12} md={5}><Card><Statistic title="Fulfillment Rate" value={stats.overallRate} suffix="%" /></Card></Col>
        <Col xs={12} md={5}><Card><Statistic title="Daily Cost" value={stats.totalDailyCost} precision={2} prefix="KD" /></Card></Col>
        <Col xs={12} md={5}><Card><Statistic title="Unfilled Slots" value={stats.unfilledCount} suffix={<Badge count={stats.unfilledCount} />} /></Card></Col>
      </Row>

      <Card>
        <Row gutter={[12, 12]} align="middle">
          <Col xs={24} md={8}>
            <Input prefix={<SearchOutlined />} placeholder="Search by contract code" value={search} onChange={(e) => setSearch(e.target.value)} />
          </Col>
          <Col xs={24} md={6}>
            <Select
              style={{ width: '100%' }}
              value={siteFilter}
              onChange={setSiteFilter}
              options={[{ value: 'all', label: 'All Sites' }, ...sites.map((site) => ({ value: String(site.uid), label: site.name || site.site_name || site.site_code || `Site ${site.uid}` }))]}
            />
          </Col>
          <Col xs={24} md={6}>
            <Select
              style={{ width: '100%' }}
              value={statusFilter}
              onChange={setStatusFilter}
              options={[
                { value: 'all', label: 'All Statuses' },
                { value: 'full', label: 'Fully Filled' },
                { value: 'partial', label: 'Partially Filled' },
                { value: 'unfilled', label: 'Unfilled' },
              ]}
            />
          </Col>
          <Col xs={24} md={4}>
            <Button type="primary" onClick={loadData} block>Refresh</Button>
          </Col>
        </Row>
      </Card>

      <Space wrap>
        <Button type="primary" onClick={() => navigate('/role-contracts/record-daily')}>Record Daily Fulfillment</Button>
        <Button onClick={() => navigate('/role-contracts/monthly-report')}>View Monthly Report</Button>
        <Button onClick={() => navigate('/role-contracts/manage-slots')}>Manage Slots</Button>
      </Space>

      {loading ? (
        <Spin size="large" />
      ) : visibleContracts.length === 0 ? (
        <Alert type="info" title="No labour contracts found for current filters." />
      ) : (
        <Row gutter={[12, 12]}>
          {visibleContracts.map((contract, index) => {
            const record = recordsByContract[contract.contract_id] || {};
            const filledSlots = Number(record.filled ?? contract.total_role_slots ?? 0);
            const siteName = (contract.site_ids || []).map((id) => siteNameById[id]).filter(Boolean).join(', ') || contract.project_name || '—';
            return (
              <Col key={contract.contract_id ?? contract.contract_code ?? `contract-${index}`} xs={24} md={12} lg={8}>
                <ContractRoleCard contract={contract} filledSlots={filledSlots} siteName={siteName} />
              </Col>
            );
          })}
        </Row>
      )}

      {!loading && !contracts.length && <Empty description="No contracts available" />}
    </Space>
  );
};

export default RoleContractFulfillmentOverview;
