import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import {
  Box,
  AppBar,
  Toolbar,
  Typography,
  IconButton,
  Avatar,
  Menu,
  MenuItem,
  Divider,
} from '@mui/material';
import {
  Menu as MenuIcon,
  AccountCircle,
} from '@mui/icons-material';
import { AppDispatch, RootState } from '../store';
import { logout } from '../store/slices/authSlice';
import PortfolioSelector from './PortfolioSelector';
import ProductTour from './ProductTour';
import UpdateNotification from './UpdateNotification';
import IconRail from './navigation/IconRail';
import FlyoutPanel from './navigation/FlyoutPanel';
import MobileDrawer from './navigation/MobileDrawer';
import { useActiveSection } from './navigation/useActiveSection';
import {
  railSections,
  allNavItems,
  groupKeyForPath,
  RAIL_WIDTH,
  RailSection,
} from './navigation/navigationData';

const Layout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const dispatch = useDispatch<AppDispatch>();
  const { user } = useSelector((state: RootState) => state.auth);

  const activeSection = useActiveSection(railSections);
  const [activeFlyout, setActiveFlyout] = useState<string | null>(null);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>({});
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const prevPathnameRef = useRef(location.pathname);

  // Close flyout synchronously on route change (no async useEffect race)
  if (prevPathnameRef.current !== location.pathname) {
    prevPathnameRef.current = location.pathname;
    if (activeFlyout !== null) {
      setActiveFlyout(null);
    }
  }

  // Auto-expand the asset group that owns the current path
  useEffect(() => {
    const active = groupKeyForPath(location.pathname);
    if (active && !openGroups[active]) {
      setOpenGroups((prev) => ({ ...prev, [active]: true }));
    }
  }, [location.pathname]); // eslint-disable-line react-hooks/exhaustive-deps

  // ESC key closes flyout
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setActiveFlyout(null);
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleRailClick = useCallback(
    (section: RailSection) => {
      if (section.path) {
        navigate(section.path);
        setActiveFlyout(null);
      } else {
        setActiveFlyout((prev) => (prev === section.key ? null : section.key));
      }
    },
    [navigate],
  );

  const handleNavigate = useCallback(
    (path: string) => {
      navigate(path);
      setActiveFlyout(null);
      setMobileOpen(false);
    },
    [navigate],
  );

  const toggleGroup = useCallback((key: string) => {
    setOpenGroups((prev) => ({ ...prev, [key]: !prev[key] }));
  }, []);

  const handleProfileMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleProfileMenuClose = () => setAnchorEl(null);

  const handleLogout = () => {
    dispatch(logout());
    handleProfileMenuClose();
    navigate('/login');
  };

  return (
    <Box sx={{ display: 'flex', width: '100%' }}>
      {/* ── AppBar ── */}
      <AppBar
        position="fixed"
        sx={{
          width: { sm: `calc(100% - ${RAIL_WIDTH}px)` },
          ml: { sm: `${RAIL_WIDTH}px` },
        }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            aria-label="open drawer"
            edge="start"
            onClick={() => setMobileOpen(!mobileOpen)}
            sx={{ mr: 2, display: { sm: 'none' } }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1, fontWeight: 700, fontSize: '1.35rem', letterSpacing: '0.02em' }}>
            {allNavItems.find((item) => item.path === location.pathname)?.text || 'PortAct'}
          </Typography>
          <Box data-tour="portfolio-selector">
            <PortfolioSelector />
          </Box>
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

      {/* ── Navigation ── */}
      <Box component="nav" sx={{ width: { sm: RAIL_WIDTH }, flexShrink: { sm: 0 } }}>
        <IconRail
          activeSection={activeSection}
          activeFlyout={activeFlyout}
          railSections={railSections}
          onRailClick={handleRailClick}
        />
        <FlyoutPanel
          activeFlyout={activeFlyout}
          railSections={railSections}
          openGroups={openGroups}
          onToggleGroup={toggleGroup}
          onNavigate={handleNavigate}
        />
        {/* Backdrop: closes flyout when clicking outside rail/flyout */}
        {activeFlyout && (
          <Box
            onClick={() => setActiveFlyout(null)}
            sx={{
              position: 'fixed',
              top: 0,
              left: RAIL_WIDTH,
              right: 0,
              bottom: 0,
              zIndex: (theme) => theme.zIndex.drawer,
              display: { xs: 'none', sm: 'block' },
            }}
          />
        )}
        <MobileDrawer
          open={mobileOpen}
          onClose={() => setMobileOpen(false)}
          onNavigate={handleNavigate}
          openGroups={openGroups}
          onToggleGroup={toggleGroup}
        />
      </Box>

      {/* ── Main Content ── */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: { sm: `calc(100% - ${RAIL_WIDTH}px)` },
          mt: 8,
          minWidth: 0,
        }}
      >
        <UpdateNotification />
        <Outlet />
        <ProductTour />
      </Box>
    </Box>
  );
};

export default Layout;
