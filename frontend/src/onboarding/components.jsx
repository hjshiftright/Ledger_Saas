import React from 'react';
import { motion } from 'framer-motion';

export const FadeIn = ({ children, delay = 0, className = '' }) => (
  <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay }} className={className}>
    {children}
  </motion.div>
);

export const Button = ({ children, onClick, variant = 'primary', className = '', ...props }) => {
  const baseStyle = "w-full py-3.5 px-6 rounded-xl font-bold transition-all duration-200 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed";
  const variants = {
    primary: "bg-indigo-600 text-white hover:bg-indigo-700 shadow-md shadow-indigo-600/20 hover:shadow-lg hover:shadow-indigo-600/30",
    secondary: "bg-white text-slate-700 border border-slate-200 hover:bg-slate-50 hover:border-slate-300",
    tertiary: "text-indigo-600 hover:bg-indigo-50 font-semibold"
  };
  return (
    <button onClick={onClick} className={`${baseStyle} ${variants[variant]} ${className}`} {...props}>
      {children}
    </button>
  );
};

export const Input = ({ label, value, onChange, placeholder, prefix, info, type = "text", required, step, min, max }) => (
  <div className="space-y-1.5 w-full">
    {label && <label className="block text-sm font-semibold text-slate-700">{label}</label>}
    <div className="relative">
      {prefix && <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 font-medium">{prefix}</span>}
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        required={required}
        step={step}
        min={min}
        max={max}
        className={`w-full bg-white border border-slate-200 rounded-xl px-4 py-3 text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all ${prefix ? 'pl-8' : ''}`}
      />
    </div>
    {info && <p className="text-xs text-slate-500">{info}</p>}
  </div>
);
