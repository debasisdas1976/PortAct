# PortAct API Documentation

## Base URL
```
http://localhost:8000/api/v1
```

## Authentication

All endpoints except `/auth/register` and `/auth/login` require authentication using JWT Bearer tokens.

### Headers
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

---

## Authentication Endpoints

### Register User
**POST** `/auth/register`

Create a new user account.

**Request Body:**
```json
{
  "email": "user@example.com",
  "username": "johndoe",
  "password": "securepassword123",
  "full_name": "John Doe"
}
```

**Response:** `201 Created`
```json
{
  "id": 1,
  "email": "user@example.com",
  "username": "johndoe",
  "full_name": "John Doe",
  "is_active": true,
  "is_superuser": false,
  "created_at": "2024-01-01T00:00:00Z"
}
```

### Login
**POST** `/auth/login`

Authenticate and receive access tokens.

**Request Body:** (Form Data)
```
username: johndoe
password: securepassword123
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### Refresh Token
**POST** `/auth/refresh`

Get a new access token using refresh token.

**Request Body:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

---

## User Endpoints

### Get Current User
**GET** `/users/me`

Get current authenticated user information.

**Response:** `200 OK`
```json
{
  "id": 1,
  "email": "user@example.com",
  "username": "johndoe",
  "full_name": "John Doe",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z"
}
```

### Update Current User
**PUT** `/users/me`

Update current user information.

**Request Body:**
```json
{
  "full_name": "John Updated Doe",
  "email": "newemail@example.com"
}
```

---

## Asset Endpoints

### Get All Assets
**GET** `/assets/`

Get all assets for the current user.

**Query Parameters:**
- `asset_type` (optional): Filter by asset type (stock, mutual_fund, crypto, etc.)
- `is_active` (optional): Filter by active status (true/false)
- `skip` (optional): Number of records to skip (default: 0)
- `limit` (optional): Maximum records to return (default: 100)

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "user_id": 1,
    "asset_type": "stock",
    "name": "Apple Inc.",
    "symbol": "AAPL",
    "quantity": 10,
    "purchase_price": 150.00,
    "current_price": 180.00,
    "total_invested": 1500.00,
    "current_value": 1800.00,
    "profit_loss": 300.00,
    "profit_loss_percentage": 20.00,
    "is_active": true,
    "details": {
      "exchange": "NASDAQ",
      "sector": "Technology"
    },
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

### Get Portfolio Summary
**GET** `/assets/summary`

Get aggregated portfolio metrics.

**Response:** `200 OK`
```json
{
  "total_assets": 15,
  "total_invested": 50000.00,
  "total_current_value": 55000.00,
  "total_profit_loss": 5000.00,
  "total_profit_loss_percentage": 10.00,
  "assets_by_type": {
    "stock": 5,
    "mutual_fund": 3,
    "crypto": 2,
    "fixed_deposit": 5
  }
}
```

### Get Single Asset
**GET** `/assets/{asset_id}`

Get details of a specific asset.

**Response:** `200 OK`

### Create Asset
**POST** `/assets/`

Create a new asset.

**Request Body:**
```json
{
  "asset_type": "stock",
  "name": "Apple Inc.",
  "symbol": "AAPL",
  "quantity": 10,
  "purchase_price": 150.00,
  "current_price": 150.00,
  "total_invested": 1500.00,
  "purchase_date": "2024-01-01T00:00:00Z",
  "details": {
    "exchange": "NASDAQ",
    "sector": "Technology"
  }
}
```

**Response:** `201 Created`

### Update Asset
**PUT** `/assets/{asset_id}`

Update an existing asset.

**Request Body:**
```json
{
  "current_price": 180.00,
  "notes": "Updated price"
}
```

**Response:** `200 OK`

### Delete Asset
**DELETE** `/assets/{asset_id}`

Delete an asset.

**Response:** `204 No Content`

---

## Transaction Endpoints

### Get All Transactions
**GET** `/transactions/`

Get all transactions for the current user.

**Query Parameters:**
- `asset_id` (optional): Filter by asset
- `transaction_type` (optional): Filter by type (buy, sell, dividend, etc.)
- `start_date` (optional): Filter from date
- `end_date` (optional): Filter to date
- `skip` (optional): Pagination offset
- `limit` (optional): Pagination limit

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "asset_id": 1,
    "transaction_type": "buy",
    "transaction_date": "2024-01-01T00:00:00Z",
    "quantity": 10,
    "price_per_unit": 150.00,
    "total_amount": 1500.00,
    "fees": 10.00,
    "taxes": 5.00,
    "description": "Purchase of AAPL shares",
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

### Create Transaction
**POST** `/transactions/`

Create a new transaction.

**Request Body:**
```json
{
  "asset_id": 1,
  "transaction_type": "buy",
  "transaction_date": "2024-01-01T00:00:00Z",
  "quantity": 10,
  "price_per_unit": 150.00,
  "total_amount": 1500.00,
  "fees": 10.00,
  "taxes": 5.00,
  "description": "Purchase of AAPL shares"
}
```

**Response:** `201 Created`

---

## Statement Endpoints

### Upload Statement
**POST** `/statements/upload`

Upload a financial statement for processing.

**Request:** (Multipart Form Data)
- `file`: File to upload (PDF, CSV, Excel)
- `statement_type`: Type of statement (bank_statement, broker_statement, etc.)
- `institution_name`: Name of financial institution
- `password` (optional): Password for encrypted PDFs (e.g., NSDL CAS)

**Supported Brokers:**
- **Zerodha**: Excel format with holdings data
- **ICICI Direct**:
  - Stock Portfolio CSV (columns: Stock Symbol, Company Name, ISIN Code, Qty, Average Cost Price, Current Market Price)
  - Mutual Fund CSV (columns: Fund, Scheme, Folio, Units, Last recorded NAV-Rs, Total value at NAV)
- **NSDL/CDSL CAS**: Password-protected PDF with consolidated account statement
- **Other brokers**: Generic CSV/Excel formats

**Response:** `201 Created`
```json
{
  "statement_id": 1,
  "filename": "statement.pdf",
  "status": "uploaded",
  "message": "Statement uploaded and processing started"
}
```

### Get All Statements
**GET** `/statements/`

Get all uploaded statements.

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "filename": "statement.pdf",
    "statement_type": "broker_statement",
    "status": "processed",
    "assets_found": 5,
    "transactions_found": 20,
    "uploaded_at": "2024-01-01T00:00:00Z"
  }
]
```

---

## Alert Endpoints

### Get All Alerts
**GET** `/alerts/`

Get all alerts for the current user.

**Query Parameters:**
- `is_read` (optional): Filter by read status
- `is_dismissed` (optional): Filter by dismissed status
- `severity` (optional): Filter by severity (info, warning, critical)

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "alert_type": "price_change",
    "severity": "warning",
    "title": "Significant Price Drop",
    "message": "AAPL has dropped by 5% today",
    "suggested_action": "Consider reviewing your position",
    "is_read": false,
    "is_dismissed": false,
    "alert_date": "2024-01-01T00:00:00Z"
  }
]
```

### Mark Alert as Read
**PATCH** `/alerts/{alert_id}`

Update alert status.

**Request Body:**
```json
{
  "is_read": true
}
```

---

## Dashboard Endpoints

### Get Dashboard Overview
**GET** `/dashboard/overview`

Get comprehensive dashboard data.

**Response:** `200 OK`
```json
{
  "portfolio_summary": {
    "total_assets": 15,
    "total_invested": 50000.00,
    "total_current_value": 55000.00,
    "total_profit_loss": 5000.00,
    "total_profit_loss_percentage": 10.00
  },
  "assets_by_type": {
    "stock": 5,
    "mutual_fund": 3
  },
  "value_by_type": {
    "stock": 30000.00,
    "mutual_fund": 25000.00
  },
  "recent_transactions": [...],
  "unread_alerts": 3,
  "top_performers": [...],
  "bottom_performers": [...],
  "monthly_investment_trend": [...]
}
```

### Get Asset Allocation
**GET** `/dashboard/asset-allocation`

Get asset allocation breakdown.

**Response:** `200 OK`
```json
{
  "total_value": 55000.00,
  "allocation": {
    "stock": {
      "value": 30000.00,
      "percentage": 54.55,
      "count": 5
    },
    "mutual_fund": {
      "value": 25000.00,
      "percentage": 45.45,
      "count": 3
    }
  }
}
```

---

## Asset Types

Supported asset types:
- `stock` - Stocks and equities
- `mutual_fund` - Mutual funds
- `commodity` - Gold, silver, etc.
- `crypto` - Cryptocurrencies
- `savings_account` - Savings accounts
- `recurring_deposit` - Recurring deposits
- `fixed_deposit` - Fixed deposits
- `real_estate` - Real estate properties
- `ppf` - Public Provident Fund
- `pf` - Provident Fund
- `nps` - National Pension System
- `ssy` - Sukanya Samriddhi Yojana
- `insurance_policy` - Insurance policies

## Transaction Types

- `buy` - Purchase of assets
- `sell` - Sale of assets
- `deposit` - Deposits
- `withdrawal` - Withdrawals
- `dividend` - Dividend received
- `interest` - Interest earned
- `bonus` - Bonus shares
- `split` - Stock split
- `transfer_in` - Transfer in
- `transfer_out` - Transfer out
- `fee` - Fees paid
- `tax` - Taxes paid

## Error Responses

All endpoints may return the following error responses:

### 400 Bad Request
```json
{
  "detail": "Invalid request data"
}
```

### 401 Unauthorized
```json
{
  "detail": "Could not validate credentials"
}
```

### 403 Forbidden
```json
{
  "detail": "Not enough privileges"
}
```

### 404 Not Found
```json
{
  "detail": "Resource not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

---

## Interactive Documentation

For interactive API documentation with the ability to test endpoints:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc