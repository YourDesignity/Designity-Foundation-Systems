import React from 'react';
import ReactApexChart from 'react-apexcharts';
import { Empty, Spin } from 'antd';

/**
 * CostBreakdownChart – pie chart showing cost split by category (labour, materials, vehicles).
 *
 * Props:
 *   data     – Array<{ category: string, value: number }>
 *   loading  – boolean
 *   height   – number (default 280)
 */
const CostBreakdownChart = ({ data = [], loading = false, height = 280 }) => {
  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height }}>
        <Spin />
      </div>
    );
  }

  if (!data.length) {
    return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="No cost data available" />;
  }

  const labels = data.map((d) => d.category);
  const series = data.map((d) => Number(d.value || 0));

  const options = {
    chart: { type: 'pie', toolbar: { show: false } },
    labels,
    legend: { position: 'bottom' },
    tooltip: { y: { formatter: (val) => `$${Number(val).toLocaleString()}` } },
    responsive: [
      {
        breakpoint: 480,
        options: { chart: { width: '100%' }, legend: { position: 'bottom' } },
      },
    ],
  };

  return <ReactApexChart options={options} series={series} type="pie" height={height} />;
};

export default CostBreakdownChart;
