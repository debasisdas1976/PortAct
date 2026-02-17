# PortAct - Quick Start Guide

## 🚀 Resolve Import Errors & Get Started

### Step 1: Install Dependencies (Fixes Import Errors)

Run this single command to install all dependencies and resolve import errors:

```bash
./install-dependencies.sh
```

This will:
- ✅ Create Python virtual environment
- ✅ Install all Python packages (FastAPI, SQLAlchemy, etc.)
- ✅ Install all Node.js packages (React, MUI, etc.)
- ✅ Verify installations
- ✅ Fix all import errors in your IDE

### Step 2: Configure Your IDE

#### VS Code
1. Press `Cmd+Shift+P` (Mac) or `Ctrl+Shift+P` (Windows/Linux)
2. Type "Python: Select Interpreter"
3. Select: `./backend/venv/bin/python`
4. Reload window: `Cmd+Shift+P` → "Developer: Reload Window"

#### PyCharm
1. Settings → Project → Python Interpreter
2. Add → Existing Environment
3. Select: `./backend/venv/bin/python`
4. Apply and restart

### Step 3: Run the Application

#### Option A: Docker (Recommended - No local setup needed)
```bash
./setup.sh
```

#### Option B: Local Development
```bash
# Terminal 1 - Backend
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 - Frontend  
cd frontend
npm start

# Terminal 3 - Database (if not using Docker)
# Make sure PostgreSQL is running locally
```

### Step 4: Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs (Interactive Swagger UI)
- **Alternative Docs**: http://localhost:8000/redoc

## 📋 Verification Checklist

After running `./install-dependencies.sh`, verify:

- [ ] No import errors in `backend/app/` files
- [ ] Python packages installed: `cd backend && source venv/bin/activate && pip list`
- [ ] Node packages installed: `cd frontend && npm list --depth=0`
- [ ] IDE recognizes imports (no red underlines)

## 🔧 Common Issues

### Issue: Still seeing import errors after installation

**Solution**:
```bash
# Reload your IDE
# VS Code: Cmd+Shift+P → "Developer: Reload Window"
# PyCharm: File → Invalidate Caches / Restart
```

### Issue: "python3: command not found"

**Solution**: Install Python 3.11+
```bash
# macOS
brew install python@3.11

# Ubuntu/Debian
sudo apt-get install python3.11

# Windows
# Download from python.org
```

### Issue: "node: command not found"

**Solution**: Install Node.js 18+
```bash
# macOS
brew install node

# Ubuntu/Debian
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Windows
# Download from nodejs.org
```

### Issue: "Permission denied" when running scripts

**Solution**:
```bash
chmod +x install-dependencies.sh
chmod +x setup.sh
```

## 📚 Next Steps

1. **Test the API**
   - Visit http://localhost:8000/docs
   - Try the `/health` endpoint
   - Register a user via `/auth/register`

2. **Create Your First Asset**
   ```bash
   # Register
   curl -X POST "http://localhost:8000/api/v1/auth/register" \
     -H "Content-Type: application/json" \
     -d '{
       "email": "test@example.com",
       "username": "testuser",
       "password": "password123",
       "full_name": "Test User"
     }'
   
   # Login (get token)
   curl -X POST "http://localhost:8000/api/v1/auth/login" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=testuser&password=password123"
   
   # Create asset (use token from login)
   curl -X POST "http://localhost:8000/api/v1/assets/" \
     -H "Authorization: Bearer YOUR_TOKEN_HERE" \
     -H "Content-Type: application/json" \
     -d '{
       "asset_type": "stock",
       "name": "Apple Inc.",
       "symbol": "AAPL",
       "quantity": 10,
       "purchase_price": 150.00,
       "current_price": 150.00,
       "total_invested": 1500.00
     }'
   ```

3. **Explore the Dashboard**
   - GET `/api/v1/dashboard/overview` - Portfolio summary
   - GET `/api/v1/assets/summary` - Asset allocation
   - GET `/api/v1/transactions/` - Transaction history

## 📖 Documentation

- **[README.md](README.md)** - Project overview
- **[INSTALLATION.md](INSTALLATION.md)** - Detailed installation guide
- **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)** - Complete API reference
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Production deployment
- **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - Technical details

## 🎯 Key Features to Try

1. **Multi-Asset Tracking**
   - Add stocks, mutual funds, crypto, FDs, real estate
   - Track 13 different asset types

2. **Statement Upload**
   - Upload PDF/CSV/Excel statements
   - Automatic asset and transaction extraction

3. **Portfolio Analytics**
   - Real-time profit/loss calculations
   - Asset allocation breakdown
   - Performance trends

4. **Transaction Management**
   - Record buys, sells, dividends
   - Complete audit trail

5. **Alerts**
   - Get notified about important events
   - Actionable suggestions

## 💡 Tips

- Use the interactive API docs at `/docs` to test endpoints
- All endpoints (except auth) require JWT token in header
- Check logs if something doesn't work: `docker-compose logs -f`
- Database is automatically created on first run
- File uploads go to `backend/uploads/`

## 🆘 Need Help?

1. Check the logs:
   ```bash
   # Docker
   cd infrastructure && docker-compose logs -f backend
   
   # Local
   cd backend && tail -f logs/app.log
   ```

2. Verify services:
   ```bash
   # Docker
   docker-compose ps
   
   # Local
   curl http://localhost:8000/health
   ```

3. Review documentation files listed above

## 🎉 You're Ready!

Your PortAct application is now set up and ready to use. Start tracking your portfolio!