import React from 'react';
import ReactApexChart from 'react-apexcharts';
import { Empty, Spin } from 'antd';

/**
 * ProjectStatusChart – donut chart showing project statuses.
 *
 * Props:
 *   data     – Array<{ status: string, count: number }>
 *   loading  – boolean
 *   height   – number (default 280)
 */
const ProjectStatusChart = ({ data = [], loading = false, height = 280 }) => {
  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height }}>
        <Spin />
      </div>
    );
  }

  if (!data.length) {
    return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="No project data available" />;
  }

  const labels = data.map((d) => d.status);
  const series = data.map((d) => Number(d.count || 0));

  const statusColors = {
    Active: '#52c41a',
    Completed: '#1677ff',
    'On Hold': '#faad14',
    Cancelled: '#ff4d4f',
    Planning: '#722ed1',
  };

  const colors = labels.map((l) => statusColors[l] || '#8c8c8c');

  const options = {
    chart: { type: 'donut', toolbar: { show: false } },
    labels,
    colors,
    legend: { position: 'bottom' },
    plotOptions: {
      pie: {
        donut: {
          size: '60%',
          labels: {
            show: true,
            total: {
              show: true,
              label: 'Total',
              formatter: (w) =>
                w.globals.seriesTotals.reduce((a, b) => a + b, 0),
            },
          },
        },
      },
    },
    tooltip: { y: { formatter: (val) => `${val} project${val !== 1 ? 's' : ''}` } },
    responsive: [
      {
        breakpoint: 480,
        options: { chart: { width: '100%' }, legend: { position: 'bottom' } },
      },
    ],
  };

  return <ReactApexChart options={options} series={series} type="donut" height={height} />;
};

export default ProjectStatusChart;
