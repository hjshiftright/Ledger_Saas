import { Shield, Sparkles, Building2, Users, Briefcase, GraduationCap, Plane, Home, TrendingUp, PiggyBank, CreditCard } from 'lucide-react';

export const PERSONAS = [
  { id: 'salaried', label: 'Salaried professional', icon: Briefcase, color: 'bg-blue-100 text-blue-700' },
  { id: 'business', label: 'Business owner', icon: Building2, color: 'bg-indigo-100 text-indigo-700' },
  { id: 'homemaker', label: 'Homemaker', icon: Home, color: 'bg-rose-100 text-rose-700' },
  { id: 'investor', label: 'Investor', icon: TrendingUp, color: 'bg-emerald-100 text-emerald-700' },
  { id: 'other', label: 'Student or other', icon: Sparkles, color: 'bg-amber-100 text-amber-700' }
];

export const HOUSEHOLD_TYPES = [
  { id: 'single', label: 'Single' },
  { id: 'couple', label: 'Couple' },
  { id: 'family', label: 'Family' },
  { id: 'other', label: 'Other' }
];

export const GOAL_TEMPLATES = [
  { id: 'emergency', label: 'Emergency fund', desc: 'Build a safety net for unexpected events.', icon: Shield, color: 'bg-red-100 text-red-600' },
  { id: 'home', label: 'Buy a home', desc: 'Save for a down payment or plan a purchase.', icon: Home, color: 'bg-blue-100 text-blue-600' },
  { id: 'education', label: "Children's education", desc: 'Plan for school or college costs.', icon: GraduationCap, color: 'bg-purple-100 text-purple-600', condition: (d) => parseInt(d.dependents) > 0 },
  { id: 'retire', label: 'Retire by a certain age', desc: 'Know your freedom number.', icon: TrendingUp, color: 'bg-emerald-100 text-emerald-600' },
  { id: 'debt', label: 'Pay off debt', desc: 'Clear your loans strategically.', icon: CreditCard, color: 'bg-rose-100 text-rose-600' },
  { id: 'purchase', label: 'Major purchase', desc: 'Car, vacation, renovation, or something else.', icon: Plane, color: 'bg-sky-100 text-sky-600' },
  { id: 'custom', label: 'Custom goal', desc: 'Something specific to you.', icon: Sparkles, color: 'bg-amber-100 text-amber-600' }
];

export const ASSET_CATS = [
  { id: 'banks', label: 'Bank accounts & cash', sub: 'Savings, salary, current, FDs, cash at home' },
  { id: 'investments', label: 'Investments', sub: 'Mutual funds, stocks, bonds, EPF-PPF, NPS' },
  { id: 'property', label: 'Property', sub: 'House, land, commercial space' },
  { id: 'vehicles', label: 'Vehicles', sub: 'Car, two-wheeler, other' },
  { id: 'gold', label: 'Gold & jewellery', sub: 'Coins, digital gold, ornaments' },
  { id: 'other', label: 'Other valuables', sub: 'Art, collectibles, business inventory, receivables' },
];

export const LIABILITY_CATS = [
  { id: 'homeLoan', label: 'Home loan' },
  { id: 'vehicleLoan', label: 'Vehicle loan' },
  { id: 'personalLoan', label: 'Personal loan' },
  { id: 'creditCards', label: 'Credit cards' },
  { id: 'educationLoan', label: 'Education loan' },
  { id: 'businessLoan', label: 'Business loan' },
  { id: 'informalLoans', label: 'Informal loans', sub: '(from family, friends)' },
  { id: 'otherLoan', label: 'Other dues' },
];

export const DEFAULT_EXPENSE_CATS = ['Housing', 'Daily living', 'Transport', 'Children', 'Health', 'Lifestyle', 'Debt payments', 'Savings & investments', 'Other'];
