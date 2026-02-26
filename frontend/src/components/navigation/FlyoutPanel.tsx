import React from 'react';
import {
  Box,
  Collapse,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Paper,
  Toolbar,
  Typography,
} from '@mui/material';
import { ExpandLess, ExpandMore } from '@mui/icons-material';
import { useLocation } from 'react-router-dom';
import { RAIL_WIDTH, FLYOUT_WIDTH, RailSection, NavItem, sectionHeaderSx } from './navigationData';

interface FlyoutPanelProps {
  activeFlyout: string | null;
  railSections: RailSection[];
  openGroups: Record<string, boolean>;
  onToggleGroup: (key: string) => void;
  onNavigate: (path: string) => void;
}

const FlyoutPanel: React.FC<FlyoutPanelProps> = ({
  activeFlyout,
  railSections,
  openGroups,
  onToggleGroup,
  onNavigate,
}) => {
  const location = useLocation();
  const activeSection = activeFlyout
    ? railSections.find((s) => s.key === activeFlyout)
    : null;

  const renderNavItem = (item: NavItem, indent = false) => (
    <ListItem key={item.path} disablePadding>
      <ListItemButton
        selected={location.pathname === item.path}
        onClick={() => onNavigate(item.path)}
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

  const renderContent = () => {
    if (!activeSection) return null;

    return (
      <>
        <Toolbar />
        <Box sx={{ px: 1, py: 1.5 }}>
          <Typography
            variant="subtitle2"
            sx={{ ...sectionHeaderSx, px: 1, pb: 1 }}
          >
            {activeSection.label}
          </Typography>

          <List disablePadding>
            {/* Render simple items */}
            {activeSection.items?.map((item) => renderNavItem(item))}

            {/* Render collapsible asset groups (only for Assets section) */}
            {activeSection.assetGroups?.map((group) => (
              <React.Fragment key={group.key}>
                <ListItemButton
                  onClick={() => onToggleGroup(group.key)}
                  sx={{ py: 0.75 }}
                >
                  <ListItemIcon sx={{ minWidth: 36 }}>{group.icon}</ListItemIcon>
                  <ListItemText
                    primary={group.title}
                    primaryTypographyProps={{ fontWeight: 500, fontSize: '0.9rem' }}
                  />
                  {openGroups[group.key] ? (
                    <ExpandLess fontSize="small" />
                  ) : (
                    <ExpandMore fontSize="small" />
                  )}
                </ListItemButton>

                <Collapse in={openGroups[group.key]} timeout="auto" unmountOnExit>
                  <List disablePadding>
                    {group.items.map((item) => renderNavItem(item, true))}
                  </List>
                </Collapse>
              </React.Fragment>
            ))}
          </List>
        </Box>
      </>
    );
  };

  const isOpen = activeFlyout !== null;

  return (
    <Paper
      elevation={isOpen ? 8 : 0}
      sx={{
        position: 'fixed',
        top: 64,
        left: RAIL_WIDTH,
        width: FLYOUT_WIDTH,
        height: 'calc(100vh - 64px)',
        zIndex: (theme) => theme.zIndex.drawer + 1,
        bgcolor: '#F8FAFC',
        overflowY: 'auto',
        borderRadius: 0,
        display: { xs: 'none', sm: 'block' },
        // Slide-in animation via CSS transform
        transform: isOpen ? 'translateX(0)' : `translateX(-${FLYOUT_WIDTH}px)`,
        opacity: isOpen ? 1 : 0,
        transition: 'transform 200ms cubic-bezier(0.4, 0, 0.2, 1), opacity 150ms ease-in-out',
        pointerEvents: isOpen ? 'auto' : 'none',
        // Custom scrollbar
        '&::-webkit-scrollbar': { width: 6 },
        '&::-webkit-scrollbar-thumb': {
          bgcolor: 'divider',
          borderRadius: 3,
        },
      }}
    >
      <Box>{renderContent()}</Box>
    </Paper>
  );
};

export default FlyoutPanel;
