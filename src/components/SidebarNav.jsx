import React from 'react';
import {
  FolderKanban,
  Users,
  CheckSquare,
  FileText,
  ShieldCheck,
  BookOpen,
  HelpCircle,
  Lock,
  PanelLeftClose,
  PanelLeftOpen,
  Activity,
  Layers,
  Settings
} from 'lucide-react';

/**
 * SidebarNav — RealTime CTMS Style Left Navigation Sidebar
 * Clean, high-density, crisp icons + labels.
 * Collapsible to mini-rail or expanded mode.
 */
export default function SidebarNav({
  currentStep,
  setCurrentStep,
  activeView,
  setActiveView,
  onOpenSopLibrary,
  onOpenHelp,
  activeCase,
  collapsed,
  setCollapsed
}) {
  const isSigned = activeCase?.status?.includes('Finalized');

  const menuItems = [
    {
      id: 'subjects',
      label: 'Subject Queue (Step 1)',
      icon: Users,
      action: () => { setActiveView('workbench'); setCurrentStep(1); },
      active: activeView === 'workbench' && currentStep === 1,
      badge: activeCase ? activeCase.id : null,
    },
    {
      id: 'evidence',
      label: 'eSource Evidence (Step 2)',
      icon: Activity,
      action: () => { setActiveView('workbench'); setCurrentStep(2); },
      active: activeView === 'workbench' && currentStep === 2,
    },
    {
      id: 'sign',
      label: 'Approve & Sign (Step 3)',
      icon: FileText,
      action: () => { setActiveView('workbench'); setCurrentStep(3); },
      active: activeView === 'workbench' && currentStep === 3,
    },
    {
      id: 'tmf',
      label: 'Locked eTMF (Step 4)',
      icon: Lock,
      action: () => { if (isSigned) { setActiveView('workbench'); setCurrentStep(4); } },
      active: activeView === 'workbench' && currentStep === 4,
      disabled: !isSigned,
    },
    {
      id: 'committee',
      label: 'Committee Review',
      icon: FolderKanban,
      action: () => setActiveView('committee'),
      active: activeView === 'committee',
    },
    {
      id: 'qc',
      label: 'QC Portal & Gates',
      icon: CheckSquare,
      action: () => { setActiveView('workbench'); setCurrentStep(2); },
      active: false,
    },
    {
      id: 'sops',
      label: 'SOP Library',
      icon: BookOpen,
      action: onOpenSopLibrary,
      active: false,
    },
    {
      id: 'guide',
      label: 'User Guide',
      icon: HelpCircle,
      action: onOpenHelp,
      active: false,
    },
  ];

  if (collapsed) {
    return (
      <aside className="rt-sidebar collapsed">
        <button
          onClick={() => setCollapsed(false)}
          className="rt-toggle-btn"
          title="Expand navigation sidebar"
          aria-label="Expand navigation sidebar"
        >
          <PanelLeftOpen size={18} />
        </button>

        <div className="rt-mini-nav">
          {menuItems.map(item => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                className={`rt-mini-btn ${item.active ? 'active' : ''} ${item.disabled ? 'disabled' : ''}`}
                onClick={item.action}
                title={item.label}
                disabled={item.disabled}
              >
                <Icon size={18} />
              </button>
            );
          })}
        </div>
      </aside>
    );
  }

  return (
    <aside className="rt-sidebar expanded">
      {/* Brand / Title Banner */}
      <div className="rt-sidebar-header">
        <span className="rt-sidebar-brand-title">RealTime Navigation</span>
        <button
          onClick={() => setCollapsed(true)}
          className="rt-toggle-btn"
          title="Collapse navigation sidebar"
          aria-label="Collapse navigation sidebar"
        >
          <PanelLeftClose size={16} />
        </button>
      </div>

      <div className="rt-sidebar-menu">
        <div className="rt-menu-group-label">Adjudication Steps</div>
        {menuItems.slice(0, 4).map(item => {
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              className={`rt-menu-btn ${item.active ? 'active' : ''} ${item.disabled ? 'disabled' : ''}`}
              onClick={item.action}
              disabled={item.disabled}
            >
              <Icon size={16} className="rt-menu-icon" />
              <span className="rt-menu-text">{item.label}</span>
              {item.badge && <span className="rt-menu-badge">{item.badge}</span>}
            </button>
          );
        })}

        <div className="rt-menu-divider" />

        <div className="rt-menu-group-label">Governance &amp; Tools</div>
        {menuItems.slice(4).map(item => {
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              className={`rt-menu-btn ${item.active ? 'active' : ''}`}
              onClick={item.action}
            >
              <Icon size={16} className="rt-menu-icon" />
              <span className="rt-menu-text">{item.label}</span>
            </button>
          );
        })}
      </div>

      <div className="rt-sidebar-footer">
        <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.5)', textAlign: 'center' }}>
          ACRN Platform v2.1 • SOP-ADJ-002
        </div>
      </div>
    </aside>
  );
}
