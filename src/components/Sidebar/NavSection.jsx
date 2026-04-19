import React, { useState } from 'react';
import { LuChevronDown, LuChevronRight } from 'react-icons/lu';

/**
 * NavSection — collapsible group of NavItems.
 *
 * Persists open/closed state in localStorage so it survives page refreshes.
 * Key uses a v2 prefix so stale entries from old builds don't interfere.
 */
const NavSection = ({ title, icon: Icon, children, defaultOpen = false }) => {
  const storageKey = `nav-section-v2-${title}`;

  const [isOpen, setIsOpen] = useState(() => {
    try {
      const saved = localStorage.getItem(storageKey);
      return saved !== null ? JSON.parse(saved) : defaultOpen;
    } catch {
      return defaultOpen;
    }
  });

  const toggleSection = () => {
    const next = !isOpen;
    setIsOpen(next);
    try {
      localStorage.setItem(storageKey, JSON.stringify(next));
    } catch {
      // localStorage not available — just update state
    }
  };

  // Filter out falsy children (permission-gated nulls)
  const validChildren = React.Children.toArray(children).filter(Boolean);
  if (validChildren.length === 0) return null;

  return (
    <div className="nav-section">
      <button onClick={toggleSection} className="nav-section-header">
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
