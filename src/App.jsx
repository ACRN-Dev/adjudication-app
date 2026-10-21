import React, { Suspense, lazy, useEffect, useState } from 'react';
import Header from './components/Header';
import SidebarNav from './components/SidebarNav';
import ErrorBoundary from './components/ErrorBoundary';
import LoginPage from './components/LoginPage';
import ForceChangePassword from './components/ForceChangePassword';
import { DEMO_UI_BUILD_ENABLED } from './config/featureFlags';

import { listAssigned, getAssigned, asWorkbenchCase, raiseDataQuery, declareRecusal } from './services/realtimeApi';
import { me, logout as logoutApi } from './services/authApi';
import { isReviewerVisitSigned } from './services/visitEvidence';
import './styles/acrn-theme.css';

const AdjudicatorWorkbench = lazy(() => import('./components/AdjudicatorWorkbench'));
const SourceDocViewer = lazy(() => import('./components/SourceDocViewer'));
const SignatureModal = lazy(() => import('./components/SignatureModal'));
const HelpModal = lazy(() => import('./components/HelpModal'));
const SopLibraryModal = lazy(() => import('./components/SopLibraryModal'));
const RecusalModal = lazy(() => import('./components/RecusalModal'));
const DataQueryModal = lazy(() => import('./components/DataQueryModal'));
const AdminPortal = lazy(() => import('./admin/AdminPortal'));
const MonitorPortal = lazy(() => import('./monitor/MonitorPortal'));
const ChairpersonPortal = lazy(() => import('./chairperson/ChairpersonPortal'));
const OwnerPortal = lazy(() => import('./owner/OwnerPortal'));

function LoadingPortal() {
  return <div role="status" aria-live="polite" className="portal-loading">Loading workspace…</div>;
}

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
    if (!isAuthenticated || user?.must_change_password || user?.portal !== 'adjudicator' && user?.portal !== 'owner') return;
    let cancelled = false;
    listAssigned(user).then(items => Promise.all(items.map(x => getAssigned(x.id, user))))
      .then(items => { if (!cancelled) setCases(items.map(item => asWorkbenchCase(item, user))); })
      .catch(() => { if (!cancelled) setCases([]); });
    return () => { cancelled = true; };
  }, [isAuthenticated, user]);

  const handleLoginSuccess = (userData) => {
    let target = '/';
    if (userData.portal === 'owner') target = '/owner';
    else if (userData.portal === 'admin') target = '/admin';
    else if (userData.portal === 'monitor') target = '/monitor';
    else if (userData.portal === 'chairperson') target = '/chairperson';
    else if (window.location.pathname.startsWith('/owner') || window.location.pathname.startsWith('/admin') || window.location.pathname.startsWith('/monitor') || window.location.pathname.startsWith('/chairperson')) target = '/';
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
    const results = Array.isArray(sigData.results) ? sigData.results : [sigData];
    const resultsByVisit = new Map(results.map(result => [
      Number(result.visit_number || signatureSubmission?.visitNumber || 1),
      result,
    ]));
    const updatedActiveVisits = (activeCase?.visits || []).map((visit, index) => {
      const visitNumber = Number(visit.visit_number || index + 1);
      const result = resultsByVisit.get(visitNumber);
      return result ? {
        ...visit,
        status: result.visit_status || 'SIGNED',
        signed: true,
        filing_status: result.filing_status,
        signature: {
          signer: user?.display_name || user?.name || user?.email,
          email: user?.email,
          timestamp: result.signed_at,
          hash: result.signature_hash,
          visit_number: visitNumber,
        },
      } : visit;
    });
    const finalVisitStates = ['CONCORDANT', 'RESOLVED_BY_MAJORITY', 'FINALIZED', 'CLOSED'];
    const allVisitsFinalized = updatedActiveVisits.length > 0 && updatedActiveVisits.every(visit =>
      finalVisitStates.includes(String(visit.resolution_status || visit.final_status || visit.status).toUpperCase())
      || visit.final_record
      || visit.finalized
    );
    const currentReviewerSigned = visit => isReviewerVisitSigned(visit, activeCase?.reviewerRole);
    const allReviewerVisitsSigned = updatedActiveVisits.length > 0
      && updatedActiveVisits.every(currentReviewerSigned);
    const firstUnsignedVisitIndex = updatedActiveVisits.findIndex(visit => !currentReviewerSigned(visit));
    const nextVisitIndex = firstUnsignedVisitIndex === -1 ? updatedActiveVisits.length : firstUnsignedVisitIndex;
    const latestResult = results[results.length - 1] || sigData;
    const caseSignature = latestResult.signature_hash ? {
      signer: user?.display_name || user?.name || user?.email,
      email: user?.email,
      timestamp: latestResult.signed_at,
      hash: latestResult.signature_hash,
    } : sigData;
    setCases(prev => prev.map(c => {
      if (c && c.id === activeCaseId) {
        const visits = (c.visits || []).map((visit, index) => {
          const visitNumber = Number(visit.visit_number || index + 1);
          return resultsByVisit.has(visitNumber) ? updatedActiveVisits[index] : visit;
        });
        return {
          ...c,
          visits,
          status: allVisitsFinalized
            ? 'Finalized & Signed'
            : allReviewerVisitsSigned
              ? 'Reviewer Adjudications Signed'
              : 'Adjudication In Progress',
          signature: caseSignature,
        };
      }
      return c;
    }));
    setAdvanceToVisitIndex(allReviewerVisitsSigned ? null : nextVisitIndex);
    setCurrentStep(allReviewerVisitsSigned || allVisitsFinalized ? 4 : 2);
    // Start each newly loaded adjudication state at the top of the workbench.
    requestAnimationFrame(() => window.scrollTo({ top: 0, left: 0, behavior: 'smooth' }));
  };

  const handleConfirmRecusal = async (recusalData) => {
    try {
      await declareRecusal(activeCase.databaseId, { reason_code: recusalData.recusalReason, comments: recusalData.comments }, user);
      setShowRecusalModal(false);
      const remaining = cases.filter(c => c && c.id !== activeCaseId);
      setCases(remaining);
      setActiveCaseId(remaining[0]?.id || null);
      alert(`FORM-ADJ-08 Recusal recorded. Participant ${recusalData.caseId} was reassigned to an independent reviewer.`);
    } catch (error) {
      alert(error.message);
    }
  };

  useEffect(() => {
    const handleOpenQuery = () => setShowDataQueryModal(true);
    window.addEventListener('open-data-query-modal', handleOpenQuery);
    return () => window.removeEventListener('open-data-query-modal', handleOpenQuery);
  }, []);

  const handleSubmitQuery = async (queryData) => {
    try {
      await raiseDataQuery(activeCase.databaseId, { category: queryData.queryCategory, query_text: queryData.queryText }, user);
      setShowDataQueryModal(false);
      alert(`FORM-ADJ-09 Data Query sent for Participant ${queryData.caseId}. Electronic signature is blocked until it is resolved.`);
    } catch (error) {
      alert(error.message);
    }
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

  if (user?.portal === 'owner' || currentPath.startsWith('/owner')) {
    if (!DEMO_UI_BUILD_ENABLED) {
      return (
        <div role="status" style={{ padding: 40, fontFamily: 'Poppins, sans-serif' }}>
          <h1>Owner portal unavailable</h1>
          <p>The owner portal is disabled in this deployment while its demonstration data is being replaced with live operational data.</p>
          {user?.roleCode === 'OWNER' && (
            <button
              className="btn-primary"
              onClick={() => {
                history.pushState({}, '', '/admin/users');
                setCurrentPath('/admin/users');
              }}
            >
              Open user administration
            </button>
          )}
          <button className="btn-primary" onClick={handleLogout}>Sign out</button>
        </div>
      );
    }
    return <Suspense fallback={<LoadingPortal />}><OwnerPortal user={user} onLogout={handleLogout} /></Suspense>;
  }
  if (currentPath.startsWith('/admin')) {
    const adminRoles = ['ADMIN', 'TECHNICAL_ADMIN', 'CLINICAL_OPS_ADMIN', 'QA_AUDITOR', 'GOVERNANCE_REVIEWER', 'ACCESS_REVIEWER', 'OWNER'];
    if (!adminRoles.includes(user?.roleCode)) {
      return <div role="alert" style={{ padding: 40, fontFamily: 'Poppins, sans-serif' }}><h1>Access denied</h1><p>Your current role is not permitted to access the Admin Portal.</p><button className="btn-primary" onClick={handleLogout}>Return to sign in</button></div>;
    }
    return <Suspense fallback={<LoadingPortal />}><AdminPortal user={user} onLogout={handleLogout} readOnly={user?.roleCode === 'OWNER'} /></Suspense>;
  }
  if (currentPath.startsWith('/monitor')) {
    const monitorRoles=['MONITOR','MEDICAL_OFFICER','MEDICAL_MONITOR','ADMIN','CHAIRPERSON','ADJUDICATION_COORDINATOR','MONITOR_QC_REVIEWER','QA_REVIEWER','RELEASE_OPERATOR','OWNER'];
    if(!monitorRoles.includes(user?.roleCode)) return <div role="alert" style={{padding:40}}><h1>Access denied</h1><p>Your role cannot access Monitor/QC operational case data.</p><button onClick={handleLogout}>Return to sign in</button></div>;
    return <Suspense fallback={<LoadingPortal />}><MonitorPortal user={user} onLogout={handleLogout}/></Suspense>;
  }
  if (currentPath.startsWith('/chairperson') || user?.roleCode === 'CHAIRPERSON' || user?.portal === 'chairperson') {
    return <Suspense fallback={<LoadingPortal />}><ChairpersonPortal user={user} onLogout={handleLogout} /></Suspense>;
  }

  const isSigned = activeCase?.status?.includes('Finalized');

  return (<ErrorBoundary><Suspense fallback={<LoadingPortal />}>
    <div className="app-container">
      <a className="skip-link" href="#main-content">Skip to main content</a>
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
        <main id="main-content" className="main-viewport" tabIndex="-1">

          <>

            {activeView === 'committee' && isCommitteeCase ? (
              <div className="wizard-card" role="status">
                <h2>Committee arbitration</h2>
                <p>
                  The legacy committee review screen has been disabled because it displayed
                  synthetic sample determinations. Committee cases must be reviewed in the
                  Chairperson Portal using the persisted adjudication record.
                </p>
              </div>
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
    </Suspense></ErrorBoundary>
  );
}
