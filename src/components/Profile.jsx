import React from 'react';
import { BiPencil } from 'react-icons/bi';
import { 
    FaRegClipboard, 
    FaSignOutAlt, 
    FaUserPlus, 
    FaBuilding, 
    FaUserTag // Imported icon for Designation
} from 'react-icons/fa';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import '../styles/profile.css';

const Profile = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  // --- Navigation Handlers ---
  const handleAddEmployeeClick = () => {
    navigate('/add-employee');
  };

  const handleSiteManagementClick = () => {
    navigate('/site-management');
  };

  const handleDesignationClick = () => {
    navigate('/designations');
  };

  if (!user) {
    return (
      <div className="profile">
        <div className="profile--header">
           <h2 className="profile--title">Profile</h2>
        </div>
        <div className="profile--details">
           <p>Loading...</p>
        </div>
      </div>
    );
  }

  const userName = user.sub;
  const userRole = user.role;

  return (
    <div className="profile">
      <div className="profile--header">
        <h2 className="profile--title">Profile</h2>
        <BiPencil className="profile--icon" />
      </div>
      <div className="profile--details">
        <img
          src="https://images.unsplash.com/photo-1500648767791-00dcc994a43e?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w1NjY1NDZ8MHwxfHNlYXJjaHwzfHxtYW4lMjBoZWFkfHxlbnwwfHx8fDE3MDAxNTAxMDZ8MA&ixlib=rb-4.0.3&q=80&w=400"
          alt={userName}
          className="profile--image"
        />
        <h3 className="profile--name">{userName}</h3>
        <p className="profile--role">{userRole}</p>
      </div>
      
      <div className="profile--activities">
          <div className="activity--item">
            <FaRegClipboard className="activity--icon" />
            <div className="activity--text">
              <p className="activity--title">Pending Review</p>
              <p className="activity--details">Details</p>
            </div>
            <span className="activity--more">...</span>
          </div>
      </div>

      {/* ACTIONS SECTION */}
      {(userRole === 'SuperAdmin' || userRole === 'Admin') && (
        <div className="profile--actions">
          {/* 1. Add Employee */}
          <button className="action--btn" onClick={handleAddEmployeeClick}>
            <FaUserPlus />
            <span>Add New Employee</span>
          </button>

          {/* 2. Site Management */}
          <button className="action--btn" onClick={handleSiteManagementClick}>
            <FaBuilding />
            <span>Site Management</span>
          </button>

          {/* 3. Manage Designation (New) - Used 'secondary' class for Green Color */}
          <button className="action--btn secondary" onClick={handleDesignationClick}>
            <FaUserTag />
            <span>Manage Designation</span>
          </button>
        </div>
      )}

      <div className="profile--footer">
        <button className="logout--btn" onClick={logout}>
          <FaSignOutAlt />
          <span>Logout</span>
        </button>
      </div>
    </div>
  );
};

export default Profile;