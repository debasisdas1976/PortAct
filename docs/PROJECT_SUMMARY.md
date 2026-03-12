# PortAct - Project Summary

## Overview

PortAct is a comprehensive, privacy-first personal finance portfolio tracking application that enables users to manage and monitor their investments across 30+ asset classes. It runs entirely on your local machine — no third-party data sharing required.

**Current Version**: 1.9.0 | **Export Version**: 5.0 (backward compatible to v1.0)

[![Watch the Introduction Video](https://img.shields.io/badge/YouTube-Watch%20Introduction-red?logo=youtube)](https://www.youtube.com/watch?v=hoEDYFW2LZs)

## What Has Been Built

### Complete Backend API (Python/FastAPI)

#### Core Infrastructure
- **FastAPI Application** with automatic API documentation (Swagger/ReDoc)
- **PostgreSQL 15 Database** with SQLAlchemy 2.0 ORM and Alembic migrations
- **JWT Authentication** with access and refresh tokens
- **APScheduler** for background jobs (price updates, snapshots, news, forex)
- **Redis 7** for caching
- **MinIO** for S3-compatible file storage
- **AI Integration** with OpenAI (ChatGPT) and xAI (Grok)

#### Database Models (15+)
1. **User** — Authentication, profile, preferences
2. **Asset** — Universal model supporting 30+ asset types with flexible JSON `details` field
3. **Transaction** — Complete audit trail with 12+ transaction types
4. **Portfolio** — Multi-portfolio support with independent tracking
5. **Bank Account** — Savings, FD, RD, credit card accounts
6. **Demat Account** — Stock broker accounts with cash balance tracking
7. **Crypto Account** — Multiple crypto exchange accounts
8. **Statement** — Uploaded statement metadata and processing status
9. **Alert** — News, events, and custom alerts with severity levels
10. **Portfolio Snapshot** — Daily EOD portfolio state (via `snapshot_source` discriminator)
11. **Asset Snapshot** — Daily per-asset valuations for historical tracking
12. **Expense** — Expense tracking with categories and AI categorization
13. **Expense Category** — Customizable expense categories
14. **Asset Type** — Master table for 30+ asset types (VARCHAR FK, not PG enum)
15. **Asset Attribute** — Custom tagging and classification system
16. **Mutual Fund Holding** — MF portfolio composition data
17. **App Settings** — Configurable system settings stored in DB

#### API Endpoints (100+ routes across 40+ endpoint groups)

**Authentication & Users**
- Registration, login, JWT refresh, profile management, account deletion

**Asset Management**
- CRUD for all 30+ asset types
- Portfolio summary with aggregated metrics
- Asset filtering, pagination, and search
- Automatic profit/loss and metric calculations
- Single and bulk price refresh with progress tracking
- Asset type reassignment

**Account Management**
- Bank accounts (savings, credit card) with statement upload
- Demat accounts with holdings import and cash balance
- Crypto accounts with multi-exchange support

**Transaction Management**
- CRUD with date/type/asset filtering
- Automatic asset updates from transactions
- Fee and tax tracking
- Tradebook import

**Statement Processing**
- File upload (PDF, CSV, Excel)
- Bank-specific parsers: ICICI, HDFC, IDFC First, SBI, Axis, Kotak
- Broker parsers: Zerodha, ICICI Direct, NSDL/CDSL CAS, Upstox, Angel One
- Tradebook parsing for trade history
- MF holdings Excel parser
- Processing status tracking

**Portfolio & Dashboard**
- Multi-portfolio management
- Comprehensive dashboard: summary cards, performance charts, asset allocation
- Top/bottom performers, recent transactions
- Portfolio export/import (v5.0 with backward compat to v1.0, auto ID remapping)

**EOD Snapshot System**
- Daily portfolio snapshots at 7 PM IST
- Per-asset historical valuations
- Missed snapshot recovery on startup
- Flexible views: 7d, 30d, 90d, 6m, 1y

**AI News & Alerts**
- Automated news analysis (9 AM & 6 PM IST)
- OpenAI/Grok integration
- INFO/WARNING/CRITICAL severity levels
- Smart filtering for portfolio-relevant news

**Insights & Analytics**
- Asset-level insights with detailed performance
- Attribute-based insights (performance grouped by tags)
- Maturity Timeline — visual timeline of upcoming maturity dates for FDs, RDs, bonds, government schemes, insurance, and SGBs with status badges and projected values
- Mutual fund holdings — top stocks across MF portfolio
- XIRR calculations using transaction history

**Expenses**
- CRUD with bank statement auto-import
- AI-powered categorization
- Expense dashboard with monthly trends and category breakdowns
- Customizable expense categories

**Master Data**
- Asset types, asset attributes, banks, brokers, crypto exchanges, institutions
- Expense categories

**System & Configuration**
- Application settings (price update interval, EOD time, monthly contributions)
- SIP transaction creator
- System health and information

#### Background Services (APScheduler)

| Task | Schedule | Description |
|------|----------|-------------|
| Price Update | Every 30 min (configurable) | Fetches latest prices for all active assets |
| EOD Snapshot | Daily 7 PM IST | Captures daily portfolio state for historical tracking |
| Monthly Contributions | 1st of each month | Auto-updates PF and Gratuity balances |
| Forex Refresh | Daily + before EOD | Updates USD-to-INR and other FX rates |
| News & Alerts | 9 AM & 6 PM IST | AI-powered market news relevant to portfolio |

#### Price Update Coverage
- **Stocks**: NSE/BSE via broker APIs
- **Mutual Funds**: AMFI API with fuzzy name matching
- **US Stocks**: Market data APIs with real-time USD-to-INR conversion
- **Crypto**: CoinGecko, Binance APIs
- **Commodities**: MCX data
- **Forex**: Live USD-to-INR rates

### Complete Frontend (React/TypeScript)

#### 65+ Pages/Routes
- **Dashboard** — Portfolio overview, performance charts, asset allocation
- **Asset Overview** — All assets in one page with type-based tabs and price refresh
- **30+ Asset Management Pages** — Dedicated page per asset type (stocks, MFs, FDs, real estate, etc.)
- **Account Pages** — Bank, demat, and crypto account management
- **Insights** — Asset insights, attribute insights, maturity timeline, mutual fund holdings
- **Expenses** — Expense dashboard, expense list, category management
- **Statements** — Upload and manage bank/broker/tradebook statements
- **Alerts** — AI-powered market news and portfolio alerts
- **Administration** — Portfolios, portfolio admin (export/import), application settings
- **Master Data** — Asset types, attributes, banks, brokers, crypto exchanges, expense categories
- **Utilities** — SIP creator, help page
- **Auth** — Login, register, forgot/reset password
- **Super Admin** — System administration

#### Frontend Architecture
- React 18 with TypeScript 4.9
- Material-UI (MUI) 5.15 component library
- Redux Toolkit 2.1 for state management
- React Router 6 for navigation
- Recharts 2.12 for charts and visualizations
- Axios 1.6 for API communication
- Responsive design for desktop/laptop use

### Infrastructure & DevOps

#### Docker Configuration
- **Backend Dockerfile** — Multi-stage Python build
- **Frontend Dockerfile** — Multi-stage Node build with Nginx
- **Docker Compose** — Complete orchestration:
  - PostgreSQL 15 (Alpine)
  - Redis 7 (Alpine)
  - MinIO object storage
  - Backend API
  - Frontend application
  - Nginx reverse proxy

#### One-Command Installation
- `./install.sh` — Automated setup with dependency checking, environment configuration, service startup, and health checks
- `./install.sh --seed-demo` — Setup with demo user and sample data
- `./install.sh --no-start` — Install only without launching

## Key Features Summary

### 1. 30+ Asset Types
- Single unified system for stocks, mutual funds, commodities, bonds, deposits, real estate, crypto, government schemes, and more
- Flexible JSON `details` field for asset-specific metadata (exchange, sector, interest rate, wallet address, property details, USD equivalents)
- Automatic metric calculations (profit/loss, percentages, XIRR)

### 2. Smart Statement Processing
- Upload bank/broker/tradebook statements (PDF, CSV, Excel)
- Bank-specific parsers: ICICI, HDFC, IDFC First, SBI, Axis, Kotak
- Broker parsers: Zerodha, ICICI Direct, NSDL/CDSL CAS, Upstox, Angel One
- Auto-extraction of assets, transactions, and expenses
- AI-powered expense categorization

### 3. Automated Price Updates
- Every 30 minutes (configurable via App Settings)
- Covers stocks (NSE/BSE), mutual funds (AMFI), crypto (CoinGecko/Binance), commodities (MCX)
- US stock prices with live USD-to-INR conversion
- Price update tracking with error logs

### 4. EOD Snapshot System
- Daily portfolio snapshots at 7 PM IST
- Full historical performance tracking
- Missed snapshot recovery
- Supports 7d, 30d, 90d, 6m, 1y views

### 5. AI-Powered News & Alerts
- Twice-daily automated analysis (9 AM & 6 PM IST)
- OpenAI (ChatGPT) or xAI (Grok) as AI provider
- Severity-based: INFO, WARNING, CRITICAL
- Smart filtering for actionable, portfolio-relevant information

### 6. Expense Tracking
- Auto-import from bank/credit card statements
- AI-powered automatic categorization
- Monthly trends and category breakdowns
- Customizable categories

### 7. Asset Attributes & Insights
- Custom tagging system (e.g., "Long-term", "Index Fund", "US Holdings")
- Bulk attribute assignment
- Attribute-based performance analytics
- Asset-level insights
- Maturity Timeline for assets with maturity dates (13 asset types)

### 7a. Day Change % Tracking
- Real-time daily price change percentage for every asset
- Weighted-average Day Change % for asset groups on the Assets Overview page
- Day Change summary card on all 30+ asset type pages and the main Dashboard
- Data sourced from Yahoo Finance, NSE, CoinGecko, and other market APIs
- Fallback to EOD snapshot price when API data is unavailable

### 8. Multi-Portfolio Management
- Create separate portfolios per person or purpose
- Portfolio export/import v5.0 (backward compat to v1.0)
- Full data backup/restore with automatic ID remapping
- Covers: assets, transactions, accounts, snapshots, expenses, alerts

### 9. Dashboard & Visualization
- Portfolio summary cards (total value, invested, gain/loss, asset count, day change)
- Performance charts: invested vs. current value over time
- Asset allocation pie chart with drill-down
- Top/bottom performers
- Recent transactions

### 10. Multi-Account Support
- Bank accounts (savings, credit card) with statement upload
- Demat accounts (broker accounts) with cash balance tracking
- Crypto accounts (multiple exchanges)
- Independent cash balances aggregated in portfolio total

### 11. US Stock Support
- DB stores all prices in INR
- Details JSON stores USD equivalents (`avg_cost_usd`, `price_usd`, `market_value_usd`, `usd_to_inr_rate`)
- Backend auto-converts USD-to-INR on create/update
- Live forex rate updates

### 12. Security
- JWT-based authentication with refresh tokens
- Password hashing with bcrypt
- User-specific data isolation
- Environment-based configuration
- SQL injection prevention (SQLAlchemy ORM)
- CORS configuration

## Technology Stack

### Backend
- **Framework**: FastAPI 0.109+
- **Language**: Python 3.11+
- **Database**: PostgreSQL 15
- **ORM**: SQLAlchemy 2.0
- **Migrations**: Alembic
- **Cache**: Redis 7
- **Authentication**: JWT (python-jose)
- **Scheduling**: APScheduler
- **File Processing**: PyPDF2, pandas, openpyxl
- **AI**: OpenAI (ChatGPT), xAI (Grok)
- **API Documentation**: Swagger UI, ReDoc

### Frontend
- **Framework**: React 18
- **Language**: TypeScript 4.9
- **UI Library**: Material-UI (MUI) 5.15
- **State Management**: Redux Toolkit 2.1
- **Routing**: React Router 6
- **Charts**: Recharts 2.12
- **HTTP Client**: Axios 1.6
- **Styling**: Emotion (CSS-in-JS)

### Infrastructure
- **Containerization**: Docker & Docker Compose
- **Database**: PostgreSQL 15 (Alpine)
- **Cache**: Redis 7 (Alpine)
- **Object Storage**: MinIO (S3-compatible)
- **Reverse Proxy**: Nginx

## Documentation

| Document | Description |
|----------|-------------|
| [README.md](../README.md) | Project overview and quick start |
| [QUICK_START.md](QUICK_START.md) | Quick start guide |
| [INSTALLATION.md](INSTALLATION.md) | Detailed installation instructions |
| [API_DOCUMENTATION.md](API_DOCUMENTATION.md) | Complete API reference |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Production deployment guide |
| [DEVOPS.md](DEVOPS.md) | DevOps and infrastructure |
| [UI_DOCUMENTATION.md](UI_DOCUMENTATION.md) | Frontend UI guide |
| [EOD_SNAPSHOT_SYSTEM.md](EOD_SNAPSHOT_SYSTEM.md) | EOD snapshot architecture |
| [AI_NEWS_ALERTS_SYSTEM.md](AI_NEWS_ALERTS_SYSTEM.md) | AI alerts setup |
| [AI_NEWS_SETUP_GUIDE.md](AI_NEWS_SETUP_GUIDE.md) | AI news configuration |
| [PRICE_UPDATE_SYSTEM.md](PRICE_UPDATE_SYSTEM.md) | Price update system |
| [MUTUAL_FUND_HOLDINGS_FEATURE.md](MUTUAL_FUND_HOLDINGS_FEATURE.md) | MF holdings feature |
| [MF_HOLDINGS_UPLOAD_GUIDE.md](MF_HOLDINGS_UPLOAD_GUIDE.md) | MF holdings upload guide |
