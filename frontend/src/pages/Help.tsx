import React, { useState } from 'react';
import {
  Box,
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Alert,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Divider,
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  RocketLaunch as GettingStartedIcon,
  Dashboard as DashboardIcon,
  AccountBalance as AssetsIcon,
  ShowChart as DematIcon,
  Receipt as BankStatementIcon,
  PieChart as MutualFundIcon,
  CloudUpload as UploadIcon,
  BarChart as ExpenseIcon,
  AdminPanelSettings as AdminIcon,
  Notifications as AlertsIcon,
  Settings as SettingsIcon,
  Lightbulb as TipsIcon,
  HelpOutline as FAQIcon,
  CheckCircle as CheckIcon,
} from '@mui/icons-material';

const Help: React.FC = () => {
  const [expanded, setExpanded] = useState<string | false>('getting-started');

  const handleChange = (panel: string) => (_event: React.SyntheticEvent, isExpanded: boolean) => {
    setExpanded(isExpanded ? panel : false);
  };

  const sectionSx = { mb: 1 };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Help & User Guide
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        Welcome to PortAct — your personal portfolio tracker. This guide covers all features
        of the application to help you get the most out of it.
      </Typography>

      {/* ─── Section 1: Getting Started ─── */}
      <Accordion expanded={expanded === 'getting-started'} onChange={handleChange('getting-started')} sx={sectionSx}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Box display="flex" alignItems="center" gap={1}>
            <GettingStartedIcon color="primary" />
            <Typography variant="h6">Getting Started</Typography>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <Alert severity="info" sx={{ mb: 2 }}>
            Follow these steps to set up your portfolio for the first time. You can always come back and add more data later.
          </Alert>

          <List>
            <ListItem alignItems="flex-start">
              <ListItemIcon><CheckIcon color="primary" /></ListItemIcon>
              <ListItemText
                primary="1. Complete your profile"
                secondary="Navigate to Administration > Application Setup. Fill in your personal details. If you are employed, fill in the Employment & Salary tab — this enables automatic PF and Gratuity calculations."
              />
            </ListItem>
            <Divider component="li" />
            <ListItem alignItems="flex-start">
              <ListItemIcon><CheckIcon color="primary" /></ListItemIcon>
              <ListItemText
                primary="2. Add your bank accounts"
                secondary="Go to Assets > Banking > Savings or use the Bank Accounts section. Add each bank account (savings, current, credit card) with the current balance. This tracks your liquid assets."
              />
            </ListItem>
            <Divider component="li" />
            <ListItem alignItems="flex-start">
              <ListItemIcon><CheckIcon color="primary" /></ListItemIcon>
              <ListItemText
                primary="3. Set up demat accounts"
                secondary="Go to Assets > Demat Holding > Demat Accounts. Add your brokerage accounts (Zerodha, Groww, ICICI Direct, Angel One, etc.) with their account IDs and cash balances."
              />
            </ListItem>
            <Divider component="li" />
            <ListItem alignItems="flex-start">
              <ListItemIcon><CheckIcon color="primary" /></ListItemIcon>
              <ListItemText
                primary="4. Upload investment statements"
                secondary="Go to the Statements page from the sidebar. Upload broker statements, NSDL CAS, or individual investment statements (PPF, NPS, PF, SSY) to auto-import your holdings with quantities, prices, and transaction history."
              />
            </ListItem>
            <Divider component="li" />
            <ListItem alignItems="flex-start">
              <ListItemIcon><CheckIcon color="primary" /></ListItemIcon>
              <ListItemText
                primary="5. Upload bank statements"
                secondary="From the Bank Accounts page, upload PDF or Excel bank statements to import transactions automatically. Supports ICICI, HDFC, IDFC First, and SBI. This powers the Expense Management features."
              />
            </ListItem>
            <Divider component="li" />
            <ListItem alignItems="flex-start">
              <ListItemIcon><CheckIcon color="primary" /></ListItemIcon>
              <ListItemText
                primary="6. Import mutual fund holdings"
                secondary="From the Mutual Fund Holdings page, upload a consolidated Excel file or individual CSVs, or use the API fetch button to pull holdings data. This shows your stock-level exposure across all mutual funds."
              />
            </ListItem>
            <Divider component="li" />
            <ListItem alignItems="flex-start">
              <ListItemIcon><CheckIcon color="primary" /></ListItemIcon>
              <ListItemText
                primary="7. Review your Dashboard"
                secondary="Visit the Dashboard to see your total portfolio value, asset allocation, performance charts, and profit/loss breakdown. The Dashboard combines all your assets, bank accounts, and demat cash balances."
              />
            </ListItem>
            <Divider component="li" />
            <ListItem alignItems="flex-start">
              <ListItemIcon><CheckIcon color="primary" /></ListItemIcon>
              <ListItemText
                primary="8. Configure schedulers"
                secondary="Go to Administration > Application Setup > Application Settings tab. Adjust the price update frequency, EOD snapshot time, and news alert schedules. Prices update automatically every 30 minutes by default."
              />
            </ListItem>
          </List>
        </AccordionDetails>
      </Accordion>

      {/* ─── Section 2: Dashboard & Overview ─── */}
      <Accordion expanded={expanded === 'dashboard'} onChange={handleChange('dashboard')} sx={sectionSx}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Box display="flex" alignItems="center" gap={1}>
            <DashboardIcon color="primary" />
            <Typography variant="h6">Dashboard & Overview</Typography>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>Summary Cards</Typography>
          <Typography variant="body2" paragraph>
            The Dashboard displays four summary cards at the top:
          </Typography>
          <List dense>
            <ListItem>
              <ListItemText
                primary="Total Value"
                secondary="Combined value of all portfolio assets + bank account balances + demat cash. Shows overall return percentage."
              />
            </ListItem>
            <ListItem>
              <ListItemText
                primary="Total Investment"
                secondary="Total amount invested across all assets plus bank balances."
              />
            </ListItem>
            <ListItem>
              <ListItemText
                primary="Total Gain/Loss"
                secondary="Difference between current value and total investment. Shown in green (profit) or red (loss) with percentage."
              />
            </ListItem>
            <ListItem>
              <ListItemText
                primary="Total Assets"
                secondary="Count of all portfolio assets plus bank accounts."
              />
            </ListItem>
          </List>

          <Divider sx={{ my: 2 }} />

          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>Hide / Show Numbers</Typography>
          <Typography variant="body2" paragraph>
            Click the eye icon in the top-right corner of the Dashboard to mask all financial figures with dots. This is useful when sharing your screen or working in a public place. Click again to reveal the numbers.
          </Typography>

          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>Performance Chart</Typography>
          <Typography variant="body2" paragraph>
            The Portfolio Performance chart shows your portfolio value over time. You can switch between Portfolio-wide and Individual Asset views, and select time periods (7D, 30D, 90D, 6M, 1Y). This chart is powered by End-of-Day (EOD) snapshots captured daily at 7 PM IST (configurable in Settings). Historical data builds up over time as the daily scheduler runs.
          </Typography>

          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>Asset Allocation</Typography>
          <Typography variant="body2" paragraph>
            The pie chart shows the distribution of your portfolio across asset types. Below it, a detailed table shows each asset type with current value, invested amount, gain/loss, return percentage, and allocation percentage.
          </Typography>

          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>Portfolio Value Over Time</Typography>
          <Typography variant="body2" paragraph>
            A line chart at the bottom shows portfolio value vs. invested amount over 90 days. Both lines help you visualize whether your portfolio is growing above or below your investment baseline.
          </Typography>
        </AccordionDetails>
      </Accordion>

      {/* ─── Section 3: Managing Assets ─── */}
      <Accordion expanded={expanded === 'managing-assets'} onChange={handleChange('managing-assets')} sx={sectionSx}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Box display="flex" alignItems="center" gap={1}>
            <AssetsIcon color="primary" />
            <Typography variant="h6">Managing Assets</Typography>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <Typography variant="body2" paragraph>
            PortAct supports over 30 asset types organized into 8 categories. Assets can be added manually from their respective pages or imported automatically via statement uploads.
          </Typography>

          <TableContainer component={Paper} variant="outlined" sx={{ mb: 2 }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell><strong>Category</strong></TableCell>
                  <TableCell><strong>Asset Types</strong></TableCell>
                  <TableCell><strong>How to Add</strong></TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                <TableRow>
                  <TableCell>Demat Holdings</TableCell>
                  <TableCell>Stocks, US Stocks, Equity MF, Debt Funds, Commodities, Sovereign Gold Bonds</TableCell>
                  <TableCell>Upload broker/demat statement or add manually</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Banking</TableCell>
                  <TableCell>Savings, Fixed Deposit, Recurring Deposit</TableCell>
                  <TableCell>Add via respective pages under Banking</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Retirement Savings</TableCell>
                  <TableCell>PPF, PF/EPF, NPS, SSY, Gratuity, Insurance</TableCell>
                  <TableCell>Upload statements (PPF, NPS, PF, SSY) or add manually</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Crypto</TableCell>
                  <TableCell>Crypto Accounts</TableCell>
                  <TableCell>Add via Crypto Accounts page</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Post Office Schemes</TableCell>
                  <TableCell>NSC, KVP, SCSS, MIS</TableCell>
                  <TableCell>Add manually via each page</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Bonds</TableCell>
                  <TableCell>Corporate Bond, RBI Bond, Tax Saving Bond</TableCell>
                  <TableCell>Add manually via each page</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>REITs / InvITs</TableCell>
                  <TableCell>REITs, InvITs</TableCell>
                  <TableCell>Add manually via each page</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Real Estate</TableCell>
                  <TableCell>Land, Farm Land, House</TableCell>
                  <TableCell>Add manually via each page</TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </TableContainer>

          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>Assets Overview Page</Typography>
          <Typography variant="body2" paragraph>
            The Assets page (sidebar: Assets &gt; Overview) shows a consolidated view of all your assets. You can filter by asset type, add new assets, edit existing ones, delete assets, and manually trigger price updates.
          </Typography>

          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>Automatic Price Updates</Typography>
          <Typography variant="body2" paragraph>
            Stocks, mutual funds, crypto, commodities, and US stocks get their prices updated automatically by a background scheduler. The default interval is every 30 minutes. You can change this in Application Settings. You can also manually refresh prices using the "Update All Prices" button on the Assets page.
          </Typography>

          <Alert severity="info" sx={{ mt: 1 }}>
            For best accuracy, upload statements from your brokers and banks rather than entering data manually. Statement parsing automatically extracts quantities, prices, and transaction history.
          </Alert>
        </AccordionDetails>
      </Accordion>

      {/* ─── Section 4: Demat Account Management ─── */}
      <Accordion expanded={expanded === 'demat-accounts'} onChange={handleChange('demat-accounts')} sx={sectionSx}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Box display="flex" alignItems="center" gap={1}>
            <DematIcon color="primary" />
            <Typography variant="h6">Demat Account Management</Typography>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>What Are Demat Accounts in PortAct?</Typography>
          <Typography variant="body2" paragraph>
            Demat accounts represent your brokerage/trading accounts. They hold your stocks, mutual funds, ETFs, and other market-linked securities. Each demat account tracks its own cash balance and linked assets.
          </Typography>

          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>Adding a Demat Account</Typography>
          <Typography variant="body2" paragraph>
            Navigate to Assets &gt; Demat Holding &gt; Demat Accounts and click "Add Account". Enter the broker name, account ID, account holder name, and current cash balance.
          </Typography>

          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>Supported Brokers</Typography>
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 2 }}>
            {['Zerodha', 'ICICI Direct', 'Groww', 'Upstox', 'Angel One', 'Vested (US)', 'INDMoney (US)'].map((broker) => (
              <Chip key={broker} label={broker} size="small" variant="outlined" />
            ))}
          </Box>

          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>Uploading Broker Statements</Typography>
          <Typography variant="body2" paragraph>
            You can upload broker-specific statements (NSDL CAS, individual broker statements) from the Statements page. Select the correct broker and statement type; the parser will extract holdings and link them to the appropriate demat account.
          </Typography>

          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>Cash Balance</Typography>
          <Typography variant="body2" paragraph>
            Uninvested cash in your demat/trading accounts is tracked separately and included in the Dashboard's total portfolio value. Update this periodically to keep your total net worth accurate.
          </Typography>
        </AccordionDetails>
      </Accordion>

      {/* ─── Section 5: Bank Statement Import ─── */}
      <Accordion expanded={expanded === 'bank-statements'} onChange={handleChange('bank-statements')} sx={sectionSx}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Box display="flex" alignItems="center" gap={1}>
            <BankStatementIcon color="primary" />
            <Typography variant="h6">Bank Statement Import</Typography>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <Typography variant="body2" paragraph>
            PortAct can parse bank statements from supported banks and automatically import transactions for expense tracking and balance reconciliation.
          </Typography>

          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>Supported Banks & Formats</Typography>
          <TableContainer component={Paper} variant="outlined" sx={{ mb: 2 }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell><strong>Bank</strong></TableCell>
                  <TableCell align="center"><strong>PDF</strong></TableCell>
                  <TableCell align="center"><strong>Excel</strong></TableCell>
                  <TableCell align="center"><strong>Credit Card</strong></TableCell>
                  <TableCell><strong>Notes</strong></TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                <TableRow>
                  <TableCell>ICICI Bank</TableCell>
                  <TableCell align="center"><Chip label="Yes" size="small" color="success" /></TableCell>
                  <TableCell align="center"><Chip label="Yes" size="small" color="success" /></TableCell>
                  <TableCell align="center"><Chip label="Yes" size="small" color="success" /></TableCell>
                  <TableCell>Password may be required for some PDFs</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>HDFC Bank</TableCell>
                  <TableCell align="center"><Chip label="Yes" size="small" color="success" /></TableCell>
                  <TableCell align="center"><Chip label="Yes" size="small" color="success" /></TableCell>
                  <TableCell align="center"><Chip label="No" size="small" color="default" /></TableCell>
                  <TableCell>Supports multiple statement formats</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>IDFC First Bank</TableCell>
                  <TableCell align="center"><Chip label="Yes" size="small" color="success" /></TableCell>
                  <TableCell align="center"><Chip label="Yes" size="small" color="success" /></TableCell>
                  <TableCell align="center"><Chip label="Yes" size="small" color="success" /></TableCell>
                  <TableCell>Credit card statements supported</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>SBI</TableCell>
                  <TableCell align="center"><Chip label="Yes" size="small" color="success" /></TableCell>
                  <TableCell align="center"><Chip label="No" size="small" color="default" /></TableCell>
                  <TableCell align="center"><Chip label="No" size="small" color="default" /></TableCell>
                  <TableCell>PDF password always required</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Scapia</TableCell>
                  <TableCell align="center"><Chip label="No" size="small" color="default" /></TableCell>
                  <TableCell align="center"><Chip label="No" size="small" color="default" /></TableCell>
                  <TableCell align="center"><Chip label="Yes" size="small" color="success" /></TableCell>
                  <TableCell>Credit card PDF statements only</TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </TableContainer>

          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>How to Upload</Typography>
          <List dense>
            <ListItem><ListItemText primary="1. Go to the Bank Accounts page" /></ListItem>
            <ListItem><ListItemText primary="2. Click 'Upload Statement'" /></ListItem>
            <ListItem><ListItemText primary="3. Select the bank account from the dropdown" /></ListItem>
            <ListItem><ListItemText primary="4. Choose the statement file (PDF or Excel)" /></ListItem>
            <ListItem><ListItemText primary="5. Enter the PDF password if prompted (required for SBI, some ICICI PDFs)" /></ListItem>
            <ListItem><ListItemText primary="6. Click Upload" /></ListItem>
          </List>

          <Typography variant="subtitle1" fontWeight="bold" gutterBottom sx={{ mt: 1 }}>After Upload</Typography>
          <Typography variant="body2" paragraph>
            The system shows a summary of imported transactions, duplicates skipped, and auto-categorized count. Bank account balance is recalculated automatically. Transactions appear in the Expenses section for expense tracking.
          </Typography>

          <Alert severity="info">
            Download statements directly from your bank's netbanking portal in PDF or Excel format. Ensure it is the complete transaction statement (not a mini-statement). For best results, upload the most recent 3-6 months. Duplicate transactions (same date, amount, description) are automatically skipped.
          </Alert>
        </AccordionDetails>
      </Accordion>

      {/* ─── Section 6: Mutual Fund Holdings ─── */}
      <Accordion expanded={expanded === 'mutual-fund-holdings'} onChange={handleChange('mutual-fund-holdings')} sx={sectionSx}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Box display="flex" alignItems="center" gap={1}>
            <MutualFundIcon color="primary" />
            <Typography variant="h6">Mutual Fund Holdings</Typography>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <Typography variant="body2" paragraph>
            The Mutual Fund Holdings page shows the individual stock holdings within each of your mutual funds. It also provides a consolidated dashboard showing your total exposure to each stock across both direct holdings and mutual funds.
          </Typography>

          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>Three Import Methods</Typography>

          <Typography variant="subtitle2" fontWeight="bold" sx={{ mt: 1 }}>Method 1: Consolidated Excel Upload (Recommended)</Typography>
          <Typography variant="body2" paragraph>
            Click the "Upload MF Holdings Excel" button at the top of the page. Upload an Excel file (.xlsx/.xls) containing fund names with their stock holdings. The system automatically matches fund names from the Excel file with your portfolio's mutual fund assets using fuzzy string matching. Review the mapping preview — similarity scores are shown as green (&ge;80%), yellow (&ge;60%), or red (&lt;60%). Only funds with &ge;80% similarity are imported to avoid incorrect matches.
          </Typography>

          <Typography variant="subtitle2" fontWeight="bold">Method 2: Individual CSV Upload</Typography>
          <Typography variant="body2" paragraph>
            Switch to the "By Fund" view. Expand a mutual fund, then click the upload icon next to it. Upload a CSV file containing that specific fund's stock holdings.
          </Typography>

          <Typography variant="subtitle2" fontWeight="bold">Method 3: API Fetch</Typography>
          <Typography variant="body2" paragraph>
            In the "By Fund" view, click the refresh icon next to a fund. This fetches holdings data from an external API. Availability depends on the fund house.
          </Typography>

          <Divider sx={{ my: 2 }} />

          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>Dashboard View</Typography>
          <Typography variant="body2" paragraph>
            The default Dashboard view shows two side-by-side tables: "Top 20 Stocks via Mutual Funds" (sorted by MF value) and "Top 20 Direct Stock Holdings" (sorted by direct value). Click the info icon on any stock to see its complete breakdown — direct quantity, MF exposure, which mutual funds hold it, and total combined value.
          </Typography>

          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>By Fund View</Typography>
          <Typography variant="body2" paragraph>
            Switch to the "By Fund" tab to see expandable accordions for each mutual fund. Each fund shows its individual stock holdings with holding percentage, value, approximate quantity, current price, and sector.
          </Typography>
        </AccordionDetails>
      </Accordion>

      {/* ─── Section 7: Investment Statement Upload ─── */}
      <Accordion expanded={expanded === 'investment-statements'} onChange={handleChange('investment-statements')} sx={sectionSx}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Box display="flex" alignItems="center" gap={1}>
            <UploadIcon color="primary" />
            <Typography variant="h6">Investment Statement Upload</Typography>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <Typography variant="body2" paragraph>
            Beyond bank statements, PortAct supports uploading statements for various retirement and government savings schemes. Uploaded statements are automatically parsed to extract account details, transactions, and balances.
          </Typography>

          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>Supported Statement Types</Typography>
          <TableContainer component={Paper} variant="outlined" sx={{ mb: 2 }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell><strong>Statement Type</strong></TableCell>
                  <TableCell><strong>What It Parses</strong></TableCell>
                  <TableCell><strong>Source</strong></TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                <TableRow>
                  <TableCell>PPF Statement</TableCell>
                  <TableCell>Account balance, deposits, interest, transaction history</TableCell>
                  <TableCell>Bank passbook or online statement</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>SSY Statement</TableCell>
                  <TableCell>Account balance, deposits, interest history</TableCell>
                  <TableCell>Bank or Post Office</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>NPS Statement</TableCell>
                  <TableCell>Tier 1/2 holdings, NAV, contributions</TableCell>
                  <TableCell>CRA (NSDL, Karvy, Protean)</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>PF/EPF Statement</TableCell>
                  <TableCell>Employee + employer contributions, interest</TableCell>
                  <TableCell>EPFO passbook</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Broker Statement</TableCell>
                  <TableCell>Stock holdings, quantities, prices</TableCell>
                  <TableCell>Zerodha, ICICI Direct, Groww, etc.</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Mutual Fund Statement</TableCell>
                  <TableCell>Fund holdings, units, NAV</TableCell>
                  <TableCell>NSDL CAS, broker statements</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Vested Statement</TableCell>
                  <TableCell>US stock holdings, cost basis</TableCell>
                  <TableCell>Vested platform</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>INDMoney Statement</TableCell>
                  <TableCell>US stock holdings</TableCell>
                  <TableCell>INDMoney platform</TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </TableContainer>

          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>How to Upload</Typography>
          <List dense>
            <ListItem><ListItemText primary="1. Go to the Statements page from the sidebar" /></ListItem>
            <ListItem><ListItemText primary="2. Click 'Upload Statement'" /></ListItem>
            <ListItem><ListItemText primary="3. Select the institution/broker and statement type" /></ListItem>
            <ListItem><ListItemText primary="4. Attach the file (PDF, CSV, or Excel)" /></ListItem>
            <ListItem><ListItemText primary="5. Provide the PDF password if the file is password-protected" /></ListItem>
            <ListItem><ListItemText primary="6. Click Upload" /></ListItem>
          </List>

          <Typography variant="subtitle1" fontWeight="bold" gutterBottom sx={{ mt: 1 }}>Processing Status</Typography>
          <Typography variant="body2" paragraph>
            After upload, the statement status transitions from "Processing" to "Processed" or "Failed". Successfully processed statements create assets and transactions that appear on their respective pages automatically.
          </Typography>

          <Alert severity="warning">
            Deleting an uploaded statement also deletes all assets and transactions that were imported from it. Use this with caution and consider taking a JSON backup first.
          </Alert>
        </AccordionDetails>
      </Accordion>

      {/* ─── Section 8: Expense Management ─── */}
      <Accordion expanded={expanded === 'expense-management'} onChange={handleChange('expense-management')} sx={sectionSx}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Box display="flex" alignItems="center" gap={1}>
            <ExpenseIcon color="primary" />
            <Typography variant="h6">Expense Management</Typography>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <Typography variant="body2" paragraph>
            PortAct includes a full expense tracking system with auto-import from bank statements and visual analytics.
          </Typography>

          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>Three Pages</Typography>

          <Typography variant="subtitle2" fontWeight="bold" sx={{ mt: 1 }}>Expense Dashboard</Typography>
          <Typography variant="body2" paragraph>
            Visual analytics showing spending patterns. View monthly expense trends, category-wise breakdowns (pie chart), and spending over time. Use date range filters and toggle between monthly and weekly views.
          </Typography>

          <Typography variant="subtitle2" fontWeight="bold">Expenses</Typography>
          <Typography variant="body2" paragraph>
            Detailed transaction list with advanced filtering by date range, category, bank account, amount range, and payment method. Sort by date, amount, merchant, or category. Search by description, merchant name, or reference number. Each transaction can be manually re-categorized or deleted.
          </Typography>

          <Typography variant="subtitle2" fontWeight="bold">Categories</Typography>
          <Typography variant="body2" paragraph>
            Manage expense categories. The system comes with default categories, and you can create custom ones. Categories are used for auto-categorization when importing bank statements.
          </Typography>

          <Divider sx={{ my: 2 }} />

          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>Auto-Import from Bank Statements</Typography>
          <Typography variant="body2" paragraph>
            When you upload bank statements, transactions are automatically imported into the Expenses section. The system analyzes transaction descriptions and merchant names to categorize them. You can always adjust categories manually from the Expenses page.
          </Typography>

          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>Manual Entry</Typography>
          <Typography variant="body2" paragraph>
            You can also add expenses manually using the "Add Expense" button on the Expenses page. Fill in the date, amount, description, category, and optionally link it to a bank account.
          </Typography>
        </AccordionDetails>
      </Accordion>

      {/* ─── Section 9: Portfolio Administration ─── */}
      <Accordion expanded={expanded === 'portfolio-admin'} onChange={handleChange('portfolio-admin')} sx={sectionSx}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Box display="flex" alignItems="center" gap={1}>
            <AdminIcon color="primary" />
            <Typography variant="h6">Portfolio Administration</Typography>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <Typography variant="body2" paragraph>
            The Portfolio Admin page provides tools for data backup, restore, and report generation.
          </Typography>

          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>JSON Backup / Export</Typography>
          <Typography variant="body2" paragraph>
            Download your entire portfolio data as a single JSON file. This includes all assets, bank accounts, demat accounts, crypto accounts, expenses, transactions, categories, alerts, and portfolio snapshots. Use this for regular backups or to migrate data between servers.
          </Typography>

          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>Restore from Backup</Typography>
          <Typography variant="body2" paragraph>
            Upload a previously downloaded JSON backup file to restore your data. The system imports only missing records — existing records with matching IDs are skipped to prevent duplicates. After import, a detailed summary shows what was imported vs. skipped for each data type.
          </Typography>

          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>PDF Statement Generation</Typography>
          <Typography variant="body2" paragraph>
            Generate a formatted PDF summary of your entire portfolio including asset allocation breakdown, individual holdings, bank account balances, and performance metrics. Useful for personal records or sharing with a financial advisor.
          </Typography>

          <Alert severity="info" sx={{ mt: 1 }}>
            Take a JSON backup regularly, especially before making large changes like bulk deletions or restoring from another backup.
          </Alert>
        </AccordionDetails>
      </Accordion>

      {/* ─── Section 10: Alerts & News ─── */}
      <Accordion expanded={expanded === 'alerts-news'} onChange={handleChange('alerts-news')} sx={sectionSx}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Box display="flex" alignItems="center" gap={1}>
            <AlertsIcon color="primary" />
            <Typography variant="h6">Alerts & News</Typography>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>AI-Powered News Alerts</Typography>
          <Typography variant="body2" paragraph>
            PortAct uses AI (OpenAI GPT or Grok, configurable in Application Settings) to fetch and analyze news relevant to your portfolio holdings. The system generates actionable alerts with severity levels and suggestions.
          </Typography>

          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>Scheduled Runs</Typography>
          <Typography variant="body2" paragraph>
            News is fetched automatically twice daily — morning and evening (hours configurable in Application Settings). You can also manually trigger a fetch using the "Fetch Latest News" button on the Alerts page. A progress bar shows the current fetch status.
          </Typography>

          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>Alert Severity Levels</Typography>
          <Box sx={{ display: 'flex', gap: 1, mb: 2, flexWrap: 'wrap' }}>
            <Chip label="High — Critical news requiring attention" color="error" size="small" />
            <Chip label="Medium — Notable market developments" color="warning" size="small" />
            <Chip label="Low — Informational updates" color="info" size="small" />
          </Box>

          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>Managing Alerts</Typography>
          <Typography variant="body2" paragraph>
            The Alerts page shows each alert with its type, message, related asset, severity, and timestamp. Dismiss individual alerts using the delete icon. The alert count badge in the sidebar shows unread alerts.
          </Typography>

          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>Configuration</Typography>
          <Typography variant="body2" paragraph>
            In Application Settings, you can configure the AI provider (OpenAI or Grok), morning and evening news times, and the number of portfolio assets analyzed per scheduled run.
          </Typography>
        </AccordionDetails>
      </Accordion>

      {/* ─── Section 11: Application Settings ─── */}
      <Accordion expanded={expanded === 'settings'} onChange={handleChange('settings')} sx={sectionSx}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Box display="flex" alignItems="center" gap={1}>
            <SettingsIcon color="primary" />
            <Typography variant="h6">Application Settings</Typography>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <Typography variant="body2" paragraph>
            The Application Setup page (Administration &gt; Application Setup) has three tabs:
          </Typography>

          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>Profile Tab</Typography>
          <Typography variant="body2" paragraph>
            Personal information: full name, email (read-only), phone number, date of birth, gender. Address details: street, city, state, pincode. These details are used in PDF statement generation and profile display.
          </Typography>

          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>Employment & Salary Tab</Typography>
          <Typography variant="body2" paragraph>
            Toggle "Currently Employed" to enable automatic PF and Gratuity calculations. Enter your employer name, date of joining, basic salary, DA percentage, and PF contribution percentages (employee and employer). A computed preview at the bottom shows your calculated monthly employee PF, monthly employer PF, and estimated gratuity based on years of service.
          </Typography>
          <Alert severity="info" sx={{ mb: 2 }}>
            The employment details drive automatic monthly PF contribution entries and gratuity amount updates. The monthly contribution scheduler runs on the 1st of each month. Ensure your salary details are accurate before that date.
          </Alert>

          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>Application Settings Tab</Typography>
          <Typography variant="body2" paragraph>
            Configure background schedulers and system settings:
          </Typography>
          <TableContainer component={Paper} variant="outlined" sx={{ mb: 2 }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell><strong>Setting</strong></TableCell>
                  <TableCell><strong>Default</strong></TableCell>
                  <TableCell><strong>Description</strong></TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                <TableRow>
                  <TableCell>Price Update Interval</TableCell>
                  <TableCell>30 minutes</TableCell>
                  <TableCell>How often asset prices are refreshed from market data</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>EOD Portfolio Snapshot</TableCell>
                  <TableCell>7:00 PM IST</TableCell>
                  <TableCell>Daily snapshot time for portfolio performance tracking</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Morning News</TableCell>
                  <TableCell>9:00 AM IST</TableCell>
                  <TableCell>Morning AI news fetch for portfolio assets</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Evening News</TableCell>
                  <TableCell>6:00 PM IST</TableCell>
                  <TableCell>Evening AI news fetch for portfolio assets</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Monthly Contributions</TableCell>
                  <TableCell>1st of month, 5:30 AM IST</TableCell>
                  <TableCell>Auto-calculate PF and Gratuity monthly entries</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Session Timeout</TableCell>
                  <TableCell>30 minutes</TableCell>
                  <TableCell>Idle time before requiring re-login (when tab is hidden)</TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </TableContainer>
          <Typography variant="body2" paragraph>
            You can also select the AI provider (OpenAI GPT or Grok) for news alerts, and use the "Reset to Defaults" button to restore all settings to factory values.
          </Typography>
        </AccordionDetails>
      </Accordion>

      {/* ─── Section 12: Tips & Productivity ─── */}
      <Accordion expanded={expanded === 'tips'} onChange={handleChange('tips')} sx={sectionSx}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Box display="flex" alignItems="center" gap={1}>
            <TipsIcon color="primary" />
            <Typography variant="h6">Tips & Productivity</Typography>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>Privacy Mode</Typography>
          <Typography variant="body2" paragraph>
            Use the eye icon on the Dashboard to hide all financial numbers. All values are replaced with masked dots. Click again to reveal. Useful during screen sharing or working in public.
          </Typography>

          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>Statement Upload Tips</Typography>
          <List dense>
            <ListItem><ListItemText primary="Download PDF statements directly from your bank's netbanking portal for best parsing results" /></ListItem>
            <ListItem><ListItemText primary="Always provide the PDF password when prompted (especially for SBI statements)" /></ListItem>
            <ListItem><ListItemText primary="Supported file formats: PDF, Excel (.xlsx/.xls), CSV" /></ListItem>
            <ListItem><ListItemText primary="Maximum file size: 10 MB" /></ListItem>
            <ListItem><ListItemText primary="For mutual fund holdings, the consolidated Excel method is fastest for bulk import" /></ListItem>
          </List>

          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>Data Management</Typography>
          <List dense>
            <ListItem><ListItemText primary="Take regular JSON backups from Portfolio Admin — especially before large changes" /></ListItem>
            <ListItem><ListItemText primary="After restoring a backup, verify the import summary for skipped vs. imported records" /></ListItem>
            <ListItem><ListItemText primary="Deleting a statement also deletes all associated assets — use with caution" /></ListItem>
            <ListItem><ListItemText primary="Deleting a bank account removes the account record; linked transactions may remain" /></ListItem>
          </List>

          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>Scheduler Tips</Typography>
          <List dense>
            <ListItem><ListItemText primary="Price updates run during market hours for best accuracy" /></ListItem>
            <ListItem><ListItemText primary="EOD snapshots should be scheduled after market close (default: 7 PM IST)" /></ListItem>
            <ListItem><ListItemText primary="For employment-based calculations, ensure salary details are up to date before the 1st of each month" /></ListItem>
            <ListItem><ListItemText primary="News alert times can be adjusted to match your schedule" /></ListItem>
          </List>

          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>Session Management</Typography>
          <Typography variant="body2" paragraph>
            The app automatically logs you out after the configured inactivity timeout (default: 30 minutes) when the browser tab is hidden. Keep the tab visible or increase the timeout in Application Settings to stay logged in longer.
          </Typography>
        </AccordionDetails>
      </Accordion>

      {/* ─── Section 13: Troubleshooting & FAQ ─── */}
      <Accordion expanded={expanded === 'troubleshooting'} onChange={handleChange('troubleshooting')} sx={sectionSx}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Box display="flex" alignItems="center" gap={1}>
            <FAQIcon color="primary" />
            <Typography variant="h6">Troubleshooting & FAQ</Typography>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <Typography variant="subtitle1" fontWeight="bold">My statement upload failed. What should I do?</Typography>
          <Typography variant="body2" paragraph>
            Check that you selected the correct institution/broker and statement type. Ensure the file format is supported (PDF, Excel, CSV). For PDF files, provide the correct password if the file is password-protected. If the statement format has changed recently, try the Excel format instead if available.
          </Typography>
          <Divider sx={{ my: 1.5 }} />

          <Typography variant="subtitle1" fontWeight="bold">Why is my portfolio value different from what I see in my broker?</Typography>
          <Typography variant="body2" paragraph>
            Prices update on a scheduled interval (default: every 30 minutes). The last price update time is shown on each asset. Some less-liquid assets (bonds, post office schemes) may not have real-time price feeds and require manual updates via the Assets page.
          </Typography>
          <Divider sx={{ my: 1.5 }} />

          <Typography variant="subtitle1" fontWeight="bold">How do I add an asset type that doesn't have a dedicated page?</Typography>
          <Typography variant="body2" paragraph>
            Go to Assets &gt; Overview and use the "Add Asset" button. You can select any supported asset type from the dropdown and enter details manually.
          </Typography>
          <Divider sx={{ my: 1.5 }} />

          <Typography variant="subtitle1" fontWeight="bold">Why are my PF/Gratuity values not updating monthly?</Typography>
          <Typography variant="body2" paragraph>
            Ensure the "Currently Employed" toggle is enabled in Application Setup &gt; Employment & Salary tab, and that your basic salary, DA percentage, and PF percentages are filled in correctly. The monthly contribution scheduler runs on the 1st of each month at 5:30 AM IST.
          </Typography>
          <Divider sx={{ my: 1.5 }} />

          <Typography variant="subtitle1" fontWeight="bold">How does auto-categorization of expenses work?</Typography>
          <Typography variant="body2" paragraph>
            When importing bank statements, PortAct analyzes transaction descriptions and merchant names to match them against your defined expense categories. The accuracy improves as you manually correct categories — the system learns from your corrections. You can always re-categorize any transaction from the Expenses page.
          </Typography>
          <Divider sx={{ my: 1.5 }} />

          <Typography variant="subtitle1" fontWeight="bold">Can I use PortAct on multiple devices?</Typography>
          <Typography variant="body2" paragraph>
            Yes. PortAct is a web application — log in from any browser on any device. Your data is stored on the server and syncs automatically. Each device has an independent session, so logging in on one device does not log you out of another.
          </Typography>
          <Divider sx={{ my: 1.5 }} />

          <Typography variant="subtitle1" fontWeight="bold">How do I change my password?</Typography>
          <Typography variant="body2" paragraph>
            Log out and use the "Forgot Password" link on the login page. Enter your email address to receive a password reset link. Follow the link to set a new password.
          </Typography>
          <Divider sx={{ my: 1.5 }} />

          <Typography variant="subtitle1" fontWeight="bold">What happens when I delete a bank or demat account?</Typography>
          <Typography variant="body2" paragraph>
            Deleting an account removes the account record. Associated assets and expense transactions may remain in the system. Take a JSON backup from Portfolio Admin before making destructive changes so you can restore if needed.
          </Typography>
          <Divider sx={{ my: 1.5 }} />

          <Typography variant="subtitle1" fontWeight="bold">How do I track real estate, gold bonds, and other non-market assets?</Typography>
          <Typography variant="body2" paragraph>
            Navigate to the respective page in the sidebar — for example, Real Estate &gt; Land or Demat Holding &gt; Sovereign Gold Bonds. Add entries manually with purchase price and current estimated market value. Update the market value periodically to keep your portfolio valuation accurate.
          </Typography>
        </AccordionDetails>
      </Accordion>

      {/* ─── Footer ─── */}
      <Paper sx={{ p: 3, mt: 3, textAlign: 'center', bgcolor: 'action.hover' }}>
        <Typography variant="body2" color="text.secondary">
          PortAct — Personal Portfolio Tracker
        </Typography>
        <Typography variant="caption" color="text.secondary">
          For additional support, refer to the project documentation or contact the administrator.
        </Typography>
      </Paper>
    </Box>
  );
};

export default Help;

// Made with Bob
