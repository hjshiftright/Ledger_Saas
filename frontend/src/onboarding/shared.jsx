import React from 'react';
import { motion } from 'framer-motion';

export const FadeIn = ({ children, className = '', delay = 0 }) => (
  <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45, delay }} className={className}>
    {children}
  </motion.div>
);

export const Btn = ({ onClick, children, disabled, variant = 'primary', className = '' }) => {
  const base = 'rounded-full py-3 px-7 font-semibold transition-all flex items-center justify-center gap-2 outline-none text-base';
  const v = {
    primary:   'bg-[#2C4A70] hover:bg-[#1F344F] text-white shadow-md disabled:opacity-40 disabled:cursor-not-allowed',
    secondary: 'bg-white border-2 border-slate-200 text-slate-700 hover:border-[#2C4A70] hover:text-[#2C4A70]',
    ghost:     'text-slate-500 hover:text-[#2C4A70] hover:bg-indigo-50 px-3',
  };
  return <button onClick={onClick} disabled={disabled} className={`${base} ${v[variant]} ${className}`}>{children}</button>;
};

export const Field = ({ label, value, onChange, placeholder, type = 'text', prefix }) => (
  <div className="flex flex-col gap-1.5">
    {label && <label className="text-xs font-bold text-slate-500 uppercase tracking-widest">{label}</label>}
    <div className="relative">
      {prefix && <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 font-medium text-sm">{prefix}</span>}
      <input type={type} value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
        className={`w-full bg-white border-2 border-slate-200 rounded-xl px-4 py-3 text-slate-800 placeholder-slate-400 text-sm
          focus:outline-none focus:border-[#2C4A70] focus:ring-4 focus:ring-[#2C4A70]/10 transition-all ${prefix ? 'pl-9' : ''}`} />
    </div>
  </div>
);

export const Textarea = ({ value, onChange, placeholder }) => (
  <textarea value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder} rows={3}
    className="w-full bg-white border-2 border-slate-200 rounded-xl p-4 text-sm text-slate-800 placeholder-slate-400
      focus:outline-none focus:border-[#2C4A70] focus:ring-4 focus:ring-[#2C4A70]/10 transition-all resize-none" />
);

export const RadioPill = ({ active, onClick, label, className = '' }) => (
  <button
    onClick={onClick}
    className={`px-4 py-1.5 rounded-full text-xs font-bold transition-colors border-2 ${
      active ? 'border-[#2C4A70] text-[#2C4A70] bg-[#2C4A70]/5' : 'border-slate-200 text-slate-500 hover:border-slate-300'
    } ${className}`}
  >
    {label}
  </button>
);
