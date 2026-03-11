import React from 'react';
import { Card, CardContent, Typography, Box } from '@mui/material';
import { TrendingUp, TrendingDown } from '@mui/icons-material';

interface DayChangeCardProps {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  assets: any[];
}

const DayChangeCard: React.FC<DayChangeCardProps> = ({ assets }) => {
  let weightedSum = 0;
  let weightTotal = 0;

  assets.forEach((a) => {
    const pct = a.details?.day_change_pct;
    const val = a.current_value || 0;
    if (pct != null && val > 0) {
      weightedSum += pct * val;
      weightTotal += val;
    }
  });

  const dayChangePct = weightTotal > 0 ? weightedSum / weightTotal : null;
  const dayChangeAbs = weightTotal > 0 ? weightedSum / 100 : null;
  const isPositive = (dayChangePct ?? 0) >= 0;

  const formatCurrency = (n: number) =>
    new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(n);

  return (
    <Card sx={{ width: '100%', height: '100%' }}>
      <CardContent>
        <Typography color="text.secondary" variant="body2" gutterBottom>
          Day Change
        </Typography>
        {dayChangePct != null ? (
          <Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <Typography
                variant="h5"
                color={isPositive ? 'success.main' : 'error.main'}
              >
                {isPositive ? '+' : ''}{dayChangePct.toFixed(2)}%
              </Typography>
              {isPositive ? (
                <TrendingUp sx={{ color: 'success.main' }} fontSize="small" />
              ) : (
                <TrendingDown sx={{ color: 'error.main' }} fontSize="small" />
              )}
            </Box>
            {dayChangeAbs != null && (
              <Typography variant="caption" color="text.secondary">
                {isPositive ? '+' : ''}{formatCurrency(dayChangeAbs)}
              </Typography>
            )}
          </Box>
        ) : (
          <Typography variant="body2" color="text.secondary">
            N/A
          </Typography>
        )}
      </CardContent>
    </Card>
  );
};

export default DayChangeCard;
