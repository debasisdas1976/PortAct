import { configureStore } from '@reduxjs/toolkit';
import authReducer from './slices/authSlice';
import portfolioReducer from './slices/portfolioSlice';
import assetsReducer from './slices/assetsSlice';
import alertsReducer from './slices/alertsSlice';
import priceRefreshReducer from './slices/priceRefreshSlice';

export const store = configureStore({
  reducer: {
    auth: authReducer,
    portfolio: portfolioReducer,
    assets: assetsReducer,
    alerts: alertsReducer,
    priceRefresh: priceRefreshReducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

// Made with Bob
