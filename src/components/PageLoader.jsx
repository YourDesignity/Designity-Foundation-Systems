import React from 'react';
import { Spin } from 'antd';

const PageLoader = () => (
  <div
    style={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      minHeight: '60vh',
    }}
  >
    <Spin size="large" />
  </div>
);

export default PageLoader;
