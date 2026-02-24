import React, { useState, useEffect } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import {
  Box,
  Collapse,
  Drawer,
  AppBar,
  Toolbar,
  List,
  Typography,
  Divider,
  IconButton,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Avatar,
  Menu,
  MenuItem,
} from '@mui/material';
import {
  Menu as MenuIcon,
  Dashboard as DashboardIcon,
  AccountBalance as AccountBalanceIcon,
  Notifications as NotificationsIcon,
  AccountCircle,
  ShowChart as ShowChartIcon,
  Receipt as ReceiptIcon,
  Category as CategoryIcon,
  Savings as SavingsIcon,
  Work as WorkIcon,
  BarChart as BarChartIcon,
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
  ExpandLess,
  ExpandMore,
  AdminPanelSettings as AdminIcon,
  Settings as SettingsIcon,
  LocalPostOffice as LocalPostOfficeIcon,
  Gavel as GavelIcon,
  Business as BusinessIcon,
  Diamond as DiamondIcon,
  Home as HomeIcon,
  HelpOutline as HelpIcon,
  FolderSpecial as PortfoliosIcon,
  Description as DescriptionIcon,
  ViewList as ViewListIcon,
  Insights as InsightsIcon,
} from '@mui/icons-material';
import { AppDispatch, RootState } from '../store';
import { logout } from '../store/slices/authSlice';
import PortfolioSelector from './PortfolioSelector';

const drawerWidth = 240;

interface NavItem {
  text: string;
  icon: React.ReactNode;
  path: string;
}

interface AssetGroup {
  key: string;
  title: string;
  icon: React.ReactNode;
  items: NavItem[];
}

// Groups nested under the "Assets" section
const assetGroups: AssetGroup[] = [
  {
    key: 'demat_holding',
    title: 'Demat Holding',
    icon: <ShowChartIcon />,
    items: [
      { text: 'Demat Accounts', icon: <ShowChartIcon />, path: '/demat-accounts' },
      { text: 'Stocks', icon: <StocksIcon />, path: '/stocks' },
      { text: 'US Stocks', icon: <USStocksIcon />, path: '/us-stocks' },
      { text: 'Equity MF', icon: <PieChartIcon />, path: '/equity-mf' },
      { text: 'Debt Funds', icon: <DebtFundIcon />, path: '/debt-funds' },
      { text: 'Commodities', icon: <CommodityIcon />, path: '/commodities' },
      { text: 'Sovereign Gold Bonds', icon: <DiamondIcon />, path: '/sovereign-gold-bonds' },
    ],
  },
  {
    key: 'banking',
    title: 'Banking',
    icon: <AccountBalanceIcon />,
    items: [
      { text: 'Savings', icon: <AccountBalanceIcon />, path: '/savings' },
      { text: 'Credit Cards', icon: <CreditCardIcon />, path: '/credit-cards' },
      { text: 'Fixed Deposit', icon: <FDIcon />, path: '/fixed-deposit' },
      { text: 'Recurring Deposit', icon: <RDIcon />, path: '/recurring-deposit' },
    ],
  },
  {
    key: 'retirement',
    title: 'Retirement Savings',
    icon: <SavingsIcon />,
    items: [
      { text: 'PPF', icon: <SavingsIcon />, path: '/ppf' },
      { text: 'PF / EPF', icon: <WorkIcon />, path: '/pf' },
      { text: 'NPS', icon: <NPSIcon />, path: '/nps' },
      { text: 'SSY', icon: <SSYIcon />, path: '/ssy' },
      { text: 'Gratuity', icon: <WorkIcon />, path: '/gratuity' },
      { text: 'Insurance', icon: <InsuranceIcon />, path: '/insurance' },
    ],
  },
  {
    key: 'crypto',
    title: 'Crypto Investment',
    icon: <CryptoIcon />,
    items: [
      { text: 'Crypto Accounts', icon: <CryptoIcon />, path: '/crypto-accounts' },
      { text: 'Crypto Assets', icon: <CryptoIcon />, path: '/crypto-assets' },
    ],
  },
  {
    key: 'post_office',
    title: 'Post Office Schemes',
    icon: <LocalPostOfficeIcon />,
    items: [
      { text: 'NSC', icon: <LocalPostOfficeIcon />, path: '/nsc' },
      { text: 'KVP', icon: <LocalPostOfficeIcon />, path: '/kvp' },
      { text: 'SCSS', icon: <LocalPostOfficeIcon />, path: '/scss' },
      { text: 'MIS', icon: <LocalPostOfficeIcon />, path: '/mis' },
    ],
  },
  {
    key: 'bonds',
    title: 'Bonds',
    icon: <GavelIcon />,
    items: [
      { text: 'Corporate Bond', icon: <GavelIcon />, path: '/corporate-bond' },
      { text: 'RBI Bond', icon: <GavelIcon />, path: '/rbi-bond' },
      { text: 'Tax Saving Bond', icon: <GavelIcon />, path: '/tax-saving-bond' },
    ],
  },
  {
    key: 'reits',
    title: 'REITs / InvITs',
    icon: <BusinessIcon />,
    items: [
      { text: 'REITs', icon: <BusinessIcon />, path: '/reits' },
      { text: 'InvITs', icon: <BusinessIcon />, path: '/invits' },
    ],
  },
  {
    key: 'real_estate',
    title: 'Real Estate',
    icon: <HomeIcon />,
    items: [
      { text: 'Land', icon: <HomeIcon />, path: '/land' },
      { text: 'Farm Land', icon: <HomeIcon />, path: '/farm-land' },
      { text: 'House', icon: <HomeIcon />, path: '/house' },
    ],
  },
];

const overviewItems: NavItem[] = [
  { text: 'Dashboard', icon: <DashboardIcon />, path: '/dashboard' },
  { text: 'Alerts', icon: <NotificationsIcon />, path: '/alerts' },
  { text: 'Statements', icon: <DescriptionIcon />, path: '/statements' },
];

const assetOverviewItem: NavItem = {
  text: 'Overview',
  icon: <AccountBalanceIcon />,
  path: '/assets',
};

const insightsItems: NavItem[] = [
  { text: 'MF Holdings', icon: <InsightsIcon />, path: '/mutual-fund-holdings' },
];

const expenseItems: NavItem[] = [
  { text: 'Expense Dashboard', icon: <BarChartIcon />, path: '/expense-dashboard' },
  { text: 'Expenses', icon: <ReceiptIcon />, path: '/expenses' },
];

const masterDataItems: NavItem[] = [
  { text: 'Asset Types', icon: <ViewListIcon />, path: '/asset-types' },
  { text: 'Banks', icon: <AccountBalanceIcon />, path: '/banks-master' },
  { text: 'Brokers', icon: <ShowChartIcon />, path: '/brokers-master' },
  { text: 'Crypto Exchanges', icon: <CryptoIcon />, path: '/crypto-exchanges' },
  { text: 'Expense Categories', icon: <CategoryIcon />, path: '/categories' },
];

const adminItems: NavItem[] = [
  { text: 'Portfolios', icon: <PortfoliosIcon />, path: '/portfolios' },
  { text: 'Portfolio Admin', icon: <AdminIcon />, path: '/portfolio-admin' },
  { text: 'Application Setup', icon: <SettingsIcon />, path: '/settings' },
];

const helpItems: NavItem[] = [
  { text: 'Help', icon: <HelpIcon />, path: '/help' },
];

// All leaf items flattened for AppBar title lookup
const allNavItems: NavItem[] = [
  ...overviewItems,
  assetOverviewItem,
  ...assetGroups.flatMap((g) => g.items),
  ...insightsItems,
  ...expenseItems,
  ...masterDataItems,
  ...adminItems,
  ...helpItems,
];

// Returns the group key that owns a given path
const groupKeyForPath = (path: string): string | null => {
  for (const group of assetGroups) {
    if (group.items.some((item) => item.path === path)) return group.key;
  }
  return null;
};

const sectionHeaderSx = {
  fontSize: '0.7rem',
  fontWeight: 'bold',
  color: 'text.secondary',
  textTransform: 'uppercase' as const,
  letterSpacing: 1,
};

const Layout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const dispatch = useDispatch<AppDispatch>();
  const { user } = useSelector((state: RootState) => state.auth);

  const [mobileOpen, setMobileOpen] = useState(false);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);

  // Track which asset groups are expanded; auto-open the active group
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>(() => {
    const active = groupKeyForPath(location.pathname);
    return {
      demat_holding: active === 'demat_holding',
      banking: active === 'banking',
      retirement: active === 'retirement',
      crypto: active === 'crypto',
      post_office: active === 'post_office',
      bonds: active === 'bonds',
      reits: active === 'reits',
      real_estate: active === 'real_estate',
    };
  });

  // When navigating to a page inside a collapsed group, auto-expand it
  useEffect(() => {
    const active = groupKeyForPath(location.pathname);
    if (active && !openGroups[active]) {
      setOpenGroups((prev) => ({ ...prev, [active]: true }));
    }
  }, [location.pathname]); // eslint-disable-line react-hooks/exhaustive-deps

  const toggleGroup = (key: string) => {
    setOpenGroups((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleDrawerToggle = () => setMobileOpen(!mobileOpen);

  const handleMenuClick = (path: string) => {
    navigate(path);
    setMobileOpen(false);
  };

  const handleProfileMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleProfileMenuClose = () => setAnchorEl(null);

  const handleLogout = () => {
    dispatch(logout());
    handleProfileMenuClose();
    navigate('/login');
  };

  const renderNavItem = (item: NavItem, indent = false) => (
    <ListItem key={item.path} disablePadding>
      <ListItemButton
        selected={location.pathname === item.path}
        onClick={() => handleMenuClick(item.path)}
        sx={indent ? { pl: 4 } : undefined}
      >
        <ListItemIcon sx={{ minWidth: 36 }}>{item.icon}</ListItemIcon>
        <ListItemText
          primary={item.text}
          primaryTypographyProps={{ fontSize: indent ? '0.875rem' : undefined }}
        />
      </ListItemButton>
    </ListItem>
  );

  const drawer = (
    <Box sx={{ overflowY: 'auto' }}>
      <Toolbar>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <img src="/logo.svg" alt="PortAct" width={32} height={32} style={{ borderRadius: 6 }} />
          <Typography variant="h6" noWrap component="div" fontWeight={700}>
            PortAct
          </Typography>
        </Box>
      </Toolbar>

      <Divider />

      {/* ── Overview ── */}
      <List
        subheader={
          <ListItem sx={{ py: 0.5 }}>
            <ListItemText primary="Overview" primaryTypographyProps={sectionHeaderSx} />
          </ListItem>
        }
      >
        {overviewItems.map((item) => renderNavItem(item))}
      </List>

      <Divider />

      {/* ── Insights ── */}
      <List
        subheader={
          <ListItem sx={{ py: 0.5 }}>
            <ListItemText primary="Insights" primaryTypographyProps={sectionHeaderSx} />
          </ListItem>
        }
      >
        {insightsItems.map((item) => renderNavItem(item))}
      </List>

      <Divider />

      {/* ── Assets ── */}
      <List
        subheader={
          <ListItem sx={{ py: 0.5 }}>
            <ListItemText primary="Assets" primaryTypographyProps={sectionHeaderSx} />
          </ListItem>
        }
      >
        {renderNavItem(assetOverviewItem)}
        {assetGroups.map((group) => (
          <React.Fragment key={group.key}>
            {/* Group toggle row */}
            <ListItemButton onClick={() => toggleGroup(group.key)} sx={{ py: 0.75 }}>
              <ListItemIcon sx={{ minWidth: 36 }}>{group.icon}</ListItemIcon>
              <ListItemText
                primary={group.title}
                primaryTypographyProps={{ fontWeight: 500, fontSize: '0.9rem' }}
              />
              {openGroups[group.key] ? <ExpandLess fontSize="small" /> : <ExpandMore fontSize="small" />}
            </ListItemButton>

            {/* Collapsed children */}
            <Collapse in={openGroups[group.key]} timeout="auto" unmountOnExit>
              <List disablePadding>
                {group.items.map((item) => renderNavItem(item, true))}
              </List>
            </Collapse>
          </React.Fragment>
        ))}
      </List>

      <Divider />

      {/* ── Expense Management ── */}
      <List
        subheader={
          <ListItem sx={{ py: 0.5 }}>
            <ListItemText primary="Expense Management" primaryTypographyProps={sectionHeaderSx} />
          </ListItem>
        }
      >
        {expenseItems.map((item) => renderNavItem(item))}
      </List>

      <Divider />

      {/* ── Administration ── */}
      <List
        subheader={
          <ListItem sx={{ py: 0.5 }}>
            <ListItemText primary="Administration" primaryTypographyProps={sectionHeaderSx} />
          </ListItem>
        }
      >
        {adminItems.map((item) => renderNavItem(item))}
      </List>

      <Divider />

      {/* ── Master Data ── */}
      <List
        subheader={
          <ListItem sx={{ py: 0.5 }}>
            <ListItemText primary="Master Data" primaryTypographyProps={sectionHeaderSx} />
          </ListItem>
        }
      >
        {masterDataItems.map((item) => renderNavItem(item))}
      </List>

      <Divider />

      {/* ── Help ── */}
      <List>
        {helpItems.map((item) => renderNavItem(item))}
      </List>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex', width: '100%' }}>
      <AppBar
        position="fixed"
        sx={{
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          ml: { sm: `${drawerWidth}px` },
        }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            aria-label="open drawer"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { sm: 'none' } }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
            {allNavItems.find((item) => item.path === location.pathname)?.text || 'PortAct'}
          </Typography>
          <PortfolioSelector />
          <IconButton
            size="large"
            edge="end"
            aria-label="account of current user"
            aria-controls="menu-appbar"
            aria-haspopup="true"
            onClick={handleProfileMenuOpen}
            color="inherit"
          >
            <Avatar sx={{ width: 32, height: 32 }}>
              {user?.email?.charAt(0).toUpperCase() || <AccountCircle />}
            </Avatar>
          </IconButton>
          <Menu
            id="menu-appbar"
            anchorEl={anchorEl}
            anchorOrigin={{ vertical: 'top', horizontal: 'right' }}
            keepMounted
            transformOrigin={{ vertical: 'top', horizontal: 'right' }}
            open={Boolean(anchorEl)}
            onClose={handleProfileMenuClose}
          >
            <MenuItem disabled>
              <Typography variant="body2">{user?.email}</Typography>
            </MenuItem>
            <Divider />
            <MenuItem onClick={handleLogout}>Logout</MenuItem>
          </Menu>
        </Toolbar>
      </AppBar>

      <Box component="nav" sx={{ width: { sm: drawerWidth }, flexShrink: { sm: 0 } }}>
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{ keepMounted: true }}
          sx={{
            display: { xs: 'block', sm: 'none' },
            '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth },
          }}
        >
          {drawer}
        </Drawer>
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', sm: 'block' },
            '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth },
          }}
          open
        >
          {drawer}
        </Drawer>
      </Box>

      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          mt: 8,
          minWidth: 0,
        }}
      >
        <Outlet />
      </Box>
    </Box>
  );
};

export default Layout;

// Made with Bob
