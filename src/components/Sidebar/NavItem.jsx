import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

const NavItem = ({ to, icon: Icon, label, badge }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const isActive = location.pathname === to;

  return (
    <button
      onClick={() => navigate(to)}
      className={`nav-item ${isActive ? 'active' : ''}`}
    >
      <Icon className="nav-item-icon" size={18} />
      <span className="nav-item-label">{label}</span>
      {badge && <span className="nav-item-badge">{badge}</span>}
    </button>
  );
};

export default NavItem;
