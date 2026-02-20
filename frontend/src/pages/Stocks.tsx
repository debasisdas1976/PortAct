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
  Alert,
} from '@mui/material';
import { TrendingUp, TrendingDown } from '@mui/icons-material';
import api from '../services/api';

interface StockAsset {
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

const buildDematLabel = (da: DematAccount) => {
  const parts: string[] = [String(da.broker_name), `(${da.account_id})`];
  if (da.account_holder_name) parts.push(`— ${da.account_holder_name}`);
  return parts.join(' ');
};

const Stocks: React.FC = () => {
  const [stocks, setStocks] = useState<StockAsset[]>([]);
  const [dematLabelMap, setDematLabelMap] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [assetsRes, dematRes] = await Promise.all([
          api.get('/assets/'),
          api.get('/demat-accounts/'),
        ]);
        const filtered = (assetsRes.data as StockAsset[]).filter(
          (a) => a.asset_type?.toLowerCase() === 'stock'
        );
        setStocks(filtered);

        const labelMap: Record<number, string> = {};
        for (const da of dematRes.data as DematAccount[]) {
          labelMap[da.id] = buildDematLabel(da);
        }
        setDematLabelMap(labelMap);
      } catch {
        setError('Failed to fetch stock holdings');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const totalInvested = stocks.reduce((s, a) => s + (a.total_invested || 0), 0);
  const totalValue = stocks.reduce((s, a) => s + (a.current_value || 0), 0);
  const totalPnL = totalValue - totalInvested;
  const totalPnLPct = totalInvested > 0 ? (totalPnL / totalInvested) * 100 : 0;

  // Group by demat_account_id (falls back to broker_name|account_id for unlinked assets)
  const groups: Record<string, StockAsset[]> = {};
  for (const stock of stocks) {
    const key = stock.demat_account_id != null
      ? String(stock.demat_account_id)
      : ([stock.broker_name, stock.account_id].filter(Boolean).join('|') || 'unlinked');
    if (!groups[key]) groups[key] = [];
    groups[key].push(stock);
  }

  const groupLabel = (groupAssets: StockAsset[]) => {
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
      <Typography variant="h4" gutterBottom>Indian Stocks</Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="body2">Holdings</Typography>
              <Typography variant="h4">{stocks.length}</Typography>
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
              <TableCell><strong>Stock</strong></TableCell>
              <TableCell align="right"><strong>Qty</strong></TableCell>
              <TableCell align="right"><strong>Avg Buy Price</strong></TableCell>
              <TableCell align="right"><strong>Current Price</strong></TableCell>
              <TableCell align="right"><strong>Invested</strong></TableCell>
              <TableCell align="right"><strong>Current Value</strong></TableCell>
              <TableCell align="right"><strong>P&L</strong></TableCell>
              <TableCell align="right"><strong>P&L %</strong></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {stocks.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} align="center">
                  <Typography color="text.secondary">No Indian stock holdings found.</Typography>
                </TableCell>
              </TableRow>
            ) : (
              Object.entries(groups).map(([key, groupStocks]) => {
                const gInvested = groupStocks.reduce((s, a) => s + (a.total_invested || 0), 0);
                const gValue = groupStocks.reduce((s, a) => s + (a.current_value || 0), 0);
                const gPnL = gValue - gInvested;
                return (
                  <React.Fragment key={key}>
                    {/* Account group header */}
                    <TableRow sx={{ bgcolor: 'action.hover' }}>
                      <TableCell colSpan={4}>
                        <Typography variant="subtitle2" fontWeight="bold">
                          {groupLabel(groupStocks)}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {groupStocks.length} holding{groupStocks.length !== 1 ? 's' : ''}
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
                    {/* Asset rows */}
                    {groupStocks.map((stock) => (
                      <TableRow key={stock.id} hover>
                        <TableCell>
                          <Typography variant="body2" fontWeight="medium">{stock.symbol}</Typography>
                          <Typography variant="caption" color="text.secondary">{stock.name}</Typography>
                        </TableCell>
                        <TableCell align="right">{stock.quantity?.toFixed(4)}</TableCell>
                        <TableCell align="right">{formatCurrency(stock.purchase_price)}</TableCell>
                        <TableCell align="right">{formatCurrency(stock.current_price)}</TableCell>
                        <TableCell align="right">{formatCurrency(stock.total_invested)}</TableCell>
                        <TableCell align="right">{formatCurrency(stock.current_value)}</TableCell>
                        <TableCell
                          align="right"
                          sx={{ color: stock.profit_loss >= 0 ? 'success.main' : 'error.main', fontWeight: 'medium' }}
                        >
                          {formatCurrency(stock.profit_loss)}
                        </TableCell>
                        <TableCell align="right">
                          <Chip
                            label={`${stock.profit_loss_percentage >= 0 ? '+' : ''}${stock.profit_loss_percentage?.toFixed(2)}%`}
                            color={stock.profit_loss_percentage >= 0 ? 'success' : 'error'}
                            size="small"
                            icon={stock.profit_loss_percentage >= 0 ? <TrendingUp /> : <TrendingDown />}
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

export default Stocks;

// Made with Bob
