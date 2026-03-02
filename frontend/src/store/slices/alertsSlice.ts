import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { alertsAPI } from '../../services/api';
import api from '../../services/api';
import { getErrorMessage } from '../../utils/errorUtils';
import type { RootState } from '..';

interface AlertsState {
  alerts: any[];
  unreadCount: number;
  loading: boolean;
  error: string | null;
  activeSessionId: string | null;
  activeProvider: { provider: string; model: string } | null;
  lastProgress: any | null;   // latest NewsProgress from polling
  polling: boolean;            // true while background poll is active
}

const initialState: AlertsState = {
  alerts: [],
  unreadCount: 0,
  loading: false,
  error: null,
  activeSessionId: null,
  activeProvider: null,
  lastProgress: null,
  polling: false,
};

// Keep a module-level timer ID so we can clear it on cancel/completion
let pollTimer: ReturnType<typeof setInterval> | null = null;

export const fetchAlerts = createAsyncThunk(
  'alerts/fetchAll',
  async (_, { rejectWithValue }) => {
    try {
      const response = await alertsAPI.getAll();
      return response;
    } catch (error: any) {
      return rejectWithValue(getErrorMessage(error, 'Failed to load alerts.'));
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
      return rejectWithValue(getErrorMessage(error, 'Failed to delete alert.'));
    }
  }
);

/**
 * Start background polling for a news-fetch session.
 * Runs independently of component lifecycle — polls every 2s until
 * the session completes, fails, or is cancelled.
 */
export const startSessionPolling = createAsyncThunk(
  'alerts/startSessionPolling',
  async (_, { dispatch, getState }) => {
    // Stop any existing poll first
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }

    const poll = async () => {
      const state = (getState as () => RootState)();
      const sessionId = state.alerts.activeSessionId;
      if (!sessionId) {
        if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
        return;
      }

      try {
        const response = await api.get(`/alerts/progress/${sessionId}`);
        dispatch(alertsSlice.actions._setProgress(response.data));

        const status = response.data.status;
        if (status === 'completed' || status === 'failed' || status === 'cancelled') {
          if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
          dispatch(alertsSlice.actions._setPolling(false));
          dispatch(clearActiveSession());
          dispatch(fetchAlerts());
        }
      } catch {
        // Non-fatal — next tick will retry
      }
    };

    // Run once immediately, then every 2s
    dispatch(alertsSlice.actions._setPolling(true));
    await poll();
    pollTimer = setInterval(poll, 2000);
  }
);

/** Stop background polling (e.g. after user cancels). */
export const stopSessionPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
};

const alertsSlice = createSlice({
  name: 'alerts',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    setActiveSession: (state, action) => {
      state.activeSessionId = action.payload.sessionId;
      state.activeProvider = action.payload.provider || null;
      state.lastProgress = null;
    },
    clearActiveSession: (state) => {
      state.activeSessionId = null;
      state.activeProvider = null;
    },
    // Internal actions used by the polling thunk
    _setProgress: (state, action) => {
      state.lastProgress = action.payload;
    },
    _setPolling: (state, action) => {
      state.polling = action.payload;
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
      .addCase(deleteAlert.pending, (state) => {
        state.error = null;
      })
      .addCase(deleteAlert.fulfilled, (state, action) => {
        state.alerts = state.alerts.filter((alert: any) => alert.id !== action.payload);
        state.unreadCount = state.alerts.filter((a: any) => !a.is_read).length;
      })
      .addCase(deleteAlert.rejected, (state, action) => {
        state.error = action.payload as string;
      });
  },
});

export const { clearError, setActiveSession, clearActiveSession } = alertsSlice.actions;
export default alertsSlice.reducer;
