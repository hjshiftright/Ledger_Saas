# Onboarding V2 UI Redesign - Implementation Guide

**Created:** March 20, 2026  
**Status:** Design Complete, Ready for Implementation  
**Estimated Effort:** 3-4 weeks (1 frontend dev + 1 backend dev)

---

## 📋 Overview

This redesign transforms the onboarding flow from a traditional account-centric approach to a **profile-first, goal-oriented** experience that:
1. Understands WHO the user is (profile, location, life stage)
2. Connects their current reality to future aspirations (goals)
3. Maps their current financial position (assets & liabilities)

---

## 🎯 Key Changes from V1

| Aspect | V1 (Old) | V2 (New) |
|--------|----------|----------|
| **Starting Point** | Chart of Accounts | User Profile & Context |
| **Profile Types** | Generic personas | Specific: Salaried, Business Owner, Investor |
| **Location** | Optional | **Required** (drives expense context) |
| **Goals** | Step 5 (late) | **Step 2** (early) - Creates motivation |
| **Assets** | Detailed upfront | Focused on net worth, optional details |
| **Screens** | 5-6 screens | **3 screens** (streamlined) |
| **Time** | 20-30 minutes | **10-15 minutes** (50% faster) |

---

## 📂 Documentation Created

### 1. **UX Specification** - [/docs/ux/onboarding-v2-profile-goals.md](e:\NonProjCode\ledger-3.0\docs\ux\onboarding-v2-profile-goals.md)

**Contents:**
- Complete screen-by-screen UX design
- Profile types: Salaried Employee, Business Owner, Early Investor
- 6 canned financial goals with calculations
- Asset & liability categorization
- Net worth calculation & review screen
- Mobile responsiveness guidelines
- Success metrics

**Key Sections:**
- Screen 1: Profile & Context (name, age, profile type, city, family)
- Screen 2: Financial Goals (retirement, education, marriage, holidays, home, car)
- Screen 3: Assets & Liabilities (banks, investments, loans, cards)
- Screen 4: Review & Dashboard Preview
- Backend API requirements

---

### 2. **Frontend Component** - [/frontend/src/OnboardingV2.jsx](e:\NonProjCode\ledger-3.0\frontend\src\OnboardingV2.jsx)

**Tech Stack:**
- React + Hooks
- Tailwind CSS for styling
- Framer Motion for animations
- Lucide React for icons

**Structure:**
- Main component: `OnboardingV2`
- Sub-components:
  - `Screen1ProfileContext` - Profile & location capture
  - `Screen2Goals` - Goal selection with calculations
  - `Screen3Finances` - Assets & liabilities entry
  - (Screen 4 review not yet implemented)

**Features:**
- Multi-step progress indicator
- Profile type cards (3 types)
- City dropdown with top Indian cities
- Goal cards with auto-calculations
- Net worth calculation
- Form validation

**Status:** ⚠️ **Incomplete** - Screen 3 & 4 need full implementation

---

### 3. **Backend API Specification** - [/docs/api/onboarding-v2-api-spec.md](e:\NonProjCode\ledger-3.0\docs\api\onboarding-v2-api-spec.md)

**API Endpoints:**
1. `POST /api/v1/onboarding/profile` - Create/update profile
2. `GET /api/v1/onboarding/profile` - Get current profile
3. `POST /api/v1/onboarding/goals` - Save financial goals
4. `GET /api/v1/onboarding/goals` - Get saved goals
5. `POST /api/v1/onboarding/assets` - Save assets
6. `POST /api/v1/onboarding/liabilities` - Save liabilities
7. `GET /api/v1/onboarding/net-worth` - Calculate net worth
8. `POST /api/v1/onboarding/complete` - Complete onboarding
9. `GET /api/v1/onboarding/resume` - Resume incomplete onboarding
10. `GET /api/v1/onboarding/cities` - Get city data

**Data Models:**
- `OnboardingProfile` - User profile with demographics
- `FinancialGoal` - Goal definitions with calculations
- `Asset` - Asset tracking
- `Liability` - Debt/liability tracking

**Calculation Algorithms:**
- Retirement corpus (25x rule + inflation)
- Education fund (with education inflation)
- Home down payment (with property appreciation)
- EMI calculations

**Status:** ⚠️ **Not Implemented** - Backend APIs don't exist yet

---

## 🏗️ Implementation Roadmap

### Phase 1: Frontend (Week 1-2)

**Tasks:**

1. **Complete Screen 3 - Finances** (3-4 days)
   - [ ] Bank account entry form
   - [ ] Investment entry sections (EPF, PPF, MF, Stocks, FD, Gold)
   - [ ] Real estate entry
   - [ ] Loan forms (Home, Vehicle, Personal, Education)
   - [ ] Credit card entry
   - [ ] Real-time net worth calculation
   - [ ] Asset/Liability split-screen layout
   - [ ] Form validation

2. **Build Screen 4 - Review** (2-3 days)
   - [ ] Profile summary card
   - [ ] Goals summary with calculations
   - [ ] Net worth display with breakdown
   - [ ] Asset allocation pie chart
   - [ ] "What happens next" section
   - [ ] Launch dashboard button

3. **Polish & Mobile** (2-3 days)
   - [ ] Mobile responsive layouts
   - [ ] Loading states
   - [ ] Error handling UI
   - [ ] Animations & transitions
   - [ ] Form auto-save (local storage)
   - [ ] Resume onboarding from any step

4. **Integration** (1-2 days)
   - [ ] Connect to backend APIs (once ready)
   - [ ] API error handling
   - [ ] Success/failure states
   - [ ] Navigation to dashboard

**Assigned To:** Frontend Developer  
**Dependencies:** None (can use mock data initially)

---

### Phase 2: Backend (Week 2-3)

**Tasks:**

1. **Database Models** (2-3 days)
   - [ ] Create `onboarding_profiles` table
   - [ ] Create `financial_goals` table
   - [ ] Create `user_assets` table
   - [ ] Create `user_liabilities` table
   - [ ] Add indexes and relationships
   - [ ] Write migration scripts

2. **API Implementation** (4-5 days)
   - [ ] Profile endpoints (POST, GET)
   - [ ] Goals endpoints (POST, GET)
   - [ ] Assets endpoints (POST, GET)
   - [ ] Liabilities endpoints (POST, GET)
   - [ ] Net worth calculation endpoint
   - [ ] Complete onboarding endpoint
   - [ ] Resume onboarding endpoint
   - [ ] City data endpoint

3. **Business Logic** (3-4 days)
   - [ ] Retirement corpus calculator
   - [ ] Education fund calculator
   - [ ] Home purchase calculator
   - [ ] EMI calculator
   - [ ] Net worth aggregator
   - [ ] Asset allocation calculator
   - [ ] Feasibility analyzer
   - [ ] Chart of Accounts generator (based on profile type)

4. **Testing** (2 days)
   - [ ] Unit tests for calculators
   - [ ] API endpoint tests
   - [ ] Integration tests
   - [ ] Test data fixtures

**Assigned To:** Backend Developer  
**Dependencies:** Database access, existing account models

---

### Phase 3: Integration & Testing (Week 4)

**Tasks:**

1. **Frontend-Backend Integration** (2-3 days)
   - [ ] Replace mock data with real API calls
   - [ ] Handle API errors gracefully
   - [ ] Test full flow end-to-end
   - [ ] Fix integration bugs

2. **Data Migration** (1-2 days)
   - [ ] Migrate existing users to new profile structure
   - [ ] Backfill city data if missing
   - [ ] Handle legacy onboarding states

3. **User Testing** (2-3 days)
   - [ ] Internal QA testing
   - [ ] Beta testing with 5-10 users
   - [ ] Collect feedback
   - [ ] Fix critical bugs

4. **Launch Preparation** (1 day)
   - [ ] Performance testing
   - [ ] Security review
   - [ ] Monitoring setup
   - [ ] Documentation for support team

**Assigned To:** Full team  
**Dependencies:** Phases 1 & 2 complete

---

## 🧪 Testing Checklist

### Functional Testing

- [ ] User can complete all 3 screens without errors
- [ ] Profile type selection applies correct defaults
- [ ] City selection adjusts cost-of-living index
- [ ] Goal calculations are mathematically correct
- [ ] Net worth calculation is accurate
- [ ] Assets sum correctly
- [ ] Liabilities sum correctly
- [ ] Form validation catches invalid inputs
- [ ] User can go back and edit previous screens
- [ ] Data persists across page refreshes
- [ ] Onboarding can be resumed later

### Edge Cases

- [ ] User skips optional fields
- [ ] User skips all goals
- [ ] User has negative net worth
- [ ] User has zero assets
- [ ] User has zero liabilities
- [ ] Very high/low income ranges
- [ ] Multiple children (1-5)
- [ ] User changes profile type mid-flow
- [ ] Invalid date of birth
- [ ] City not in list (uses "Other")

### Performance

- [ ] All calculations complete < 100ms
- [ ] Page loads < 2 seconds
- [ ] Smooth animations (60 FPS)
- [ ] Mobile responsive (tested on 3 devices)

### Security

- [ ] All inputs sanitized
- [ ] API calls authenticated
- [ ] Sensitive data encrypted
- [ ] No personal data in logs

---

## 📊 Success Metrics

### Primary Metrics

1. **Completion Rate**
   - **Target:** >75% complete all 3 screens
   - **Measurement:** Track users who reach "Launch Dashboard"
   - **Baseline:** V1 was ~55%

2. **Time to Complete**
   - **Target:** 10-15 minutes median
   - **Measurement:** Server-side timestamps
   - **Baseline:** V1 was 20-25 minutes

3. **Goal Selection Rate**
   - **Target:** >60% select at least 2 goals
   - **Measurement:** Goals saved per user
   - **Hypothesis:** Early goal setting increases engagement

### Secondary Metrics

4. **Profile Type Distribution**
   - Track: Salaried vs. Business vs. Investor
   - Expected: 70% Salaried, 20% Business, 10% Investor

5. **City Tier Distribution**
   - Track: Tier 1 vs. Tier 2 vs. Tier 3
   - Expected: 60% Tier 1, 30% Tier 2, 10% Tier 3

6. **Net Worth Distribution**
   - Track: Positive vs. Negative net worth
   - Insight: Affects product positioning

7. **Drop-off Points**
   - Track: Where users abandon
   - Action: Optimize problem screens

---

## 🚀 Deployment Plan

### Stage 1: Development (Week 1-3)
- Develop on `dev` branch
- Test on local/staging environment
- Internal team testing

### Stage 2: Beta (Week 4)
- Deploy to beta environment
- Invite 10-20 beta users
- Collect detailed feedback
- Monitor for errors

### Stage 3: Gradual Rollout (Week 5)
- 10% of new users → V2
- 90% of new users → V1
- Monitor metrics for 2-3 days
- If success metrics met, increase to 50%
- If issues detected, rollback to V1

### Stage 4: Full Launch (Week 6)
- 100% of new users → V2
- Keep V1 as fallback
- Monitor for 1 week
- After stability, deprecate V1

### Rollback Criteria
- Completion rate drops below 65%
- Critical bugs affecting >5% users
- Page load time >5 seconds
- Negative user feedback >50%

---

## 🔗 Related Work Streams

### Frontend Stream (Stream 6):
- Primary owner of implementation
- Needs: React dev with Tailwind CSS experience
- Time: 2 weeks

### Backend Stream (Stream 5):
- Implements APIs and business logic
- Needs: Python dev with FastAPI experience
- Time: 2 weeks

### Database Stream (Stream 3):
- Creates models and migrations
- Needs: Database design expertise
- Time: 3-4 days

### Testing Stream (Stream 7):
- Writes comprehensive test suite
- Can work in parallel with dev
- Time: 1 week

---

## 💡 Future Enhancements (Post-Launch)

### V2.1 Features:
1. **AI-Assisted Profile**
   - Chat interface: "Tell me about yourself" → Auto-fill form
   - Voice input option

2. **Bank Auto-Connect**
   - Account Aggregator integration
   - Auto-fetch balances
   - Reduce manual entry

3. **Social Benchmarking**
   - "Users like you in Bangalore saved ₹45k/month on average"
   - Goal recommendations based on similar users

4. **Goal Templates**
   - Pre-built goal packages: "Young Professional Pack", "Family Starter Pack"
   - One-click goal selection

5. **Visual Progress**
   - Progress bars for each goal
   - Gamification: Unlock badges for completing onboarding

---

## 📝 Open Questions

1. **Q: Should we block users who skip goals?**
   - A: No, allow skip. Goals can be added later from dashboard.

2. **Q: How granular should asset entry be?**
   - A: Two modes: Quick (total value) & Detailed (individual items). Default to Quick.

3. **Q: What if user has >10 banks?**
   - A: Allow unlimited, but suggest consolidation after 5.

4. **Q: Should we ask for exact account numbers?**
   - A: Optional. Mask if provided (show last 4 digits only).

5. **Q: How do we handle joint accounts?**
   - A: V2.1 feature. For now, ask to enter full balance.

---

## 🎓 Knowledge Transfer

### For Frontend Team:
- Read: [/docs/ux/onboarding-v2-profile-goals.md](e:\NonProjCode\ledger-3.0\docs\ux\onboarding-v2-profile-goals.md)
- Review: [/frontend/src/OnboardingV2.jsx](e:\NonProjCode\ledger-3.0\frontend\src\OnboardingV2.jsx)
- Understand: Profile types, goal calculations, net worth logic

### For Backend Team:
- Read: [/docs/api/onboarding-v2-api-spec.md](e:\NonProjCode\ledger-3.0\docs\api\onboarding-v2-api-spec.md)
- Study: Calculation algorithms (retirement, education, home)
- Reference: Existing account models in `/backend/src/accounts/`

### For Product Team:
- Monitor: Completion rates, time-to-complete, goal selection
- Collect: User feedback via in-app survey after onboarding
- Analyze: Drop-off points, most popular goals, net worth distribution

---

## ✅ Pre-Launch Checklist

### Development:
- [ ] All 3 screens fully functional
- [ ] All 10 API endpoints implemented
- [ ] Calculation algorithms tested
- [ ] Frontend-backend integration complete

### Testing:
- [ ] Unit tests: >80% coverage
- [ ] Integration tests passing
- [ ] Manual QA: All screens tested
- [ ] Mobile responsive: iOS + Android

### Documentation:
- [ ] API docs published
- [ ] Frontend component docs updated
- [ ] Database schema documented
- [ ] Support team trained

### Infrastructure:
- [ ] Monitoring dashboards set up
- [ ] Error tracking configured (Sentry)
- [ ] Analytics events configured (Mixpanel)
- [ ] Rollback plan documented

### Legal/Compliance:
- [ ] Data privacy review
- [ ] Financial disclaimer added
- [ ] Terms of service updated

---

## 🤝 Collaboration

This is a **cross-functional** project requiring:

| Role | Responsibility | Time Commitment |
|------|----------------|-----------------|
| Frontend Dev | Build UI components | Full-time (2 weeks) |
| Backend Dev | Build APIs + calculations | Full-time (2 weeks) |
| Product Manager | Define priorities, track metrics | Part-time (5 hrs/week) |
| Designer | UI polish, illustrations | Part-time (3 hrs/week) |
| QA Engineer | Testing & bug reporting | Part-time (10 hrs/week) |

**Communication:**
- Daily standups (async in [PROGRESS.md](e:\NonProjCode\ledger-3.0\PROGRESS.md))
- Blockers escalated within 4 hours
- Weekly demo every Friday

---

## 📞 Questions?

Contact the project lead or post in #onboarding-v2 channel.

**Let's build an amazing first experience for our users!** 🚀
