import React, { useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { Box } from '@mui/material';
import { AppDispatch, RootState } from './store';
import { getCurrentUser } from './store/slices/authSlice';

// Layout
import Layout from './components/Layout';

// Components
import SessionTimeout from './components/SessionTimeout';

// Pages
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import Assets from './pages/Assets';
import Statements from './pages/Statements';
import Alerts from './pages/Alerts';
import BankAccounts from './pages/BankAccounts';
import DematAccounts from './pages/DematAccounts';
import CryptoAccounts from './pages/CryptoAccounts';
import Expenses from './pages/Expenses';
import ExpenseDashboard from './pages/ExpenseDashboard';
import Categories from './pages/Categories';
import PPF from './pages/PPF';
import PF from './pages/PF';
import MutualFundHoldings from './pages/MutualFundHoldings';

// Protected Route Component
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated } = useSelector((state: RootState) => state.auth);
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  
  return <>{children}</>;
};

function App() {
  const dispatch = useDispatch<AppDispatch>();
  const { isAuthenticated } = useSelector((state: RootState) => state.auth);

  useEffect(() => {
    if (isAuthenticated) {
      dispatch(getCurrentUser());
    }
  }, [dispatch, isAuthenticated]);

  // Monitor authentication state and redirect to login if session expires
  useEffect(() => {
    // Check if we have a token in localStorage
    const token = localStorage.getItem('token');
    
    // If Redux says we're authenticated but no token exists, force logout
    if (isAuthenticated && !token) {
      console.log('Session expired: Token not found in localStorage');
      window.location.href = '/login?session_expired=true';
    }
  }, [isAuthenticated]);

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      {/* Session Timeout Component */}
      <SessionTimeout />
      
      <Routes>
        {/* Public Routes */}
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        
        {/* Protected Routes */}
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="assets" element={<Assets />} />
          <Route path="mutual-fund-holdings" element={<MutualFundHoldings />} />
          <Route path="statements" element={<Statements />} />
          <Route path="alerts" element={<Alerts />} />
          <Route path="bank-accounts" element={<BankAccounts />} />
          <Route path="demat-accounts" element={<DematAccounts />} />
          <Route path="crypto-accounts" element={<CryptoAccounts />} />
          <Route path="expenses" element={<Expenses />} />
          <Route path="expense-dashboard" element={<ExpenseDashboard />} />
          <Route path="categories" element={<Categories />} />
          <Route path="ppf" element={<PPF />} />
          <Route path="pf" element={<PF />} />
        </Route>
        
        {/* Catch all */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Box>
  );
}

export default App;

// Made with Bob
