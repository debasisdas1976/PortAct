import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import api from '../../services/api';
import type { RootState } from '..';

interface PriceRefreshState {
  activeSessionId: string | null;
  lastProgress: any | null;
  polling: boolean;
}

const initialState: PriceRefreshState = {
  activeSessionId: null,
  lastProgress: null,
  polling: false,
};

// Module-level timer so polling survives component unmount
let pollTimer: ReturnType<typeof setInterval> | null = null;

/**
 * Start background polling for a price-refresh session.
 * Runs independently of component lifecycle — polls every 2s until
 * the session completes or fails.
 */
export const startPriceRefreshPolling = createAsyncThunk(
  'priceRefresh/startPolling',
  async (_, { dispatch, getState }) => {
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }

    const poll = async () => {
      const state = (getState as () => RootState)();
      const sessionId = state.priceRefresh.activeSessionId;
      if (!sessionId) {
        if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
        return;
      }

      try {
        const response = await api.get(`/assets/price-refresh-progress/${sessionId}`);
        dispatch(priceRefreshSlice.actions._setProgress(response.data));

        const status = response.data.status;
        if (status === 'completed' || status === 'failed') {
          if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
          dispatch(priceRefreshSlice.actions._setPolling(false));
        }
      } catch {
        // Non-fatal — next tick will retry
      }
    };

    dispatch(priceRefreshSlice.actions._setPolling(true));
    await poll();
    pollTimer = setInterval(poll, 2000);
  }
);

/** Stop background polling. */
export const stopPriceRefreshPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
};

/**
 * Check for an active session on page load (resume after navigation).
 * Calls GET /assets/price-refresh-active and, if a running session exists,
 * stores it and starts polling.
 */
export const checkActivePriceRefresh = createAsyncThunk(
  'priceRefresh/checkActive',
  async (_, { dispatch }) => {
    try {
      const response = await api.get('/assets/price-refresh-active');
      if (response.data && response.data.session_id) {
        dispatch(priceRefreshSlice.actions.setActiveSession(response.data.session_id));
        dispatch(priceRefreshSlice.actions._setProgress(response.data));
        dispatch(startPriceRefreshPolling());
      }
    } catch {
      // No active session or error — ignore
    }
  }
);

const priceRefreshSlice = createSlice({
  name: 'priceRefresh',
  initialState,
  reducers: {
    setActiveSession: (state, action) => {
      state.activeSessionId = action.payload;
      state.lastProgress = null;
    },
    clearActiveSession: (state) => {
      state.activeSessionId = null;
      state.lastProgress = null;
      state.polling = false;
    },
    _setProgress: (state, action) => {
      state.lastProgress = action.payload;
    },
    _setPolling: (state, action) => {
      state.polling = action.payload;
    },
  },
});

export const { setActiveSession, clearActiveSession } = priceRefreshSlice.actions;
export default priceRefreshSlice.reducer;
