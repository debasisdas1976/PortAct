# PortAct Installation Guide

## Resolving Import Errors

The import errors you see in your IDE are expected because the Python dependencies haven't been installed yet. Follow these steps to resolve them:

## Option 1: Quick Start with Docker (Recommended)

This will install all dependencies automatically inside containers:

```bash
# Make setup script executable
chmod +x setup.sh

# Run setup (this installs everything in Docker)
./setup.sh
```

The dependencies will be installed inside the Docker containers, and the application will work perfectly.

## Option 2: Local Development Setup

If you want to develop locally and resolve IDE import errors:

### Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "import fastapi; import sqlalchemy; import pydantic; print('All imports working!')"
```

### Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Verify installation
npm list react
```

## Option 3: Install Dependencies for IDE Support Only

If you just want IDE autocomplete and error checking but will run via Docker:

```bash
# Backend
cd backend
python3 -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```

Then configure your IDE to use the virtual environment:

### VS Code
1. Press `Cmd+Shift+P` (Mac) or `Ctrl+Shift+P` (Windows/Linux)
2. Type "Python: Select Interpreter"
3. Choose the interpreter from `backend/venv/bin/python`

### PyCharm
1. Go to Settings/Preferences → Project → Python Interpreter
2. Click the gear icon → Add
3. Select "Existing environment"
4. Browse to `backend/venv/bin/python`

## Verifying the Installation

### Check Backend Dependencies

```bash
cd backend
source venv/bin/activate
python -c "
import fastapi
import sqlalchemy
import pydantic
import jose
import passlib
print('✓ All core dependencies installed')
"
```

### Check Frontend Dependencies

```bash
cd frontend
npm list --depth=0
```

## Common Issues and Solutions

### Issue: "ModuleNotFoundError: No module named 'fastapi'"

**Solution**: Install dependencies in virtual environment
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

### Issue: "Cannot find module 'react'"

**Solution**: Install npm dependencies
```bash
cd frontend
npm install
```

### Issue: Import errors persist in IDE

**Solution**: 
1. Restart your IDE
2. Ensure IDE is using the correct Python interpreter (venv)
3. Reload the window (VS Code: Cmd+Shift+P → "Reload Window")

### Issue: "pg_config executable not found"

**Solution**: Install PostgreSQL development headers
```bash
# macOS
brew install postgresql

# Ubuntu/Debian
sudo apt-get install libpq-dev

# CentOS/RHEL
sudo yum install postgresql-devel
```

## Running the Application

### With Docker (Recommended)
```bash
cd infrastructure
docker-compose up -d
```

### Local Development
```bash
# Terminal 1 - Backend
cd backend
source venv/bin/activate
uvicorn app.main:app --reload

# Terminal 2 - Frontend
cd frontend
npm start

# Terminal 3 - Database (if not using Docker)
# Start PostgreSQL on your system
```

## Environment Variables

Make sure to set up environment variables:

```bash
# Backend
cd backend
cp .env.example .env
# Edit .env with your settings

# Frontend
cd frontend
cp .env.example .env
# Edit .env with your settings
```

## Database Setup

### With Docker
Database is automatically created and configured.

### Local PostgreSQL
```bash
# Create database
createdb portact_db

# Run migrations (when implemented)
cd backend
alembic upgrade head
```

## Verification Checklist

- [ ] Python virtual environment created
- [ ] Backend dependencies installed (`pip list` shows fastapi, sqlalchemy, etc.)
- [ ] Frontend dependencies installed (`npm list` shows react, @mui/material, etc.)
- [ ] IDE recognizes imports (no red underlines)
- [ ] Environment files created (.env)
- [ ] Docker containers running (if using Docker)
- [ ] Backend accessible at http://localhost:8000
- [ ] Frontend accessible at http://localhost:3000
- [ ] API docs accessible at http://localhost:8000/docs

## Next Steps

Once installation is complete:

1. **Test the API**: Visit http://localhost:8000/docs
2. **Register a user**: Use the `/auth/register` endpoint
3. **Login**: Get your JWT token
4. **Create assets**: Start tracking your portfolio
5. **Upload statements**: Test the statement processing

## Getting Help

If you encounter issues:

1. Check the logs:
   ```bash
   # Docker logs
   docker-compose logs -f backend
   
   # Local logs
   tail -f backend/logs/app.log
   ```

2. Verify services are running:
   ```bash
   docker-compose ps
   ```

3. Check database connection:
   ```bash
   docker exec -it portact-postgres psql -U portact_user -d portact_db
   ```

## Development Workflow

1. **Make changes** to code
2. **Backend**: Auto-reloads with `--reload` flag
3. **Frontend**: Auto-reloads with `npm start`
4. **Test**: Use API docs or frontend
5. **Commit**: Git commit your changes

## Production Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for production deployment instructions.