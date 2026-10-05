import React, { useState, useEffect } from 'react';
import { Search, ChevronDown, LogOut, ShieldCheck } from 'lucide-react';
import { checkBackendHealth } from '../services/api';

export default function Header({ activeCase, cases = [], onSelectCase, user, onLogout }) {
  const [apiOnline, setApiOnline] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [showRecentSubjects, setShowRecentSubjects] = useState(false);
  const [showRecentStudies, setShowRecentStudies] = useState(false);
  const [selectedStudy, setSelectedStudy] = useState('MUTALA (ACRN) - PROTECT-Africa');

  useEffect(() => {
    checkBackendHealth().then(res => {
      setApiOnline(res.online);
    });
  }, []);

  const userName = user?.name || 'Dr. Tinotenda Chibongore';
  const userRole = user?.role || 'Primary Adjudicator • ACRN';

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    if (!searchQuery.trim() || !cases.length) return;
    const match = cases.find(c =>
      c.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.caseNo.toLowerCase().includes(searchQuery.toLowerCase())
    );
    if (match && onSelectCase) {
      onSelectCase(match.id);
    }
  };

  return (
    <header className="rt-header">
      {/* Top Utility Row (RealTime CTMS Style) */}
      <div className="rt-header-top app-header-layout">
        {/* Brand section */}
        <div className="rt-brand-box header-brand-zone">
          <div className="rt-logo-card">
            <img src="/acrn-logo.png" alt="ACRN Logo" className="brand-logo" />
          </div>
          <div className="rt-brand-titles portal-identity">
            <span className="rt-brand-main">Adjudication Portal</span>
            <span className="rt-brand-sub">PROTECT-Africa (EOPE) &amp; LOPE-Nigeria</span>
          </div>
        </div>

        <div className="rt-nav-utility header-work-zone"></div>

        {/* User Badge & API Status */}
        <div className="rt-user-section header-user-zone">
          <span className={`rt-status-pill ${apiOnline ? 'online' : 'standalone'}`}>
            <span className="rt-dot"></span>
            {apiOnline ? 'API Connected' : 'Demo Mode'}
          </span>

          <div className="user-details">
            <div className="user-name">{userName}</div>
            <div className="user-role">{userRole}</div>
          </div>

          {onLogout && (
            <button onClick={onLogout} title="Sign Out" className="rt-logout-btn">
              <LogOut size={16} />
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
