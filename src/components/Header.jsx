import React, { useState, useEffect } from 'react';
import { Search, ChevronDown, LogOut, ShieldCheck } from 'lucide-react';
import { checkBackendHealth } from '../services/api';

export default function Header({ activeCase, cases = [], onSelectCase, user, onLogout }) {
  const [apiOnline, setApiOnline] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [showRecentSubjects, setShowRecentSubjects] = useState(false);
  const [showRecentStudies, setShowRecentStudies] = useState(false);

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

        {/* RealTime Search & Recent Studies/Subjects Navigation Bar */}
        <div className="rt-nav-utility header-work-zone">
          {/* Search Box */}
          <form onSubmit={handleSearchSubmit} className="rt-search-box subject-search">
            <select className="rt-search-scope" aria-label="Search filter scope">
              <option value="all">All</option>
              <option value="subject">Subject ID</option>
              <option value="site">Site</option>
            </select>
            <input
              type="text"
              placeholder="Search subjects, cases..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="rt-search-input"
            />
            <button type="submit" className="rt-search-btn" title="Search">
              <Search size={14} />
            </button>
          </form>

          {/* Recent Studies Dropdown */}
          <div className="rt-recent-dropdown recent-study">
            <button
              className="rt-recent-btn"
              onClick={() => setShowRecentStudies(!showRecentStudies)}
              type="button"
            >
              <span className="rt-recent-label">Recent Studies:</span>
              <strong className="rt-recent-val">MUTALA (ACRN) - PROTECT-Africa</strong>
              <ChevronDown size={14} />
            </button>
            {showRecentStudies && (
              <div className="rt-dropdown-menu">
                <div className="rt-dropdown-item active">
                  <strong>MUTALA (ACRN) - PROTECT-Africa (A202501 v1.2)</strong>
                  <div style={{ fontSize: '11px', color: '#64748b' }}>Primary Study • EOPE &amp; Biomarker Trial</div>
                </div>
                <div className="rt-dropdown-item">
                  <strong>LOPE-Nigeria (ACRN-202503 v1.1)</strong>
                  <div style={{ fontSize: '11px', color: '#64748b' }}>Late-Onset Pre-Eclampsia Cohort</div>
                </div>
              </div>
            )}
          </div>

          {/* Recent Subjects Dropdown */}
          <div className="rt-recent-dropdown recent-subject">
            <button
              className="rt-recent-btn"
              onClick={() => setShowRecentSubjects(!showRecentSubjects)}
              type="button"
            >
              <span className="rt-recent-label">Recent Subjects:</span>
              <strong className="rt-recent-val">
                {activeCase ? `${activeCase.id} (${activeCase.gaAtEvent || 'N/A'})` : 'Select Subject...'}
              </strong>
              <ChevronDown size={14} />
            </button>

            {showRecentSubjects && (
              <div className="rt-dropdown-menu">
                {cases.length > 0 ? (
                  cases.map(c => (
                    <div
                      key={c.id}
                      className={`rt-dropdown-item ${activeCase?.id === c.id ? 'active' : ''}`}
                      onClick={() => {
                        onSelectCase && onSelectCase(c.id);
                        setShowRecentSubjects(false);
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <strong>{c.id}</strong>
                        <span style={{ fontSize: '11px', color: '#64748b' }}>{c.caseNo}</span>
                      </div>
                      <div style={{ fontSize: '11px', color: '#64748b', marginTop: '2px' }}>
                        GA {c.gaAtEvent || 'N/A'} • {c.derivedSubtype || 'EOPE'} • {c.status}
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="rt-dropdown-item" style={{ color: '#94a3b8' }}>
                    No subjects loaded in queue
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

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
