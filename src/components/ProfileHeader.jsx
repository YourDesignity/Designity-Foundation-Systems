// src/components/ProfileHeader.jsx

import React from 'react';
import { FaSearch } from 'react-icons/fa';
import '../styles/profileHeader.css';

const ProfileHeader = () => {
    return (
        <header className="profile-header">
            <div className="search-bar">
                <FaSearch className="search-icon" />
                <input type="text" placeholder="Search anything here..." />
            </div>
        </header>
    );
};

export default ProfileHeader;