import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

/**
 * NavItem — a single navigation link inside a NavSection.
 *
 * Active detection uses startsWith so that a parent route stays highlighted
 * when the user is on a child route.
 * e.g. /project-workflow stays active when on /project-workflow/123/details
 *
 * Pass  exact={true}  for routes where you only want an exact match
 * (e.g. /dashboard should NOT stay active when on /dashboard-something).
 */
const NavItem = ({ to, icon: Icon, label, badge, exact = false }) => {
  const navigate  = useNavigate();
  const { pathname } = useLocation();

  const isActive = exact
    ? pathname === to
    : pathname === to || pathname.startsWith(to + '/');

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
