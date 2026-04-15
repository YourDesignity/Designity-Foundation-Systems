# 🐧 Linux Virtual Environment Setup Guide

Complete step-by-step guide to set up the Montreal Management System on Linux.

---

## 📦 **Prerequisites**

Before starting, ensure you have:
- ✅ Python 3.10+ installed
- ✅ MongoDB installed and running
- ✅ Git installed
- ✅ `pip` and `venv` available

---

## 🚀 **Step 1: Install Python & pip**

### **Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv -y
```

### **RHEL/CentOS/Fedora:**
```bash
sudo dnf install python3 python3-pip -y
```

### **Arch Linux:**
```bash
sudo pacman -S python python-pip
```

### **Verify Installation:**
```bash
python3 --version  # Should show 3.10 or higher
pip3 --version
```

---

## 🗂️ **Step 2: Clone the Repository**

```bash
# Navigate to your projects directory
cd ~

# Clone the repository
git clone https://github.com/YourDesignity/MONTREAL.git
cd MONTREAL
```

---

## 🌐 **Step 3: Create Virtual Environment**

### **Option A: Using venv (Recommended)**

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Your prompt should now show (venv)
# Example: (venv) user@hostname:~/MONTREAL$
```

### **Option B: Using virtualenv**

```bash
# Install virtualenv if not available
pip3 install virtualenv

# Create virtual environment
virtualenv venv

# Activate
source venv/bin/activate
```

---

## 📦 **Step 4: Install Dependencies**

```bash
# Make sure virtual environment is activated!
# You should see (venv) in your prompt

# Upgrade pip first
pip install --upgrade pip

# Install all dependencies
pip install -r requirements.txt

# This will install ~25 packages
# Takes about 2-3 minutes on average connection
```

**Expected Output:**
```
Collecting fastapi==0.104.1
  Downloading fastapi-0.104.1-py3-none-any.whl (92 kB)
Collecting uvicorn[standard]==0.24.0
  Downloading uvicorn-0.24.0-py3-none-any.whl (59 kB)
...
Successfully installed fastapi-0.104.1 uvicorn-0.24.0 ... (25 packages)
```

---

## 🔧 **Step 5: Configure Environment Variables**

```bash
# Create .env file
cp backend/.env.example backend/.env

# Edit with your preferred editor
nano backend/.env
# OR
vim backend/.env
```

### **Required Configuration:**

```env
# MongoDB Configuration (Linux)
DB_USER=your_mongodb_username
DB_PASS=your_mongodb_password
DB_HOST=localhost
DB_PORT=27017
AUTH_SOURCE=admin
DB_NAME=payroll_db

# JWT Secret (generate a secure random string — see command below)
SECRET_KEY=REPLACE_THIS_WITH_GENERATED_KEY_FROM_COMMAND_BELOW

# Access Token Expiry (in minutes)
ACCESS_TOKEN_EXPIRE_MINUTES=43200
```

### **Generate Secure SECRET_KEY:**

```bash
# Generate random secret key
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Copy the output and paste it as your SECRET_KEY in .env**

---

## 🗄️ **Step 6: Setup MongoDB**

### **Start MongoDB Service:**

```bash
# Ubuntu/Debian
sudo systemctl start mongod
sudo systemctl enable mongod  # Auto-start on boot

# Check status
sudo systemctl status mongod
```

### **Create MongoDB User (if not exists):**

> ⚠️ **Security Warning:** Replace `your_mongodb_username` and `your_secure_password` below with your own credentials. **Never use example values in production.**

```bash
# Connect to MongoDB
mongosh

# Switch to admin database
use admin

# Create admin user (replace username and password with your own!)
db.createUser({
  user: "your_mongodb_username",
  pwd: "your_secure_password",
  roles: [
    { role: "readWrite", db: "payroll_db" },
    { role: "dbAdmin", db: "payroll_db" }
  ]
})

# Exit MongoDB shell
exit
```

---

## 🎯 **Step 7: Initialize Database**

```bash
# Reset database and create default data
python scripts/reset_database.py --full

# You'll see:
# ✅ Connected to MongoDB: payroll_db
# 📦 Creating backup...
# 🗑️  Dropping collections...
# 🌱 Seeding default data...
# 🎉 DATABASE RESET COMPLETE!
# 📧 Default Admin: admin@montreal.com
# 🔑 Default Password: admin123
```

> ⚠️ **Security Warning:** The default admin password `admin123` is for initial setup only. **Change it immediately after your first login.**

---

## 🚀 **Step 8: Run the Backend Server**

```bash
# Make sure virtual environment is active!
# You should see (venv) in your prompt

# Run the FastAPI backend
python -m backend.main

# Expected output:
# INFO:     Will watch for changes in these directories: ['/home/user/MONTREAL']
# INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
# INFO:     Started reloader process [12345] using WatchFiles
# INFO:     Started server process [12346]
# INFO:     Waiting for application startup.
# SYSTEM STARTUP: Database Connected Successfully.
# INFO:     Application startup complete.
```

**Server is now running on:** `http://127.0.0.1:8000`

---

## 🌐 **Step 9: Run the Frontend (Optional)**

### **Install Node.js & npm:**

```bash
# Ubuntu/Debian
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Verify
node --version  # Should show v20.x.x
npm --version
```

### **Install Frontend Dependencies:**

```bash
# Install packages
npm install

# Run development server
npm run dev

# Frontend runs on: http://localhost:1420
```

---

## ✅ **Step 10: Verify Everything Works**

### **Test Backend API:**

```bash
# In a new terminal (keep server running in the first one)
curl http://127.0.0.1:8000/

# Expected response:
# {"status":"online","message":"Montreal Management API"}
```

### **Test Login:**

```bash
# Login with default admin
curl -X POST http://127.0.0.1:8000/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@montreal.com&password=admin123"

# Expected: JSON response with access_token
```

### **Open in Browser:**

1. Backend API Docs: `http://127.0.0.1:8000/docs`
2. Frontend UI: `http://localhost:1420`
3. Login with:
   - Email: `admin@montreal.com`
   - Password: `admin123`

---

## 🔄 **Daily Usage**

### **Start Working:**

```bash
# Navigate to project
cd ~/MONTREAL

# Activate virtual environment
source venv/bin/activate

# Run backend
python -m backend.main
```

### **Stop Working:**

```bash
# Stop server (Ctrl+C in terminal)

# Deactivate virtual environment
deactivate
```

---

## 🛠️ **Troubleshooting**

### **Problem: "python3: command not found"**

**Solution:**
```bash
sudo apt install python3 python3-pip -y
```

---

### **Problem: "venv: command not found"**

**Solution:**
```bash
sudo apt install python3-venv -y
```

---

### **Problem: "pip: command not found"**

**Solution:**
```bash
sudo apt install python3-pip -y
```

---

### **Problem: MongoDB Connection Failed**

**Solution:**
```bash
# Check if MongoDB is running
sudo systemctl status mongod

# If not running, start it
sudo systemctl start mongod

# Check MongoDB logs
sudo tail -f /var/log/mongodb/mongod.log
```

---

### **Problem: "Module not found" errors**

**Solution:**
```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

---

### **Problem: Permission Denied**

**Solution:**
```bash
# Don't use sudo with pip in virtual environment!
# Just activate venv and run:
pip install -r requirements.txt

# If you accidentally used sudo, remove and recreate venv:
deactivate
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

### **Problem: Port 8000 Already in Use**

**Solution:**
```bash
# Find process using port 8000
sudo lsof -i :8000

# Kill the process (replace <PID> with the actual process ID)
sudo kill -9 <PID>
```

---

### **Problem: "No module named 'backend'"**

**Solution:**
```bash
# Make sure you run from the project root directory
cd ~/MONTREAL

# Not from inside the backend folder!
python -m backend.main
```

---

### **Problem: ReportLab / PDF generation errors**

**Solution:**
```bash
# Install system font dependencies
sudo apt install libfreetype6-dev -y

# Reinstall reportlab
pip install --force-reinstall reportlab==4.0.7
```

---

## 📚 **Additional Resources**

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [MongoDB Installation Guide](https://www.mongodb.com/docs/manual/installation/)
- [Python venv Documentation](https://docs.python.org/3/library/venv.html)
- [Motor (Async MongoDB Driver)](https://motor.readthedocs.io/)
