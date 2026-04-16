import React from 'react';
import { Column } from '@ant-design/charts';
import { Empty } from 'antd';

const CostBreakdownChart = ({ costByDesignation = {} }) => {
  const data = Object.entries(costByDesignation).map(([designation, cost]) => ({ designation, cost: Number(cost || 0) }));
  if (!data.length) {
    return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="No cost data" />;
  }

  return (
    <Column
      data={data}
      xField="designation"
      yField="cost"
      legend={{ position: 'bottom' }}
      label={{ text: 'cost', position: 'top' }}
      height={280}
    />
  );
};

export default CostBreakdownChart;
