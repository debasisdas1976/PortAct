import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { assetsAPI } from '../../services/api';

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
  async (_, { rejectWithValue }) => {
    try {
      const response = await assetsAPI.getAll();
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to fetch assets');
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
