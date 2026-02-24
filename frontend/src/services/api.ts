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

// Response interceptor to handle errors
api.interceptors.response.use(
  (response) => {
    // Update last activity on successful response
    localStorage.setItem('lastApiActivity', Date.now().toString());
    return response;
  },
  (error) => {
    if (error.response?.status === 401) {
      // Clear auth data from localStorage
      localStorage.removeItem('token');
      localStorage.removeItem('lastApiActivity');

      // Only redirect to login if not already on login or register page
      const currentPath = window.location.pathname;
      if (currentPath !== '/login' && currentPath !== '/register') {
        // Redirect with session expired message
        // The App component will detect the missing token and update Redux state
        window.location.href = '/login?session_expired=true';
      }
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
};

// System API (version check)
export const systemAPI = {
  checkUpdate: async () => {
    const response = await api.get('/system/check-update');
    return response.data;
  },
};

export default api;

// Made with Bob
