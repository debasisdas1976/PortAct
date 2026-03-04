import React, { useEffect, useState } from 'react';
import { Card, CardContent, Typography, CircularProgress, Box, Tooltip } from '@mui/material';
import { dashboardAPI } from '../services/api';

interface XirrCardProps {
  assetType: string;
  portfolioId?: number | null;
}

const XirrCard: React.FC<XirrCardProps> = ({ assetType, portfolioId }) => {
  const [xirr, setXirr] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let cancelled = false;
    const fetchXirr = async () => {
      try {
        setLoading(true);
        const data = await dashboardAPI.getAssetTypeXirr(assetType, portfolioId);
        if (!cancelled) setXirr(data.xirr);
      } catch {
        if (!cancelled) setXirr(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    fetchXirr();
    return () => { cancelled = true; };
  }, [assetType, portfolioId]);

  return (
    <Card sx={{ width: '100%', height: '100%' }}>
      <CardContent>
        <Typography color="text.secondary" variant="body2" gutterBottom>
          XIRR (Annualized)
        </Typography>
        {loading ? (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <CircularProgress size={20} />
            <Typography variant="body2" color="text.secondary">Calculating...</Typography>
          </Box>
        ) : xirr != null ? (
          <Box>
            <Typography
              variant="h5"
              color={xirr >= 0 ? 'success.main' : 'error.main'}
            >
              {xirr >= 0 ? '+' : ''}{xirr.toFixed(2)}%
            </Typography>
            <Typography variant="caption" color="text.secondary">
              per annum
            </Typography>
          </Box>
        ) : (
          <Tooltip title="XIRR requires transaction history or purchase date with current value">
            <Typography variant="body2" color="text.secondary">
              N/A
            </Typography>
          </Tooltip>
        )}
      </CardContent>
    </Card>
  );
};

export default XirrCard;
