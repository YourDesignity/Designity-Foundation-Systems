import React from 'react';
import ReactApexChart from 'react-apexcharts';
import { Empty, Spin } from 'antd';

/**
 * CostTrendChart – monthly cost trend for a role contract.
 *
 * Props:
 *   data     – Array<{ month: string, total_cost: number }>
 *   loading  – boolean
 *   height   – number (default 280)
 */
const CostTrendChart = ({ data = [], loading = false, height = 280 }) => {
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

  const categories = data.map((d) => d.month);
  const series = [{ name: 'Total Cost', data: data.map((d) => Number(d.total_cost || 0)) }];

  const options = {
    chart: {
      type: 'area',
      toolbar: { show: false },
      zoom: { enabled: false },
    },
    dataLabels: { enabled: false },
    stroke: { curve: 'smooth', width: 2 },
    fill: {
      type: 'gradient',
      gradient: {
        shadeIntensity: 1,
        opacityFrom: 0.4,
        opacityTo: 0.05,
        stops: [0, 90, 100],
      },
    },
    xaxis: { categories, labels: { rotate: -30 } },
    yaxis: {
      labels: {
        formatter: (val) =>
          val >= 1000 ? `$${(val / 1000).toFixed(1)}k` : `$${val}`,
      },
    },
    tooltip: {
      y: { formatter: (val) => `$${Number(val).toLocaleString()}` },
    },
    colors: ['#1677ff'],
  };

  return <ReactApexChart options={options} series={series} type="area" height={height} />;
};

export default CostTrendChart;
