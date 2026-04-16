import React from 'react';
import { Pie } from '@ant-design/charts';

const CostBreakdownChart = ({ costByDesignation = {} }) => {
  const data = Object.entries(costByDesignation).map(([designation, cost]) => ({ designation, cost: Number(cost || 0) }));

  return (
    <Pie
      data={data}
      angleField="cost"
      colorField="designation"
      legend={{ position: 'bottom' }}
      label={{ text: 'designation', position: 'outside' }}
      height={280}
    />
  );
};

export default CostBreakdownChart;
