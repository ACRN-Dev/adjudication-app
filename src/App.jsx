import React, { useEffect, useState } from 'react';
import Header from './components/Header';
import SidebarNav from './components/SidebarNav';
import InstructionBanner from './components/InstructionBanner';
import AdjudicatorWorkbench from './components/AdjudicatorWorkbench';
import SourceDocViewer from './components/SourceDocViewer';
import SignatureModal from './components/SignatureModal';
import HelpModal from './components/HelpModal';
import SopLibraryModal from './components/SopLibraryModal';
import RecusalModal from './components/RecusalModal';
import DataQueryModal from './components/DataQueryModal';
import CommitteeDashboard from './components/CommitteeDashboard';
import LoginPage from './components/LoginPage';
import ForceChangePassword from './components/ForceChangePassword';
import AdminPortal from './admin/AdminPortal';
import MonitorPortal from './monitor/MonitorPortal';
import ChairpersonPortal from './chairperson/ChairpersonPortal';

import { listAssigned, getAssigned, asWorkbenchCase } from './services/realtimeApi';
import { me, logout as logoutApi } from './services/authApi';
import './styles/acrn-theme.css';

export default function App() {
  const [currentPath, setCurrentPath] = useState(window.location.pathname);
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  const [cases, setCases] = useState([]);
  const [activeCaseId, setActiveCaseId] = useState(null);
  const [currentStep, setCurrentStep] = useState(1);
  const [activeView, setActiveView] = useState('workbench');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const [showSourceDocs, setShowSourceDocs] = useState(false);
  const [showSignatureModal, setShowSignatureModal] = useState(false);
  const [signatureSubmission, setSignatureSubmission] = useState(null);
  const [advanceToVisitIndex, setAdvanceToVisitIndex] = useState(null);
  const [showHelpModal, setShowHelpModal] = useState(false);
  const [showSopLibrary, setShowSopLibrary] = useState(false);
  const [showRecusalModal, setShowRecusalModal] = useState(false);
  const [showDataQueryModal, setShowDataQueryModal] = useState(false);

  const activeCase = cases.find(c => c.id === activeCaseId) || null;
  const isCommitteeCase = ['DISCORDANT', 'COMMITTEE_PENDING', 'THREE_WAY_DIVERGENT'].some(
    status => String(activeCase?.status || '').toUpperCase().includes(status)
  );

  useEffect(() => {
    const handlePop = () => setCurrentPath(window.location.pathname);
    window.addEventListener('popstate', handlePop);
    return () => window.removeEventListener('popstate', handlePop);
  }, []);

  useEffect(() => {
    me().then(handleLoginSuccess).catch(() => {});
  }, []);

  useEffect(() => {
    if (!isAuthenticated || user?.must_change_password || user?.portal !== 'adjudicator') return;
    let cancelled = false;
    listAssigned(user).then(items => Promise.all(items.map(x => getAssigned(x.id, user))))
      .then(items => { if (!cancelled) setCases(items.map(item => asWorkbenchCase(item, user))); })
      .catch(() => { if (!cancelled) setCases([]); });
    return () => { cancelled = true; };
  }, [isAuthenticated, user]);

  const handleLoginSuccess = (userData) => {
    let target = '/';
    if (userData.portal === 'admin') target = '/admin';
    else if (userData.portal === 'monitor') target = '/monitor';
    else if (userData.portal === 'chairperson') target = '/chairperson';
    else if (window.location.pathname.startsWith('/admin') || window.location.pathname.startsWith('/monitor') || window.location.pathname.startsWith('/chairperson')) target = '/';
    else target = window.location.pathname;

    window.history.replaceState({}, '', target);
    setCurrentPath(target);
    setUser(userData);
    setIsAuthenticated(true);
  };


  const handleLogout = async () => {
    try { await logoutApi(); } catch {}
    setIsAuthenticated(false);
    setUser(null);
    window.history.replaceState({}, '', '/');
    setCurrentPath('/');
  };

  const handleSelectCase = (id) => {
    setActiveCaseId(id);
    setAdvanceToVisitIndex(null);
  };

  const handleCsvParsed = (newCase) => {
    setCases(prev => [newCase, ...prev]);
    setActiveCaseId(newCase.id);
  };

  const handleSignatureSuccess = (sigData) => {
    setShowSignatureModal(false);
    const signedVisit=Number(sigData.visit_number||signatureSubmission?.visitNumber||1);
    const updatedActiveVisits=(activeCase?.visits||[]).map((visit,index)=>index+1===signedVisit?{...visit,status:sigData.visit_status||'SIGNED',signed:true,filing_status:sigData.filing_status,signature:sigData}:visit);
    const visitCount = Math.max(6, updatedActiveVisits.length || 0);
    const finalVisitStates = ['CONCORDANT', 'RESOLVED_BY_MAJORITY', 'FINALIZED', 'CLOSED', 'SIGNED'];
    const allVisitsComplete = Array.from({ length: visitCount }, (_, index) => {
      const visit = updatedActiveVisits[index];
      return Boolean(
        visit
        && (finalVisitStates.includes(String(visit.resolution_status || visit.final_status || visit.status).toUpperCase())
          || visit.final_record
          || visit.finalized
          || visit.signed)
      );
    }).every(Boolean);
    const nextVisitIndex = Math.min(Math.max(signedVisit, 0), visitCount);
    setCases(prev => prev.map(c => {
      if (c && c.id === activeCaseId) {
        const visits=(c.visits||[]).map((visit,index)=>index+1===signedVisit?{...visit,status:sigData.visit_status||'SIGNED',signed:true,filing_status:sigData.filing_status,signature:sigData}:visit);
        return {
          ...c,
          visits,
          status: allVisitsComplete ? 'Finalized & Signed' : 'Adjudication In Progress',
          signature: sigData,
        };
      }
      return c;
    }));
    setAdvanceToVisitIndex(allVisitsComplete ? null : nextVisitIndex);
    setCurrentStep(allVisitsComplete ? 4 : 3);
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

  if (!isAuthenticated) {
    return <LoginPage onLoginSuccess={handleLoginSuccess} />;
  }

  if (user?.must_change_password) {
    return (
      <ForceChangePassword
        user={user}
        onChanged={(updatedUser) => setUser(updatedUser)}
        onLogout={handleLogout}
      />
    );
  }

  if (currentPath.startsWith('/admin')) {
    const adminRoles = ['ADMIN', 'TECHNICAL_ADMIN', 'CLINICAL_OPS_ADMIN', 'QA_AUDITOR', 'GOVERNANCE_REVIEWER', 'ACCESS_REVIEWER'];
    if (!adminRoles.includes(user?.roleCode)) {
      return <div role="alert" style={{ padding: 40, fontFamily: 'Poppins, sans-serif' }}><h1>Access denied</h1><p>Your current role is not permitted to access the Admin Portal.</p><button className="btn-primary" onClick={handleLogout}>Return to sign in</button></div>;
    }
    return <AdminPortal user={user} onLogout={handleLogout} />;
  }
  if (currentPath.startsWith('/monitor')) {
    const monitorRoles=['MONITOR','ADMIN','ADJUDICATION_COORDINATOR','MONITOR_QC_REVIEWER','QA_REVIEWER','RELEASE_OPERATOR'];
    if(!monitorRoles.includes(user?.roleCode)) return <div role="alert" style={{padding:40}}><h1>Access denied</h1><p>Your role cannot access Monitor/QC operational case data.</p><button onClick={handleLogout}>Return to sign in</button></div>;
    return <MonitorPortal user={user} onLogout={handleLogout}/>;
  }
  if (currentPath.startsWith('/chairperson') || user?.roleCode === 'CHAIRPERSON' || user?.portal === 'chairperson') {
    return <ChairpersonPortal user={user} onLogout={handleLogout} />;
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
          onOpenCommitteeReview={() => setActiveView('committee')}
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

          </div>

          <>
            <InstructionBanner step={currentStep} />

            {activeView === 'committee' && isCommitteeCase ? (
              <CommitteeDashboard caseData={activeCase} onAdoptOutcome={() => setActiveView('workbench')} />
            ) : (
            <AdjudicatorWorkbench
              currentStep={currentStep}
              setCurrentStep={setCurrentStep}
              cases={cases}
              activeCase={activeCase}
              user={user}
              onSelectCase={handleSelectCase}
              onCsvParsed={handleCsvParsed}
              onOpenSignature={submission => { setSignatureSubmission(submission); setShowSignatureModal(true); }}
              onOpenSourceDocs={() => setShowSourceDocs(true)}
              onOpenRecusalModal={() => setShowRecusalModal(true)}
              onOpenDataQueryModal={() => setShowDataQueryModal(true)}
              advanceToVisitIndex={advanceToVisitIndex}
            />
            )}
          </>
        </main>
      </div>

      {showSourceDocs && activeCase && (
        <SourceDocViewer caseData={activeCase} onClose={() => setShowSourceDocs(false)} />
      )}

      {showSignatureModal && activeCase && (
        <SignatureModal
          caseData={activeCase}
          user={user}
          submission={signatureSubmission}
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
