import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { dashboardAPI } from '../../services/api';

interface PortfolioState {
  overview: any;
  allocation: any;
  summary: any;
  history: any[];
  performanceData: any;
  assetPerformanceData: any;
  assetsList: any[];
  loading: boolean;
  error: string | null;
  performanceLoading: boolean;
  performanceError: string | null;
}

const initialState: PortfolioState = {
  overview: null,
  allocation: null,
  summary: null,
  history: [],
  performanceData: null,
  assetPerformanceData: null,
  assetsList: [],
  loading: false,
  error: null,
  performanceLoading: false,
  performanceError: null,
};

export const fetchPortfolioOverview = createAsyncThunk(
  'portfolio/fetchOverview',
  async (_, { rejectWithValue }) => {
    try {
      const response = await dashboardAPI.getOverview();
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to fetch portfolio');
    }
  }
);

export const fetchAssetAllocation = createAsyncThunk(
  'portfolio/fetchAllocation',
  async (_, { rejectWithValue }) => {
    try {
      const response = await dashboardAPI.getAssetAllocation();
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to fetch allocation');
    }
  }
);

export const fetchPortfolioSummary = createAsyncThunk(
  'portfolio/fetchSummary',
  async (_, { rejectWithValue }) => {
    try {
      const response = await dashboardAPI.getOverview();
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to fetch summary');
    }
  }
);

export const fetchPortfolioHistory = createAsyncThunk(
  'portfolio/fetchHistory',
  async (_, { rejectWithValue }) => {
    try {
      const response = await dashboardAPI.getOverview();
      return response.history || [];
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to fetch history');
    }
  }
);

export const fetchPortfolioPerformance = createAsyncThunk(
  'portfolio/fetchPerformance',
  async (days: number = 30, { rejectWithValue }) => {
    try {
      const response = await dashboardAPI.getPortfolioPerformance(days);
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to fetch performance data');
    }
  }
);

export const fetchAssetPerformance = createAsyncThunk(
  'portfolio/fetchAssetPerformance',
  async ({ assetId, days = 30 }: { assetId: number; days?: number }, { rejectWithValue }) => {
    try {
      const response = await dashboardAPI.getAssetPerformance(assetId, days);
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to fetch asset performance');
    }
  }
);

export const fetchAssetsList = createAsyncThunk(
  'portfolio/fetchAssetsList',
  async (_, { rejectWithValue }) => {
    try {
      const response = await dashboardAPI.getAssetsList();
      return response.assets || [];
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to fetch assets list');
    }
  }
);

const portfolioSlice = createSlice({
  name: 'portfolio',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchPortfolioOverview.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchPortfolioOverview.fulfilled, (state, action) => {
        state.loading = false;
        state.overview = action.payload;
      })
      .addCase(fetchPortfolioOverview.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      })
      .addCase(fetchAssetAllocation.fulfilled, (state, action) => {
        state.allocation = action.payload;
      })
      .addCase(fetchPortfolioSummary.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchPortfolioSummary.fulfilled, (state, action) => {
        state.loading = false;
        state.summary = action.payload;
      })
      .addCase(fetchPortfolioSummary.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      })
      .addCase(fetchPortfolioHistory.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchPortfolioHistory.fulfilled, (state, action) => {
        state.loading = false;
        state.history = action.payload;
      })
      .addCase(fetchPortfolioHistory.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      })
      .addCase(fetchPortfolioPerformance.pending, (state) => {
        state.performanceLoading = true;
        state.performanceError = null;
      })
      .addCase(fetchPortfolioPerformance.fulfilled, (state, action) => {
        state.performanceLoading = false;
        state.performanceData = action.payload;
      })
      .addCase(fetchPortfolioPerformance.rejected, (state, action) => {
        state.performanceLoading = false;
        state.performanceError = action.payload as string;
      })
      .addCase(fetchAssetPerformance.pending, (state) => {
        state.performanceLoading = true;
        state.performanceError = null;
      })
      .addCase(fetchAssetPerformance.fulfilled, (state, action) => {
        state.performanceLoading = false;
        state.assetPerformanceData = action.payload;
      })
      .addCase(fetchAssetPerformance.rejected, (state, action) => {
        state.performanceLoading = false;
        state.performanceError = action.payload as string;
      })
      .addCase(fetchAssetsList.fulfilled, (state, action) => {
        state.assetsList = action.payload;
      })
      .addCase(fetchAssetsList.rejected, (state, action) => {
        state.error = action.payload as string;
      });
  },
});

export const { clearError } = portfolioSlice.actions;
export default portfolioSlice.reducer;

// Made with Bob
