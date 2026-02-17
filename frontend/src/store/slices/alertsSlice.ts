import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { alertsAPI } from '../../services/api';

interface AlertsState {
  alerts: any[];
  unreadCount: number;
  loading: boolean;
  error: string | null;
}

const initialState: AlertsState = {
  alerts: [],
  unreadCount: 0,
  loading: false,
  error: null,
};

export const fetchAlerts = createAsyncThunk(
  'alerts/fetchAll',
  async (_, { rejectWithValue }) => {
    try {
      const response = await alertsAPI.getAll();
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to fetch alerts');
    }
  }
);

export const deleteAlert = createAsyncThunk(
  'alerts/delete',
  async (alertId: number, { rejectWithValue }) => {
    try {
      await alertsAPI.dismiss(alertId);
      return alertId;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to delete alert');
    }
  }
);

const alertsSlice = createSlice({
  name: 'alerts',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchAlerts.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchAlerts.fulfilled, (state, action) => {
        state.loading = false;
        state.alerts = action.payload;
        state.unreadCount = action.payload.filter((a: any) => !a.is_read).length;
      })
      .addCase(fetchAlerts.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      })
      .addCase(deleteAlert.fulfilled, (state, action) => {
        state.alerts = state.alerts.filter((alert: any) => alert.id !== action.payload);
        state.unreadCount = state.alerts.filter((a: any) => !a.is_read).length;
      });
  },
});

export const { clearError } = alertsSlice.actions;
export default alertsSlice.reducer;

// Made with Bob
