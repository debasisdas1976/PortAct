import React, { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import {
  Box,
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
  CreditCard as CreditCardIcon,
  ShowChart as ShowChartIcon,
  Receipt as ReceiptIcon,
  Category as CategoryIcon,
  Savings as SavingsIcon,
  Work as WorkIcon,
  BarChart as BarChartIcon,
  CurrencyBitcoin as CryptoIcon,
  PieChart as PieChartIcon,
} from '@mui/icons-material';
import { AppDispatch, RootState } from '../store';
import { logout } from '../store/slices/authSlice';

const drawerWidth = 240;

const menuSections = [
  {
    title: 'Overview',
    items: [
      { text: 'Dashboard', icon: <DashboardIcon />, path: '/dashboard' },
      { text: 'Alerts', icon: <NotificationsIcon />, path: '/alerts' },
    ]
  },
  {
    title: 'Portfolio Management',
    items: [
      { text: 'Assets', icon: <AccountBalanceIcon />, path: '/assets' },
      { text: 'MF Holdings', icon: <PieChartIcon />, path: '/mutual-fund-holdings' },
      { text: 'Bank Accounts', icon: <CreditCardIcon />, path: '/bank-accounts' },
      { text: 'Demat Accounts', icon: <ShowChartIcon />, path: '/demat-accounts' },
      { text: 'Crypto Accounts', icon: <CryptoIcon />, path: '/crypto-accounts' },
      { text: 'PPF', icon: <SavingsIcon />, path: '/ppf' },
      { text: 'PF/EPF', icon: <WorkIcon />, path: '/pf' },
    ]
  },
  {
    title: 'Expense Management',
    items: [
      { text: 'Expense Dashboard', icon: <BarChartIcon />, path: '/expense-dashboard' },
      { text: 'Expenses', icon: <ReceiptIcon />, path: '/expenses' },
      { text: 'Categories', icon: <CategoryIcon />, path: '/categories' },
    ]
  }
];

// Flatten menu items for path matching in AppBar
const allMenuItems = menuSections.flatMap(section => section.items);

const Layout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const dispatch = useDispatch<AppDispatch>();
  const { user } = useSelector((state: RootState) => state.auth);
  
  const [mobileOpen, setMobileOpen] = useState(false);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const handleMenuClick = (path: string) => {
    navigate(path);
    setMobileOpen(false);
  };

  const handleProfileMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleProfileMenuClose = () => {
    setAnchorEl(null);
  };

  const handleLogout = () => {
    dispatch(logout());
    handleProfileMenuClose();
    navigate('/login');
  };

  const drawer = (
    <Box>
      <Toolbar>
        <Typography variant="h6" noWrap component="div">
          PortAct
        </Typography>
      </Toolbar>
      <Divider />
      {menuSections.map((section, sectionIndex) => (
        <React.Fragment key={section.title}>
          <List
            subheader={
              <ListItem>
                <ListItemText
                  primary={section.title}
                  primaryTypographyProps={{
                    fontSize: '0.75rem',
                    fontWeight: 'bold',
                    color: 'text.secondary',
                    textTransform: 'uppercase',
                    letterSpacing: 1,
                  }}
                />
              </ListItem>
            }
          >
            {section.items.map((item) => (
              <ListItem key={item.text} disablePadding>
                <ListItemButton
                  selected={location.pathname === item.path}
                  onClick={() => handleMenuClick(item.path)}
                >
                  <ListItemIcon>{item.icon}</ListItemIcon>
                  <ListItemText primary={item.text} />
                </ListItemButton>
              </ListItem>
            ))}
          </List>
          {sectionIndex < menuSections.length - 1 && <Divider />}
        </React.Fragment>
      ))}
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
            {allMenuItems.find((item) => item.path === location.pathname)?.text || 'PortAct'}
          </Typography>
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
            anchorOrigin={{
              vertical: 'top',
              horizontal: 'right',
            }}
            keepMounted
            transformOrigin={{
              vertical: 'top',
              horizontal: 'right',
            }}
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
      <Box
        component="nav"
        sx={{ width: { sm: drawerWidth }, flexShrink: { sm: 0 } }}
      >
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{
            keepMounted: true,
          }}
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
        }}
      >
        <Outlet />
      </Box>
    </Box>
  );
};

export default Layout;

// Made with Bob
