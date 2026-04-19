// src/components/ContentHeader.jsx

import React from 'react';
import { FaSearch } from 'react-icons/fa';
// Your CSS file is named content.css in the file list, but the code you provided
// uses classes from ContentHeader.css. I will assume the file is content.css.
import '../styles/content.css'; 

const ContentHeader = () => {
  return (
    <div className="content--header">
        <h1 className="header--title">Dashboard</h1>
        <div className="header--activity">
            <div className="search-box">
                <input type="text" placeholder="Search anything here..." />
                <FaSearch className="icon" />
            </div>
            {/* The notification icon was here. It can be added back if needed. */}
        </div>
    </div>
  );
};

export default ContentHeader;