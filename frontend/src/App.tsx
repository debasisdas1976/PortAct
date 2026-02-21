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
import ErrorBoundary from './components/ErrorBoundary';

// Pages
import Login from './pages/Login';
import Register from './pages/Register';
import ForgotPassword from './pages/ForgotPassword';
import ResetPassword from './pages/ResetPassword';
import Dashboard from './pages/Dashboard';
import Assets from './pages/Assets';
import Statements from './pages/Statements';
import AlertsWithProgress from './pages/AlertsWithProgress';
import BankAccounts from './pages/BankAccounts';
import DematAccounts from './pages/DematAccounts';
import CryptoAccounts from './pages/CryptoAccounts';
import CryptoAssets from './pages/CryptoAssets';
import CryptoExchanges from './pages/CryptoExchanges';
import Expenses from './pages/Expenses';
import ExpenseDashboard from './pages/ExpenseDashboard';
import Categories from './pages/Categories';
import PPF from './pages/PPF';
import PF from './pages/PF';
import SSY from './pages/SSY';
import NPS from './pages/NPS';
import MutualFundHoldings from './pages/MutualFundHoldings';
import Gratuity from './pages/Gratuity';
import Insurance from './pages/Insurance';
import Stocks from './pages/Stocks';
import USStocks from './pages/USStocks';
import EquityMF from './pages/EquityMF';
import Savings from './pages/Savings';
import FixedDeposit from './pages/FixedDeposit';
import RecurringDeposit from './pages/RecurringDeposit';
import DebtFunds from './pages/DebtFunds';
import Commodities from './pages/Commodities';
import PortfolioAdmin from './pages/PortfolioAdmin';
import NSC from './pages/NSC';
import KVP from './pages/KVP';
import SCSS from './pages/SCSS';
import MIS from './pages/MIS';
import CorporateBond from './pages/CorporateBond';
import RBIBond from './pages/RBIBond';
import TaxSavingBond from './pages/TaxSavingBond';
import REITs from './pages/REITs';
import InvITs from './pages/InvITs';
import SovereignGoldBond from './pages/SovereignGoldBond';
import RealEstate from './pages/RealEstate';
import BanksMaster from './pages/BanksMaster';
import BrokersMaster from './pages/BrokersMaster';
import Settings from './pages/Settings';
import Help from './pages/Help';

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
window.location.href = '/login?session_expired=true';
    }
  }, [isAuthenticated]);

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      {/* Session Timeout Component */}
      <SessionTimeout />
      
      <Routes>
        {/* Public Routes */}
        <Route path="/login" element={<ErrorBoundary><Login /></ErrorBoundary>} />
        <Route path="/register" element={<ErrorBoundary><Register /></ErrorBoundary>} />
        <Route path="/forgot-password" element={<ErrorBoundary><ForgotPassword /></ErrorBoundary>} />
        <Route path="/reset-password" element={<ErrorBoundary><ResetPassword /></ErrorBoundary>} />
        
        {/* Protected Routes */}
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <ErrorBoundary>
                <Layout />
              </ErrorBoundary>
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="assets" element={<Assets />} />
          <Route path="mutual-fund-holdings" element={<MutualFundHoldings />} />
          <Route path="statements" element={<Statements />} />
          <Route path="alerts" element={<AlertsWithProgress />} />
          <Route path="bank-accounts" element={<BankAccounts />} />
          <Route path="demat-accounts" element={<DematAccounts />} />
          <Route path="crypto-accounts" element={<CryptoAccounts />} />
          <Route path="crypto-assets" element={<CryptoAssets />} />
          <Route path="crypto-exchanges" element={<CryptoExchanges />} />
          <Route path="expenses" element={<Expenses />} />
          <Route path="expense-dashboard" element={<ExpenseDashboard />} />
          <Route path="categories" element={<Categories />} />
          <Route path="ppf" element={<PPF />} />
          <Route path="pf" element={<PF />} />
          <Route path="ssy" element={<SSY />} />
          <Route path="nps" element={<NPS />} />
          <Route path="gratuity" element={<Gratuity />} />
          <Route path="insurance" element={<Insurance />} />
          <Route path="stocks" element={<Stocks />} />
          <Route path="us-stocks" element={<USStocks />} />
          <Route path="equity-mf" element={<EquityMF />} />
          <Route path="savings" element={<Savings />} />
          <Route path="fixed-deposit" element={<FixedDeposit />} />
          <Route path="recurring-deposit" element={<RecurringDeposit />} />
          <Route path="debt-funds" element={<DebtFunds />} />
          <Route path="commodities" element={<Commodities />} />
          <Route path="portfolio-admin" element={<PortfolioAdmin />} />
          <Route path="banks-master" element={<BanksMaster />} />
          <Route path="brokers-master" element={<BrokersMaster />} />
          <Route path="nsc" element={<NSC />} />
          <Route path="kvp" element={<KVP />} />
          <Route path="scss" element={<SCSS />} />
          <Route path="mis" element={<MIS />} />
          <Route path="corporate-bond" element={<CorporateBond />} />
          <Route path="rbi-bond" element={<RBIBond />} />
          <Route path="tax-saving-bond" element={<TaxSavingBond />} />
          <Route path="reits" element={<REITs />} />
          <Route path="invits" element={<InvITs />} />
          <Route path="sovereign-gold-bonds" element={<SovereignGoldBond />} />
          <Route path="land" element={<RealEstate propertyType="land" title="Land" />} />
          <Route path="farm-land" element={<RealEstate propertyType="farm_land" title="Farm Land" />} />
          <Route path="house" element={<RealEstate propertyType="house" title="House" />} />
          <Route path="settings" element={<Settings />} />
          <Route path="help" element={<Help />} />
        </Route>
        
        {/* Catch all */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Box>
  );
}

export default App;

// Made with Bob
