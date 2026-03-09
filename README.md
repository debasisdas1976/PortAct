# PortAct - Personal Finance Portfolio Tracker

A comprehensive, privacy-first personal finance portfolio tracker that runs entirely on your machine. Track 30+ asset types, auto-import from bank and broker statements, get AI-powered market alerts, and maintain full ownership of your financial data.

**Your data stays on your machine. No third-party sharing. No cloud dependency.**

[![Watch the Introduction Video](https://img.shields.io/badge/YouTube-Watch%20Introduction-red?logo=youtube)](https://www.youtube.com/watch?v=hoEDYFW2LZs)

## Why PortAct?

Most portfolio trackers require you to share sensitive financial data with third parties. PortAct is different:

- **Complete data ownership** — All data lives on your machine in a local PostgreSQL database
- **No cloud accounts** — No sign-ups, no API keys shared with external services
- **Privacy by design** — Built for those who value security over convenience
- **Open source** — Inspect, modify, and extend the code freely

## Key Features

### 30+ Asset Types
Track virtually every Indian and international investment vehicle:

| Category | Asset Types |
|----------|-------------|
| **Equities** | Stocks, US Stocks (with USD/INR conversion), ESOPs, RSUs |
| **Mutual Funds** | Equity MF, Hybrid MF, Debt MF |
| **Commodities** | Gold, Silver, Sovereign Gold Bonds |
| **Banking** | Savings Accounts, Fixed Deposits, Recurring Deposits, Credit Cards |
| **Retirement** | PPF, PF/EPF, NPS, Gratuity, Pension, Insurance |
| **Government Schemes** | NSC, KVP, MIS, SCSS, SSY |
| **Bonds** | Corporate Bonds, RBI Bonds, Tax-Saving Bonds |
| **Real Estate** | Land, Farm Land, House, REITs, InvITs |
| **Crypto** | All major cryptocurrencies via multiple exchanges |
| **Cash** | Cash in hand |

### Smart Statement Processing
Upload statements and let PortAct do the rest:

- **Bank Statements (PDF)** — ICICI, HDFC, IDFC First, SBI, Axis, Kotak + generic formats
- **Broker Holdings (CSV/Excel)** — Zerodha, ICICI Direct, Upstox, Angel One
- **Consolidated Statements** — NSDL/CDSL CAS (password-protected PDF)
- **Tradebooks** — Import trade history for transaction tracking
- **Mutual Fund Holdings** — Excel-based MF portfolio composition

### Automated Price Updates
- Real-time price fetching every 30 minutes (configurable)
- NSE/BSE stock prices, AMFI mutual fund NAVs, CoinGecko/Binance crypto prices
- USD-to-INR conversion for US stocks with live forex rates
- MCX commodity prices

### Portfolio Dashboard
- Total portfolio valuation with gain/loss metrics
- Performance charts (invested vs. current value over time)
- Asset allocation with drill-down pie charts
- Top and bottom performers
- Recent transactions

### End-of-Day (EOD) Snapshots
- Daily portfolio snapshots captured automatically at 7 PM IST
- Full historical performance tracking (7d, 30d, 90d, 6m, 1y views)
- Missed snapshot recovery on app restart

### AI-Powered News & Alerts
- Automated market news analysis twice daily (9 AM & 6 PM IST)
- Supports OpenAI (ChatGPT) or xAI (Grok) as AI providers
- Severity-based alerts: INFO, WARNING, CRITICAL
- Smart filtering for actionable, portfolio-relevant information only

### Expense Tracking
- Upload bank/credit card statements to auto-extract expenses
- AI-powered automatic expense categorization
- Expense dashboard with monthly trends and category breakdowns
- Customizable expense categories

### Asset Attributes & Insights
- Custom tagging system for assets (e.g., "Long-term", "Index Fund", "US Holdings")
- Bulk attribute assignment across multiple assets
- Attribute-based analytics and performance insights
- Asset-level insights with detailed performance analysis

### Multi-Portfolio Support
- Create separate portfolios (personal, spouse, retirement, children)
- Independent tracking per portfolio
- Full portfolio export/import (v5.0 format with backward compatibility to v1.0)
- Complete data backup and restore with automatic ID remapping

### Additional Features
- **SIP Creator** — Generate SIP transactions for mutual funds
- **Mutual Fund Holdings** — View top stocks held across your MF portfolio
- **Multi-Account Support** — Bank, demat, and crypto accounts with independent cash balances
- **Transaction History** — Complete audit trail with buy, sell, dividend, interest, and more
- **XIRR Calculations** — Annualized returns using full transaction history

## Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL 15
- **ORM**: SQLAlchemy 2.0
- **Cache**: Redis 7
- **Authentication**: JWT tokens (python-jose)
- **Scheduling**: APScheduler (price updates, EOD snapshots, news fetching)
- **Statement Processing**: PyPDF2, pandas, openpyxl
- **AI Integration**: OpenAI (ChatGPT), xAI (Grok)

### Frontend
- **Framework**: React 18 with TypeScript
- **UI Library**: Material-UI (MUI) 5
- **State Management**: Redux Toolkit
- **Charts**: Recharts
- **Routing**: React Router 6
- **API Client**: Axios

### Infrastructure
- **Containerization**: Docker & Docker Compose
- **File Storage**: MinIO (S3-compatible)
- **Reverse Proxy**: Nginx
- **Database**: PostgreSQL 15 (Alpine)

## Getting Started

### One-Command Install (Recommended)

```bash
git clone https://github.com/debasisdas1976/PortAct.git && cd PortAct && ./install.sh
```

Or if you've already cloned the repository:
```bash
./install.sh
```

**Options:**
- `./install.sh` — Full install and launch
- `./install.sh --no-start` — Install only, don't launch
- `./install.sh --seed-demo` — Install with a demo user and sample data

Once complete, open your browser:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

### Alternative: Docker Setup

```bash
git clone https://github.com/debasisdas1976/PortAct.git
cd PortAct
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
docker-compose up -d
```

### Alternative: Manual Local Development

**Prerequisites:** Python 3.11+, Node.js 18+, PostgreSQL 15

#### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

#### Frontend
```bash
cd frontend
npm install
npm start
```

## Project Structure

```
PortAct/
├── backend/                 # FastAPI backend application
│   ├── app/
│   │   ├── api/            # API routes (40+ endpoint groups)
│   │   ├── core/           # Core config, enums, database, security
│   │   ├── models/         # SQLAlchemy models (15+ models)
│   │   ├── schemas/        # Pydantic request/response schemas
│   │   ├── services/       # Business logic (price updater, parsers, scheduler, etc.)
│   │   └── utils/          # Utility functions
│   ├── tests/              # Backend tests
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/               # React frontend application
│   ├── src/
│   │   ├── components/     # Reusable UI components
│   │   ├── pages/          # 65+ page components
│   │   ├── services/       # API service layer
│   │   ├── store/          # Redux store and slices
│   │   └── utils/          # Utility functions
│   ├── package.json
│   └── Dockerfile
├── docs/                   # Detailed documentation (20+ guides)
├── scripts/                # Setup and utility scripts
├── infrastructure/         # Docker Compose, Nginx config
├── install.sh              # One-command installation script
└── README.md
```

## Background Scheduled Tasks

| Task | Schedule | Description |
|------|----------|-------------|
| Price Update | Every 30 min | Fetches latest prices for all active assets |
| EOD Snapshot | Daily 7 PM IST | Captures daily portfolio state for historical tracking |
| Monthly Contributions | 1st of each month | Auto-updates PF and Gratuity balances |
| Forex Refresh | Daily | Updates USD-to-INR and other FX rates |
| News & Alerts | 9 AM & 6 PM IST | AI-powered market news relevant to your portfolio |

## Documentation

Detailed documentation is available in the [docs/](docs/) directory:

- [Quick Start Guide](docs/QUICK_START.md)
- [Installation Guide](docs/INSTALLATION.md)
- [API Documentation](docs/API_DOCUMENTATION.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [DevOps Guide](docs/DEVOPS.md)
- [EOD Snapshot System](docs/EOD_SNAPSHOT_SYSTEM.md)
- [AI News & Alerts](docs/AI_NEWS_ALERTS_SYSTEM.md)
- [Price Update System](docs/PRICE_UPDATE_SYSTEM.md)
- [Mutual Fund Holdings](docs/MUTUAL_FUND_HOLDINGS_FEATURE.md)
- [UI Documentation](docs/UI_DOCUMENTATION.md)
- [Project Summary](docs/PROJECT_SUMMARY.md)

## API Documentation

Once the backend is running, visit http://localhost:8000/docs for interactive API documentation (Swagger UI).

## Contributing

This is a personal project. For major changes, please open an issue first to discuss what you would like to change.

## License

MIT License — See LICENSE file for details.

## Support

For issues and questions, please create an issue in the repository.
