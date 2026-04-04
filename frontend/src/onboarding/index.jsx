import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { API } from '../api.js';
import ProfileScreen from './ProfileScreen.jsx';
import Hub from './Hub.jsx';
import { saveJson } from './utils.js';
import { SK, DEFAULT_PROFILE } from './constants.js';

export default function OnboardingV4({ userEmail = '', onLogout, onComplete }) {
  const [sections,      setSections]      = useState({});
  const [profileData,   setProfileData]   = useState(DEFAULT_PROFILE);
  const [bootstrapping, setBootstrapping] = useState(true);

  useEffect(() => {
    API.dashboard.load()
      .then(dbData => {
        if (!dbData) return;
        const hasName   = dbData.name && dbData.name.trim().length > 0 && dbData.name !== 'Rahul';
        const hasAssets = Object.values(dbData.assets  || {}).flat().length > 0;
        const hasGoals  = (dbData.goals || []).length > 0;
        if (hasName || hasAssets || hasGoals) {
          setProfileData(d => ({ ...d, legalName: dbData.name !== 'Rahul' ? dbData.name : d.legalName }));
          setSections({ profiling: !!hasName, mapping: !!hasAssets, goals: !!hasGoals });
        }
      })
      .catch(() => {})
      .finally(() => setBootstrapping(false));
  }, []);

  const handleProfileDone = (data) => {
    setProfileData(data);
    saveJson(SK.profile, data);
    const updated = { ...sections, profiling: true };
    setSections(updated);
    saveJson(SK.sections, updated);
    if (onComplete) onComplete(data);
  };

  if (bootstrapping) {
    return (
      <div className="flex h-screen items-center justify-center bg-[#F7F8F9]">
        <div className="w-8 h-8 rounded-full border-2 border-[#2C4A70] border-t-transparent animate-spin" />
      </div>
    );
  }

  if (!sections.profiling) {
    return (
      <AnimatePresence mode="wait">
        <motion.div key="profile" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0, scale: 0.98 }} transition={{ duration: 0.35 }}>
          <ProfileScreen initial={profileData} onDone={handleProfileDone} />
        </motion.div>
      </AnimatePresence>
    );
  }

  return (
    <AnimatePresence mode="wait">
      <motion.div key="hub" initial={{ opacity: 0, x: 30 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.4 }} className="h-screen">
        <Hub
          sections={sections}
          setSections={setSections}
          profileData={profileData}
          setProfileData={setProfileData}
          userEmail={userEmail}
          onLogout={onLogout}
        />
      </motion.div>
    </AnimatePresence>
  );
}
