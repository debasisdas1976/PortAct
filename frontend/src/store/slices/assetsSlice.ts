import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { assetsAPI } from '../../services/api';
import { getErrorMessage } from '../../utils/errorUtils';

interface AssetsState {
  assets: any[];
  loading: boolean;
  error: string | null;
}

const initialState: AssetsState = {
  assets: [],
  loading: false,
  error: null,
};

export const fetchAssets = createAsyncThunk(
  'assets/fetchAll',
  async (portfolioId: number | null | undefined, { rejectWithValue }) => {
    try {
      const params: any = {};
      if (portfolioId) params.portfolio_id = portfolioId;
      const response = await assetsAPI.getAll(params);
      return response;
    } catch (error: any) {
      return rejectWithValue(getErrorMessage(error, 'Failed to load assets.'));
    }
  }
);

const assetsSlice = createSlice({
  name: 'assets',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchAssets.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchAssets.fulfilled, (state, action) => {
        state.loading = false;
        state.assets = action.payload;
      })
      .addCase(fetchAssets.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      });
  },
});

export const { clearError } = assetsSlice.actions;
export default assetsSlice.reducer;

// Made with Bob
