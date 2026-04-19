import React from 'react';
import { Tag } from 'antd';
import { getContractTypeLabel, getContractTypeColor } from '../../constants/contractTypes';

const ContractCard = ({ contract, onClick }) => {
  if (!contract) return null;

  const typeLabel = getContractTypeLabel(contract.contract_type);
  const typeColor = getContractTypeColor(contract.contract_type);

  return (
    <div
      className="contract-card"
      onClick={() => onClick && onClick(contract)}
      style={{ cursor: onClick ? 'pointer' : 'default' }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 4 }}>
            {contract.contract_name || contract.contract_code}
          </div>
          <div style={{ fontSize: 12, color: '#888', marginBottom: 8 }}>
            {contract.contract_code}
          </div>
        </div>
        <Tag color={typeColor} style={{ fontSize: 11 }}>
          {typeLabel}
        </Tag>
      </div>

      {contract.project_name && (
        <div style={{ fontSize: 12, color: '#555', marginBottom: 4 }}>
          Project: {contract.project_name}
        </div>
      )}

      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 8 }}>
        {contract.status && (
          <Tag color={contract.status === 'Active' ? 'green' : contract.status === 'Expired' ? 'red' : 'default'}>
            {contract.status}
          </Tag>
        )}
        {contract.days_remaining !== undefined && contract.days_remaining > 0 && (
          <Tag color={contract.is_expiring_soon ? 'warning' : 'default'}>
            {contract.days_remaining}d remaining
          </Tag>
        )}
      </div>
    </div>
  );
};

export default ContractCard;
