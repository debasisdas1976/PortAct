import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
  Chip,
  CircularProgress,
  Alert,
  Card,
  CardContent,
  Grid,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Tooltip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  Refresh as RefreshIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Info as InfoIcon,
  Upload as UploadIcon,
} from '@mui/icons-material';
import axios from 'axios';

interface MutualFundHolding {
  id: number;
  stock_name: string;
  stock_symbol: string | null;
  isin: string | null;
  holding_percentage: number;
  holding_value: number;
  quantity_held: number;
  stock_current_price: number;
  sector: string | null;
  industry: string | null;
  market_cap: string | null;
}

interface MutualFundWithHoldings {
  asset_id: number;
  fund_name: string;
  fund_symbol: string | null;
  isin: string | null;
  units_held: number;
  current_nav: number;
  total_value: number;
  holdings: MutualFundHolding[];
  holdings_count: number;
  last_updated: string | null;
}

interface HoldingsDashboardStock {
  stock_name: string;
  stock_symbol: string | null;
  isin: string | null;
  direct_quantity: number;
  direct_value: number;
  direct_invested: number;
  mf_quantity: number;
  mf_value: number;
  mf_holding_percentage: number;
  mf_count: number;
  mutual_funds: string[];
  total_quantity: number;
  total_value: number;
  current_price: number;
  sector: string | null;
  industry: string | null;
  market_cap: string | null;
  profit_loss: number;
  profit_loss_percentage: number;
}

interface HoldingsDashboard {
  stocks: HoldingsDashboardStock[];
  summary: {
    total_stocks: number;
    total_direct_value: number;
    total_mf_value: number;
    total_value: number;
    stocks_with_direct_holdings: number;
    stocks_with_mf_holdings: number;
    stocks_with_both: number;
  };
  last_updated: string;
}

const MutualFundHoldings: React.FC = () => {
  const [mutualFunds, setMutualFunds] = useState<MutualFundWithHoldings[]>([]);
  const [dashboard, setDashboard] = useState<HoldingsDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [fetchingHoldings, setFetchingHoldings] = useState<number | null>(null);
  const [selectedStock, setSelectedStock] = useState<HoldingsDashboardStock | null>(null);
  const [view, setView] = useState<'funds' | 'dashboard'>('dashboard');
  const [uploadingFor, setUploadingFor] = useState<number | null>(null);
  const [uploadingConsolidatedFile, setUploadingConsolidatedFile] = useState(false);
  const [consolidatedFileResults, setConsolidatedFileResults] = useState<any>(null);
  const [showConsolidatedFileDialog, setShowConsolidatedFileDialog] = useState(false);
  const [fundMappingPreview, setFundMappingPreview] = useState<any>(null);
  const [showFundMappingDialog, setShowFundMappingDialog] = useState(false);
  const [confirmingImport, setConfirmingImport] = useState(false);

  const fetchMutualFunds = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get<MutualFundWithHoldings[]>(
        'http://localhost:8000/api/v1/mutual-fund-holdings/',
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      setMutualFunds(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch mutual funds');
    }
  };

  const fetchDashboard = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get<HoldingsDashboard>(
        'http://localhost:8000/api/v1/mutual-fund-holdings/dashboard/stocks',
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      setDashboard(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch dashboard');
    }
  };

  const fetchHoldingsForFund = async (assetId: number) => {
    setFetchingHoldings(assetId);
    try {
      const token = localStorage.getItem('token');
      await axios.post(
        `http://localhost:8000/api/v1/mutual-fund-holdings/${assetId}/fetch?force_refresh=true`,
        {},
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      await fetchMutualFunds();
      await fetchDashboard();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch holdings');
    } finally {
      setFetchingHoldings(null);
    }
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>, assetId: number) => {
    const file = event.target.files?.[0];
    if (file) {
      uploadCSV(assetId, file);
    }
  };

  const uploadCSV = async (assetId: number, file: File) => {
    setUploadingFor(assetId);
    try {
      const token = localStorage.getItem('token');
      const formData = new FormData();
      formData.append('file', file);

      await axios.post(
        `http://localhost:8000/api/v1/mutual-fund-holdings/${assetId}/upload-csv`,
        formData,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'multipart/form-data',
          },
        }
      );

      await fetchMutualFunds();
      await fetchDashboard();
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to upload CSV');
    } finally {
      setUploadingFor(null);
    }
  };


  const handleConsolidatedFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
      setError('Please upload an Excel file (.xlsx or .xls)');
      return;
    }

    setUploadingConsolidatedFile(true);
    setError(null);
    try {
      const token = localStorage.getItem('token');
      const formData = new FormData();
      formData.append('file', file);

      // Step 1: Get preview of fund mappings
      const response = await axios.post(
        'http://localhost:8000/api/v1/mutual-fund-holdings/preview-consolidated-file',
        formData,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'multipart/form-data',
          },
        }
      );
      
      // Show preview dialog for user to confirm mappings
      setFundMappingPreview(response.data);
      setShowFundMappingDialog(true);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to preview consolidated file');
    } finally {
      setUploadingConsolidatedFile(false);
      // Reset file input
      event.target.value = '';
    }
  };

  const handleConfirmImport = async () => {
    if (!fundMappingPreview) return;

    setConfirmingImport(true);
    setError(null);
    try {
      const token = localStorage.getItem('token');
      
      // Prepare confirmed mappings - collect ALL matching asset IDs for each fund
      const confirmedMappings = fundMappingPreview.mappings
        .filter((m: any) => m.matched_asset_id !== null)
        .map((m: any) => ({
          fund_name_from_excel: m.fund_name_from_excel,
          asset_ids: m.all_matched_asset_ids || [m.matched_asset_id],  // Use all matches if available
        }));

      // Step 2: Confirm import with mappings
      const response = await axios.post(
        'http://localhost:8000/api/v1/mutual-fund-holdings/confirm-consolidated-import',
        {
          temp_file_id: fundMappingPreview.temp_file_id,
          confirmed_mappings: confirmedMappings,
        },
        {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        }
      );
      
      // Close mapping dialog and show results
      setShowFundMappingDialog(false);
      setConsolidatedFileResults(response.data);
      setShowConsolidatedFileDialog(true);
      
      // Refresh data
      await fetchMutualFunds();
      await fetchDashboard();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to import consolidated file');
    } finally {
      setConfirmingImport(false);
    }
  };

  const handleCancelImport = () => {
    setShowFundMappingDialog(false);
    setFundMappingPreview(null);
  };

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([fetchMutualFunds(), fetchDashboard()]);
      setLoading(false);
    };
    loadData();
  }, []);

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(value);
  };

  const formatPercentage = (value: number) => {
    return `${value.toFixed(2)}%`;
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          Mutual Fund Holdings
        </Typography>
        <Box display="flex" gap={1}>
          <Button
            variant={view === 'dashboard' ? 'contained' : 'outlined'}
            onClick={() => setView('dashboard')}
          >
            Dashboard
          </Button>
          <Button
            variant={view === 'funds' ? 'contained' : 'outlined'}
            onClick={() => setView('funds')}
          >
            By Fund
          </Button>
          <Button
            variant="contained"
            color="success"
            component="label"
            startIcon={uploadingConsolidatedFile ? <CircularProgress size={20} color="inherit" /> : <UploadIcon />}
            disabled={uploadingConsolidatedFile}
          >
            {uploadingConsolidatedFile ? 'Uploading...' : 'Upload MF Holdings Excel'}
            <input
              type="file"
              hidden
              accept=".xlsx,.xls"
              onChange={handleConsolidatedFileUpload}
            />
          </Button>
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {view === 'dashboard' && dashboard && (
        <>
          {/* Summary Cards */}
          <Grid container spacing={3} sx={{ mb: 3 }}>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="textSecondary" gutterBottom>
                    Total Stocks
                  </Typography>
                  <Typography variant="h4">{dashboard.summary.total_stocks}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="textSecondary" gutterBottom>
                    Total Value
                  </Typography>
                  <Typography variant="h4">{formatCurrency(dashboard.summary.total_value)}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="textSecondary" gutterBottom>
                    Direct Holdings
                  </Typography>
                  <Typography variant="h4">{formatCurrency(dashboard.summary.total_direct_value)}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="textSecondary" gutterBottom>
                    MF Holdings
                  </Typography>
                  <Typography variant="h4">{formatCurrency(dashboard.summary.total_mf_value)}</Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          {/* Two Tables Side by Side */}
          <Grid container spacing={3}>
            {/* Top 20 MF Holdings */}
            <Grid item xs={12} md={6}>
              <Paper sx={{ height: '100%' }}>
                <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
                  <Typography variant="h6">Top 20 Stocks via Mutual Funds</Typography>
                  <Typography variant="caption" color="textSecondary">
                    Sorted by MF value
                  </Typography>
                </Box>
                <TableContainer sx={{ maxHeight: 600 }}>
                  <Table stickyHeader size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Stock</TableCell>
                        <TableCell align="right">MF Value</TableCell>
                        <TableCell align="center">MFs</TableCell>
                        <TableCell align="center">Details</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {dashboard.stocks
                        .filter(stock => stock.mf_value > 0)
                        .sort((a, b) => b.mf_value - a.mf_value)
                        .slice(0, 20)
                        .map((stock, index) => (
                          <TableRow key={index} hover>
                            <TableCell>
                              <Box>
                                <Typography variant="body2" fontWeight="medium">
                                  {stock.stock_name}
                                </Typography>
                                <Typography variant="caption" color="textSecondary">
                                  {stock.stock_symbol || '-'}
                                </Typography>
                              </Box>
                            </TableCell>
                            <TableCell align="right">
                              <Typography variant="body2" fontWeight="bold">
                                {formatCurrency(stock.mf_value)}
                              </Typography>
                              <Typography variant="caption" color="textSecondary">
                                {stock.mf_quantity.toFixed(2)} shares
                              </Typography>
                            </TableCell>
                            <TableCell align="center">
                              <Chip label={stock.mf_count} size="small" color="primary" />
                            </TableCell>
                            <TableCell align="center">
                              <IconButton size="small" onClick={() => setSelectedStock(stock)}>
                                <InfoIcon fontSize="small" />
                              </IconButton>
                            </TableCell>
                          </TableRow>
                        ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Paper>
            </Grid>

            {/* Top 20 Direct Holdings */}
            <Grid item xs={12} md={6}>
              <Paper sx={{ height: '100%' }}>
                <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
                  <Typography variant="h6">Top 20 Direct Stock Holdings</Typography>
                  <Typography variant="caption" color="textSecondary">
                    Sorted by direct value
                  </Typography>
                </Box>
                <TableContainer sx={{ maxHeight: 600 }}>
                  <Table stickyHeader size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Stock</TableCell>
                        <TableCell align="right">Direct Value</TableCell>
                        <TableCell align="right">P&L</TableCell>
                        <TableCell align="center">Details</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {dashboard.stocks
                        .filter(stock => stock.direct_value > 0)
                        .sort((a, b) => b.direct_value - a.direct_value)
                        .slice(0, 20)
                        .map((stock, index) => (
                          <TableRow key={index} hover>
                            <TableCell>
                              <Box>
                                <Typography variant="body2" fontWeight="medium">
                                  {stock.stock_name}
                                </Typography>
                                <Typography variant="caption" color="textSecondary">
                                  {stock.stock_symbol || '-'}
                                </Typography>
                              </Box>
                            </TableCell>
                            <TableCell align="right">
                              <Typography variant="body2" fontWeight="bold">
                                {formatCurrency(stock.direct_value)}
                              </Typography>
                              <Typography variant="caption" color="textSecondary">
                                {stock.direct_quantity.toFixed(2)} shares
                              </Typography>
                            </TableCell>
                            <TableCell align="right">
                              <Box display="flex" alignItems="center" justifyContent="flex-end">
                                {stock.profit_loss >= 0 ? (
                                  <TrendingUpIcon color="success" fontSize="small" />
                                ) : (
                                  <TrendingDownIcon color="error" fontSize="small" />
                                )}
                                <Box sx={{ ml: 0.5 }}>
                                  <Typography
                                    variant="body2"
                                    color={stock.profit_loss >= 0 ? 'success.main' : 'error.main'}
                                  >
                                    {formatCurrency(Math.abs(stock.profit_loss))}
                                  </Typography>
                                  <Typography
                                    variant="caption"
                                    color={stock.profit_loss >= 0 ? 'success.main' : 'error.main'}
                                  >
                                    ({formatPercentage(stock.profit_loss_percentage)})
                                  </Typography>
                                </Box>
                              </Box>
                            </TableCell>
                            <TableCell align="center">
                              <IconButton size="small" onClick={() => setSelectedStock(stock)}>
                                <InfoIcon fontSize="small" />
                              </IconButton>
                            </TableCell>
                          </TableRow>
                        ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Paper>
            </Grid>
          </Grid>
        </>
      )}

      {view === 'funds' && (
        <Box>
          {mutualFunds.length === 0 ? (
            <Alert severity="info">
              No mutual fund holdings found. Add mutual funds to your portfolio and fetch their holdings.
            </Alert>
          ) : (
            mutualFunds.map((fund) => (
              <Accordion key={fund.asset_id} sx={{ mb: 2 }}>
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Box display="flex" justifyContent="space-between" width="100%" alignItems="center" pr={2}>
                    <Box>
                      <Typography variant="h6">{fund.fund_name}</Typography>
                      <Typography variant="body2" color="textSecondary">
                        Units: {fund.units_held.toFixed(2)} | NAV: {formatCurrency(fund.current_nav)} | Value:{' '}
                        {formatCurrency(fund.total_value)}
                      </Typography>
                    </Box>
                    <Box display="flex" alignItems="center" gap={1}>
                      <Chip label={`${fund.holdings_count} stocks`} size="small" />
                      <Tooltip title="Upload CSV">
                        <IconButton
                          size="small"
                          component="label"
                          disabled={uploadingFor === fund.asset_id}
                          onClick={(e) => e.stopPropagation()}
                        >
                          {uploadingFor === fund.asset_id ? (
                            <CircularProgress size={20} />
                          ) : (
                            <UploadIcon />
                          )}
                          <input
                            type="file"
                            hidden
                            accept=".csv"
                            onChange={(e) => handleFileSelect(e, fund.asset_id)}
                          />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Fetch/Refresh Holdings (API)">
                        <IconButton
                          size="small"
                          onClick={(e) => {
                            e.stopPropagation();
                            fetchHoldingsForFund(fund.asset_id);
                          }}
                          disabled={fetchingHoldings === fund.asset_id}
                        >
                          {fetchingHoldings === fund.asset_id ? (
                            <CircularProgress size={20} />
                          ) : (
                            <RefreshIcon />
                          )}
                        </IconButton>
                      </Tooltip>
                    </Box>
                  </Box>
                </AccordionSummary>
                <AccordionDetails>
                  {fund.holdings.length === 0 ? (
                    <Alert severity="info">
                      No holdings data available. Upload a CSV file with portfolio holdings or click the refresh button to fetch from API (if available).
                    </Alert>
                  ) : (
                    <TableContainer>
                      <Table size="small">
                        <TableHead>
                          <TableRow>
                            <TableCell>Stock Name</TableCell>
                            <TableCell>Symbol</TableCell>
                            <TableCell align="right">Holding %</TableCell>
                            <TableCell align="right">Value</TableCell>
                            <TableCell align="right">Approx. Qty</TableCell>
                            <TableCell align="right">Price</TableCell>
                            <TableCell>Sector</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {fund.holdings.map((holding) => (
                            <TableRow key={holding.id}>
                              <TableCell>{holding.stock_name}</TableCell>
                              <TableCell>{holding.stock_symbol || '-'}</TableCell>
                              <TableCell align="right">{formatPercentage(holding.holding_percentage)}</TableCell>
                              <TableCell align="right">{formatCurrency(holding.holding_value)}</TableCell>
                              <TableCell align="right">{holding.quantity_held.toFixed(2)}</TableCell>
                              <TableCell align="right">{formatCurrency(holding.stock_current_price)}</TableCell>
                              <TableCell>{holding.sector || '-'}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </TableContainer>
                  )}
                </AccordionDetails>
              </Accordion>
            ))
          )}
        </Box>
      )}

      {/* Stock Details Dialog */}
      <Dialog open={!!selectedStock} onClose={() => setSelectedStock(null)} maxWidth="md" fullWidth>
        {selectedStock && (
          <>
            <DialogTitle>{selectedStock.stock_name}</DialogTitle>
            <DialogContent>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <Typography variant="subtitle2" color="textSecondary">
                    Symbol
                  </Typography>
                  <Typography variant="body1">{selectedStock.stock_symbol || 'N/A'}</Typography>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Typography variant="subtitle2" color="textSecondary">
                    Current Price
                  </Typography>
                  <Typography variant="body1">{formatCurrency(selectedStock.current_price)}</Typography>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Typography variant="subtitle2" color="textSecondary">
                    Sector
                  </Typography>
                  <Typography variant="body1">{selectedStock.sector || 'N/A'}</Typography>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Typography variant="subtitle2" color="textSecondary">
                    Market Cap
                  </Typography>
                  <Typography variant="body1">{selectedStock.market_cap || 'N/A'}</Typography>
                </Grid>
                <Grid item xs={12}>
                  <Typography variant="h6" sx={{ mt: 2, mb: 1 }}>
                    Holdings Breakdown
                  </Typography>
                </Grid>
                {selectedStock.direct_quantity > 0 && (
                  <>
                    <Grid item xs={12} sm={4}>
                      <Typography variant="subtitle2" color="textSecondary">
                        Direct Quantity
                      </Typography>
                      <Typography variant="body1">{selectedStock.direct_quantity.toFixed(2)}</Typography>
                    </Grid>
                    <Grid item xs={12} sm={4}>
                      <Typography variant="subtitle2" color="textSecondary">
                        Direct Value
                      </Typography>
                      <Typography variant="body1">{formatCurrency(selectedStock.direct_value)}</Typography>
                    </Grid>
                    <Grid item xs={12} sm={4}>
                      <Typography variant="subtitle2" color="textSecondary">
                        Direct Invested
                      </Typography>
                      <Typography variant="body1">{formatCurrency(selectedStock.direct_invested)}</Typography>
                    </Grid>
                  </>
                )}
                {selectedStock.mf_quantity > 0 && (
                  <>
                    <Grid item xs={12} sm={4}>
                      <Typography variant="subtitle2" color="textSecondary">
                        MF Quantity (Approx)
                      </Typography>
                      <Typography variant="body1">{selectedStock.mf_quantity.toFixed(2)}</Typography>
                    </Grid>
                    <Grid item xs={12} sm={4}>
                      <Typography variant="subtitle2" color="textSecondary">
                        MF Value
                      </Typography>
                      <Typography variant="body1">{formatCurrency(selectedStock.mf_value)}</Typography>
                    </Grid>
                    <Grid item xs={12} sm={4}>
                      <Typography variant="subtitle2" color="textSecondary">
                        Held in MFs
                      </Typography>
                      <Typography variant="body1">{selectedStock.mf_count}</Typography>
                    </Grid>
                    <Grid item xs={12}>
                      <Typography variant="subtitle2" color="textSecondary">
                        Mutual Funds
                      </Typography>
                      <Box sx={{ mt: 1 }}>
                        {selectedStock.mutual_funds.map((fund, idx) => (
                          <Chip key={idx} label={fund} size="small" sx={{ mr: 1, mb: 1 }} />
                        ))}
                      </Box>
                    </Grid>
                  </>
                )}
              </Grid>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setSelectedStock(null)}>Close</Button>
            </DialogActions>
          </>
        )}
      </Dialog>

      {/* Fund Mapping Preview Dialog */}
      <Dialog
        open={showFundMappingDialog}
        onClose={handleCancelImport}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>
          Review Fund Mappings
        </DialogTitle>
        <DialogContent>
          {fundMappingPreview && (
            <>
              <Alert severity="info" sx={{ mb: 2 }}>
                {fundMappingPreview.message}
              </Alert>
              
              <Grid container spacing={2} sx={{ mb: 3 }}>
                <Grid item xs={6}>
                  <Card>
                    <CardContent>
                      <Typography color="textSecondary" variant="body2">
                        Funds in Excel File
                      </Typography>
                      <Typography variant="h5">
                        {fundMappingPreview.total_funds_in_file}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={6}>
                  <Card>
                    <CardContent>
                      <Typography color="textSecondary" variant="body2">
                        Funds in Your Portfolio
                      </Typography>
                      <Typography variant="h5">
                        {fundMappingPreview.total_funds_in_portfolio}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>

              <Typography variant="h6" sx={{ mb: 2 }}>
                Fund Mappings
              </Typography>
              <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
                Review the automatic fund name matching below. Funds with high similarity scores (≥80%) will be imported automatically.
              </Typography>
              
              <TableContainer component={Paper} variant="outlined">
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Fund Name (from Excel)</TableCell>
                      <TableCell>Matched Fund (in Portfolio)</TableCell>
                      <TableCell align="center">Similarity</TableCell>
                      <TableCell align="center">Holdings</TableCell>
                      <TableCell align="center">Status</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {fundMappingPreview.mappings?.map((mapping: any, idx: number) => (
                      <TableRow key={idx}>
                        <TableCell>
                          <Typography variant="body2" fontWeight="medium">
                            {mapping.fund_name_from_excel}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          {mapping.matched_asset_name ? (
                            <Typography variant="body2">
                              {mapping.matched_asset_name}
                            </Typography>
                          ) : (
                            <Typography variant="body2" color="textSecondary">
                              No match found
                            </Typography>
                          )}
                        </TableCell>
                        <TableCell align="center">
                          <Chip
                            label={`${(mapping.similarity_score * 100).toFixed(0)}%`}
                            size="small"
                            color={
                              mapping.similarity_score >= 0.8
                                ? 'success'
                                : mapping.similarity_score >= 0.6
                                ? 'warning'
                                : 'error'
                            }
                          />
                        </TableCell>
                        <TableCell align="center">
                          <Typography variant="body2">
                            {mapping.holdings_count}
                          </Typography>
                        </TableCell>
                        <TableCell align="center">
                          {mapping.can_auto_import ? (
                            <Chip label="Will Import" size="small" color="success" />
                          ) : mapping.needs_confirmation ? (
                            <Chip label="Needs Review" size="small" color="warning" />
                          ) : (
                            <Chip label="Skip" size="small" color="default" />
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>

              <Alert severity="warning" sx={{ mt: 2 }}>
                <Typography variant="body2">
                  <strong>Note:</strong> Only funds with similarity ≥80% will be imported. 
                  Funds with lower similarity scores will be skipped to avoid incorrect mappings.
                </Typography>
              </Alert>
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCancelImport} disabled={confirmingImport}>
            Cancel
          </Button>
          <Button
            onClick={handleConfirmImport}
            variant="contained"
            color="primary"
            disabled={confirmingImport || !fundMappingPreview?.mappings?.some((m: any) => m.can_auto_import)}
            startIcon={confirmingImport ? <CircularProgress size={20} /> : null}
          >
            {confirmingImport ? 'Importing...' : 'Confirm & Import'}
          </Button>
        </DialogActions>
      </Dialog>


      {/* Consolidated File Upload Results Dialog */}
      <Dialog
        open={showConsolidatedFileDialog}
        onClose={() => setShowConsolidatedFileDialog(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          Consolidated File Import Results
        </DialogTitle>
        <DialogContent>
          {consolidatedFileResults && (
            <>
              <Alert
                severity={consolidatedFileResults.failed_imports === 0 ? 'success' : 'warning'}
                sx={{ mb: 2 }}
              >
                {consolidatedFileResults.message}
              </Alert>
              
              <Grid container spacing={2} sx={{ mb: 3 }}>
                <Grid item xs={3}>
                  <Card>
                    <CardContent>
                      <Typography color="textSecondary" variant="body2">
                        File
                      </Typography>
                      <Typography variant="body1" noWrap>
                        {consolidatedFileResults.filename}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={3}>
                  <Card>
                    <CardContent>
                      <Typography color="textSecondary" variant="body2">
                        Funds in File
                      </Typography>
                      <Typography variant="h5">
                        {consolidatedFileResults.total_funds_in_file}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={3}>
                  <Card>
                    <CardContent>
                      <Typography color="textSecondary" variant="body2">
                        Successful
                      </Typography>
                      <Typography variant="h5" color="success.main">
                        {consolidatedFileResults.successful_imports}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={3}>
                  <Card>
                    <CardContent>
                      <Typography color="textSecondary" variant="body2">
                        Failed
                      </Typography>
                      <Typography variant="h5" color="error.main">
                        {consolidatedFileResults.failed_imports}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>

              <Typography variant="h6" sx={{ mb: 2 }}>
                Details
              </Typography>
              
              <TableContainer component={Paper} variant="outlined">
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Fund Name (from Excel)</TableCell>
                      <TableCell>Matched Asset</TableCell>
                      <TableCell align="center">Similarity</TableCell>
                      <TableCell align="center">Status</TableCell>
                      <TableCell align="right">Holdings</TableCell>
                      <TableCell>Message</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {consolidatedFileResults.results?.map((result: any, idx: number) => (
                      <TableRow key={idx}>
                        <TableCell>{result.fund_name_from_excel}</TableCell>
                        <TableCell>
                          {result.matched_asset || '-'}
                        </TableCell>
                        <TableCell align="center">
                          {result.similarity_score ?
                            <Chip
                              label={`${(result.similarity_score * 100).toFixed(0)}%`}
                              size="small"
                              color={result.similarity_score >= 0.8 ? 'success' :
                                     result.similarity_score >= 0.6 ? 'warning' : 'default'}
                            /> : '-'
                          }
                        </TableCell>
                        <TableCell align="center">
                          <Chip
                            label={result.success ? 'Success' : 'Failed'}
                            color={result.success ? 'success' : 'error'}
                            size="small"
                          />
                        </TableCell>
                        <TableCell align="right">
                          {result.holdings_count || 0}
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" color="textSecondary">
                            {result.message}
                          </Typography>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowConsolidatedFileDialog(false)}>
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default MutualFundHoldings;

// Made with Bob
