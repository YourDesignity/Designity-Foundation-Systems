import React, { useState } from 'react';
import { LuChevronDown, LuChevronRight } from 'react-icons/lu';

const NavSection = ({ title, icon: Icon, children, defaultOpen = false }) => {
  const [isOpen, setIsOpen] = useState(() => {
    const saved = localStorage.getItem(`nav-section-${title}`);
    return saved !== null ? JSON.parse(saved) : defaultOpen;
  });

  const toggleSection = () => {
    const newState = !isOpen;
    setIsOpen(newState);
    localStorage.setItem(`nav-section-${title}`, JSON.stringify(newState));
  };

  const validChildren = React.Children.toArray(children).filter(Boolean);
  if (validChildren.length === 0) return null;

  return (
    <div className="nav-section">
      <button
        onClick={toggleSection}
        className="nav-section-header"
      >
        <div className="nav-section-title">
          <Icon className="nav-section-icon" size={20} />
          <span>{title}</span>
        </div>
        {isOpen ? <LuChevronDown size={16} /> : <LuChevronRight size={16} />}
      </button>

      {isOpen && (
        <div className="nav-section-items">
          {children}
        </div>
      )}
    </div>
  );
};

export default NavSection;
