# DevOps Documentation

## Overview

This document describes the DevOps setup, CI/CD pipeline, and deployment procedures for the PortAct application.

## Repository Structure

```
PortAct/
├── .github/
│   └── workflows/          # GitHub Actions workflows
│       ├── ci-cd.yml       # Main CI/CD pipeline
│       └── dependency-update.yml  # Dependency security checks
├── backend/                # Python FastAPI backend
├── frontend/               # React TypeScript frontend
├── infrastructure/         # Docker and infrastructure configs
└── .gitignore             # Git ignore rules
```

## CI/CD Pipeline

### GitHub Actions Workflows

#### 1. Main CI/CD Pipeline (`ci-cd.yml`)

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches

**Jobs:**

##### Backend Tests
- Sets up Python 3.11 environment
- Starts PostgreSQL test database
- Installs dependencies
- Runs linting (flake8, black, isort)
- Executes pytest with coverage
- Uploads coverage reports to Codecov

##### Frontend Tests
- Sets up Node.js 18 environment
- Installs npm dependencies
- Runs ESLint
- Executes tests with coverage
- Builds production bundle
- Uploads build artifacts

##### Security Scan
- Runs Trivy vulnerability scanner
- Scans filesystem for security issues
- Uploads results to GitHub Security tab

##### Docker Build
- Builds Docker images for backend and frontend
- Tags with `latest` and commit SHA
- Uses layer caching for faster builds
- Pushes to Docker Hub (on main branch only)

##### Deploy
- Deploys to production environment
- Only runs on main branch after successful tests
- Placeholder for deployment strategy (customize based on infrastructure)

#### 2. Dependency Update Check (`dependency-update.yml`)

**Triggers:**
- Scheduled: Every Monday at 9 AM UTC
- Manual trigger via workflow_dispatch

**Jobs:**
- Checks Python dependencies with pip-audit
- Checks npm dependencies with npm audit
- Creates GitHub issue if vulnerabilities found

## Setup Instructions

### 1. GitHub Repository Setup

1. **Create Repository Secrets:**
   Go to Settings → Secrets and variables → Actions, and add:
   
   - `DOCKER_USERNAME`: Your Docker Hub username
   - `DOCKER_PASSWORD`: Your Docker Hub password or access token
   - `AWS_ACCESS_KEY_ID`: (Optional) For AWS deployments
   - `AWS_SECRET_ACCESS_KEY`: (Optional) For AWS deployments

2. **Enable GitHub Actions:**
## Database Initialization

### Available Initialization Scripts

The project includes multiple database initialization scripts for different deployment scenarios:

#### 1. Local Development Setup (`scripts/init_database.sh`)

**Use Case:** Setting up database on local machine with PostgreSQL installed

**Features:**
- Checks PostgreSQL installation and status
- Creates database and user from .env configuration
- Sets up Python virtual environment
- Installs dependencies
- Runs Alembic migrations
- Seeds initial data (expense categories)
- Verifies setup with table count

**Usage:**
```bash
./scripts/init_database.sh
```

**Requirements:**
- PostgreSQL installed locally
- Python 3.11+
- backend/.env file configured

#### 2. Docker-based Setup (`init_database_docker.sh`)

**Use Case:** Setting up database using Docker containers

**Features:**
- Starts PostgreSQL container via docker-compose
- Waits for database to be ready
- Builds backend container
- Runs migrations in container
- Seeds initial data
- Verifies setup

**Usage:**
```bash
./init_database_docker.sh
```

**Requirements:**
- Docker and Docker Compose installed
- infrastructure/docker-compose.yml configured

#### 3. SQL Script (`backend/init.sql`)

**Use Case:** Production database setup or manual initialization

**Features:**
- Creates database user with secure password
- Creates database with proper ownership
- Grants all necessary privileges
- Enables required PostgreSQL extensions (uuid-ossp, pgcrypto)
- Creates audit trigger function for updated_at columns
- Sets default privileges for future tables

**Usage:**
```bash
# As PostgreSQL superuser
psql -U postgres -f backend/init.sql

# Or remotely
psql -h your-db-host -U postgres -f backend/init.sql
```

**Important:** Change the default password in the script before running in production!

#### 4. Legacy Script (`backend/setup_database.sh`)

**Use Case:** Simple database and user creation

**Features:**
- Creates PostgreSQL user and database
- Grants basic privileges
- Provides connection string

**Usage:**
```bash
cd backend
./setup_database.sh
```

### Database Migration Workflow

After initializing the database, manage schema changes with Alembic:

```bash
cd backend
source .venv/bin/activate  # If using virtual environment

# View current migration status
alembic current

# View migration history
alembic history

# Create new migration (auto-generate from models)
alembic revision --autogenerate -m "description of changes"

# Apply all pending migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade <revision_id>
```

### Initial Data Seeding

The application includes a seed script for expense categories:

```bash
cd backend
python seed_categories.py
```

This creates default expense categories like:
- Food & Dining
- Transportation
- Shopping
- Bills & Utilities
- Entertainment
- Healthcare
- etc.

### Database Connection Strings

**Local Development:**
```
postgresql://portact_user:portact_password@localhost:5432/portact_db
```

**Docker:**
```
postgresql://postgres:postgres@postgres:5432/portact_db
```

**Production (example):**
```
postgresql://portact_user:secure_password@db.example.com:5432/portact_db
```

Set in `backend/.env`:
```env
DATABASE_URL=postgresql://user:password@host:port/database
```

   - Go to Settings → Actions → General
   - Enable "Allow all actions and reusable workflows"

3. **Configure Branch Protection:**
   - Go to Settings → Branches
   - Add rule for `main` branch:
     - Require pull request reviews
     - Require status checks to pass
     - Require branches to be up to date

### 2. Local Development Setup

```bash
# Clone repository
git clone https://github.com/debasisdas1976/PortAct.git
cd PortAct

# Backend setup
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your configuration

# Frontend setup
cd ../frontend
npm install
cp .env.example .env
# Edit .env with your configuration

# Run application
cd ..
./scripts/run_app.sh
```

### 3. Docker Setup

```bash
# Build images
docker-compose -f infrastructure/docker-compose.yml build

# Run containers
docker-compose -f infrastructure/docker-compose.yml up -d

# View logs
docker-compose -f infrastructure/docker-compose.yml logs -f

# Stop containers
docker-compose -f infrastructure/docker-compose.yml down
```

## Deployment Strategies

### Option 1: Docker Compose (Simple)

Best for: Small deployments, single server

```bash
# On production server
git pull origin main
docker-compose -f infrastructure/docker-compose.yml up -d --build
```

### Option 2: AWS ECS (Recommended for Production)

1. **Setup ECS Cluster:**
   ```bash
   aws ecs create-cluster --cluster-name portact-cluster
   ```

2. **Create Task Definitions:**
   - Backend task definition
   - Frontend task definition
   - PostgreSQL RDS instance

3. **Configure Load Balancer:**
   - Application Load Balancer
   - Target groups for backend and frontend
   - SSL certificate via ACM

4. **Update CI/CD Pipeline:**
   Uncomment AWS deployment section in `.github/workflows/ci-cd.yml`

### Option 3: Kubernetes

1. **Create Kubernetes Manifests:**
   ```yaml
   # k8s/backend-deployment.yaml
   # k8s/frontend-deployment.yaml
   # k8s/postgres-statefulset.yaml
   # k8s/ingress.yaml
   ```

2. **Deploy to Cluster:**
   ```bash
   kubectl apply -f k8s/
   ```

3. **Update CI/CD Pipeline:**
   Uncomment Kubernetes deployment section in `.github/workflows/ci-cd.yml`

### Option 4: Traditional VM Deployment

1. **Setup Server:**
   ```bash
   # Install dependencies
   sudo apt update
   sudo apt install python3.11 nodejs npm postgresql nginx

   # Clone repository
   git clone https://github.com/debasisdas1976/PortAct.git
   cd PortAct

   # Setup application
   ./scripts/setup.sh
   ```

2. **Configure Nginx:**
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;

       location /api {
           proxy_pass http://localhost:8000;
       }

       location / {
           proxy_pass http://localhost:3000;
       }
   }
   ```

3. **Setup Systemd Services:**
   ```bash
   # Create service files for backend and frontend
   sudo systemctl enable portact-backend
   sudo systemctl enable portact-frontend
   sudo systemctl start portact-backend
   sudo systemctl start portact-frontend
   ```

## Monitoring and Logging

### Application Logs

**Backend:**
```bash
# View logs
tail -f backend.log

# Docker logs
docker logs portact-backend -f
```

**Frontend:**
```bash
# View logs
tail -f frontend.log

# Docker logs
docker logs portact-frontend -f
```

### Recommended Monitoring Tools

1. **Application Performance:**
   - New Relic
   - Datadog
   - AWS CloudWatch

2. **Error Tracking:**
   - Sentry
   - Rollbar

3. **Uptime Monitoring:**
   - UptimeRobot
   - Pingdom

4. **Log Aggregation:**
   - ELK Stack (Elasticsearch, Logstash, Kibana)
   - Splunk
   - AWS CloudWatch Logs

## Database Management

### Migrations

```bash
# Create new migration
cd backend
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

### Backups

**Automated Backups:**
```bash
# Add to crontab
0 2 * * * pg_dump portact > /backups/portact_$(date +\%Y\%m\%d).sql
```

**Manual Backup:**
```bash
pg_dump portact > backup.sql
```

**Restore:**
```bash
psql portact < backup.sql
```

## Security Best Practices

1. **Environment Variables:**
   - Never commit `.env` files
   - Use secrets management (AWS Secrets Manager, HashiCorp Vault)
   - Rotate credentials regularly

2. **Database:**
   - Use strong passwords
   - Enable SSL connections
   - Restrict network access
   - Regular security updates

3. **API Security:**
   - JWT token authentication
   - Rate limiting
   - CORS configuration
   - Input validation

4. **Infrastructure:**
   - Keep dependencies updated
   - Regular security scans
   - Firewall configuration
   - HTTPS only

## Troubleshooting

### Common Issues

**1. Pipeline Fails on Tests:**
```bash
# Run tests locally
cd backend
pytest tests/ -v

cd ../frontend
npm test
```

**2. Docker Build Fails:**
```bash
# Clear Docker cache
docker system prune -a

# Rebuild without cache
docker-compose build --no-cache
```

**3. Database Connection Issues:**
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Check connection
psql -h localhost -U postgres -d portact
```

**4. Port Already in Use:**
```bash
# Find process using port
lsof -i :8000
lsof -i :3000

# Kill process
kill -9 <PID>
```

## Maintenance

### Regular Tasks

**Daily:**
- Monitor application logs
- Check error rates
- Review security alerts

**Weekly:**
- Review dependency updates
- Check disk space
- Verify backups

**Monthly:**
- Security audit
- Performance review
- Update documentation
- Review and rotate credentials

## Support and Contact

For issues or questions:
- Create GitHub issue: https://github.com/debasisdas1976/PortAct/issues
- Check documentation: [README.md](../README.md), [API_DOCUMENTATION.md](API_DOCUMENTATION.md)
- Review logs: backend.log, frontend.log

## Version History

- **v1.0.0** (2026-02-17): Initial DevOps setup with GitHub Actions CI/CD pipeline