import axios from 'axios';
export { getErrorMessage } from '../utils/errorUtils';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token and track activity
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    // Store last activity timestamp for session tracking
    // This helps the SessionTimeout component know when the last API call was made
    localStorage.setItem('lastApiActivity', Date.now().toString());
    
    return config;
  },
  (error) => Promise.reject(error)
);

// --- Silent token refresh logic ---
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (error: any) => void;
}> = [];

const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (token) {
      prom.resolve(token);
    } else {
      prom.reject(error);
    }
  });
  failedQueue = [];
};

const forceLogout = () => {
  localStorage.removeItem('token');
  localStorage.removeItem('refreshToken');
  localStorage.removeItem('lastApiActivity');
  const currentPath = window.location.pathname;
  if (currentPath !== '/login' && currentPath !== '/register') {
    window.location.href = '/login?session_expired=true';
  }
};

// Response interceptor to handle errors
api.interceptors.response.use(
  (response) => {
    // Update last activity on successful response
    localStorage.setItem('lastApiActivity', Date.now().toString());
    return response;
  },
  async (error) => {
    const originalRequest = error.config;

    // Only attempt refresh on 401, and not for auth endpoints themselves
    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !originalRequest.url?.includes('/auth/')
    ) {
      const refreshToken = localStorage.getItem('refreshToken');

      if (!refreshToken) {
        forceLogout();
        return Promise.reject(error);
      }

      if (isRefreshing) {
        // Another refresh is in progress — queue this request
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return api(originalRequest);
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const response = await axios.post(
          `${API_URL}/auth/refresh`,
          null,
          { params: { refresh_token: refreshToken } }
        );

        const { access_token, refresh_token: newRefreshToken } = response.data;
        localStorage.setItem('token', access_token);
        localStorage.setItem('refreshToken', newRefreshToken);

        // Retry queued requests with the new token
        processQueue(null, access_token);

        // Retry the original request
        originalRequest.headers.Authorization = `Bearer ${access_token}`;
        return api(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        forceLogout();
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    if (error.response?.status === 401) {
      // 401 on an auth endpoint (e.g., bad credentials) — don't try to refresh
      forceLogout();
    }

    // Normalize detail: if it's an array (validation errors), join into a readable string
    if (error.response?.data?.detail && Array.isArray(error.response.data.detail)) {
      error.response.data.detail = error.response.data.detail
        .map((d: any) => {
          if (d.loc && d.msg) {
            const fields = d.loc.filter((l: string) => l !== 'body' && l !== 'query' && l !== 'path');
            const fieldName = fields.length > 0 ? fields.join(' > ').replace(/_/g, ' ') : 'input';
            return `${fieldName}: ${d.msg}`;
          }
          return d.msg || String(d);
        })
        .join('. ');
    }

    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  login: async (credentials: { username: string; password: string }) => {
    const formData = new FormData();
    formData.append('username', credentials.username);
    formData.append('password', credentials.password);
    const response = await api.post('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    return response.data;
  },
  
  register: async (userData: { email: string; username: string; full_name: string; password: string }) => {
    const response = await api.post('/auth/register', userData);
    return response.data;
  },
  
  getCurrentUser: async () => {
    const response = await api.get('/users/me');
    return response.data;
  },

  forgotPassword: async (email: string) => {
    const response = await api.post('/auth/forgot-password', { email });
    return response.data as {
      message: string;
      reset_token: string;
      expires_in_minutes: number;
    };
  },

  resetPassword: async (token: string, newPassword: string) => {
    const response = await api.post('/auth/reset-password', {
      token,
      new_password: newPassword,
    });
    return response.data as { message: string };
  },

  updateProfile: async (data: Record<string, any>) => {
    const response = await api.put('/users/me', data);
    return response.data;
  },

  updatePreferences: async (prefs: Record<string, any>) => {
    const response = await api.patch('/users/me/preferences', prefs);
    return response.data;
  },
};

// Portfolios API
export const portfoliosAPI = {
  getAll: async () => {
    const response = await api.get('/portfolios/');
    return response.data;
  },

  getById: async (id: number) => {
    const response = await api.get(`/portfolios/${id}`);
    return response.data;
  },

  create: async (data: { name: string; description?: string }) => {
    const response = await api.post('/portfolios/', data);
    return response.data;
  },

  update: async (id: number, data: { name?: string; description?: string; is_active?: boolean }) => {
    const response = await api.put(`/portfolios/${id}`, data);
    return response.data;
  },

  delete: async (id: number) => {
    await api.delete(`/portfolios/${id}`);
  },
};

// Dashboard API
export const dashboardAPI = {
  getOverview: async (portfolioId?: number | null) => {
    const params: any = {};
    if (portfolioId) params.portfolio_id = portfolioId;
    const response = await api.get('/dashboard/overview', { params });
    return response.data;
  },

  getAssetAllocation: async (portfolioId?: number | null) => {
    const params: any = {};
    if (portfolioId) params.portfolio_id = portfolioId;
    const response = await api.get('/dashboard/asset-allocation', { params });
    return response.data;
  },

  getPortfolioPerformance: async (days: number = 30, portfolioId?: number | null) => {
    const params: any = { days };
    if (portfolioId) params.portfolio_id = portfolioId;
    const response = await api.get('/dashboard/portfolio-performance', { params });
    return response.data;
  },

  getAssetPerformance: async (assetId: number, days: number = 30) => {
    const response = await api.get(`/dashboard/asset-performance/${assetId}`, {
      params: { days }
    });
    return response.data;
  },

  getAssetsList: async (portfolioId?: number | null) => {
    const params: any = {};
    if (portfolioId) params.portfolio_id = portfolioId;
    const response = await api.get('/dashboard/assets-list', { params });
    return response.data;
  },

  getAssetTypeXirr: async (assetType: string, portfolioId?: number | null) => {
    const params: any = { asset_type: assetType };
    if (portfolioId) params.portfolio_id = portfolioId;
    const response = await api.get('/dashboard/asset-type-xirr', { params });
    return response.data;
  },

  takeSnapshot: async () => {
    const response = await api.post('/dashboard/take-snapshot');
    return response.data;
  },
};

// Assets API
export const assetsAPI = {
  getAll: async (params?: any) => {
    const response = await api.get('/assets/', { params });
    return response.data;
  },

  getById: async (id: number) => {
    const response = await api.get(`/assets/${id}`);
    return response.data;
  },

  create: async (data: any) => {
    const response = await api.post('/assets/', data);
    return response.data;
  },

  update: async (id: number, data: any) => {
    const response = await api.put(`/assets/${id}`, data);
    return response.data;
  },

  delete: async (id: number) => {
    await api.delete(`/assets/${id}`);
  },

  getSummary: async () => {
    const response = await api.get('/assets/summary');
    return response.data;
  },
};

// Transactions API
export const transactionsAPI = {
  getAll: async (params?: any) => {
    const response = await api.get('/transactions', { params });
    return response.data;
  },
  
  create: async (data: any) => {
    const response = await api.post('/transactions', data);
    return response.data;
  },

  update: async (id: number, data: any) => {
    const response = await api.put(`/transactions/${id}`, data);
    return response.data;
  },

  delete: async (id: number) => {
    await api.delete(`/transactions/${id}`);
  },
};

// SIP Creator API
export const sipCreatorAPI = {
  preview: async (data: any) => {
    const response = await api.post('/sip-creator/preview', data);
    return response.data;
  },
  create: async (data: any) => {
    const response = await api.post('/sip-creator/create', data);
    return response.data;
  },
};

// Alerts API
export const alertsAPI = {
  getAll: async (params?: any) => {
    const response = await api.get('/alerts', { params });
    return response.data;
  },
  
  markAsRead: async (id: number) => {
    const response = await api.patch(`/alerts/${id}`, { is_read: true });
    return response.data;
  },
  
  dismiss: async (id: number) => {
    const response = await api.patch(`/alerts/${id}`, { is_dismissed: true });
    return response.data;
  },
};

// Statements API
export const statementsAPI = {
  getAll: async () => {
    const response = await api.get('/statements');
    return response.data;
  },
  
  upload: async (file: File, statementType: string, institutionName?: string) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('statement_type', statementType);
    if (institutionName) {
      formData.append('institution_name', institutionName);
    }
    
    const response = await api.post('/statements/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },
  
  delete: async (id: number) => {
    await api.delete(`/statements/${id}`);
  },

  getPortfolioAccounts: async (portfolioId?: number | null) => {
    const params: Record<string, any> = {};
    if (portfolioId) params.portfolio_id = portfolioId;
    const response = await api.get('/statements/accounts', { params });
    return response.data;
  },

  getUnmatchedMFs: async (statementId: number) => {
    const response = await api.get(`/statements/${statementId}/unmatched-mfs`);
    return response.data;
  },

  resolveMFs: async (statementId: number, resolutions: Array<{
    asset_id: number;
    selected_isin: string;
    selected_scheme_name: string;
  }>) => {
    const response = await api.post(`/statements/${statementId}/resolve-mfs`, {
      resolutions,
    });
    return response.data;
  },
};

// Crypto Exchanges API
export const cryptoExchangesAPI = {
  getAll: async (params?: { is_active?: boolean; exchange_type?: string }) => {
    const response = await api.get('/crypto-exchanges/', { params });
    return response.data;
  },

  getById: async (id: number) => {
    const response = await api.get(`/crypto-exchanges/${id}`);
    return response.data;
  },

  create: async (data: { name?: string; display_label: string; exchange_type?: string; website?: string | null; sort_order?: number }) => {
    const response = await api.post('/crypto-exchanges/', data);
    return response.data;
  },

  update: async (id: number, data: Record<string, any>) => {
    const response = await api.put(`/crypto-exchanges/${id}`, data);
    return response.data;
  },

  delete: async (id: number) => {
    await api.delete(`/crypto-exchanges/${id}`);
  },
};

// Banks API
export const banksAPI = {
  getAll: async (params?: { is_active?: boolean; bank_type?: string }) => {
    const response = await api.get('/banks/', { params });
    return response.data;
  },

  getById: async (id: number) => {
    const response = await api.get(`/banks/${id}`);
    return response.data;
  },

  create: async (data: { name?: string; display_label: string; bank_type?: string; website?: string | null; sort_order?: number }) => {
    const response = await api.post('/banks/', data);
    return response.data;
  },

  update: async (id: number, data: Record<string, any>) => {
    const response = await api.put(`/banks/${id}`, data);
    return response.data;
  },

  delete: async (id: number) => {
    await api.delete(`/banks/${id}`);
  },
};

// Brokers API
export const brokersAPI = {
  getAll: async (params?: { is_active?: boolean; broker_type?: string }) => {
    const response = await api.get('/brokers/', { params });
    return response.data;
  },

  getById: async (id: number) => {
    const response = await api.get(`/brokers/${id}`);
    return response.data;
  },

  create: async (data: { name?: string; display_label: string; broker_type?: string; supported_markets?: string; website?: string | null; sort_order?: number }) => {
    const response = await api.post('/brokers/', data);
    return response.data;
  },

  update: async (id: number, data: Record<string, any>) => {
    const response = await api.put(`/brokers/${id}`, data);
    return response.data;
  },

  delete: async (id: number) => {
    await api.delete(`/brokers/${id}`);
  },
};

// Asset Categories API
export const assetCategoriesAPI = {
  getAll: async (params?: { is_active?: boolean }) => {
    const response = await api.get('/asset-categories/', { params });
    return response.data;
  },

  update: async (id: number, data: Record<string, any>) => {
    const response = await api.put(`/asset-categories/${id}`, data);
    return response.data;
  },
};

// Asset Types API
export const assetTypesAPI = {
  getAll: async (params?: { is_active?: boolean; category?: string }) => {
    const response = await api.get('/asset-types/', { params });
    return response.data;
  },

  update: async (id: number, data: Record<string, any>) => {
    const response = await api.put(`/asset-types/${id}`, data);
    return response.data;
  },

  getCategories: async () => {
    const response = await api.get('/asset-types/categories');
    return response.data;
  },
};

// Institutions API (NPS fund managers, insurance providers, NPS CRAs, etc.)
export const institutionsAPI = {
  getAll: async (params?: { is_active?: boolean; category?: string }) => {
    const response = await api.get('/institutions/', { params });
    return response.data;
  },

  create: async (data: { name?: string; display_label: string; category: string; website?: string | null; sort_order?: number }) => {
    const response = await api.post('/institutions/', data);
    return response.data;
  },

  update: async (id: number, data: Record<string, any>) => {
    const response = await api.put(`/institutions/${id}`, data);
    return response.data;
  },

  delete: async (id: number) => {
    await api.delete(`/institutions/${id}`);
  },
};

// Application Settings API
export const settingsAPI = {
  getAll: async () => {
    const response = await api.get('/settings/');
    return response.data;
  },

  bulkUpdate: async (settings: { key: string; value: string }[]) => {
    const response = await api.put('/settings/', { settings });
    return response.data;
  },

  reset: async () => {
    const response = await api.post('/settings/reset');
    return response.data;
  },

  getAutomations: async () => {
    const response = await api.get('/settings/automations');
    return response.data;
  },

  getAiModels: async (refresh = false) => {
    const response = await api.get('/settings/ai-models', { params: refresh ? { refresh: true } : {} });
    return response.data;
  },

  getApiKeysStatus: async (): Promise<Record<string, boolean>> => {
    const response = await api.get('/settings/api-keys-status');
    return response.data;
  },

  getSecretValue: async (key: string): Promise<string> => {
    const response = await api.get(`/settings/secret/${key}`);
    return response.data.value;
  },
};

// System API (version check)
export const systemAPI = {
  checkUpdate: async () => {
    const response = await api.get('/system/check-update');
    return response.data;
  },
};

// Insights API
export const insightsAPI = {
  getCategoryAllocationXirr: async (portfolioId?: number | null) => {
    const params: any = {};
    if (portfolioId) params.portfolio_id = portfolioId;
    const response = await api.get('/insights/category-allocation-xirr', { params });
    return response.data;
  },

  getCategoryPerformanceHistory: async (days: number = 90, portfolioId?: number | null, category?: string | null) => {
    const params: any = { days };
    if (portfolioId) params.portfolio_id = portfolioId;
    if (category) params.category = category;
    const response = await api.get('/insights/category-performance-history', { params });
    return response.data;
  },

  getCategoryXirrTrend: async (days: number = 90, portfolioId?: number | null) => {
    const params: any = { days };
    if (portfolioId) params.portfolio_id = portfolioId;
    const response = await api.get('/insights/category-xirr-trend', { params });
    return response.data;
  },

  getAttributeAllocation: async (portfolioId?: number | null) => {
    const params: any = {};
    if (portfolioId) params.portfolio_id = portfolioId;
    const response = await api.get('/insights/attribute-allocation', { params });
    return response.data;
  },

  getMaturityTimeline: async (portfolioId?: number | null) => {
    const params: any = {};
    if (portfolioId) params.portfolio_id = portfolioId;
    const response = await api.get('/insights/maturity-timeline', { params });
    return response.data;
  },
};

// Asset Attributes API
export const assetAttributesAPI = {
  getAll: async (isActive?: boolean) => {
    const params: any = {};
    if (isActive !== undefined) params.is_active = isActive;
    const response = await api.get('/asset-attributes/', { params });
    return response.data;
  },

  getById: async (id: number) => {
    const response = await api.get(`/asset-attributes/${id}`);
    return response.data;
  },

  create: async (data: {
    display_label: string;
    name?: string;
    description?: string;
    icon?: string;
    sort_order?: number;
    values?: Array<{ label: string; color?: string; sort_order?: number }>;
  }) => {
    const response = await api.post('/asset-attributes/', data);
    return response.data;
  },

  update: async (id: number, data: Record<string, any>) => {
    const response = await api.put(`/asset-attributes/${id}`, data);
    return response.data;
  },

  delete: async (id: number) => {
    await api.delete(`/asset-attributes/${id}`);
  },

  addValue: async (attributeId: number, data: { label: string; color?: string; sort_order?: number }) => {
    const response = await api.post(`/asset-attributes/${attributeId}/values`, data);
    return response.data;
  },

  updateValue: async (attributeId: number, valueId: number, data: Record<string, any>) => {
    const response = await api.put(`/asset-attributes/${attributeId}/values/${valueId}`, data);
    return response.data;
  },

  deleteValue: async (attributeId: number, valueId: number) => {
    await api.delete(`/asset-attributes/${attributeId}/values/${valueId}`);
  },

  getAssignments: async (assetId: number) => {
    const response = await api.get(`/asset-attributes/assignments/${assetId}`);
    return response.data;
  },

  getBulkAssignments: async (assetIds: number[]) => {
    const response = await api.get('/asset-attributes/assignments/bulk/by-ids', {
      params: { asset_ids: assetIds.join(',') },
    });
    return response.data;
  },

  setAssignments: async (assetId: number, assignments: Array<{ attribute_id: number; attribute_value_id: number }>) => {
    const response = await api.put(`/asset-attributes/assignments/${assetId}`, { assignments });
    return response.data;
  },

  removeAssignment: async (assetId: number, attributeId: number) => {
    await api.delete(`/asset-attributes/assignments/${assetId}/${attributeId}`);
  },

  setBulkAssignments: async (assetIds: number[], assignments: Array<{ attribute_id: number; attribute_value_id: number }>) => {
    const response = await api.put('/asset-attributes/assignments/bulk', { asset_ids: assetIds, assignments });
    return response.data;
  },
};

// Liquidity Insight API
export const liquidityAPI = {
  getData: async () => {
    const response = await api.get('/liquidity');
    return response.data;
  },

  refresh: async () => {
    const response = await api.post('/liquidity/refresh');
    return response.data;
  },
};

// MF Systematic Plans API (SIP/STP/SWP Setup)
export const mfPlansAPI = {
  getAll: async (planType?: string) => {
    const params: any = {};
    if (planType) params.plan_type = planType;
    const response = await api.get('/mf-plans', { params });
    return response.data;
  },

  create: async (data: any) => {
    const response = await api.post('/mf-plans', data);
    return response.data;
  },

  update: async (id: number, data: any) => {
    const response = await api.put(`/mf-plans/${id}`, data);
    return response.data;
  },

  delete: async (id: number) => {
    await api.delete(`/mf-plans/${id}`);
  },

  toggle: async (id: number) => {
    const response = await api.patch(`/mf-plans/${id}/toggle`);
    return response.data;
  },
};

export default api;

// Made with Bob
