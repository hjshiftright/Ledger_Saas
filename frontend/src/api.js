const BASE = "http://127.0.0.1:8000/api/v1";
const ONBOARDING_BASE = `${BASE}/onboarding`;

class ApiError extends Error {
  constructor(status, statusText, body) {
    super(`HTTP ${status}: ${statusText}`);
    this.status = status;
    this.statusText = statusText;
    this.body = body;
  }
}

export const apiCall = async (endpoint, method = "GET", body = null, params = null) => {
  const options = {
    method,
    headers: { "Content-Type": "application/json" },
  };
  if (body) options.body = JSON.stringify(body);
  
  let url = `${ONBOARDING_BASE}${endpoint}`;
  if (params) {
    const qs = new URLSearchParams(params).toString();
    url += (url.includes('?') ? '&' : '?') + qs;
  }

  const res = await fetch(url, options);
  if (!res.ok) {
    let errorBody = null;
    try { errorBody = await res.json(); } catch (_) {}
    throw new ApiError(res.status, res.statusText, errorBody);
  }
  if (res.status === 204) return null;
  return res.json();
};

// Generic call to the v1 API (non-onboarding)
const v1Call = async (path, method = "GET", body = null, params = null) => {
  const options = { method, headers: { "Content-Type": "application/json" } };
  if (body) options.body = JSON.stringify(body);
  let url = `${BASE}${path}`;
  if (params) {
    const qs = new URLSearchParams(
      Object.fromEntries(Object.entries(params).filter(([, v]) => v != null))
    ).toString();
    if (qs) url += "?" + qs;
  }
  const res = await fetch(url, options);
  if (!res.ok) {
    let errorBody = null;
    try { errorBody = await res.json(); } catch (_) {}
    throw new ApiError(res.status, res.statusText, errorBody);
  }
  if (res.status === 204) return null;
  return res.json();
};

export const API = {
  profile: {
    create: (data) => apiCall("/profile/", "POST", data),
  },
  coa: {
    initialize: () => apiCall("/coa/initialize", "POST"),
  },
  institutions: {
    create: (data) => apiCall("/institutions/", "POST", data),
  },
  accounts: {
    createBank: (data) => apiCall("/accounts/bank", "POST", data),
    createCard: (data) => apiCall("/accounts/credit-card", "POST", data),
    createLoan: (data) => apiCall("/accounts/loan", "POST", data),
    createBrokerage: (data) => apiCall("/accounts/brokerage", "POST", data),
    list: () => v1Call("/accounts"),
    bankable: () => v1Call("/accounts/bankable"),
  },
  openingBalances: {
    submitBulk: (data) => apiCall("/opening-balances/bulk", "POST", { entries: data }),
  },
  netWorth: {
    compute: (date) => apiCall("/networth", "GET", null, { as_of_date: date }), // Correcting to GET as per backend
  },
  dashboard: {
    save: (data) => apiCall("/dashboard/save", "POST", data),
    load: () => apiCall("/dashboard", "GET"),
  },

  // ── Import Pipeline ──────────────────────────────────────────────────────
  pipeline: {
    /**
     * Detect source type + extract metadata without parsing.
     * Call this on file drop before /parse — returns bank identity, IFSC code,
     * account number, statement period, and a list of fields still missing.
     * @param {File} file
     * @param {object} opts - { sourceTypeHint, password }
     * @returns DetectResponse
     */
    detect: async (file, { sourceTypeHint = "", password = "" } = {}) => {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("source_type_hint", sourceTypeHint);
      fd.append("password", password);
      const res = await fetch(`${BASE}/pipeline/detect`, { method: "POST", body: fd });
      if (!res.ok) {
        let errorBody = null;
        try { errorBody = await res.json(); } catch (_) {}
        throw new ApiError(res.status, res.statusText, errorBody);
      }
      return res.json();
    },

    /**
     * Upload + detect + parse a statement file.
     * @param {File} file
     * @param {object} opts - { accountId, sourceTypeHint, password, useLlm }
     * @returns ParseResponse
     */
    parse: async (file, { accountId = "", sourceTypeHint = "", password = "", useLlm = false, providerId = "" } = {}) => {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("account_id", accountId);
      fd.append("source_type_hint", sourceTypeHint);
      fd.append("password", password);
      fd.append("use_llm", useLlm ? "true" : "false");
      fd.append("llm_provider_id", providerId ?? "");
      const res = await fetch(`${BASE}/pipeline/parse`, { method: "POST", body: fd });
      if (!res.ok) {
        let errorBody = null;
        try { errorBody = await res.json(); } catch (_) {}
        throw new ApiError(res.status, res.statusText, errorBody);
      }
      return res.json();
    },

    /** Run full smart pipeline (normalize → dedup → categorize → score → propose). */
    process: (batchId, { useLlm = false, providerId = null, llmForRedOnly = true, bankAccountId = "1102", accountId = "" } = {}) =>
      v1Call(`/pipeline/process/${batchId}`, "POST", {
        use_llm: useLlm,
        provider_id: providerId,
        llm_for_red_band_only: llmForRedOnly,
        bank_account_id: bankAccountId,
        account_id: accountId,
      }),

    sourceTypes: () => v1Call("/pipeline/source-types"),

    /** Fetch paginated raw parsed rows for a batch (for Quick Look preview). */
    rawRows: (batchId) => v1Call(`/pipeline/parse/${batchId}/rows`),
  },

  // ── Proposals / Review ───────────────────────────────────────────────────
  proposals: {
    /** Fetch all proposals for a batch. */
    list: (batchId) => v1Call(`/proposals/${batchId}`),

    /** Mark specific proposals as CONFIRMED (reversible; not yet stored to DB). */
    approve: (batchId, proposalIds) =>
      v1Call(`/proposals/${batchId}/approve`, "POST", { proposal_ids: proposalIds }),

    /** Persist all CONFIRMED proposals to SQLite. */
    commit: (batchId) => v1Call(`/proposals/${batchId}/commit`, "POST"),

    /** Update a single journal line's account assignment (in-memory; takes effect on commit). */
    updateLine: (batchId, proposalId, lineIndex, accountCode, accountName) =>
      v1Call(`/proposals/${batchId}/${proposalId}`, "PATCH", {
        line_index: lineIndex,
        account_code: accountCode,
        account_name: accountName,
      }),
  },

  // ── LLM Providers ───────────────────────────────────────────────────────
  llm: {
    /** List registered LLM providers for the current user. */
    list: () => v1Call("/llm/providers"),

    /** Register a new LLM provider with an API key. */
    register: ({ providerName, apiKey, displayName = "", isDefault = false }) =>
      v1Call("/llm/providers", "POST", {
        provider_name: providerName,
        api_key: apiKey,
        display_name: displayName || providerName,
        is_default: isDefault,
      }),

    /** Remove a registered provider. */
    delete: (providerId) => v1Call(`/llm/providers/${providerId}`, "DELETE"),

    /** Update display name, API key, or models for an existing provider. */
    update: (providerId, { displayName, apiKey, textModel, visionModel, isDefault } = {}) =>
      v1Call(`/llm/providers/${providerId}`, "PATCH", {
        ...(displayName  !== undefined && { display_name:  displayName  }),
        ...(apiKey       !== undefined && { api_key:       apiKey       }),
        ...(textModel    !== undefined && { text_model:    textModel    }),
        ...(visionModel  !== undefined && { vision_model:  visionModel  }),
        ...(isDefault    !== undefined && { is_default:    isDefault    }),
      }),

    /** Test connectivity for a registered provider. */
    test: (providerId) => v1Call(`/llm/providers/${providerId}/test`, "POST"),
  },

  // ── Reports ─────────────────────────────────────────────────────────────
  reports: {
    /** Dashboard KPIs — net worth, period income/expenses, top categories. */
    summary: ({ asOf, fromDate, toDate } = {}) =>
      v1Call("/reports/summary", "GET", null, { as_of: asOf, from_date: fromDate, to_date: toDate }),

    /** Income & Expense statement for a period. */
    incomeExpense: ({ fromDate, toDate } = {}) =>
      v1Call("/reports/income-expense", "GET", null, { from_date: fromDate, to_date: toDate }),

    /** Balance sheet (asset / liability tree) as of a date. */
    balanceSheet: ({ asOf } = {}) =>
      v1Call("/reports/balance-sheet", "GET", null, { as_of: asOf }),

    /** Monthly net worth trend for last N months. */
    netWorthHistory: (months = 12) =>
      v1Call("/reports/net-worth-history", "GET", null, { months }),

    /** Monthly income vs expense bars for last N months. */
    monthlyTrend: (months = 12) =>
      v1Call("/reports/monthly-trend", "GET", null, { months }),

    /** Category-wise expense breakdown with percentages. */
    expenseCategories: ({ fromDate, toDate } = {}) =>
      v1Call("/reports/expense-categories", "GET", null, { from_date: fromDate, to_date: toDate }),

    /** Flat list of leaf accounts for the account-statement selector. */
    accountsList: (accountType) =>
      v1Call("/reports/accounts-list", "GET", null, accountType ? { account_type: accountType } : null),

    /** Per-account transaction ledger with running balance. */
    accountStatement: (accountId, { fromDate, toDate } = {}) =>
      v1Call(`/reports/account-statement/${accountId}`, "GET", null, { from_date: fromDate, to_date: toDate }),

    /** LLM narrative commentary — optional, returns {insight, error}. */
    insights: ({ reportType, data, providerId } = {}) =>
      v1Call("/reports/insights", "POST", { report_type: reportType, data, provider_id: providerId }),

    /** Trial Balance — all accounts with Dr/Cr columns as of a date. */
    trialBalance: ({ asOf } = {}) =>
      v1Call("/reports/trial-balance", "GET", null, { as_of: asOf }),

    /** General Ledger — per-account T-account entries grouped by category. */
    generalLedger: ({ fromDate, toDate, accountType } = {}) =>
      v1Call("/reports/general-ledger", "GET", null, {
        from_date: fromDate, to_date: toDate,
        ...(accountType ? { account_type: accountType } : {}),
      }),

    /** Journal / Day Book — all transactions as double-entry lines, paginated. */
    journal: ({ fromDate, toDate, page = 1, pageSize = 50 } = {}) =>
      v1Call("/reports/journal", "GET", null, {
        from_date: fromDate, to_date: toDate,
        page, page_size: pageSize,
      }),

    /** NAV Dashboard — net worth history, asset distribution, liquidity split. */
    navDashboard: ({ months = 12 } = {}) =>
      v1Call("/reports/dashboard/net-asset-value", "GET", null, { months }),

    /** Cash Flow Dashboard — monthly in/out, savings rate trend, category detail. */
    cashFlowDashboard: ({ months = 12 } = {}) =>
      v1Call("/reports/dashboard/cash-flow", "GET", null, { months }),

    /** Diversification Dashboard — asset class breakdown and concentration warning. */
    diversificationDashboard: () =>
      v1Call("/reports/dashboard/diversification", "GET"),

    /** Spending Analysis Dashboard — category trends and month-on-month delta. */
    spendingDashboard: ({ months = 6 } = {}) =>
      v1Call("/reports/dashboard/spending-analysis", "GET", null, { months }),

    /** Tax Optimization Dashboard — FY section utilization and tax savings potential. */
    taxDashboard: () =>
      v1Call("/reports/dashboard/tax-optimization", "GET"),

    /** Life Insights — survival runway, FIRE clock, wealth velocity, lifestyle creep, lazy money, passive orchard, inflation ghost, debt snowball. */
    lifeInsights: ({ months = 12 } = {}) =>
      v1Call("/reports/dashboard/life-insights", "GET", null, { months }),
  },

  // ── Chat / AI Assistant ──────────────────────────────────────────────────
  chat: {
    /**
     * Send a message to the AI assistant with optional conversation history.
     * @param {string} message  - The user's latest message
     * @param {Array}  history  - [{role, content}, ...] prior turns
     * @param {string} [providerId] - Optional LLM provider id (uses default if omitted)
     */
    send: (message, history = [], providerId = null) =>
      v1Call("/chat", "POST", {
        message,
        history,
        ...(providerId ? { provider_id: providerId } : {}),
      }),
  },

  // ── Auth ────────────────────────────────────────────────────────────────────
  auth: {
    /** Check if any users exist in the database. */
    status: () => v1Call("/auth/status"),

    /** Create a new user account. */
    signup: ({ email, password, llmProviderName = null, llmApiKey = null }) =>
      v1Call("/auth/signup", "POST", {
        email,
        password,
        ...(llmProviderName ? { llm_provider_name: llmProviderName } : {}),
        ...(llmApiKey ? { llm_api_key: llmApiKey } : {}),
      }),

    /** Login with email + password. */
    login: ({ email, password }) =>
      v1Call("/auth/login", "POST", { email, password }),

    /** Reset the database (destructive). */
    resetDb: () =>
      v1Call("/auth/reset-db", "POST", { confirm: true }),
  },
};
