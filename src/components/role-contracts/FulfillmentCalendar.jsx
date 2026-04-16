import React from 'react';
import { Calendar, Badge } from 'antd';
import dayjs from 'dayjs';

const FulfillmentCalendar = ({ dailyBreakdown = [] }) => {
  const map = dailyBreakdown.reduce((acc, row) => {
    acc[row.date] = row;
    return acc;
  }, {});

  return (
    <Calendar
      fullscreen={false}
      cellRender={(date) => {
        const key = dayjs(date).format('YYYY-MM-DD');
        const row = map[key];
        if (!row) return null;
        const color = row.unfilled_slots?.length ? 'red' : 'green';
        return <Badge color={color} text={`${Math.round((row.total_filled / Math.max(row.total_required, 1)) * 100)}%`} />;
      }}
    />
  );
};

export default FulfillmentCalendar;
