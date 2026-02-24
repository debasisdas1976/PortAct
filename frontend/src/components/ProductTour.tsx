import React, { useState, useEffect, useCallback } from 'react';
import Joyride, { CallBackProps, STATUS, Step } from 'react-joyride';
import { useLocation } from 'react-router-dom';
import { useTheme } from '@mui/material/styles';

const TOUR_STORAGE_KEY = 'portact_tour_completed';

const tourSteps: Step[] = [
  {
    target: 'body',
    content:
      'Welcome to PortAct! Let us take you on a quick tour of the application to help you get started.',
    placement: 'center',
    disableBeacon: true,
    title: 'Welcome to PortAct',
  },
  {
    target: '[data-tour="dashboard"]',
    content:
      'The Dashboard shows your complete portfolio overview — total value, asset allocation charts, and performance over time.',
    title: 'Dashboard',
    placement: 'right',
    disableBeacon: true,
  },
  {
    target: '[data-tour="statements"]',
    content:
      'Upload bank statements, broker statements, and government scheme statements here. PortAct will automatically parse them and import your holdings and transactions.',
    title: 'Statements & Upload',
    placement: 'right',
    disableBeacon: true,
  },
  {
    target: '[data-tour="sidebar-assets"]',
    content:
      'Your investments are organized into categories: Demat Holdings, Banking, Retirement, Crypto, Post Office Schemes, Bonds, REITs/InvITs, and Real Estate. Click any category to expand and see sub-pages.',
    title: 'Asset Categories',
    placement: 'right',
    disableBeacon: true,
  },
  {
    target: '[data-tour="portfolio-selector"]',
    content:
      'Use the portfolio selector to switch between portfolios or view all combined. You can create multiple portfolios to organize different investment strategies.',
    title: 'Portfolio Selector',
    placement: 'bottom',
    disableBeacon: true,
  },
  {
    target: '[data-tour="help"]',
    content:
      'Visit the Help page for detailed guides on every feature, supported file formats, and troubleshooting tips.',
    title: 'Help & Guide',
    placement: 'right',
    disableBeacon: true,
  },
  {
    target: '[data-tour="settings"]',
    content:
      'Configure your profile, employment details (for automatic PF/Gratuity calculations), price update schedules, and AI news alert settings.',
    title: 'Settings',
    placement: 'right',
    disableBeacon: true,
  },
  {
    target: 'body',
    content:
      'You\'re all set! Start by uploading your first statement from the Statements page, or add accounts manually from the respective asset pages. You can restart this tour any time from the Help page.',
    placement: 'center',
    disableBeacon: true,
    title: 'Ready to Go!',
  },
];

interface ProductTourProps {
  /** Set to true to force-start the tour (e.g. from Help page "Restart Tour"). */
  run?: boolean;
  onComplete?: () => void;
}

const ProductTour: React.FC<ProductTourProps> = ({ run: externalRun, onComplete }) => {
  const [runTour, setRunTour] = useState(false);
  const location = useLocation();
  const theme = useTheme();

  // Auto-start on first visit to dashboard
  useEffect(() => {
    const completed = localStorage.getItem(TOUR_STORAGE_KEY);
    if (!completed && location.pathname === '/dashboard') {
      const timer = setTimeout(() => setRunTour(true), 1000);
      return () => clearTimeout(timer);
    }
    return undefined;
  }, [location.pathname]);

  // External trigger
  useEffect(() => {
    if (externalRun) {
      setRunTour(true);
    }
  }, [externalRun]);

  const handleCallback = useCallback(
    (data: CallBackProps) => {
      const { status } = data;
      const finishedStatuses: string[] = [STATUS.FINISHED, STATUS.SKIPPED];

      if (finishedStatuses.includes(status)) {
        setRunTour(false);
        localStorage.setItem(TOUR_STORAGE_KEY, 'true');
        onComplete?.();
      }
    },
    [onComplete],
  );

  return (
    <Joyride
      steps={tourSteps}
      run={runTour}
      continuous
      showProgress
      showSkipButton
      scrollToFirstStep
      disableOverlayClose
      callback={handleCallback}
      styles={{
        options: {
          primaryColor: theme.palette.primary.main,
          textColor: theme.palette.text.primary,
          backgroundColor: theme.palette.background.paper,
          zIndex: 10000,
        },
        tooltip: {
          borderRadius: Number(theme.shape.borderRadius),
          fontSize: '0.875rem',
        },
        buttonNext: {
          backgroundColor: theme.palette.primary.main,
          borderRadius: Number(theme.shape.borderRadius),
          fontWeight: 600,
        },
        buttonBack: {
          color: theme.palette.text.secondary,
          marginRight: 10,
        },
        buttonSkip: {
          color: theme.palette.text.secondary,
        },
      }}
      locale={{
        back: 'Back',
        close: 'Close',
        last: 'Done',
        next: 'Next',
        skip: 'Skip Tour',
      }}
    />
  );
};

export { TOUR_STORAGE_KEY };
export default ProductTour;
