import React from 'react';
import ReactApexChart from 'react-apexcharts';
import { Empty, Spin } from 'antd';

/**
 * RevenueTrendChart – bar chart showing monthly revenue for the last 12 months.
 *
 * Props:
 *   data     – Array<{ month: string, revenue: number }>
 *   loading  – boolean
 *   height   – number (default 280)
 */
const RevenueTrendChart = ({ data = [], loading = false, height = 280 }) => {
  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height }}>
        <Spin />
      </div>
    );
  }

  if (!data.length) {
    return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="No revenue data available" />;
  }

  const categories = data.map((d) => d.month);
  const series = [{ name: 'Revenue', data: data.map((d) => Number(d.revenue || 0)) }];

  const options = {
    chart: {
      type: 'bar',
      toolbar: { show: false },
    },
    plotOptions: {
      bar: { borderRadius: 4, columnWidth: '55%' },
    },
    dataLabels: { enabled: false },
    xaxis: { categories },
    yaxis: {
      labels: {
        formatter: (val) =>
          val >= 1000 ? `$${(val / 1000).toFixed(0)}k` : `$${val}`,
      },
    },
    tooltip: { y: { formatter: (val) => `$${Number(val).toLocaleString()}` } },
    colors: ['#1677ff'],
    grid: { borderColor: '#f0f0f0' },
  };

  return <ReactApexChart options={options} series={series} type="bar" height={height} />;
};

export default RevenueTrendChart;
