import React from 'react';
import ReactApexChart from 'react-apexcharts';
import { Empty, Spin } from 'antd';

/**
 * AttendanceTrendChart – line chart showing attendance rate over the last 30 days.
 *
 * Props:
 *   data     – Array<{ date: string, rate: number (0-100) }>
 *   loading  – boolean
 *   height   – number (default 280)
 */
const AttendanceTrendChart = ({ data = [], loading = false, height = 280 }) => {
  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height }}>
        <Spin />
      </div>
    );
  }

  if (!data.length) {
    return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="No attendance data available" />;
  }

  const categories = data.map((d) => d.date);
  const series = [{ name: 'Attendance Rate (%)', data: data.map((d) => Math.round(Number(d.rate || 0))) }];

  const options = {
    chart: {
      type: 'line',
      toolbar: { show: false },
      zoom: { enabled: false },
    },
    stroke: { curve: 'smooth', width: 2 },
    dataLabels: { enabled: false },
    markers: { size: 3 },
    xaxis: {
      categories,
      labels: { rotate: -45, style: { fontSize: '10px' } },
    },
    yaxis: {
      min: 0,
      max: 100,
      labels: { formatter: (val) => `${val}%` },
    },
    tooltip: { y: { formatter: (val) => `${val}%` } },
    colors: ['#52c41a'],
    grid: { borderColor: '#f0f0f0' },
  };

  return <ReactApexChart options={options} series={series} type="line" height={height} />;
};

export default AttendanceTrendChart;
