import React, { Suspense, useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { Box, CircularProgress } from '@mui/material';
import { AppDispatch, RootState } from './store';
import { getCurrentUser } from './store/slices/authSlice';

// Layout
import Layout from './components/Layout';

// Components
import SessionTimeout from './components/SessionTimeout';
import ErrorBoundary from './components/ErrorBoundary';

// Pages (lazy-loaded for code splitting)
const Login = React.lazy(() => import('./pages/Login'));
const Register = React.lazy(() => import('./pages/Register'));
const ForgotPassword = React.lazy(() => import('./pages/ForgotPassword'));
const ResetPassword = React.lazy(() => import('./pages/ResetPassword'));
const Dashboard = React.lazy(() => import('./pages/Dashboard'));
const Assets = React.lazy(() => import('./pages/Assets'));
const Statements = React.lazy(() => import('./pages/Statements'));
const AlertsWithProgress = React.lazy(() => import('./pages/AlertsWithProgress'));
const BankAccounts = React.lazy(() => import('./pages/BankAccounts'));
const DematAccounts = React.lazy(() => import('./pages/DematAccounts'));
const CryptoAccounts = React.lazy(() => import('./pages/CryptoAccounts'));
const CryptoAssets = React.lazy(() => import('./pages/CryptoAssets'));
const CryptoExchanges = React.lazy(() => import('./pages/CryptoExchanges'));
const Expenses = React.lazy(() => import('./pages/Expenses'));
const ExpenseDashboard = React.lazy(() => import('./pages/ExpenseDashboard'));
const Categories = React.lazy(() => import('./pages/Categories'));
const PPF = React.lazy(() => import('./pages/PPF'));
const PF = React.lazy(() => import('./pages/PF'));
const SSY = React.lazy(() => import('./pages/SSY'));
const NPS = React.lazy(() => import('./pages/NPS'));
const MutualFundHoldings = React.lazy(() => import('./pages/MutualFundHoldings'));
const Gratuity = React.lazy(() => import('./pages/Gratuity'));
const Insurance = React.lazy(() => import('./pages/Insurance'));
const Stocks = React.lazy(() => import('./pages/Stocks'));
const USStocks = React.lazy(() => import('./pages/USStocks'));
const EquityMF = React.lazy(() => import('./pages/EquityMF'));
const HybridMF = React.lazy(() => import('./pages/HybridMF'));
const Savings = React.lazy(() => import('./pages/Savings'));
const CreditCards = React.lazy(() => import('./pages/CreditCards'));
const FixedDeposit = React.lazy(() => import('./pages/FixedDeposit'));
const RecurringDeposit = React.lazy(() => import('./pages/RecurringDeposit'));
const DebtFunds = React.lazy(() => import('./pages/DebtFunds'));
const Commodities = React.lazy(() => import('./pages/Commodities'));
const PortfolioAdmin = React.lazy(() => import('./pages/PortfolioAdmin'));
const NSC = React.lazy(() => import('./pages/NSC'));
const KVP = React.lazy(() => import('./pages/KVP'));
const SCSS = React.lazy(() => import('./pages/SCSS'));
const MIS = React.lazy(() => import('./pages/MIS'));
const CorporateBond = React.lazy(() => import('./pages/CorporateBond'));
const RBIBond = React.lazy(() => import('./pages/RBIBond'));
const TaxSavingBond = React.lazy(() => import('./pages/TaxSavingBond'));
const REITs = React.lazy(() => import('./pages/REITs'));
const InvITs = React.lazy(() => import('./pages/InvITs'));
const SovereignGoldBond = React.lazy(() => import('./pages/SovereignGoldBond'));
const RealEstate = React.lazy(() => import('./pages/RealEstate'));
const BanksMaster = React.lazy(() => import('./pages/BanksMaster'));
const BrokersMaster = React.lazy(() => import('./pages/BrokersMaster'));
const Settings = React.lazy(() => import('./pages/Settings'));
const Help = React.lazy(() => import('./pages/Help'));
const Portfolios = React.lazy(() => import('./pages/Portfolios'));
const AssetTypesMaster = React.lazy(() => import('./pages/AssetTypesMaster'));
const SuperAdmin = React.lazy(() => import('./pages/SuperAdmin'));

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
      
      <Suspense fallback={<Box display="flex" justifyContent="center" alignItems="center" minHeight="50vh"><CircularProgress /></Box>}>
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
            <Route path="hybrid-mf" element={<HybridMF />} />
            <Route path="savings" element={<Savings />} />
            <Route path="credit-cards" element={<CreditCards />} />
            <Route path="fixed-deposit" element={<FixedDeposit />} />
            <Route path="recurring-deposit" element={<RecurringDeposit />} />
            <Route path="debt-funds" element={<DebtFunds />} />
            <Route path="commodities" element={<Commodities />} />
            <Route path="portfolios" element={<Portfolios />} />
            <Route path="portfolio-admin" element={<PortfolioAdmin />} />
            <Route path="banks-master" element={<BanksMaster />} />
            <Route path="brokers-master" element={<BrokersMaster />} />
            <Route path="asset-types" element={<AssetTypesMaster />} />
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
            <Route path="super-admin" element={<SuperAdmin />} />
            <Route path="settings" element={<Settings />} />
            <Route path="help" element={<Help />} />
          </Route>

          {/* Catch all */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </Box>
  );
}

export default App;

// Made with Bob
