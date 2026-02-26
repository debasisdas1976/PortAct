import React from 'react';
import { Box, Typography, useTheme, useMediaQuery } from '@mui/material';
import {
  AccountBalance,
  Assessment,
  CloudUpload,
  Shield,
  TrendingUp,
} from '@mui/icons-material';

interface AuthLayoutProps {
  children: React.ReactNode;
}

const features = [
  {
    icon: <TrendingUp />,
    title: 'Multi-Asset Tracking',
    description: 'Stocks, mutual funds, crypto, real estate, and 20+ asset types in one place',
  },
  {
    icon: <CloudUpload />,
    title: 'Smart Statement Processing',
    description: 'Upload broker statements and auto-extract transactions with AI',
  },
  {
    icon: <Assessment />,
    title: 'Portfolio Analytics',
    description: 'Performance charts, gain/loss tracking, and trend analysis across all assets',
  },
  {
    icon: <AccountBalance />,
    title: 'Multi-Broker Support',
    description: 'Zerodha, ICICI Direct, NSDL, CDSL, and many more brokers supported',
  },
  {
    icon: <Shield />,
    title: 'Private & Secure',
    description: 'Self-hosted solution — your financial data stays on your own infrastructure',
  },
];

const AuthLayout: React.FC<AuthLayoutProps> = ({ children }) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', width: '100%' }}>
      {/* Left Panel - Hero */}
      {!isMobile && (
        <Box
          sx={{
            width: '55%',
            background: 'linear-gradient(135deg, #0F172A 0%, #1E293B 50%, #0F172A 100%)',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            p: 8,
            position: 'relative',
            overflow: 'hidden',
          }}
        >
          {/* Decorative circles */}
          <Box
            sx={{
              position: 'absolute',
              top: -80,
              right: -80,
              width: 320,
              height: 320,
              borderRadius: '50%',
              background: 'rgba(255,255,255,0.06)',
            }}
          />
          <Box
            sx={{
              position: 'absolute',
              bottom: -120,
              left: -120,
              width: 380,
              height: 380,
              borderRadius: '50%',
              background: 'rgba(255,255,255,0.04)',
            }}
          />
          <Box
            sx={{
              position: 'absolute',
              top: '50%',
              right: -40,
              width: 180,
              height: 180,
              borderRadius: '50%',
              background: 'rgba(255,255,255,0.05)',
            }}
          />
          <Box
            sx={{
              position: 'absolute',
              top: 60,
              left: 80,
              width: 100,
              height: 100,
              borderRadius: '50%',
              background: 'rgba(255,255,255,0.03)',
            }}
          />

          {/* Content */}
          <Box sx={{ position: 'relative', zIndex: 1, maxWidth: 520 }}>
            {/* Brand */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2.5, mb: 3 }}>
              <img
                src="/logo.png"
                alt="PortAct"
                width={120}
                height={120}
              />
              <Typography
                sx={{
                  color: 'white',
                  fontWeight: 800,
                  fontSize: '2.75rem',
                  letterSpacing: '-0.03em',
                }}
              >
                PortAct
              </Typography>
            </Box>

            {/* Tagline */}
            <Typography
              variant="h4"
              sx={{
                color: 'white',
                fontWeight: 600,
                mb: 1.5,
                lineHeight: 1.3,
                fontSize: '1.75rem',
              }}
            >
              Your complete portfolio tracker for every asset class
            </Typography>
            <Typography
              sx={{
                color: 'rgba(255,255,255,0.75)',
                fontSize: '1.05rem',
                mb: 5,
                lineHeight: 1.6,
                maxWidth: 440,
              }}
            >
              Track, analyze, and manage all your investments from a single dashboard.
              From equities to real estate, get a unified view of your net worth.
            </Typography>

            {/* Feature list */}
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
              {features.map((feature, index) => (
                <Box
                  key={index}
                  sx={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: 2,
                  }}
                >
                  <Box
                    sx={{
                      width: 42,
                      height: 42,
                      borderRadius: '12px',
                      background: 'rgba(255,255,255,0.12)',
                      backdropFilter: 'blur(4px)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                      '& svg': {
                        color: 'rgba(255,255,255,0.9)',
                        fontSize: 22,
                      },
                    }}
                  >
                    {feature.icon}
                  </Box>
                  <Box>
                    <Typography
                      sx={{
                        color: 'white',
                        fontWeight: 600,
                        fontSize: '0.95rem',
                        mb: 0.25,
                      }}
                    >
                      {feature.title}
                    </Typography>
                    <Typography
                      sx={{
                        color: 'rgba(255,255,255,0.6)',
                        fontSize: '0.85rem',
                        lineHeight: 1.5,
                      }}
                    >
                      {feature.description}
                    </Typography>
                  </Box>
                </Box>
              ))}
            </Box>
          </Box>
        </Box>
      )}

      {/* Right Panel - Form Area */}
      <Box
        sx={{
          width: isMobile ? '100%' : '45%',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          p: { xs: 3, sm: 4, md: 6 },
          bgcolor: 'background.default',
          minHeight: '100vh',
        }}
      >
        {/* Mobile-only branding header */}
        {isMobile && (
          <Box sx={{ mb: 4, textAlign: 'center' }}>
            <img
              src="/logo.png"
              alt="PortAct"
              width={110}
              height={110}
              style={{ marginBottom: 12 }}
            />
            <Typography
              variant="h4"
              sx={{
                color: theme.palette.primary.main,
                fontWeight: 700,
                letterSpacing: '-0.02em',
              }}
            >
              PortAct
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              Your complete portfolio tracker
            </Typography>
          </Box>
        )}

        <Box sx={{ width: '100%', maxWidth: 420 }}>
          {children}
        </Box>
      </Box>
    </Box>
  );
};

export default AuthLayout;
