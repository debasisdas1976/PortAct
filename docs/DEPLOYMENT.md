# PortAct Deployment Guide

This guide will help you deploy the PortAct application locally or in production.

## Prerequisites

- Docker and Docker Compose installed
- Git
- At least 4GB RAM available
- 10GB free disk space

## Quick Start (Local Development)

### 1. Clone the Repository

```bash
git clone <repository-url>
cd PortAct
```

### 2. Set Up Environment Variables

#### Backend
```bash
cd backend
cp .env.example .env
# Edit .env with your configurations
```

Required environment variables:
- `SECRET_KEY`: Generate a secure random key
- `DATABASE_URL`: PostgreSQL connection string (auto-configured in Docker)
- `OPENAI_API_KEY`: (Optional) For intelligent statement parsing
- `ALPHA_VANTAGE_API_KEY`: (Optional) For market data

#### Frontend
```bash
cd ../frontend
cp .env.example .env
# Edit .env with your configurations
```

### 3. Start All Services

```bash
cd ../infrastructure
docker-compose up -d
```

This will start:
- PostgreSQL database (port 5432)
- Redis cache (port 6379)
- MinIO file storage (ports 9000, 9001)
- Backend API (port 8000)
- Frontend (port 3000)
- Nginx reverse proxy (port 80)

### 4. Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **MinIO Console**: http://localhost:9001

### 5. Create First User

You can register through the frontend or use the API:

```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "testuser",
    "password": "securepassword123",
    "full_name": "Test User"
  }'
```

## Development Setup

### Backend Development

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm start
```

The frontend will be available at http://localhost:3000

## Database Migrations

### Create a New Migration

```bash
cd backend
alembic revision --autogenerate -m "Description of changes"
```

### Apply Migrations

```bash
alembic upgrade head
```

### Rollback Migration

```bash
alembic downgrade -1
```

## Production Deployment

### 1. Update Environment Variables

Set production values in `.env` files:
- Use strong `SECRET_KEY`
- Set `DEBUG=False`
- Configure proper database credentials
- Set up email SMTP settings
- Configure external API keys

### 2. Build Production Images

```bash
# Backend
cd backend
docker build -t portact-backend:latest .

# Frontend
cd ../frontend
docker build -t portact-frontend:latest .
```

### 3. Deploy with Docker Compose

```bash
cd infrastructure
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### 4. Set Up SSL/TLS

Update nginx configuration to use SSL certificates:

```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    
    # ... rest of configuration
}
```

### 5. Set Up Backups

#### Database Backup

```bash
# Create backup
docker exec portact-postgres pg_dump -U portact_user portact_db > backup_$(date +%Y%m%d).sql

# Restore backup
docker exec -i portact-postgres psql -U portact_user portact_db < backup_20240101.sql
```

#### File Storage Backup

```bash
# Backup MinIO data
docker run --rm -v portact_minio_data:/data -v $(pwd):/backup alpine tar czf /backup/minio_backup_$(date +%Y%m%d).tar.gz /data
```

## Monitoring and Logs

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f postgres
```

### Health Checks

```bash
# Backend health
curl http://localhost:8000/health

# Database connection
docker exec portact-postgres pg_isready -U portact_user

# Redis connection
docker exec portact-redis redis-cli ping
```

## Troubleshooting

### Backend Not Starting

1. Check database connection:
   ```bash
   docker-compose logs postgres
   ```

2. Verify environment variables:
   ```bash
   docker-compose config
   ```

3. Check backend logs:
   ```bash
   docker-compose logs backend
   ```

### Frontend Not Loading

1. Check if backend is accessible:
   ```bash
   curl http://localhost:8000/health
   ```

2. Verify CORS settings in backend

3. Check browser console for errors

### Database Connection Issues

1. Ensure PostgreSQL is running:
   ```bash
   docker-compose ps postgres
   ```

2. Test connection:
   ```bash
   docker exec -it portact-postgres psql -U portact_user -d portact_db
   ```

### File Upload Issues

1. Check MinIO is running:
   ```bash
   docker-compose ps minio
   ```

2. Verify upload directory permissions:
   ```bash
   docker exec portact-backend ls -la /app/uploads
   ```

## Scaling

### Horizontal Scaling

To scale backend instances:

```bash
docker-compose up -d --scale backend=3
```

Update nginx configuration for load balancing:

```nginx
upstream backend {
    server backend:8000;
    server backend:8000;
    server backend:8000;
}
```

### Database Optimization

1. Add indexes for frequently queried fields
2. Configure connection pooling
3. Set up read replicas for heavy read workloads

## Security Checklist

- [ ] Change default passwords
- [ ] Use strong SECRET_KEY
- [ ] Enable HTTPS/SSL
- [ ] Configure firewall rules
- [ ] Set up regular backups
- [ ] Enable database encryption
- [ ] Implement rate limiting
- [ ] Set up monitoring and alerts
- [ ] Regular security updates
- [ ] Implement proper CORS policies

## Maintenance

### Update Application

```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose down
docker-compose build
docker-compose up -d
```

### Clean Up

```bash
# Remove unused images
docker image prune -a

# Remove unused volumes
docker volume prune

# Remove stopped containers
docker container prune
```

## Support

For issues and questions:
- Check the [README.md](../README.md)
- Review API documentation at `/docs`
- Create an issue in the repository