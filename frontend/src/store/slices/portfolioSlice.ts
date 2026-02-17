import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { dashboardAPI } from '../../services/api';

interface PortfolioState {
  overview: any;
  allocation: any;
  summary: any;
  history: any[];
  loading: boolean;
  error: string | null;
}

const initialState: PortfolioState = {
  overview: null,
  allocation: null,
  summary: null,
  history: [],
  loading: false,
  error: null,
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
      });
  },
});

export const { clearError } = portfolioSlice.actions;
export default portfolioSlice.reducer;

// Made with Bob
