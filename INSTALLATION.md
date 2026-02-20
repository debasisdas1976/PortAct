# PortAct Installation Guide

A complete, step-by-step guide to install and run PortAct on your computer. This guide assumes **no prior experience** with the tools involved.

---

## Table of Contents

1. [What You Need](#what-you-need)
2. [Option A: Docker Setup (Recommended)](#option-a-docker-setup-recommended)
3. [Option B: Local Setup (Without Docker)](#option-b-local-setup-without-docker)
   - [Step 1: Install Prerequisites](#step-1-install-prerequisites)
   - [Step 2: Download the Code](#step-2-download-the-code)
   - [Step 3: Install and Start PostgreSQL](#step-3-install-and-start-postgresql)
   - [Step 4: Install and Start Redis](#step-4-install-and-start-redis)
   - [Step 5: Install and Start MinIO](#step-5-install-and-start-minio)
   - [Step 6: Set Up the Backend](#step-6-set-up-the-backend)
   - [Step 7: Set Up the Frontend](#step-7-set-up-the-frontend)
   - [Step 8: Start the Application](#step-8-start-the-application)
4. [After Installation](#after-installation)
5. [Stopping the Application](#stopping-the-application)
6. [Troubleshooting](#troubleshooting)

---

## What You Need

| Requirement       | Version  | Purpose                         |
|-------------------|----------|---------------------------------|
| Git               | Any      | Download the source code        |
| Python            | 3.11+    | Run the backend server          |
| Node.js           | 18+      | Run the frontend                |
| PostgreSQL        | 15+      | Database                        |
| Redis             | 7+       | Caching and background jobs     |
| MinIO             | Latest   | File storage (statement uploads)|

> **Tip:** If you prefer not to install PostgreSQL, Redis, and MinIO individually, use **Option A (Docker)** which sets everything up automatically.

---

## Option A: Docker Setup (Recommended)

Docker bundles the entire application and all its services into containers. This is the easiest way to get started.

### A1. Install Docker Desktop

<details>
<summary><strong>macOS</strong></summary>

1. Go to https://www.docker.com/products/docker-desktop/
2. Click **Download for Mac** (choose Apple Silicon or Intel based on your Mac).
3. Open the downloaded `.dmg` file and drag **Docker** to your **Applications** folder.
4. Open **Docker** from Applications. It will ask for permission — click **OK**.
5. Wait until the Docker icon in the menu bar shows **"Docker Desktop is running"**.

</details>

<details>
<summary><strong>Windows</strong></summary>

1. Go to https://www.docker.com/products/docker-desktop/
2. Click **Download for Windows**.
3. Run the installer (`.exe` file). Follow the on-screen prompts.
4. When asked, enable **WSL 2** (Windows Subsystem for Linux). The installer may ask you to restart your computer.
5. After restart, open **Docker Desktop** from the Start menu.
6. Wait until the bottom-left of Docker Desktop shows **"Engine running"**.

> **Note:** If you see a WSL 2 error, open **PowerShell as Administrator** and run:
> ```powershell
> wsl --install
> ```
> Then restart your computer and open Docker Desktop again.

</details>

<details>
<summary><strong>Linux (Ubuntu/Debian)</strong></summary>

Open a terminal and run these commands one by one:

```bash
# Update package list
sudo apt update

# Install required packages
sudo apt install -y ca-certificates curl gnupg

# Add Docker's official GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Add Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Allow your user to run Docker without sudo
sudo usermod -aG docker $USER
```

**Log out and log back in** for the group change to take effect. Then verify:

```bash
docker --version
docker compose version
```

</details>

### A2. Install Git

<details>
<summary><strong>macOS</strong></summary>

Open **Terminal** (search for "Terminal" in Spotlight) and run:

```bash
xcode-select --install
```

Click **Install** in the popup. This installs Git along with other developer tools.

</details>

<details>
<summary><strong>Windows</strong></summary>

1. Go to https://git-scm.com/download/win
2. Download and run the installer. Accept all default options.
3. After installation, open **Git Bash** from the Start menu (this is the terminal you'll use).

</details>

<details>
<summary><strong>Linux (Ubuntu/Debian)</strong></summary>

```bash
sudo apt update
sudo apt install -y git
```

</details>

### A3. Download and Run PortAct

Open your terminal (Terminal on Mac/Linux, Git Bash on Windows) and run:

```bash
# 1. Download the code
git clone https://github.com/YOUR_USERNAME/PortAct.git

# 2. Go into the project folder
cd PortAct

# 3. Make the setup script executable (Mac/Linux only)
chmod +x setup.sh

# 4. Run the setup script
./setup.sh
```

> **Windows users:** If `./setup.sh` doesn't work in Git Bash, run:
> ```bash
> bash setup.sh
> ```

The script will:
- Create configuration files automatically
- Generate a secure secret key
- Build and start all services (PostgreSQL, Redis, MinIO, Backend, Frontend)

Wait until you see **"Setup Complete!"** — this may take 5-10 minutes the first time as it downloads all required images.

### A4. Open the Application

| Service            | URL                          |
|--------------------|------------------------------|
| **Application**    | http://localhost:3000         |
| **API Docs**       | http://localhost:8000/docs    |
| **MinIO Console**  | http://localhost:9001         |

Open http://localhost:3000 in your browser and **register a new account** to get started.

---

## Option B: Local Setup (Without Docker)

This option installs everything directly on your computer. Follow each step in order.

### Step 1: Install Prerequisites

#### 1a. Install Git

<details>
<summary><strong>macOS</strong></summary>

```bash
xcode-select --install
```

</details>

<details>
<summary><strong>Windows</strong></summary>

Download and install from https://git-scm.com/download/win — accept all default options.

</details>

<details>
<summary><strong>Linux (Ubuntu/Debian)</strong></summary>

```bash
sudo apt update && sudo apt install -y git
```

</details>

#### 1b. Install Python 3.11+

<details>
<summary><strong>macOS</strong></summary>

Install Homebrew first (if you don't have it):

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Then install Python:

```bash
brew install python@3.11
```

Verify:

```bash
python3 --version
# Should show: Python 3.11.x or higher
```

</details>

<details>
<summary><strong>Windows</strong></summary>

1. Go to https://www.python.org/downloads/
2. Download **Python 3.11** or later.
3. Run the installer.
4. **IMPORTANT:** Check the box **"Add Python to PATH"** at the bottom of the first screen.
5. Click **Install Now**.

Verify by opening **Command Prompt** and running:

```cmd
python --version
```

> **Note:** On Windows, use `python` instead of `python3` in all commands below.

</details>

<details>
<summary><strong>Linux (Ubuntu/Debian)</strong></summary>

```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip
```

Verify:

```bash
python3 --version
```

</details>

#### 1c. Install Node.js 18+

<details>
<summary><strong>macOS</strong></summary>

```bash
brew install node@18
```

Verify:

```bash
node --version    # Should show v18.x or higher
npm --version     # Should show 9.x or higher
```

</details>

<details>
<summary><strong>Windows</strong></summary>

1. Go to https://nodejs.org/
2. Download the **LTS** version (18 or later).
3. Run the installer. Accept all default options.

Verify by opening **Command Prompt**:

```cmd
node --version
npm --version
```

</details>

<details>
<summary><strong>Linux (Ubuntu/Debian)</strong></summary>

```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
```

Verify:

```bash
node --version
npm --version
```

</details>

### Step 2: Download the Code

```bash
# Download the code from GitHub
git clone https://github.com/YOUR_USERNAME/PortAct.git

# Go into the project folder
cd PortAct
```

### Step 3: Install and Start PostgreSQL

<details>
<summary><strong>macOS</strong></summary>

```bash
# Install PostgreSQL
brew install postgresql@15

# Start PostgreSQL (runs in the background)
brew services start postgresql@15

# Verify it's running
pg_isready
# Should show: accepting connections
```

Now create the database and user:

```bash
# Connect to PostgreSQL
psql postgres

# Inside the psql prompt, run these commands one by one:
CREATE USER portact_user WITH PASSWORD 'portact_password';
CREATE DATABASE portact_db OWNER portact_user;
GRANT ALL PRIVILEGES ON DATABASE portact_db TO portact_user;
\q
```

</details>

<details>
<summary><strong>Windows</strong></summary>

1. Go to https://www.postgresql.org/download/windows/
2. Download the installer from **EDB**.
3. Run the installer:
   - Set a password for the `postgres` superuser (remember this!).
   - Keep the default port **5432**.
   - Click **Next** through the rest of the prompts.
4. After installation, open **pgAdmin 4** (installed with PostgreSQL) or **SQL Shell (psql)** from the Start menu.

In **SQL Shell (psql)**, press Enter for all defaults, then enter the password you set:

```sql
CREATE USER portact_user WITH PASSWORD 'portact_password';
CREATE DATABASE portact_db OWNER portact_user;
GRANT ALL PRIVILEGES ON DATABASE portact_db TO portact_user;
\q
```

</details>

<details>
<summary><strong>Linux (Ubuntu/Debian)</strong></summary>

```bash
# Install PostgreSQL
sudo apt update
sudo apt install -y postgresql postgresql-contrib

# Start PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create the database and user
sudo -u postgres psql -c "CREATE USER portact_user WITH PASSWORD 'portact_password';"
sudo -u postgres psql -c "CREATE DATABASE portact_db OWNER portact_user;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE portact_db TO portact_user;"
```

</details>

### Step 4: Install and Start Redis

<details>
<summary><strong>macOS</strong></summary>

```bash
brew install redis
brew services start redis

# Verify
redis-cli ping
# Should respond: PONG
```

</details>

<details>
<summary><strong>Windows</strong></summary>

Redis does not officially support Windows. Use one of these options:

**Option 1: Use Memurai (Redis-compatible for Windows)**
1. Go to https://www.memurai.com/
2. Download and install the free developer edition.

**Option 2: Use Docker for just Redis**
```cmd
docker run -d --name portact-redis -p 6379:6379 redis:7-alpine
```

**Option 3: Use WSL**
```powershell
# In PowerShell (as Administrator):
wsl --install

# In WSL terminal:
sudo apt update && sudo apt install -y redis-server
sudo service redis-server start
```

</details>

<details>
<summary><strong>Linux (Ubuntu/Debian)</strong></summary>

```bash
sudo apt update
sudo apt install -y redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Verify
redis-cli ping
# Should respond: PONG
```

</details>

### Step 5: Install and Start MinIO

MinIO is used to store uploaded statement files (PDFs, Excel files).

<details>
<summary><strong>macOS</strong></summary>

```bash
brew install minio/stable/minio

# Start MinIO (this runs in the foreground — use a separate terminal)
mkdir -p ~/minio-data
minio server ~/minio-data --console-address ":9001"
```

> **Tip:** Open a new terminal tab/window for MinIO since it runs in the foreground. Press `Ctrl+C` to stop it later.

Default credentials: `minioadmin` / `minioadmin`

</details>

<details>
<summary><strong>Windows</strong></summary>

1. Go to https://min.io/download#/windows
2. Download the MinIO executable.
3. Open **Command Prompt** and run:

```cmd
mkdir C:\minio-data
minio.exe server C:\minio-data --console-address ":9001"
```

Default credentials: `minioadmin` / `minioadmin`

</details>

<details>
<summary><strong>Linux (Ubuntu/Debian)</strong></summary>

```bash
# Download MinIO
wget https://dl.min.io/server/minio/release/linux-amd64/minio
chmod +x minio
sudo mv minio /usr/local/bin/

# Create data directory and start
mkdir -p ~/minio-data
minio server ~/minio-data --console-address ":9001"
```

Default credentials: `minioadmin` / `minioadmin`

</details>

After MinIO is running, open http://localhost:9001 in your browser, log in with `minioadmin`/`minioadmin`, and create a bucket named **`portact-statements`**.

### Step 6: Set Up the Backend

These commands work on **all platforms**. On Windows, use `python` instead of `python3` and `venv\Scripts\activate` instead of `source venv/bin/activate`.

```bash
# Go to the backend folder
cd backend

# Create the configuration file
cp .env.example .env
```

Now **edit the `.env` file** with a text editor and make these changes:

```
# Change this line — generate a key by running: openssl rand -hex 32
# (or python3 -c "import secrets; print(secrets.token_urlsafe(32))")
SECRET_KEY=paste-your-generated-key-here

# Change this for local development
ENVIRONMENT=development
```

All other defaults are fine for local development. Continue with:

<details>
<summary><strong>macOS / Linux</strong></summary>

```bash
# Create a virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install Python dependencies (this may take 2-3 minutes)
pip install --upgrade pip
pip install -r requirements.txt

# Create necessary directories
mkdir -p uploads logs

# Set up the database tables
alembic upgrade head

# Go back to the project root
cd ..
```

</details>

<details>
<summary><strong>Windows</strong></summary>

```cmd
:: Create a virtual environment
python -m venv venv

:: Activate it
venv\Scripts\activate

:: Install Python dependencies (this may take 2-3 minutes)
pip install --upgrade pip
pip install -r requirements.txt

:: Create necessary directories
mkdir uploads
mkdir logs

:: Set up the database tables
alembic upgrade head

:: Go back to the project root
cd ..
```

</details>

### Step 7: Set Up the Frontend

```bash
# Go to the frontend folder
cd frontend

# Create the configuration file
echo "REACT_APP_API_URL=http://localhost:8000/api/v1" > .env

# Install JavaScript dependencies (this may take 2-3 minutes)
npm install

# Go back to the project root
cd ..
```

### Step 8: Start the Application

You need **two terminal windows** — one for the backend and one for the frontend.

#### Terminal 1 — Start the Backend

<details>
<summary><strong>macOS / Linux</strong></summary>

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

</details>

<details>
<summary><strong>Windows</strong></summary>

```cmd
cd backend
venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

</details>

You should see output like:

```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
```

#### Terminal 2 — Start the Frontend

Open a **new** terminal window and run:

```bash
cd frontend
npm start
```

This will automatically open http://localhost:3000 in your browser. If it doesn't, open it manually.

### You're Done!

| Service            | URL                          |
|--------------------|------------------------------|
| **Application**    | http://localhost:3000         |
| **API Docs**       | http://localhost:8000/docs    |
| **MinIO Console**  | http://localhost:9001         |

**Register a new account** and start tracking your portfolio!

---

## After Installation

### First-Time Setup Checklist

After registration and login, follow these steps to set up your portfolio:

1. **Go to Application Setup** (sidebar → Administration → Application Setup)
   - Set your profile information
   - Configure your employment details (for automatic PF/Gratuity tracking)
   - Review scheduler settings (price updates, news alerts)

2. **Add Bank Accounts** (sidebar → Banking → Savings)
   - Add your savings accounts for balance tracking

3. **Add Demat Accounts** (sidebar → Demat Holding → Demat Accounts)
   - Add your brokerage/demat accounts

4. **Upload Statements** to auto-import holdings
   - Navigate to any asset page and use the upload button
   - Supported formats: PDF, CSV, Excel

5. **Check the Dashboard** to see your portfolio overview

### Optional: AI News Alerts

PortAct can provide AI-powered investment insights for your portfolio. To enable this:

1. Get an API key from [OpenAI](https://platform.openai.com/api-keys) (requires billing) or [xAI/Grok](https://console.x.ai/)
2. Edit `backend/.env`:
   ```
   # For OpenAI:
   AI_NEWS_PROVIDER=openai
   OPENAI_API_KEY=sk-your-key-here

   # Or for Grok:
   AI_NEWS_PROVIDER=grok
   GROK_API_KEY=xai-your-key-here
   ```
3. Restart the backend server

---

## Stopping the Application

### Docker Setup

```bash
cd infrastructure
docker-compose down
```

To stop and **remove all data** (start fresh):

```bash
cd infrastructure
docker-compose down -v
```

### Local Setup

- **Backend:** Press `Ctrl+C` in the backend terminal.
- **Frontend:** Press `Ctrl+C` in the frontend terminal.
- **MinIO:** Press `Ctrl+C` in the MinIO terminal.
- **PostgreSQL and Redis:**

  <details>
  <summary><strong>macOS</strong></summary>

  ```bash
  brew services stop postgresql@15
  brew services stop redis
  ```

  </details>

  <details>
  <summary><strong>Linux</strong></summary>

  ```bash
  sudo systemctl stop postgresql
  sudo systemctl stop redis-server
  ```

  </details>

  <details>
  <summary><strong>Windows</strong></summary>

  Stop services from **Services** (search "Services" in Start menu) or:
  ```cmd
  net stop postgresql-x64-15
  ```

  </details>

---

## Troubleshooting

### "Port 8000 is already in use"

Another process is using port 8000. Find and stop it:

```bash
# macOS / Linux
lsof -i :8000
kill -9 <PID>

# Windows (in Command Prompt as Administrator)
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### "Port 3000 is already in use"

Same as above, but for port 3000. Or when `npm start` asks "Would you like to run on another port?", type `Y`.

### "FATAL: password authentication failed for user portact_user"

The database user wasn't created correctly. Re-run the PostgreSQL setup commands from [Step 3](#step-3-install-and-start-postgresql).

### "pg_config executable not found" (during pip install)

You need PostgreSQL development headers:

```bash
# macOS
brew install postgresql@15

# Ubuntu/Debian
sudo apt install -y libpq-dev

# Windows
# This is included with the PostgreSQL installer
```

### "ModuleNotFoundError: No module named 'xxx'"

Your virtual environment isn't activated. Run:

```bash
# macOS / Linux
cd backend
source venv/bin/activate

# Windows
cd backend
venv\Scripts\activate
```

Then try your command again.

### "Cannot connect to Redis"

Make sure Redis is running:

```bash
# macOS
brew services start redis

# Linux
sudo systemctl start redis-server

# Windows (if using Docker)
docker start portact-redis
```

### "alembic upgrade head" fails

1. Make sure PostgreSQL is running and the database exists.
2. Check that `DATABASE_URL` in `backend/.env` matches your PostgreSQL setup.
3. Make sure your virtual environment is activated.

### Backend starts but frontend shows "Network Error"

1. Check that the backend is running on http://localhost:8000
2. Check that `frontend/.env` contains: `REACT_APP_API_URL=http://localhost:8000/api/v1`
3. Check that `BACKEND_CORS_ORIGINS` in `backend/.env` includes `http://localhost:3000`

### Everything worked before but now it doesn't start

Try a clean start:

```bash
# Backend
cd backend
source venv/bin/activate    # or venv\Scripts\activate on Windows
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

# Frontend
cd frontend
rm -rf node_modules
npm install
npm start
```
