import React from 'react';
import {
  Dashboard as DashboardIcon,
  AccountBalance as AccountBalanceIcon,
  Notifications as NotificationsIcon,
  ShowChart as ShowChartIcon,
  Receipt as ReceiptIcon,
  Category as CategoryIcon,
  Savings as SavingsIcon,
  Work as WorkIcon,
  CurrencyBitcoin as CryptoIcon,
  PieChart as PieChartIcon,
  ChildCare as SSYIcon,
  AccountBalanceWallet as NPSIcon,
  Shield as InsuranceIcon,
  TrendingUp as StocksIcon,
  Language as USStocksIcon,
  CreditCard as CreditCardIcon,
  Lock as FDIcon,
  Autorenew as RDIcon,
  MonetizationOn as DebtFundIcon,
  Grain as CommodityIcon,
  AdminPanelSettings as AdminIcon,
  Settings as SettingsIcon,
  LocalPostOffice as LocalPostOfficeIcon,
  Gavel as GavelIcon,
  Business as BusinessIcon,
  Diamond as DiamondIcon,
  Home as HomeIcon,
  WorkOutline as ESOPIcon,
  CardGiftcard as RSUIcon,
  HelpOutline as HelpIcon,
  FolderSpecial as PortfoliosIcon,
  Description as DescriptionIcon,
  ViewList as ViewListIcon,
  Insights as InsightsIcon,
  BarChart as BarChartIcon,
  Paid as PaidIcon,
  Wallet as WalletIcon,
} from '@mui/icons-material';

// ── Constants ──

export const RAIL_WIDTH = 64;
export const FLYOUT_WIDTH = 260;

// ── Interfaces ──

export interface NavItem {
  text: string;
  icon: React.ReactElement;
  path: string;
}

export interface AssetGroup {
  key: string;
  title: string;
  icon: React.ReactElement;
  items: NavItem[];
}

export interface RailSection {
  key: string;
  label: string;
  icon: React.ReactElement;
  path?: string;
  items?: NavItem[];
  assetGroups?: AssetGroup[];
  dataTour?: string;
  bottomAligned?: boolean;
}

// ── Asset Groups ──

export const assetGroups: AssetGroup[] = [
  {
    key: 'demat_holding',
    title: 'Demat Holding',
    icon: React.createElement(ShowChartIcon),
    items: [
      { text: 'Demat Accounts', icon: React.createElement(ShowChartIcon), path: '/demat-accounts' },
      { text: 'Stocks', icon: React.createElement(StocksIcon), path: '/stocks' },
      { text: 'US Stocks', icon: React.createElement(USStocksIcon), path: '/us-stocks' },
      { text: 'Equity MF', icon: React.createElement(PieChartIcon), path: '/equity-mf' },
      { text: 'Hybrid MF', icon: React.createElement(PieChartIcon), path: '/hybrid-mf' },
      { text: 'Debt Funds', icon: React.createElement(DebtFundIcon), path: '/debt-funds' },
      { text: 'Commodities', icon: React.createElement(CommodityIcon), path: '/commodities' },
      { text: 'Sovereign Gold Bonds', icon: React.createElement(DiamondIcon), path: '/sovereign-gold-bonds' },
      { text: 'ESOPs', icon: React.createElement(ESOPIcon), path: '/esops' },
      { text: 'RSUs', icon: React.createElement(RSUIcon), path: '/rsus' },
    ],
  },
  {
    key: 'banking',
    title: 'Banking',
    icon: React.createElement(AccountBalanceIcon),
    items: [
      { text: 'Savings', icon: React.createElement(AccountBalanceIcon), path: '/savings' },
      { text: 'Credit Cards', icon: React.createElement(CreditCardIcon), path: '/credit-cards' },
      { text: 'Fixed Deposit', icon: React.createElement(FDIcon), path: '/fixed-deposit' },
      { text: 'Recurring Deposit', icon: React.createElement(RDIcon), path: '/recurring-deposit' },
    ],
  },
  {
    key: 'retirement',
    title: 'Retirement Savings',
    icon: React.createElement(SavingsIcon),
    items: [
      { text: 'PPF', icon: React.createElement(SavingsIcon), path: '/ppf' },
      { text: 'PF / EPF', icon: React.createElement(WorkIcon), path: '/pf' },
      { text: 'NPS', icon: React.createElement(NPSIcon), path: '/nps' },
      { text: 'SSY', icon: React.createElement(SSYIcon), path: '/ssy' },
      { text: 'Gratuity', icon: React.createElement(WorkIcon), path: '/gratuity' },
      { text: 'Insurance', icon: React.createElement(InsuranceIcon), path: '/insurance' },
    ],
  },
  {
    key: 'crypto',
    title: 'Crypto Investment',
    icon: React.createElement(CryptoIcon),
    items: [
      { text: 'Crypto Accounts', icon: React.createElement(CryptoIcon), path: '/crypto-accounts' },
      { text: 'Crypto Assets', icon: React.createElement(CryptoIcon), path: '/crypto-assets' },
    ],
  },
  {
    key: 'post_office',
    title: 'Post Office Schemes',
    icon: React.createElement(LocalPostOfficeIcon),
    items: [
      { text: 'NSC', icon: React.createElement(LocalPostOfficeIcon), path: '/nsc' },
      { text: 'KVP', icon: React.createElement(LocalPostOfficeIcon), path: '/kvp' },
      { text: 'SCSS', icon: React.createElement(LocalPostOfficeIcon), path: '/scss' },
      { text: 'MIS', icon: React.createElement(LocalPostOfficeIcon), path: '/mis' },
    ],
  },
  {
    key: 'bonds',
    title: 'Bonds',
    icon: React.createElement(GavelIcon),
    items: [
      { text: 'Corporate Bond', icon: React.createElement(GavelIcon), path: '/corporate-bond' },
      { text: 'RBI Bond', icon: React.createElement(GavelIcon), path: '/rbi-bond' },
      { text: 'Tax Saving Bond', icon: React.createElement(GavelIcon), path: '/tax-saving-bond' },
    ],
  },
  {
    key: 'reits',
    title: 'REITs / InvITs',
    icon: React.createElement(BusinessIcon),
    items: [
      { text: 'REITs', icon: React.createElement(BusinessIcon), path: '/reits' },
      { text: 'InvITs', icon: React.createElement(BusinessIcon), path: '/invits' },
    ],
  },
  {
    key: 'real_estate',
    title: 'Real Estate',
    icon: React.createElement(HomeIcon),
    items: [
      { text: 'Land', icon: React.createElement(HomeIcon), path: '/land' },
      { text: 'Farm Land', icon: React.createElement(HomeIcon), path: '/farm-land' },
      { text: 'House', icon: React.createElement(HomeIcon), path: '/house' },
    ],
  },
];

// ── Section Item Lists ──

const insightsItems: NavItem[] = [
  { text: 'Alerts', icon: React.createElement(NotificationsIcon), path: '/alerts' },
  { text: 'MF Holdings', icon: React.createElement(InsightsIcon), path: '/mutual-fund-holdings' },
];

const assetOverviewItem: NavItem = {
  text: 'Asset Overview',
  icon: React.createElement(PaidIcon),
  path: '/assets',
};

const expenseItems: NavItem[] = [
  { text: 'Expense Dashboard', icon: React.createElement(BarChartIcon), path: '/expense-dashboard' },
  { text: 'Expenses', icon: React.createElement(ReceiptIcon), path: '/expenses' },
];

const adminItems: NavItem[] = [
  { text: 'Portfolios', icon: React.createElement(PortfoliosIcon), path: '/portfolios' },
  { text: 'Portfolio Admin', icon: React.createElement(AdminIcon), path: '/portfolio-admin' },
  { text: 'Application Setup', icon: React.createElement(SettingsIcon), path: '/settings' },
];

const masterDataItems: NavItem[] = [
  { text: 'Asset Types', icon: React.createElement(ViewListIcon), path: '/asset-types' },
  { text: 'Banks', icon: React.createElement(AccountBalanceIcon), path: '/banks-master' },
  { text: 'Brokers', icon: React.createElement(ShowChartIcon), path: '/brokers-master' },
  { text: 'Crypto Exchanges', icon: React.createElement(CryptoIcon), path: '/crypto-exchanges' },
  { text: 'Expense Categories', icon: React.createElement(CategoryIcon), path: '/categories' },
];

// ── Rail Sections ──

export const railSections: RailSection[] = [
  {
    key: 'dashboard',
    label: 'Dashboard',
    icon: React.createElement(DashboardIcon),
    path: '/dashboard',
    dataTour: 'dashboard',
  },
  {
    key: 'asset-overview',
    label: 'Asset Overview',
    icon: React.createElement(PaidIcon),
    path: '/assets',
  },
  {
    key: 'statements',
    label: 'Statements',
    icon: React.createElement(DescriptionIcon),
    path: '/statements',
    dataTour: 'statements',
  },
  {
    key: 'insights',
    label: 'Insights',
    icon: React.createElement(InsightsIcon),
    items: insightsItems,
  },
  {
    key: 'assets',
    label: 'Assets',
    icon: React.createElement(WalletIcon),
    assetGroups: assetGroups,
    dataTour: 'sidebar-assets',
  },
  {
    key: 'expenses',
    label: 'Expenses',
    icon: React.createElement(ReceiptIcon),
    items: expenseItems,
  },
  {
    key: 'admin',
    label: 'Administration',
    icon: React.createElement(AdminIcon),
    items: adminItems,
    dataTour: 'settings',
  },
  {
    key: 'master-data',
    label: 'Master Data',
    icon: React.createElement(CategoryIcon),
    items: masterDataItems,
  },
  {
    key: 'help',
    label: 'Help',
    icon: React.createElement(HelpIcon),
    path: '/help',
    bottomAligned: true,
    dataTour: 'help',
  },
];

// ── Helpers ──

/** Flat list of all navigable items (used for AppBar title lookup) */
export const allNavItems: NavItem[] = [
  { text: 'Dashboard', icon: React.createElement(DashboardIcon), path: '/dashboard' },
  { text: 'Statements', icon: React.createElement(DescriptionIcon), path: '/statements' },
  ...insightsItems,
  assetOverviewItem,
  ...assetGroups.flatMap((g) => g.items),
  ...expenseItems,
  ...adminItems,
  ...masterDataItems,
  { text: 'Help', icon: React.createElement(HelpIcon), path: '/help' },
];

/** Returns the asset-group key that owns a given path, or null */
export const groupKeyForPath = (path: string): string | null => {
  for (const group of assetGroups) {
    if (group.items.some((item) => item.path === path)) return group.key;
  }
  return null;
};

export const sectionHeaderSx = {
  fontSize: '0.7rem',
  fontWeight: 'bold',
  color: 'text.secondary',
  textTransform: 'uppercase' as const,
  letterSpacing: 1,
};
