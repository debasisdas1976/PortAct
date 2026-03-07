/**
 * Asset field configuration for GenericAssetEditDialog.
 * Defines which form fields to render for each asset type.
 */

export type AccountType = 'demat' | 'bank' | 'crypto' | 'none';

export interface FieldDef {
  name: string;
  label: string;
  type: 'text' | 'number' | 'date' | 'select' | 'textarea' | 'currency_radio';
  required?: boolean;
  helperText?: string;
  isDetail?: boolean;       // stored in asset.details JSON, not main columns
  half?: boolean;           // half-width in grid (xs=6)
  options?: { value: string; label: string }[];
  step?: string;
  computed?: 'qty_x_price';  // auto-compute hint
}

export interface AssetTypeConfig {
  assetType: string;
  label: string;
  accountType: AccountType;
  currencyInput?: 'INR' | 'USD';
  useSpecializedDialog?: boolean;     // crypto → CryptoAssetDialog
  navigateToPage?: boolean;           // account-centric types → navigate to dedicated page
  filterDematMarket?: 'INTERNATIONAL'; // filter demat accounts by market
  fields: FieldDef[];
}

// ── Standard field sets ─────────────────────────────────────────────────

const STANDARD_STOCK_FIELDS: FieldDef[] = [
  { name: 'name', label: 'Name', type: 'text', required: true },
  { name: 'symbol', label: 'Symbol', type: 'text', half: true },
  { name: 'isin', label: 'ISIN', type: 'text', half: true },
  { name: 'quantity', label: 'Quantity', type: 'number', half: true },
  { name: 'purchase_price', label: 'Average Buy Price', type: 'number', half: true },
  { name: 'total_invested', label: 'Total Invested', type: 'number', half: true, helperText: 'Leave 0 to auto-calculate (Qty × Avg Price)', computed: 'qty_x_price' },
  { name: 'current_price', label: 'Current Price', type: 'number', half: true, helperText: 'Will be auto-updated by price scheduler' },
  { name: 'xirr', label: 'XIRR (%)', type: 'number', half: true, helperText: 'Auto-calculated from transactions. Enter manually if needed.' },
];

const USD_STOCK_FIELDS: FieldDef[] = [
  { name: 'name', label: 'Name', type: 'text', required: true },
  { name: 'symbol', label: 'Symbol', type: 'text', half: true },
  { name: 'isin', label: 'ISIN', type: 'text', half: true },
  { name: 'quantity', label: 'Quantity', type: 'number', half: true },
  { name: 'purchase_price', label: 'Average Buy Price (USD)', type: 'number', half: true },
  { name: 'total_invested', label: 'Total Invested (USD)', type: 'number', half: true, helperText: 'Leave 0 to auto-calculate (Qty × Avg Price)', computed: 'qty_x_price' },
  { name: 'current_price', label: 'Current Price (USD)', type: 'number', half: true, helperText: 'Will be auto-updated by price scheduler' },
  { name: 'xirr', label: 'XIRR (%)', type: 'number', half: true, helperText: 'Auto-calculated from transactions. Enter manually if needed.' },
];

const BOND_FIELDS: FieldDef[] = [
  { name: 'name', label: 'Name', type: 'text', required: true },
  { name: 'symbol', label: 'Symbol', type: 'text', half: true },
  { name: 'isin', label: 'ISIN', type: 'text', half: true },
  { name: 'quantity', label: 'Quantity', type: 'number', half: true, step: '0.01' },
  { name: 'purchase_price', label: 'Purchase Price', type: 'number', half: true, step: '0.01' },
  { name: 'current_price', label: 'Current Price', type: 'number', half: true, step: '0.01', helperText: 'Leave empty to use purchase price' },
  { name: 'interest_rate', label: 'Coupon / Interest Rate (%)', type: 'number', half: true, step: '0.01', isDetail: true },
  { name: 'maturity_date', label: 'Maturity Date', type: 'date', half: true, isDetail: true },
  { name: 'broker_name', label: 'Broker', type: 'text', half: true },
  { name: 'xirr', label: 'XIRR (%)', type: 'number', half: true, helperText: 'Auto-calculated from transactions. Enter manually if needed.' },
  { name: 'notes', label: 'Notes', type: 'textarea' },
];

const POST_OFFICE_FIELDS: FieldDef[] = [
  { name: 'name', label: 'Name', type: 'text', required: true },
  { name: 'symbol', label: 'Certificate / Account No.', type: 'text', half: true },
  { name: 'broker_name', label: 'Institution / Branch', type: 'text', half: true },
  { name: 'total_invested', label: 'Amount Invested', type: 'number', half: true },
  { name: 'current_price', label: 'Current Value', type: 'number', half: true },
  { name: 'interest_rate', label: 'Interest Rate (%)', type: 'number', half: true, step: '0.01', isDetail: true },
  { name: 'maturity_date', label: 'Maturity Date', type: 'date', half: true, isDetail: true },
  { name: 'xirr', label: 'XIRR (%)', type: 'number', half: true, helperText: 'Auto-calculated from transactions. Enter manually if needed.' },
  { name: 'notes', label: 'Notes', type: 'textarea' },
];

const ESOP_FIELDS: FieldDef[] = [
  { name: 'name', label: 'Stock Name', type: 'text', required: true },
  { name: 'symbol', label: 'Symbol', type: 'text', half: true },
  { name: 'currency', label: 'Currency', type: 'currency_radio', half: true, isDetail: true, options: [{ value: 'INR', label: 'INR' }, { value: 'USD', label: 'USD' }] },
  { name: 'company_name', label: 'Company Name', type: 'text', half: true, isDetail: true },
  { name: 'grant_date', label: 'Grant Date', type: 'date', half: true, isDetail: true },
  { name: 'vesting_date', label: 'Vesting Date', type: 'date', half: true, isDetail: true },
  { name: 'shares_granted', label: 'Shares Granted', type: 'number', half: true, isDetail: true },
  { name: 'shares_vested', label: 'Shares Vested', type: 'number', half: true, isDetail: true },
  { name: 'exercise_price', label: 'Exercise Price', type: 'number', half: true, isDetail: true },
  { name: 'current_price', label: 'Current Price', type: 'number', half: true },
  { name: 'cliff_period', label: 'Cliff Period', type: 'text', half: true, isDetail: true },
  { name: 'xirr', label: 'XIRR (%)', type: 'number', half: true, helperText: 'Auto-calculated from transactions. Enter manually if needed.' },
];

const RSU_FIELDS: FieldDef[] = [
  { name: 'name', label: 'Stock Name', type: 'text', required: true },
  { name: 'symbol', label: 'Symbol', type: 'text', half: true },
  { name: 'currency', label: 'Currency', type: 'currency_radio', half: true, isDetail: true, options: [{ value: 'INR', label: 'INR' }, { value: 'USD', label: 'USD' }] },
  { name: 'company_name', label: 'Company Name', type: 'text', half: true, isDetail: true },
  { name: 'grant_date', label: 'Grant Date', type: 'date', half: true, isDetail: true },
  { name: 'vesting_date', label: 'Vesting Date', type: 'date', half: true, isDetail: true },
  { name: 'shares_granted', label: 'Shares Granted', type: 'number', half: true, isDetail: true },
  { name: 'shares_vested', label: 'Shares Vested', type: 'number', half: true, isDetail: true },
  { name: 'fmv_at_grant', label: 'FMV at Grant', type: 'number', half: true, isDetail: true },
  { name: 'current_price', label: 'Current Price', type: 'number', half: true },
  { name: 'xirr', label: 'XIRR (%)', type: 'number', half: true, helperText: 'Auto-calculated from transactions. Enter manually if needed.' },
];

const CASH_CURRENCIES = [
  { value: 'INR', label: 'INR - Indian Rupee' },
  { value: 'USD', label: 'USD - US Dollar' },
  { value: 'EUR', label: 'EUR - Euro' },
  { value: 'GBP', label: 'GBP - British Pound' },
  { value: 'AED', label: 'AED - UAE Dirham' },
  { value: 'SGD', label: 'SGD - Singapore Dollar' },
  { value: 'JPY', label: 'JPY - Japanese Yen' },
  { value: 'AUD', label: 'AUD - Australian Dollar' },
  { value: 'CAD', label: 'CAD - Canadian Dollar' },
  { value: 'CHF', label: 'CHF - Swiss Franc' },
];

const CASH_FIELDS: FieldDef[] = [
  { name: 'name', label: 'Name', type: 'text', required: true },
  { name: 'currency', label: 'Currency', type: 'select', half: true, isDetail: true, options: CASH_CURRENCIES },
  { name: 'original_amount', label: 'Amount', type: 'number', half: true, isDetail: true },
  { name: 'inr_value', label: 'INR Value', type: 'number', half: true },
  { name: 'xirr', label: 'XIRR (%)', type: 'number', half: true, helperText: 'Auto-calculated from transactions. Enter manually if needed.' },
  { name: 'notes', label: 'Notes', type: 'textarea' },
];

const SIMPLE_ASSET_FIELDS: FieldDef[] = [
  { name: 'name', label: 'Name', type: 'text', required: true },
  { name: 'total_invested', label: 'Total Invested', type: 'number', half: true },
  { name: 'current_price', label: 'Current Value', type: 'number', half: true },
  { name: 'xirr', label: 'XIRR (%)', type: 'number', half: true, helperText: 'Auto-calculated from transactions. Enter manually if needed.' },
  { name: 'notes', label: 'Notes', type: 'textarea' },
];

// ── Config map ──────────────────────────────────────────────────────────

const ASSET_TYPE_CONFIGS: AssetTypeConfig[] = [
  // Stocks & MFs (demat account)
  { assetType: 'stock', label: 'Stock', accountType: 'demat', fields: STANDARD_STOCK_FIELDS },
  { assetType: 'equity_mutual_fund', label: 'Equity Mutual Fund', accountType: 'demat', fields: STANDARD_STOCK_FIELDS },
  { assetType: 'hybrid_mutual_fund', label: 'Hybrid Mutual Fund', accountType: 'demat', fields: STANDARD_STOCK_FIELDS },
  { assetType: 'debt_mutual_fund', label: 'Debt Mutual Fund', accountType: 'demat', fields: STANDARD_STOCK_FIELDS },
  { assetType: 'commodity', label: 'Commodity', accountType: 'demat', fields: STANDARD_STOCK_FIELDS },
  { assetType: 'reit', label: 'REIT', accountType: 'demat', fields: STANDARD_STOCK_FIELDS },
  { assetType: 'invit', label: 'InvIT', accountType: 'demat', fields: STANDARD_STOCK_FIELDS },

  // US Stock (demat, USD)
  { assetType: 'us_stock', label: 'US Stock', accountType: 'demat', currencyInput: 'USD', filterDematMarket: 'INTERNATIONAL', fields: USD_STOCK_FIELDS },

  // ESOPs & RSUs (demat with extras)
  { assetType: 'esop', label: 'ESOP', accountType: 'demat', fields: ESOP_FIELDS },
  { assetType: 'rsu', label: 'RSU', accountType: 'demat', fields: RSU_FIELDS },

  // Sovereign Gold Bond (portfolio, no FK account)
  { assetType: 'sovereign_gold_bond', label: 'Sovereign Gold Bond', accountType: 'none', fields: [
    { name: 'name', label: 'SGB Series Name', type: 'text', required: true },
    { name: 'symbol', label: 'Symbol / Ticker', type: 'text', half: true },
    { name: 'isin', label: 'ISIN', type: 'text', half: true },
    { name: 'quantity', label: 'Quantity (grams)', type: 'number', half: true },
    { name: 'purchase_price', label: 'Issue / Purchase Price', type: 'number', half: true },
    { name: 'current_price', label: 'Current Price', type: 'number', half: true },
    { name: 'broker_name', label: 'Broker', type: 'text', half: true },
    { name: 'account_id', label: 'Account ID', type: 'text', half: true },
    { name: 'xirr', label: 'XIRR (%)', type: 'number', half: true, helperText: 'Auto-calculated from transactions. Enter manually if needed.' },
    { name: 'notes', label: 'Notes', type: 'textarea' },
  ]},

  // Bonds (portfolio, no FK account)
  { assetType: 'corporate_bond', label: 'Corporate Bond', accountType: 'none', fields: BOND_FIELDS },
  { assetType: 'rbi_bond', label: 'RBI Bond', accountType: 'none', fields: BOND_FIELDS },
  { assetType: 'tax_saving_bond', label: 'Tax Saving Bond', accountType: 'none', fields: BOND_FIELDS },

  // Post office schemes
  { assetType: 'nsc', label: 'NSC', accountType: 'none', fields: POST_OFFICE_FIELDS },
  { assetType: 'kvp', label: 'KVP', accountType: 'none', fields: POST_OFFICE_FIELDS },
  { assetType: 'scss', label: 'SCSS', accountType: 'none', fields: POST_OFFICE_FIELDS },
  { assetType: 'mis', label: 'MIS', accountType: 'none', fields: POST_OFFICE_FIELDS },

  // Cash
  { assetType: 'cash', label: 'Cash In Hand', accountType: 'none', fields: CASH_FIELDS },

  // Real estate & Insurance — navigate to dedicated page
  { assetType: 'land', label: 'Land', accountType: 'none', navigateToPage: true, fields: SIMPLE_ASSET_FIELDS },
  { assetType: 'farm_land', label: 'Farm Land', accountType: 'none', navigateToPage: true, fields: SIMPLE_ASSET_FIELDS },
  { assetType: 'house', label: 'House', accountType: 'none', navigateToPage: true, fields: SIMPLE_ASSET_FIELDS },
  { assetType: 'insurance_policy', label: 'Insurance', accountType: 'none', navigateToPage: true, fields: SIMPLE_ASSET_FIELDS },

  // Account-centric types — navigate to dedicated page
  { assetType: 'ppf', label: 'PPF', accountType: 'bank', navigateToPage: true, fields: SIMPLE_ASSET_FIELDS },
  { assetType: 'pf', label: 'Provident Fund', accountType: 'bank', navigateToPage: true, fields: SIMPLE_ASSET_FIELDS },
  { assetType: 'nps', label: 'NPS', accountType: 'bank', navigateToPage: true, fields: SIMPLE_ASSET_FIELDS },
  { assetType: 'ssy', label: 'SSY', accountType: 'bank', navigateToPage: true, fields: SIMPLE_ASSET_FIELDS },
  { assetType: 'gratuity', label: 'Gratuity', accountType: 'none', navigateToPage: true, fields: SIMPLE_ASSET_FIELDS },
  { assetType: 'pension', label: 'Pension', accountType: 'none', navigateToPage: true, fields: SIMPLE_ASSET_FIELDS },
  { assetType: 'savings_account', label: 'Savings Account', accountType: 'bank', navigateToPage: true, fields: SIMPLE_ASSET_FIELDS },
  { assetType: 'fixed_deposit', label: 'Fixed Deposit', accountType: 'bank', navigateToPage: true, fields: SIMPLE_ASSET_FIELDS },
  { assetType: 'recurring_deposit', label: 'Recurring Deposit', accountType: 'bank', navigateToPage: true, fields: SIMPLE_ASSET_FIELDS },

  // Crypto — uses CryptoAssetDialog
  { assetType: 'crypto', label: 'Crypto', accountType: 'crypto', useSpecializedDialog: true, fields: [] },
];

const CONFIG_MAP = new Map<string, AssetTypeConfig>();
for (const cfg of ASSET_TYPE_CONFIGS) {
  CONFIG_MAP.set(cfg.assetType, cfg);
}

export function getAssetTypeConfig(assetType: string): AssetTypeConfig | undefined {
  return CONFIG_MAP.get(assetType.toLowerCase());
}

export function getAssetTypeLabel(assetType: string): string {
  return CONFIG_MAP.get(assetType.toLowerCase())?.label || assetType;
}

/** Asset types that should navigate to their dedicated page for editing */
export const NAVIGATE_TO_PAGE_TYPES = new Set(
  ASSET_TYPE_CONFIGS.filter(c => c.navigateToPage).map(c => c.assetType)
);

/** Asset types that use a specialized dialog (crypto) */
export const SPECIALIZED_DIALOG_TYPES = new Set(
  ASSET_TYPE_CONFIGS.filter(c => c.useSpecializedDialog).map(c => c.assetType)
);
