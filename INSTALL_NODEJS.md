# Installing Node.js and npm on macOS

## What is Node.js and npm?

- **Node.js**: JavaScript runtime that allows you to run JavaScript on your computer (not just in browsers)
- **npm**: Node Package Manager - comes bundled with Node.js and is used to install JavaScript packages

## Installation Methods

### Method 1: Using Homebrew (Recommended) ⭐

Homebrew is a package manager for macOS that makes installing software easy.

#### Step 1: Install Homebrew (if not already installed)

Open Terminal and run:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Follow the on-screen instructions. After installation, you may need to add Homebrew to your PATH:
```bash
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
```

#### Step 2: Install Node.js and npm

```bash
brew install node
```

This will install both Node.js and npm.

#### Step 3: Verify Installation

```bash
node --version
npm --version
```

You should see version numbers like:
```
v20.x.x
10.x.x
```

### Method 2: Using Official Installer

#### Step 1: Download Node.js

1. Visit: https://nodejs.org/
2. Download the **LTS (Long Term Support)** version for macOS
3. Choose the `.pkg` installer

#### Step 2: Run the Installer

1. Open the downloaded `.pkg` file
2. Follow the installation wizard
3. Accept the license agreement
4. Choose installation location (default is fine)
5. Click "Install"
6. Enter your password when prompted

#### Step 3: Verify Installation

Open Terminal and run:
```bash
node --version
npm --version
```

### Method 3: Using nvm (Node Version Manager)

This method allows you to install and manage multiple Node.js versions.

#### Step 1: Install nvm

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
```

#### Step 2: Restart Terminal or run:

```bash
source ~/.zshrc
```

#### Step 3: Install Node.js

```bash
nvm install --lts
nvm use --lts
```

#### Step 4: Verify Installation

```bash
node --version
npm --version
```

## After Installation

### Update npm to Latest Version

```bash
npm install -g npm@latest
```

### Set npm Global Directory (Optional but Recommended)

To avoid permission issues:

```bash
mkdir ~/.npm-global
npm config set prefix '~/.npm-global'
echo 'export PATH=~/.npm-global/bin:$PATH' >> ~/.zprofile
source ~/.zprofile
```

## Installing PortAct Frontend Dependencies

Once Node.js and npm are installed:

```bash
# Navigate to frontend directory
cd /Users/debasis/Debasis/personal/Projects/PortAct/frontend

# Install dependencies
npm install

# Start the development server
npm start
```

The frontend will be available at: http://localhost:3000

## Troubleshooting

### Issue: "command not found: node" or "command not found: npm"

**Solution 1**: Restart your terminal

**Solution 2**: Check if Node.js is in your PATH:
```bash
echo $PATH
```

**Solution 3**: If using Homebrew, ensure it's in your PATH:
```bash
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
source ~/.zprofile
```

### Issue: Permission Errors During npm install

**Solution**: Use the global directory setup mentioned above, or:
```bash
sudo chown -R $(whoami) ~/.npm
sudo chown -R $(whoami) /usr/local/lib/node_modules
```

### Issue: npm install is slow

**Solution**: Clear npm cache:
```bash
npm cache clean --force
npm install
```

### Issue: Port 3000 already in use

**Solution**: Kill the process using port 3000:
```bash
lsof -ti:3000 | xargs kill -9
```

Or use a different port:
```bash
PORT=3001 npm start
```

## Recommended Node.js Version

For PortAct, we recommend:
- **Node.js**: v18.x or v20.x (LTS versions)
- **npm**: v9.x or v10.x

## Quick Start After Installation

```bash
# 1. Navigate to project
cd /Users/debasis/Debasis/personal/Projects/PortAct

# 2. Install frontend dependencies
cd frontend
npm install

# 3. Start frontend (in one terminal)
npm start

# 4. Start backend (in another terminal)
cd ../backend
source venv/bin/activate
uvicorn app.main:app --reload
```

## Alternative: Use the Automated Script

After installing Node.js and npm, you can use our automated script:

```bash
cd /Users/debasis/Debasis/personal/Projects/PortAct
./run_app.sh
```

This script will:
1. Check if Node.js and npm are installed
2. Install all dependencies
3. Start both backend and frontend
4. Provide access URLs

## Verifying Everything Works

After installation, run:

```bash
# Check Node.js
node --version

# Check npm
npm --version

# Check if you can install packages
npm install -g create-react-app

# If all above work, you're ready!
```

## Additional Resources

- Node.js Official Documentation: https://nodejs.org/docs/
- npm Documentation: https://docs.npmjs.com/
- Homebrew Documentation: https://docs.brew.sh/

## Need Help?

If you encounter any issues:

1. **Check Node.js version**: Ensure you have v18 or higher
2. **Check npm version**: Ensure you have v9 or higher
3. **Restart terminal**: Sometimes PATH changes need a restart
4. **Clear cache**: Run `npm cache clean --force`
5. **Reinstall**: If all else fails, uninstall and reinstall Node.js

## Uninstalling Node.js (if needed)

### If installed via Homebrew:
```bash
brew uninstall node
```

### If installed via official installer:
```bash
sudo rm -rf /usr/local/lib/node_modules
sudo rm -rf /usr/local/include/node
sudo rm -rf /usr/local/bin/node
sudo rm -rf /usr/local/bin/npm
```

### If installed via nvm:
```bash
nvm uninstall <version>
```

---

**Once Node.js and npm are installed, you're ready to run the PortAct frontend!**