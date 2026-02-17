# PortAct - Personal Finance Portfolio Tracker

A comprehensive web/mobile application for tracking and managing your personal finance portfolio across multiple asset classes.

## Features

### Asset Tracking Modules
1. **Stocks and Mutual Funds Tracker** - Track equity investments, SIPs, and mutual fund holdings
2. **Commodity Tracker** - Monitor gold, silver, and other commodity investments
3. **Crypto Tracker** - Track cryptocurrency holdings and transactions
4. **Banks Tracker** - Manage savings accounts, recurring deposits (RD), and fixed deposits (FD)
5. **Real Estate Tracker** - Track property investments and valuations
6. **Government Schemes Tracker** - Monitor PPF, PF, NPS, SSY, and insurance policies

### Core Capabilities
- **Statement Upload** - Upload bank statements, broker statements, and transaction records
- **Intelligent Processing** - Automated extraction of assets and transactions from statements
- **Multi-Broker Support** - Supports Zerodha, ICICI Direct, NSDL/CDSL CAS, and more
- **Asset Management** - View all assets with current valuations and historical performance
- **Transaction History** - Complete audit trail of all transactions
- **Profit/Loss Analysis** - Real-time calculation of gains and losses
- **News & Alerts** - Actionable insights based on market events affecting your portfolio

### Supported Brokers & Formats
- **Zerodha** - Excel holdings export
- **ICICI Direct** - Stock portfolio CSV and Mutual Fund CSV
- **NSDL/CDSL CAS** - Consolidated Account Statement (password-protected PDF)
- **Generic formats** - CSV and Excel files with standard columns

## Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL 15
- **ORM**: SQLAlchemy
- **Authentication**: JWT tokens
- **Statement Processing**: PyPDF2, pandas, OpenAI API

### Frontend
- **Framework**: React 18 with TypeScript
- **UI Library**: Material-UI (MUI)
- **State Management**: Redux Toolkit
- **Charts**: Recharts
- **API Client**: Axios

### Infrastructure
- **Containerization**: Docker & Docker Compose
- **Reverse Proxy**: Nginx
- **File Storage**: MinIO (S3-compatible)

## Project Structure

```
PortAct/
├── backend/                 # FastAPI backend application
│   ├── app/
│   │   ├── api/            # API routes
│   │   ├── core/           # Core configurations
│   │   ├── models/         # Database models
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # Business logic
│   │   └── utils/          # Utility functions
│   ├── tests/              # Backend tests
│   ├── requirements.txt    # Python dependencies
│   └── Dockerfile
├── frontend/               # React frontend application
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── pages/          # Page components
│   │   ├── services/       # API services
│   │   ├── store/          # Redux store
│   │   └── utils/          # Utility functions
│   ├── package.json
│   └── Dockerfile
├── infrastructure/         # Infrastructure as code
│   ├── docker-compose.yml
│   ├── nginx/
│   └── scripts/
└── README.md
```

## Getting Started

### Prerequisites
- Docker and Docker Compose
- Node.js 18+ (for local frontend development)
- Python 3.11+ (for local backend development)

### Quick Start with Docker

1. Clone the repository
```bash
git clone <repository-url>
cd PortAct
```

2. Set up environment variables
```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
# Edit the .env files with your configurations
```

3. Start all services
```bash
docker-compose up -d
```

4. Access the application
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

### Local Development

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

## API Documentation

Once the backend is running, visit http://localhost:8000/docs for interactive API documentation (Swagger UI).

## Database Schema

The application uses PostgreSQL with the following main tables:
- `users` - User accounts and authentication
- `assets` - All asset records across different types
- `transactions` - Transaction history for all assets
- `statements` - Uploaded statement metadata
- `news_events` - Market news and events
- `alerts` - User-specific alerts and notifications

## Contributing

This is a personal project. For major changes, please open an issue first to discuss what you would like to change.

## License

MIT License - See LICENSE file for details

## Support

For issues and questions, please create an issue in the repository.# PortAct
