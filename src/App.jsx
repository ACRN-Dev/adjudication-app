import React, { useEffect, useState } from 'react';
import Header from './components/Header';
import SidebarNav from './components/SidebarNav';
import InstructionBanner from './components/InstructionBanner';
import AdjudicatorWorkbench from './components/AdjudicatorWorkbench';
import CommitteeDashboard from './components/CommitteeDashboard';
import SourceDocViewer from './components/SourceDocViewer';
import SignatureModal from './components/SignatureModal';
import HelpModal from './components/HelpModal';
import SopLibraryModal from './components/SopLibraryModal';
import RecusalModal from './components/RecusalModal';
import DataQueryModal from './components/DataQueryModal';
import LoginPage from './components/LoginPage';
import AdminPortal from './admin/AdminPortal';
import MonitorPortal from './monitor/MonitorPortal';

import { listAssigned, getAssigned, asWorkbenchCase } from './services/realtimeApi';
import { me, logout as logoutApi } from './services/authApi';
import './styles/acrn-theme.css';

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);

  const [cases, setCases] = useState([]);
  const [activeCaseId, setActiveCaseId] = useState(null);
  const [currentStep, setCurrentStep] = useState(1);
  const [activeView, setActiveView] = useState('workbench');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const [showSourceDocs, setShowSourceDocs] = useState(false);
  const [showSignatureModal, setShowSignatureModal] = useState(false);
  const [showHelpModal, setShowHelpModal] = useState(false);
  const [showSopLibrary, setShowSopLibrary] = useState(false);
  const [showRecusalModal, setShowRecusalModal] = useState(false);
  const [showDataQueryModal, setShowDataQueryModal] = useState(false);

  const activeCase = cases.find(c => c.id === activeCaseId) || null;

  useEffect(() => {
    me().then(handleLoginSuccess).catch(() => {});
  }, []);

  useEffect(() => {
    if (!isAuthenticated || user?.portal !== 'adjudicator') return;
    let cancelled = false;
    listAssigned(user).then(items => Promise.all(items.map(x => getAssigned(x.id, user))))
      .then(items => { if (!cancelled) setCases(items.map(asWorkbenchCase)); })
      .catch(() => { if (!cancelled) setCases([]); });
    return () => { cancelled = true; };
  }, [isAuthenticated, user]);

  const handleLoginSuccess = (userData) => {
    setUser(userData);
    setIsAuthenticated(true);
    if (userData.portal === 'admin') history.replaceState({}, '', '/admin');
    else if (userData.portal === 'monitor') history.replaceState({}, '', '/monitor');
    else if (location.pathname.startsWith('/admin')) history.replaceState({}, '', '/');
  };

  const handleLogout = async () => {
    try { await logoutApi(); } catch {}
    setIsAuthenticated(false);
    setUser(null);
    history.replaceState({}, '', '/');
  };

  const handleSelectCase = (id) => {
    setActiveCaseId(id);
  };

  const handleCsvParsed = (newCase) => {
    setCases(prev => [newCase, ...prev]);
    setActiveCaseId(newCase.id);
  };

  const handleSignatureSuccess = (sigData) => {
    setShowSignatureModal(false);
    setCases(prev => prev.map(c => {
      if (c && c.id === activeCaseId) {
        return { ...c, status: 'Finalized & Signed', signature: sigData };
      }
      return c;
    }));
    setCurrentStep(4);
  };

  const handleConfirmRecusal = (recusalData) => {
    setShowRecusalModal(false);
    alert(`FORM-ADJ-08 Recusal Recorded: Participant ${recusalData.caseId} has been recused and re-routed to an independent non-conflicted reviewer.`);
    const nextCase = cases.find(c => c && c.id !== activeCaseId);
    if (nextCase) setActiveCaseId(nextCase.id);
  };

  const handleSubmitQuery = (queryData) => {
    setShowDataQueryModal(false);
    alert(`FORM-ADJ-09 Data Query Sent: Query for Participant ${queryData.caseId} submitted to Adjudication Coordinator for review and dispatch.`);
  };

  const handleAdoptCommitteeOutcome = ({ caseId, outcome, chairComment }) => {
    setCases(prev => prev.map(c => {
      if (c && c.id === caseId) {
        return { ...c, status: 'Finalized (Committee Consensus)', chairComment, adoptedOutcome: outcome };
      }
      return c;
    }));
  };

  if (!isAuthenticated) {
    return <LoginPage onLoginSuccess={handleLoginSuccess} />;
  }

  if (location.pathname.startsWith('/admin')) {
    const adminRoles = ['ADMIN', 'TECHNICAL_ADMIN', 'CLINICAL_OPS_ADMIN', 'QA_AUDITOR', 'GOVERNANCE_REVIEWER', 'ACCESS_REVIEWER'];
    if (!adminRoles.includes(user?.roleCode)) {
      return <div role="alert" style={{ padding: 40, fontFamily: 'Poppins, sans-serif' }}><h1>Access denied</h1><p>Your current role is not permitted to access the Admin Portal.</p><button className="btn-primary" onClick={handleLogout}>Return to sign in</button></div>;
    }
    return <AdminPortal user={user} onLogout={handleLogout} />;
  }
  if (location.pathname.startsWith('/monitor')) {
    const monitorRoles=['MONITOR','ADMIN','ADJUDICATION_COORDINATOR','MONITOR_QC_REVIEWER','QA_REVIEWER','RELEASE_OPERATOR'];
    if(!monitorRoles.includes(user?.roleCode)) return <div role="alert" style={{padding:40}}><h1>Access denied</h1><p>Your role cannot access Monitor/QC operational case data.</p><button onClick={handleLogout}>Return to sign in</button></div>;
    return <MonitorPortal user={user} onLogout={handleLogout}/>;
  }

  const isSigned = activeCase?.status?.includes('Finalized');

  return (
    <div className="app-container">
      {/* RealTime CTMS Header Bar */}
      <Header
        activeCase={activeCase}
        cases={cases}
        onSelectCase={handleSelectCase}
        user={user}
        onLogout={handleLogout}
      />

      <div className="app-main-layout">
        {/* RealTime Left Sidebar */}
        <SidebarNav
          currentStep={currentStep}
          setCurrentStep={setCurrentStep}
          activeView={activeView}
          setActiveView={setActiveView}
          onOpenSopLibrary={() => setShowSopLibrary(true)}
          onOpenHelp={() => setShowHelpModal(true)}
          activeCase={activeCase}
          collapsed={sidebarCollapsed}
          setCollapsed={setSidebarCollapsed}
        />

        {/* Main Viewport */}
        <main className="main-viewport">
          {/* RealTime CTMS Horizontal Tab Strip */}
          <div className="rt-tab-strip">
            <button
              className={`rt-tab-btn ${activeView === 'workbench' && currentStep === 1 ? 'active' : currentStep > 1 ? 'completed' : ''}`}
              onClick={() => { setActiveView('workbench'); setCurrentStep(1); }}
            >
              <span className="rt-tab-badge">1</span>
              Subject Queue
            </button>

            <button
              className={`rt-tab-btn ${activeView === 'workbench' && currentStep === 2 ? 'active' : currentStep > 2 ? 'completed' : ''}`}
              onClick={() => { setActiveView('workbench'); setCurrentStep(2); }}
            >
              <span className="rt-tab-badge">2</span>
              eSource &amp; Evidence
            </button>

            <button
              className={`rt-tab-btn ${activeView === 'workbench' && currentStep === 3 ? 'active' : currentStep > 3 ? 'completed' : ''}`}
              onClick={() => { setActiveView('workbench'); setCurrentStep(3); }}
            >
              <span className="rt-tab-badge">3</span>
              Approve &amp; Sign (FORM-ADJ-15)
            </button>

            <button
              className={`rt-tab-btn ${activeView === 'workbench' && currentStep === 4 ? 'active completed' : ''}`}
              onClick={() => { if (isSigned) { setActiveView('workbench'); setCurrentStep(4); } }}
              disabled={!isSigned}
            >
              <span className="rt-tab-badge">4</span>
              Locked eTMF Record
            </button>

            <button
              className={`rt-tab-btn ${activeView === 'committee' ? 'active' : ''}`}
              onClick={() => setActiveView('committee')}
            >
              Committee Review
            </button>
          </div>

          {activeView === 'workbench' ? (
            <>
              <InstructionBanner step={currentStep} />

              <AdjudicatorWorkbench
                currentStep={currentStep}
                setCurrentStep={setCurrentStep}
                cases={cases}
                activeCase={activeCase}
                onSelectCase={handleSelectCase}
                onCsvParsed={handleCsvParsed}
                onOpenSignature={() => setShowSignatureModal(true)}
                onOpenSourceDocs={() => setShowSourceDocs(true)}
                onOpenRecusalModal={() => setShowRecusalModal(true)}
                onOpenDataQueryModal={() => setShowDataQueryModal(true)}
              />
            </>
          ) : (
            activeCase ? <CommitteeDashboard caseData={activeCase} onAdoptOutcome={handleAdoptCommitteeOutcome} /> :
              <div className="wizard-card"><h2>No assigned participant selected</h2><p>Select an assigned, QC-approved participant before opening committee review.</p></div>
          )}
        </main>
      </div>

      {showSourceDocs && activeCase && (
        <SourceDocViewer caseData={activeCase} onClose={() => setShowSourceDocs(false)} />
      )}

      {showSignatureModal && activeCase && (
        <SignatureModal
          caseData={activeCase}
          onClose={() => setShowSignatureModal(false)}
          onSignConfirm={handleSignatureSuccess}
        />
      )}

      {showHelpModal && <HelpModal onClose={() => setShowHelpModal(false)} />}

      {showSopLibrary && <SopLibraryModal onClose={() => setShowSopLibrary(false)} />}

      {showRecusalModal && activeCase && (
        <RecusalModal
          caseData={activeCase}
          onConfirmRecusal={handleConfirmRecusal}
          onClose={() => setShowRecusalModal(false)}
        />
      )}

      {showDataQueryModal && activeCase && (
        <DataQueryModal
          caseData={activeCase}
          onSubmitQuery={handleSubmitQuery}
          onClose={() => setShowDataQueryModal(false)}
        />
      )}
    </div>
  );
}
