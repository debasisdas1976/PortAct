# PortAct - UI Documentation

## Overview

PortAct features a modern, responsive React-based user interface built with Material-UI components. The UI provides comprehensive portfolio management capabilities including statement uploads, asset visualization, and real-time portfolio tracking.

## Technology Stack

### Frontend Framework
- **React 18.2** - Modern React with hooks and functional components
- **TypeScript 4.9** - Type-safe development
- **React Router 6** - Client-side routing

### State Management
- **Redux Toolkit 2.1** - Centralized state management
- **React Redux 9.1** - React bindings for Redux

### UI Components
- **Material-UI (MUI) 5.15** - Comprehensive component library
- **MUI Icons** - Icon set for consistent UI
- **Emotion** - CSS-in-JS styling

### Data Visualization
- **Recharts 2.12** - Responsive charts and graphs

### HTTP Client
- **Axios 1.6** - Promise-based HTTP client with interceptors

## Project Structure

```
frontend/
├── public/
│   └── index.html              # HTML template
├── src/
│   ├── components/             # Reusable components
│   │   ├── Layout.tsx          # Main layout with navigation
│   │   └── charts/             # Chart components
│   │       ├── PortfolioChart.tsx
│   │       ├── PerformanceChart.tsx
│   │       └── AssetAllocationChart.tsx
│   ├── pages/                  # Page components
│   │   ├── Login.tsx           # Login page
│   │   ├── Register.tsx        # Registration page
│   │   ├── Dashboard.tsx       # Main dashboard
│   │   ├── Assets.tsx          # Assets management
│   │   ├── Statements.tsx      # Statement upload & history
│   │   └── Alerts.tsx          # Alerts & notifications
│   ├── store/                  # Redux store
│   │   ├── index.ts            # Store configuration
│   │   └── slices/             # Redux slices
│   │       ├── authSlice.ts
│   │       ├── portfolioSlice.ts
│   │       ├── assetsSlice.ts
│   │       └── alertsSlice.ts
│   ├── services/               # API services
│   │   └── api.ts              # Axios configuration & API calls
│   ├── App.tsx                 # Main app component
│   └── index.tsx               # Entry point
├── package.json                # Dependencies
└── .env                        # Environment variables
```

## Features

### 1. Authentication
- **Login Page** - Secure user authentication
- **Register Page** - New user registration with validation
- **JWT Token Management** - Automatic token refresh and storage
- **Protected Routes** - Route guards for authenticated pages

### 2. Dashboard
- **Portfolio Summary Cards**
  - Total Portfolio Value
  - Total Investment
  - Total Gain/Loss with percentage
  - Asset Count
  - Day Change — Portfolio-level daily change vs. previous EOD snapshot
- **Portfolio Performance Chart** - Line chart showing value over time
- **Asset Allocation Chart** - Pie chart showing distribution by asset type
- **Portfolio Value Chart** - Area chart comparing current value vs invested amount

### 3. Statement Upload
- **File Upload Dialog**
  - Support for PDF, CSV, and XLSX files
  - Broker selection (Zerodha, Groww, Upstox, Angel One, etc.)
  - Statement type selection (Equity, Mutual Fund, Consolidated)
- **Statement History Table**
  - Filename and upload date
  - Processing status with color-coded chips
  - Broker and statement type information

### 4. Assets Management
- **Summary Cards**
  - Total Value
  - Total Invested
  - Total Gain/Loss
  - Return Percentage
- **Detailed Assets Table**
  - Symbol, Name, and Type
  - Quantity and Prices (Average, Current)
  - Investment and Current Value
  - Gain/Loss with color coding
  - Return percentage

### 5. Alerts & Notifications
- **Alert Table**
  - Alert type and message
  - Associated asset
  - Severity levels (High, Medium, Low)
  - Timestamp
  - Delete functionality

## UI Components

### Layout Component
- **Responsive Sidebar Navigation** with collapsible sections:
  - Dashboard
  - Asset Overview
  - Demat Holdings (Stocks, US Stocks, Equity MF, Hybrid MF, Debt Funds, Commodities, SGBs, ESOPs, RSUs)
  - Banking (Savings, Credit Cards, FD, RD, Bank Accounts)
  - Retirement Plans (PPF, PF, NPS, Gratuity, Pension, Insurance, SCSS)
  - Government Schemes (NSC, KVP, MIS, SSY)
  - Bonds (Corporate, RBI, Tax-Saving)
  - Real Estate (Land, Farm Land, House, REITs, InvITs)
  - Crypto (Accounts, Assets)
  - Insights (Asset Insight, Attribute Insight, Maturity Timeline, Alerts, MF Holdings, Cash)
  - Expenses (Dashboard, Expenses)
  - Statements
  - Utilities (SIP Creator)
  - Administration (Portfolios, Portfolio Admin, Settings)
  - Master Data (Asset Types, Attributes, Banks, Brokers, Exchanges, Categories)
- **Top App Bar**
  - Page title, portfolio selector, user profile menu, logout
- **Responsive Design**
  - Collapsible navigation drawer

### Chart Components

#### PortfolioChart
- Line chart showing portfolio value over time
- Compares current value vs total invested
- Responsive design
- Formatted currency values
- Date-based x-axis

#### PerformanceChart
- Area chart showing gain/loss over time
- Gradient fill for visual appeal
- Return percentage tooltip
- Color-coded positive/negative values

#### AssetAllocationChart
- Pie chart showing asset distribution by type
- Percentage labels
- Color-coded segments
- Interactive tooltips

## State Management

### Redux Slices

#### authSlice
```typescript
State:
- user: User | null
- token: string | null
- isAuthenticated: boolean
- loading: boolean
- error: string | null

Actions:
- login(credentials)
- register(userData)
- logout()
- getCurrentUser()
- clearError()
```

#### portfolioSlice
```typescript
State:
- summary: PortfolioSummary | null
- history: PortfolioHistory[]
- loading: boolean
- error: string | null

Actions:
- fetchPortfolioSummary()
- fetchPortfolioHistory()
```

#### assetsSlice
```typescript
State:
- assets: Asset[]
- loading: boolean
- error: string | null

Actions:
- fetchAssets()
- fetchAssetById(id)
```

#### alertsSlice
```typescript
State:
- alerts: Alert[]
- loading: boolean
- error: string | null

Actions:
- fetchAlerts()
- deleteAlert(id)
```

## API Integration

### Axios Configuration
- Base URL: `http://localhost:8000/api/v1`
- Request Interceptor: Adds JWT token to headers
- Response Interceptor: Handles 401 errors and token refresh
- Error Handling: Centralized error management

### API Endpoints Used
```
Authentication:
- POST /auth/login
- POST /auth/register
- GET /auth/me

Portfolio:
- GET /dashboard/summary
- GET /dashboard/history

Assets:
- GET /assets/
- GET /assets/{id}

Statements:
- GET /statements/
- POST /statements/upload

Alerts:
- GET /alerts/
- DELETE /alerts/{id}
```

## Styling

### Theme Configuration
- **Primary Color**: Blue (#1976d2)
- **Secondary Color**: Purple (#9c27b0)
- **Success Color**: Green (#4caf50)
- **Error Color**: Red (#f44336)
- **Warning Color**: Orange (#ff9800)

### Responsive Design
- Mobile-first approach
- Breakpoints:
  - xs: 0px
  - sm: 600px
  - md: 900px
  - lg: 1200px
  - xl: 1536px

### Typography
- Font Family: Roboto
- Headings: h4, h5, h6
- Body: body1, body2
- Captions: caption

## Running the Frontend

### Development Mode
```bash
cd frontend
npm install
npm start
```
Access at: http://localhost:3000

### Production Build
```bash
cd frontend
npm run build
```
Creates optimized build in `build/` directory

### Using the Complete Setup Script
```bash
./scripts/run_app.sh
```
This script:
1. Checks prerequisites
2. Sets up backend and frontend
3. Starts both servers
4. Provides URLs for access

## Environment Variables

Create a `.env` file in the frontend directory:
```
REACT_APP_API_URL=http://localhost:8000/api/v1
```

## User Workflow

### First Time User
1. **Register** - Create account with email and password
2. **Login** - Authenticate with credentials
3. **Upload Statement** - Upload first broker statement
4. **View Dashboard** - See portfolio summary and charts
5. **Manage Assets** - View detailed asset information
6. **Monitor Alerts** - Check for important notifications

### Returning User
1. **Login** - Authenticate
2. **Dashboard** - View portfolio performance
3. **Upload New Statements** - Add new transactions
4. **Track Changes** - Monitor gains/losses
5. **Review Alerts** - Check notifications

## Features in Detail

### Dashboard Cards
- **Real-time Updates** - Fetches latest data on load
- **Color Coding** - Green for gains, red for losses
- **Trend Indicators** - Up/down arrows for performance
- **Formatted Values** - Indian Rupee formatting

### Statement Upload
- **Drag & Drop** - Easy file selection
- **File Validation** - Accepts PDF, CSV, XLSX
- **Progress Indication** - Loading states during upload
- **Success Feedback** - Confirmation messages

### Asset Table
- **Sortable Columns** - Click headers to sort
- **Color-Coded Values** - Visual gain/loss indicators
- **Detailed Information** - Complete asset details
- **Responsive Design** - Works on all screen sizes

### Charts
- **Interactive Tooltips** - Hover for detailed information
- **Responsive Sizing** - Adapts to container size
- **Smooth Animations** - Engaging transitions
- **Export Ready** - Can be exported as images

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## Performance Optimizations

- **Code Splitting** - Lazy loading of routes
- **Memoization** - React.memo for expensive components
- **Debouncing** - Input field optimizations
- **Caching** - Redux state persistence

## Accessibility

- **ARIA Labels** - Screen reader support
- **Keyboard Navigation** - Full keyboard accessibility
- **Color Contrast** - WCAG AA compliant
- **Focus Indicators** - Clear focus states

## Current Feature Highlights

The frontend has grown significantly beyond the initial pages listed above. The application now includes **65+ pages** covering:

- **30+ Asset Type Pages** — Dedicated management page per asset type (Stocks, US Stocks, Equity/Hybrid/Debt MFs, FDs, RDs, PPF, PF, NPS, Gratuity, Pension, Insurance, SCSS, NSC, KVP, MIS, SSY, Bonds, Real Estate, REITs, InvITs, Crypto, ESOPs, RSUs, Cash, Commodities, SGBs)
- **Account Management** — Bank accounts, demat accounts, crypto accounts with independent cash balances
- **Asset Attributes** — Custom tagging system with bulk assignment and attribute-based insights
- **Expense Tracking** — Expense dashboard with monthly trends, AI-powered categorization, category management
- **Multi-Portfolio** — Create and manage multiple portfolios; full export/import with auto ID remapping
- **Price Updates** — Real-time price refresh with progress tracking (stocks, MFs, crypto, commodities, US stocks with forex)
- **EOD Snapshots** — Daily portfolio snapshots with historical performance charts (7d to 1y views)
- **AI News & Alerts** — Automated market news analysis via OpenAI/Grok with severity levels
- **Insights** — Asset insights, attribute insights, maturity timeline, mutual fund holdings analysis
- **Day Change % Tracking** — Daily price change percentage on Dashboard, Assets Overview, and all 30+ asset pages via DayChangeCard component
- **Maturity Timeline** — Custom SVG timeline chart showing upcoming maturity dates for FDs, RDs, bonds, government schemes, insurance, and SGBs with status badges and summary cards
- **Statements** — Upload bank/broker/tradebook statements with bank-specific parsers
- **SIP Creator** — Generate SIP transactions for mutual funds
- **Master Data** — Asset types, attributes, banks, brokers, crypto exchanges, expense categories
- **Application Settings** — Configurable price update interval, EOD time, monthly contributions

## Potential Future Enhancements

1. **Mobile App** - React Native version
2. **Multi-language** - i18n support
3. **Custom Dashboards** - User-configurable layouts

## Troubleshooting

### Common Issues

**Issue**: TypeScript errors after installation
**Solution**: Run `npm install` to install all dependencies

**Issue**: API connection errors
**Solution**: Ensure backend is running on port 8000

**Issue**: Charts not rendering
**Solution**: Check browser console for errors, ensure data is loaded

**Issue**: Login not working
**Solution**: Verify backend is running and .env file is configured

## Support

For issues or questions:
1. Check the documentation
2. Review error messages in browser console
3. Verify backend API is running
4. Check network tab for API responses

## License

This project is part of the PortAct portfolio management system.