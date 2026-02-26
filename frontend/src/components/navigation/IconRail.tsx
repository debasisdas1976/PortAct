import React from 'react';
import { Box, IconButton, Tooltip, Divider } from '@mui/material';
import { RAIL_WIDTH, RailSection } from './navigationData';

interface IconRailProps {
  activeSection: string | null;
  activeFlyout: string | null;
  railSections: RailSection[];
  onRailClick: (section: RailSection) => void;
}

const IconRail: React.FC<IconRailProps> = ({ activeSection, activeFlyout, railSections, onRailClick }) => {
    const topSections = railSections.filter((s) => !s.bottomAligned);
    const bottomSections = railSections.filter((s) => s.bottomAligned);

    const renderIcon = (section: RailSection) => {
      const isActive = activeSection === section.key;
      const isFlyoutOpen = activeFlyout === section.key;

      return (
        <Tooltip key={section.key} title={section.label} placement="right" arrow disableInteractive>
          <IconButton
            data-tour={section.dataTour}
            onClick={() => onRailClick(section)}
            sx={{
              width: 44,
              height: 44,
              borderRadius: '12px',
              position: 'relative',
              color: isActive || isFlyoutOpen ? 'primary.main' : 'text.secondary',
              bgcolor: isFlyoutOpen
                ? 'action.selected'
                : isActive
                  ? 'action.hover'
                  : 'transparent',
              transition: 'background-color 0.15s ease-in-out, color 0.15s ease-in-out',
              '&:hover': {
                bgcolor: 'action.hover',
              },
              // Active left-edge indicator
              '&::before': isActive
                ? {
                    content: '""',
                    position: 'absolute',
                    left: -10,
                    top: '25%',
                    height: '50%',
                    width: 3,
                    borderRadius: '0 2px 2px 0',
                    bgcolor: 'primary.main',
                  }
                : {},
            }}
          >
            {section.icon}
          </IconButton>
        </Tooltip>
      );
    };

    return (
      <Box
        sx={{
          position: 'fixed',
          top: 64,
          left: 0,
          width: RAIL_WIDTH,
          height: 'calc(100vh - 64px)',
          bgcolor: '#F1F5F9',
          borderRight: 1,
          borderColor: 'divider',
          // Engraved line between AppBar and rail
          borderTop: '1px solid',
          borderTopColor: 'divider',
          boxShadow: (theme) =>
            `inset 0 1px 0 0 rgba(255,255,255,0.08), inset 0 2px 3px -2px ${theme.palette.divider}`,
          display: { xs: 'none', sm: 'flex' },
          flexDirection: 'column',
          alignItems: 'center',
          zIndex: (theme) => theme.zIndex.drawer + 1,
          pt: 1.5,
          pb: 1.5,
        }}
      >

        {/* Top section icons */}
        <Box
          sx={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 0.5,
            flexGrow: 1,
          }}
        >
          {topSections.map(renderIcon)}
        </Box>

        {/* Bottom section icons */}
        <Divider sx={{ width: '60%', my: 1 }} />
        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 0.5 }}>
          {bottomSections.map(renderIcon)}
        </Box>
      </Box>
    );
};

export default IconRail;
