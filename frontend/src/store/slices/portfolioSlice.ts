import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { dashboardAPI, portfoliosAPI } from '../../services/api';
import { getErrorMessage } from '../../utils/errorUtils';

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
  // Multi-portfolio support
  portfolios: any[];
  selectedPortfolioId: number | null;
  portfoliosLoading: boolean;
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
  // Multi-portfolio support
  portfolios: [],
  selectedPortfolioId: (() => {
    const stored = localStorage.getItem('selectedPortfolioId');
    return stored ? parseInt(stored, 10) : null;
  })(),
  portfoliosLoading: false,
};

export const fetchPortfolios = createAsyncThunk(
  'portfolio/fetchPortfolios',
  async (_, { rejectWithValue }) => {
    try {
      const response = await portfoliosAPI.getAll();
      return response;
    } catch (error: any) {
      return rejectWithValue(getErrorMessage(error, 'Failed to load portfolios.'));
    }
  }
);

export const fetchPortfolioOverview = createAsyncThunk(
  'portfolio/fetchOverview',
  async (portfolioId: number | null | undefined, { rejectWithValue }) => {
    try {
      const response = await dashboardAPI.getOverview(portfolioId);
      return response;
    } catch (error: any) {
      return rejectWithValue(getErrorMessage(error, 'Failed to load portfolio data.'));
    }
  }
);

export const fetchAssetAllocation = createAsyncThunk(
  'portfolio/fetchAllocation',
  async (portfolioId: number | null | undefined, { rejectWithValue }) => {
    try {
      const response = await dashboardAPI.getAssetAllocation(portfolioId);
      return response;
    } catch (error: any) {
      return rejectWithValue(getErrorMessage(error, 'Failed to load allocation data.'));
    }
  }
);

export const fetchPortfolioSummary = createAsyncThunk(
  'portfolio/fetchSummary',
  async (portfolioId: number | null | undefined, { rejectWithValue }) => {
    try {
      const response = await dashboardAPI.getOverview(portfolioId);
      return response;
    } catch (error: any) {
      return rejectWithValue(getErrorMessage(error, 'Failed to load summary.'));
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
      return rejectWithValue(getErrorMessage(error, 'Failed to load history.'));
    }
  }
);

export const fetchPortfolioPerformance = createAsyncThunk(
  'portfolio/fetchPerformance',
  async ({ days = 30, portfolioId }: { days?: number; portfolioId?: number | null }, { rejectWithValue }) => {
    try {
      const response = await dashboardAPI.getPortfolioPerformance(days, portfolioId);
      return response;
    } catch (error: any) {
      return rejectWithValue(getErrorMessage(error, 'Failed to load performance data.'));
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
      return rejectWithValue(getErrorMessage(error, 'Failed to load asset performance.'));
    }
  }
);

export const fetchAssetsList = createAsyncThunk(
  'portfolio/fetchAssetsList',
  async (portfolioId: number | null | undefined, { rejectWithValue }) => {
    try {
      const response = await dashboardAPI.getAssetsList(portfolioId);
      return response.assets || [];
    } catch (error: any) {
      return rejectWithValue(getErrorMessage(error, 'Failed to load assets list.'));
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
    setSelectedPortfolioId: (state, action: PayloadAction<number | null>) => {
      state.selectedPortfolioId = action.payload;
      if (action.payload === null) {
        localStorage.removeItem('selectedPortfolioId');
      } else {
        localStorage.setItem('selectedPortfolioId', String(action.payload));
      }
    },
  },
  extraReducers: (builder) => {
    builder
      // Portfolios list
      .addCase(fetchPortfolios.pending, (state) => {
        state.portfoliosLoading = true;
      })
      .addCase(fetchPortfolios.fulfilled, (state, action) => {
        state.portfoliosLoading = false;
        state.portfolios = action.payload;
      })
      .addCase(fetchPortfolios.rejected, (state) => {
        state.portfoliosLoading = false;
      })
      // Overview
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

export const { clearError, setSelectedPortfolioId } = portfolioSlice.actions;
export default portfolioSlice.reducer;

// Made with Bob
