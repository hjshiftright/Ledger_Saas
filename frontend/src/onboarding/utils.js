export const loadJson = (key, fb) => {
  try { return JSON.parse(localStorage.getItem(key)) || fb; } catch { return fb; }
};

export const saveJson = (key, val) => localStorage.setItem(key, JSON.stringify(val));

export function num(s) { return parseInt(String(s).replace(/\D/g, '')) || 0; }

export function inr(v) {
  const n = typeof v === 'number' ? v : num(v);
  const abs = Math.abs(n).toLocaleString('en-IN');
  return n < 0 ? `-₹${abs}` : `₹${abs}`;
}
