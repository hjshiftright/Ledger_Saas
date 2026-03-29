import React, { useState } from 'react';
import { WelcomeScreen, TriageScreen } from './GlobalEntry';
import { BP1Screen, BP2Screen, BP3Screen } from './BasicProfiling';
import { FMHubScreen, FMNLScreen, FMGalleryScreen, FMChecklistScreen } from './FinancialMapping';
import { GS1Screen, GSWizardScreen, GSSummaryScreen } from './GoalSetting';
import { CFHubScreen, CFQ1Screen, CFQ2Screen, CFQ3Screen } from './CashFlow';
import { BGHubScreen, BGMasterScreen } from './Budgeting';
import { SEHubScreen, SEMasterScreen } from './SplitExpenses';

export default function OnboardingController({ onComplete, onAuthenticated, userEmail }) {
  const [stage, setStage] = useState('welcome');
  const [data, setData] = useState({
    name: '', country: 'India', currency: 'INR',
    persona: null, timeAvailable: null,
    householdType: null, dependents: '', partnerName: '',
    numberFormat: 'lakhs', financialYearStart: 'April', previousTool: '',
    assets: [], liabilities: [], goals: [],
    cashflow: null, budget: null, splitInfo: null,
    email: userEmail
  });
  
  // Temporary state for the specific module flow
  const [tempState, setTempState] = useState({});

  const updateData = (updates) => setData(prev => ({ ...prev, ...updates }));

  const resolveCashFlowDetailed = () => {
    // According to blueprint, detailed is a 5+ minute flow. For the sake of this reference implementation, we redirect to quick. 
    // In a full production build, this would map to cf-d1 -> d2 -> d3 -> d4.
    setStage('cf-q1');
  };

  const handleFinalComplete = () => {
    const payload = {
      user_profile: {
        name: data.name, country: data.country, currency: data.currency,
        persona: data.persona, household_type: data.householdType,
        dependents: data.dependents, number_format: data.numberFormat,
        financial_year_start: data.financialYearStart
      },
      net_worth: { assets: data.assets, liabilities: data.liabilities, total_assets: data.assets.reduce((sum, a) => sum + Number(a.value), 0), total_liabilities: data.liabilities.reduce((sum, l) => sum + Number(l.value), 0) },
      goals: data.goals, cashflow: data.cashflow, budget: data.budget, split_expenses: data.splitInfo, onboadingV4: true
    };
    onComplete(payload);
  };

  const renderCurrentStage = () => {
    switch (stage) {
      // Global Entry
      case 'welcome': return <WelcomeScreen onNext={() => setStage('triage')} />;
      case 'triage': return <TriageScreen data={data} updateData={updateData} onNext={() => setStage('bp-1')} />;
      
      // Basic Profiling
      case 'bp-1': return <BP1Screen data={data} updateData={updateData} onNext={() => setStage('bp-2')} onAuthenticated={onAuthenticated} />;
      case 'bp-2': return <BP2Screen data={data} updateData={updateData} onNext={() => {
        if(data.timeAvailable === 'browsing') handleFinalComplete(); // fast track to dashboard
        else setStage('bp-3');
      }} />;
      case 'bp-3': return <BP3Screen data={data} updateData={updateData} onNext={() => setStage('fm-hub')} />;

      // Financial Mapping
      case 'fm-hub': return <FMHubScreen onModeSelect={(mode) => mode === 'skip' ? setStage('gs-1') : (mode === 'nl' ? setStage('fm-nl') : setStage('fm-gallery'))} />;
      case 'fm-nl': return <FMNLScreen data={data} updateData={updateData} onNext={() => setStage('gs-1')} onSkip={() => setStage('gs-1')} />;
      case 'fm-gallery': return <FMGalleryScreen data={data} onNext={(cats) => { setTempState({ selectedCats: cats }); setStage('fm-checklist'); }} onSwitchToNL={() => setStage('fm-nl')} />;
      case 'fm-checklist': return <FMChecklistScreen data={data} updateData={updateData} selectedCats={tempState.selectedCats} onComplete={() => setStage('gs-1')} />;

      // Goal Setting
      case 'gs-1': return <GS1Screen data={data} updateData={updateData} onNext={() => setStage('gs-wizard')} onSkip={() => handleFinalComplete()} />;
      case 'gs-wizard': return <GSWizardScreen data={data} updateData={updateData} onComplete={() => setStage('gs-summary')} />;
      case 'gs-summary': return <GSSummaryScreen data={data} onNext={() => setStage('cf-hub')} />;

      // Cash Flow Discovery
      case 'cf-hub': return <CFHubScreen onQuick={() => setStage('cf-q1')} onDetailed={resolveCashFlowDetailed} onSkip={() => handleFinalComplete()} />;
      case 'cf-q1': return <CFQ1Screen data={data} onNext={(incomeNodes) => { setTempState({ ...tempState, incomeNodes }); setStage('cf-q2'); }} />;
      case 'cf-q2': return <CFQ2Screen data={data} onNext={(expensesObj) => { setTempState({ ...tempState, expensesObj }); setStage('cf-q3'); }} />;
      case 'cf-q3': return <CFQ3Screen data={data} updateData={updateData} incomeNodes={tempState.incomeNodes} expensesObj={tempState.expensesObj} onComplete={() => setStage('bg-hub')} />;

      // Budgeting
      case 'bg-hub': return <BGHubScreen onAuto={() => setStage('bg-master')} onScratch={() => setStage('bg-master')} data={data} />;
      case 'bg-master': return <BGMasterScreen data={data} updateData={updateData} onComplete={() => {
        if(data.householdType === 'couple' || data.householdType === 'family') setStage('se-hub');
        else handleFinalComplete();
      }} />;

      // Split Expenses
      case 'se-hub': return <SEHubScreen onSetup={() => setStage('se-master')} onSkip={() => handleFinalComplete()} />;
      case 'se-master': return <SEMasterScreen data={data} updateData={updateData} onComplete={() => handleFinalComplete()} />;

      default: return null;
    }
  };

  return (
    <div className="fixed inset-0 bg-slate-100 z-50 overflow-hidden flex flex-col font-sans">
       <header className="h-16 flex items-center px-6 lg:px-10 justify-between shrink-0 top-0 w-full z-10 sticky bg-slate-100 border-b border-transparent shadow-sm">
         <div className="flex items-center gap-2">
            <span className="text-xl font-black text-indigo-700 tracking-tight">Ledger</span>
         </div>
         {stage !== 'welcome' && (
           <button onClick={handleFinalComplete} className="text-sm font-semibold text-slate-500 hover:text-indigo-600 transition-colors bg-white px-4 py-2 rounded-xl shadow-sm border border-slate-200">
             Skip to Dashboard
           </button>
         )}
       </header>

       <main className="flex-1 overflow-y-auto w-full max-w-[1200px] mx-auto px-4 md:px-0">
          <div className="h-full flex items-center justify-center min-h-[500px] sm:min-h-0">
             {renderCurrentStage()}
          </div>
       </main>
    </div>
  )
}
