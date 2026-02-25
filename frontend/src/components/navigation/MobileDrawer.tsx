import React from 'react';
import {
  Box,
  Collapse,
  Divider,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Typography,
} from '@mui/material';
import { ExpandLess, ExpandMore } from '@mui/icons-material';
import { useLocation } from 'react-router-dom';
import { railSections, NavItem, sectionHeaderSx } from './navigationData';

const MOBILE_DRAWER_WIDTH = 260;

interface MobileDrawerProps {
  open: boolean;
  onClose: () => void;
  onNavigate: (path: string) => void;
  openGroups: Record<string, boolean>;
  onToggleGroup: (key: string) => void;
}

const MobileDrawer: React.FC<MobileDrawerProps> = ({
  open,
  onClose,
  onNavigate,
  openGroups,
  onToggleGroup,
}) => {
  const location = useLocation();

  const handleNav = (path: string) => {
    onNavigate(path);
    onClose();
  };

  const renderNavItem = (item: NavItem, indent = false) => (
    <ListItem key={item.path} disablePadding>
      <ListItemButton
        selected={location.pathname === item.path}
        onClick={() => handleNav(item.path)}
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

      {railSections.map((section) => (
        <React.Fragment key={section.key}>
          <List
            subheader={
              <ListItem sx={{ py: 0.5 }} data-tour={section.dataTour}>
                <ListItemText primary={section.label} primaryTypographyProps={sectionHeaderSx} />
              </ListItem>
            }
          >
            {/* Direct nav section (no flyout items) */}
            {section.path && (
              <ListItem disablePadding>
                <ListItemButton
                  selected={location.pathname === section.path}
                  onClick={() => handleNav(section.path!)}
                >
                  <ListItemIcon sx={{ minWidth: 36 }}>{section.icon}</ListItemIcon>
                  <ListItemText primary={section.label} />
                </ListItemButton>
              </ListItem>
            )}

            {/* Simple items */}
            {section.items?.map((item) => renderNavItem(item))}

            {/* Asset groups with collapse */}
            {section.assetGroups?.map((group) => (
              <React.Fragment key={group.key}>
                <ListItemButton onClick={() => onToggleGroup(group.key)} sx={{ py: 0.75 }}>
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
          <Divider />
        </React.Fragment>
      ))}
    </Box>
  );

  return (
    <Drawer
      variant="temporary"
      open={open}
      onClose={onClose}
      ModalProps={{ keepMounted: true }}
      sx={{
        display: { xs: 'block', sm: 'none' },
        '& .MuiDrawer-paper': { boxSizing: 'border-box', width: MOBILE_DRAWER_WIDTH },
      }}
    >
      {drawer}
    </Drawer>
  );
};

export default MobileDrawer;
