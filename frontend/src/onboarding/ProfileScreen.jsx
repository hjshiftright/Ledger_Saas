import React, { useState, useRef } from 'react';
import { ChevronRight, User, ArrowRight } from 'lucide-react';
import { ProtonInline } from '../ProtonAssistant.jsx';
import { FadeIn, RadioPill } from './shared.jsx';
import { PERSPECTIVES } from './constants.js';

export default function ProfileScreen({ initial, onDone }) {
  const [data, setData] = useState({
    legalName:       initial?.legalName       || '',
    age:             initial?.age             || '',
    gender:          initial?.gender          || '',
    perspective:     initial?.perspective     || '',
    maritalStatus:   initial?.maritalStatus   || '',
    kids:            initial?.kids            || '',
    otherDependants: initial?.otherDependants || '',
    timeAvailable:   initial?.timeAvailable   || 'standard',
  });

  const set = (k, v) => setData(d => ({ ...d, [k]: v }));
  const canSubmit = data.legalName && data.perspective;

  const protonRef = useRef(null);
  const handleProtonSend = async () => "Got it! I've securely noted your profile.";

  return (
    <div className="flex flex-col h-screen bg-[#F7F8F9]">
      {/* Top bar */}
      <div className="bg-white border-b border-slate-200 px-8 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <span className="text-base italic font-serif font-bold text-[#2C4A70]">The Private Ledger</span>
          <ChevronRight size={14} className="text-slate-300" />
          <span className="text-sm font-semibold text-slate-600">Profile Configuration</span>
        </div>
        <div className="w-8 h-8 rounded-full bg-[#2C4A70] flex items-center justify-center">
          <User size={14} className="text-white" />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-8 py-6 w-full max-w-[1400px] mx-auto">
        <FadeIn>
          <div className="mb-4">
            <h1 className="text-3xl font-serif font-black text-[#2C4A70] leading-tight mb-1">
              Hey {data.legalName ? <span className="font-bold">{data.legalName}</span> : ''} ! I'm your Ledger Advisor.
            </h1>
            <p className="text-slate-500 text-[14px]">Let's quickly verify your basic profile details for tax considerations.</p>
          </div>

          <div className="flex gap-6 items-start">
            {/* LEFT column */}
            <div className="w-[60%] flex flex-col gap-4 shrink-0">
              <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
                <div className="flex flex-wrap gap-x-6 gap-y-3">
                  <div>
                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">Preferred Name</p>
                    <input type="text" value={data.legalName} onChange={e => set('legalName', e.target.value)} placeholder="e.g. prana"
                      className="w-48 border-2 border-slate-100 rounded-lg px-3 py-1.5 text-slate-800 focus:border-[#2C4A70] focus:ring-2 focus:ring-[#2C4A70]/10 outline-none transition-colors text-sm font-medium" />
                  </div>
                  <div>
                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">Age</p>
                    <input type="number" value={data.age} onChange={e => set('age', e.target.value)} placeholder="30"
                      className="w-20 border-2 border-slate-100 rounded-lg px-3 py-1.5 text-slate-800 text-center focus:border-[#2C4A70] focus:ring-2 focus:ring-[#2C4A70]/10 outline-none transition-colors text-sm font-medium" />
                  </div>
                  <div>
                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">Gender</p>
                    <div className="flex gap-1.5">
                      {['Male', 'Female', 'Other'].map(g => (
                        <RadioPill key={g} active={data.gender === g} onClick={() => set('gender', g)} label={g} />
                      ))}
                    </div>
                  </div>
                </div>

                <hr className="my-4 border-slate-100" />

                <div className="flex flex-wrap gap-x-6 gap-y-3">
                  <div>
                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">Marital Status</p>
                    <div className="flex gap-1.5">
                      {['Single', 'Married', 'Other'].map(s => (
                        <RadioPill key={s} active={data.maritalStatus === s} onClick={() => set('maritalStatus', s)} label={s} />
                      ))}
                    </div>
                  </div>
                  <div>
                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">Kids</p>
                    <div className="flex gap-1.5">
                      {['0', '1', '2', '3+'].map(k => (
                        <RadioPill key={k} active={data.kids === k} onClick={() => set('kids', k)} label={k} className="w-10 px-0 flex justify-center" />
                      ))}
                    </div>
                  </div>
                  <div>
                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">Dependants</p>
                    <div className="flex gap-1.5">
                      {['0', '1', '2', '3+'].map(k => (
                        <RadioPill key={k} active={data.otherDependants === k} onClick={() => set('otherDependants', k)} label={k} className="w-10 px-0 flex justify-center" />
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
                <div className="flex items-end justify-between mb-3">
                  <h3 className="text-[14px] font-bold text-slate-800">Which of these best describes your current situation?</h3>
                  <p className="text-[10px] text-slate-400">Helps customize accounts & budgets.</p>
                </div>
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-2.5">
                  {PERSPECTIVES.map(({ id, title, desc }) => {
                    const active = data.perspective === id;
                    return (
                      <button key={id} onClick={() => set('perspective', id)}
                        className={`text-left p-3 rounded-lg border-2 transition-all
                          ${active ? 'border-[#2C4A70] shadow-sm bg-[#2C4A70]/5 ring-1 ring-[#2C4A70]' : 'border-slate-100 hover:border-slate-200'}`}>
                        <h3 className={`font-bold text-[13px] mb-0.5 ${active ? 'text-[#2C4A70]' : 'text-slate-800'}`}>{title}</h3>
                        <p className="text-[10px] text-slate-500 leading-snug">{desc}</p>
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
                <p className="text-[11px] font-semibold text-slate-500 mb-2.5">How much time do you have to set things up today?</p>
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { id: 'basics',   title: 'Just the basics', desc: 'Setup: ~2 mins' },
                    { id: 'standard', title: 'Standard setup',  desc: 'Setup: ~5 mins' },
                    { id: 'deep',     title: 'Deep dive',       desc: 'Setup: 10+ mins' },
                  ].map(({ id, title, desc }) => {
                    const active = data.timeAvailable === id;
                    return (
                      <button key={id} onClick={() => set('timeAvailable', id)}
                        className={`text-left p-3 rounded-lg border-2 transition-all
                          ${active ? 'border-[#2C4A70] bg-[#F7F8F9]' : 'border-slate-100 hover:border-slate-200'}`}>
                        <h3 className={`font-bold text-[13px] ${active ? 'text-[#2C4A70]' : 'text-slate-800'}`}>{title}</h3>
                        <p className="text-[10px] text-slate-500 mt-0.5">{desc}</p>
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* RIGHT column */}
            <div className="flex-1 sticky top-0 h-[520px] border border-slate-200 rounded-xl overflow-hidden shadow-sm bg-white">
              <ProtonInline
                ref={protonRef}
                initialMessage="I'm Proton! I help you fill out details using plain English. E.g. 'I'm a 30yo software engineer with a car loan'."
                onSend={handleProtonSend}
              />
            </div>
          </div>
        </FadeIn>
      </div>

      <div className="bg-white border-t border-slate-200 px-8 py-4 flex items-center justify-end shrink-0">
        <button onClick={() => onDone(data)} disabled={!canSubmit}
          className="bg-[#2C4A70] hover:bg-[#1F344F] text-white font-bold py-3 px-8 rounded-full shadow-md flex items-center gap-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed">
          Next: Set Up Accounts <ArrowRight size={16} strokeWidth={2.5} />
        </button>
      </div>
    </div>
  );
}
