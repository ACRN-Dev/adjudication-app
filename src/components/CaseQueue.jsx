import React, { useState } from 'react';
import { Search, Filter, CheckCircle, AlertTriangle, Clock, ShieldAlert } from 'lucide-react';

export default function CaseQueue({ cases, activeCaseId, onSelectCase }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterTab, setFilterTab] = useState('ALL');

  const filteredCases = cases.filter(c => {
    const matchesSearch = c.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          c.caseNo.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          c.site.toLowerCase().includes(searchTerm.toLowerCase());
    
    if (filterTab === 'ALL') return matchesSearch;
    if (filterTab === 'PENDING') return matchesSearch && c.status === 'Pending Review';
    if (filterTab === 'DISCORDANT') return matchesSearch && c.status.includes('Discordant');
    if (filterTab === 'SIGNED') return matchesSearch && c.status.includes('Finalized');
    return matchesSearch;
  });

  return (
    <aside className="sidebar-queue">
      <div className="queue-header">
        <div style={{ position: 'relative' }}>
          <Search size={16} style={{ position: 'absolute', left: 10, top: 10, color: 'var(--text-light)' }} />
          <input
            type="text"
            className="queue-search-input"
            placeholder="Search Participant or Case #..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        <div className="queue-tabs">
          <button
            className={`queue-tab-btn ${filterTab === 'ALL' ? 'active' : ''}`}
            onClick={() => setFilterTab('ALL')}
          >
            All ({cases.length})
          </button>
          <button
            className={`queue-tab-btn ${filterTab === 'PENDING' ? 'active' : ''}`}
            onClick={() => setFilterTab('PENDING')}
          >
            Pending
          </button>
          <button
            className={`queue-tab-btn ${filterTab === 'DISCORDANT' ? 'active' : ''}`}
            onClick={() => setFilterTab('DISCORDANT')}
          >
            Discordant
          </button>
          <button
            className={`queue-tab-btn ${filterTab === 'SIGNED' ? 'active' : ''}`}
            onClick={() => setFilterTab('SIGNED')}
          >
            Locked
          </button>
        </div>
      </div>

      <div className="queue-list">
        {filteredCases.map(c => {
          const isActive = c.id === activeCaseId;
          const isFullScore = c.pktScore >= 1.0;
          return (
            <div
              key={c.id}
              className={`case-card ${isActive ? 'active' : ''}`}
              onClick={() => onSelectCase(c.id)}
            >
              <div className="case-card-top">
                <span className="participant-id">{c.id}</span>
                <span className={`score-pill ${isFullScore ? 'full' : 'warn'}`}>
                  Data Score {c.pktScore.toFixed(2)}
                </span>
              </div>

              <div className="case-card-meta">
                <span>{c.caseNo}</span>
                <span>GA {c.gaAtEvent}</span>
              </div>

              <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginTop: '4px' }}>
                {c.status.includes('Discordant') ? (
                  <span className="badge-tag discordant">Discordant Review</span>
                ) : c.status.includes('Finalized') ? (
                  <span className="badge-tag" style={{ background: '#dcfce7', color: '#15803d' }}>Signed & Locked</span>
                ) : (
                  <span className="badge-tag ope">Pending Action</span>
                )}
                
                {c.derivedSeverity === 'SEVERE_FEATURES' && (
                  <span className="badge-tag severe">Severe Features</span>
                )}
                {c.derivedSeverity === 'ECLAMPSIA' && (
                  <span className="badge-tag severe">Eclampsia SAE</span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </aside>
  );
}
