import React, { useEffect, useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  CircularProgress,
  Grid,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
  Chip,
} from '@mui/material';
import { TrendingUp, TrendingDown } from '@mui/icons-material';
import api from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import { getErrorMessage } from '../utils/errorUtils';

interface MFAsset {
  id: number;
  name: string;
  symbol: string;
  quantity: number;
  purchase_price: number;
  current_price: number;
  total_invested: number;
  current_value: number;
  profit_loss: number;
  profit_loss_percentage: number;
  asset_type: string;
  demat_account_id?: number;
  broker_name?: string;
  account_id?: string;
  account_holder_name?: string;
}

interface DematAccount {
  id: number;
  broker_name: string;
  account_id: string;
  account_holder_name?: string;
  nickname?: string;
}

const formatCurrency = (value: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value);

const formatNav = (value: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 4 }).format(value);

const buildDematLabel = (da: DematAccount) => {
  const parts: string[] = [String(da.broker_name), `(${da.account_id})`];
  if (da.account_holder_name) parts.push(`— ${da.account_holder_name}`);
  return parts.join(' ');
};

const DebtFunds: React.FC = () => {
  const [funds, setFunds] = useState<MFAsset[]>([]);
  const [dematLabelMap, setDematLabelMap] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(true);
  const { notify } = useNotification();

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [assetsRes, dematRes] = await Promise.all([
          api.get('/assets/'),
          api.get('/demat-accounts/'),
        ]);
        const filtered = (assetsRes.data as MFAsset[]).filter(
          (a) => a.asset_type?.toLowerCase() === 'debt_mutual_fund'
        );
        setFunds(filtered);

        const labelMap: Record<number, string> = {};
        for (const da of dematRes.data as DematAccount[]) {
          labelMap[da.id] = buildDematLabel(da);
        }
        setDematLabelMap(labelMap);
      } catch (err) {
        notify.error(getErrorMessage(err, 'Failed to load data'));
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const totalInvested = funds.reduce((s, a) => s + (a.total_invested || 0), 0);
  const totalValue = funds.reduce((s, a) => s + (a.current_value || 0), 0);
  const totalPnL = totalValue - totalInvested;
  const totalPnLPct = totalInvested > 0 ? (totalPnL / totalInvested) * 100 : 0;

  // Group by demat_account_id (falls back to broker_name|account_id for unlinked assets)
  const groups: Record<string, MFAsset[]> = {};
  for (const fund of funds) {
    const key = fund.demat_account_id != null
      ? String(fund.demat_account_id)
      : ([fund.broker_name, fund.account_id].filter(Boolean).join('|') || 'unlinked');
    if (!groups[key]) groups[key] = [];
    groups[key].push(fund);
  }

  const groupLabel = (groupAssets: MFAsset[]) => {
    const first = groupAssets[0];
    if (first.demat_account_id != null && dematLabelMap[first.demat_account_id]) {
      return dematLabelMap[first.demat_account_id];
    }
    const parts: string[] = [];
    if (first.broker_name) parts.push(first.broker_name);
    if (first.account_id) parts.push(`(${first.account_id})`);
    if (first.account_holder_name) parts.push(`— ${first.account_holder_name}`);
    return parts.length ? parts.join(' ') : 'Unlinked Holdings';
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '40vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>Debt Mutual Funds</Typography>

      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="body2">Funds</Typography>
              <Typography variant="h4">{funds.length}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="body2">Current Value</Typography>
              <Typography variant="h5">{formatCurrency(totalValue)}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="body2">Total Invested</Typography>
              <Typography variant="h5">{formatCurrency(totalInvested)}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="body2">Total P&L</Typography>
              <Typography variant="h5" color={totalPnL >= 0 ? 'success.main' : 'error.main'}>
                {formatCurrency(totalPnL)}
              </Typography>
              <Typography variant="body2" color={totalPnL >= 0 ? 'success.main' : 'error.main'}>
                {totalPnL >= 0 ? '+' : ''}{totalPnLPct.toFixed(2)}%
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell><strong>Fund</strong></TableCell>
              <TableCell align="right"><strong>Units</strong></TableCell>
              <TableCell align="right"><strong>Avg NAV</strong></TableCell>
              <TableCell align="right"><strong>Current NAV</strong></TableCell>
              <TableCell align="right"><strong>Invested</strong></TableCell>
              <TableCell align="right"><strong>Current Value</strong></TableCell>
              <TableCell align="right"><strong>P&L</strong></TableCell>
              <TableCell align="right"><strong>P&L %</strong></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {funds.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} align="center">
                  <Typography color="text.secondary">No debt mutual fund holdings found.</Typography>
                </TableCell>
              </TableRow>
            ) : (
              Object.entries(groups).map(([key, groupFunds]) => {
                const gInvested = groupFunds.reduce((s, a) => s + (a.total_invested || 0), 0);
                const gValue = groupFunds.reduce((s, a) => s + (a.current_value || 0), 0);
                const gPnL = gValue - gInvested;
                return (
                  <React.Fragment key={key}>
                    {/* Account group header */}
                    <TableRow sx={{ bgcolor: 'action.hover' }}>
                      <TableCell colSpan={4}>
                        <Typography variant="subtitle2" fontWeight="bold">
                          {groupLabel(groupFunds)}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {groupFunds.length} fund{groupFunds.length !== 1 ? 's' : ''}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="caption" color="text.secondary">Invested</Typography>
                        <Typography variant="body2" fontWeight="medium">{formatCurrency(gInvested)}</Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="caption" color="text.secondary">Value</Typography>
                        <Typography variant="body2" fontWeight="medium">{formatCurrency(gValue)}</Typography>
                      </TableCell>
                      <TableCell align="right" colSpan={2}>
                        <Typography variant="caption" color="text.secondary">P&L</Typography>
                        <Typography variant="body2" fontWeight="medium" color={gPnL >= 0 ? 'success.main' : 'error.main'}>
                          {formatCurrency(gPnL)}
                        </Typography>
                      </TableCell>
                    </TableRow>
                    {/* Fund rows */}
                    {groupFunds.map((fund) => (
                      <TableRow key={fund.id} hover>
                        <TableCell>
                          <Typography variant="body2" fontWeight="medium">{fund.name}</Typography>
                          {fund.symbol && (
                            <Typography variant="caption" color="text.secondary">{fund.symbol}</Typography>
                          )}
                        </TableCell>
                        <TableCell align="right">{fund.quantity?.toFixed(4)}</TableCell>
                        <TableCell align="right">{formatNav(fund.purchase_price)}</TableCell>
                        <TableCell align="right">{formatNav(fund.current_price)}</TableCell>
                        <TableCell align="right">{formatCurrency(fund.total_invested)}</TableCell>
                        <TableCell align="right">{formatCurrency(fund.current_value)}</TableCell>
                        <TableCell
                          align="right"
                          sx={{ color: fund.profit_loss >= 0 ? 'success.main' : 'error.main', fontWeight: 'medium' }}
                        >
                          {formatCurrency(fund.profit_loss)}
                        </TableCell>
                        <TableCell align="right">
                          <Chip
                            label={`${fund.profit_loss_percentage >= 0 ? '+' : ''}${fund.profit_loss_percentage?.toFixed(2)}%`}
                            color={fund.profit_loss_percentage >= 0 ? 'success' : 'error'}
                            size="small"
                            icon={fund.profit_loss_percentage >= 0 ? <TrendingUp /> : <TrendingDown />}
                          />
                        </TableCell>
                      </TableRow>
                    ))}
                  </React.Fragment>
                );
              })
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default DebtFunds;

// Made with Bob
