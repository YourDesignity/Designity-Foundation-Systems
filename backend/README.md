# Montreal Backend

FastAPI + MongoDB backend for the Montreal Int. Business Dashboard.

---

## Installation

### Prerequisites

- Python 3.10 – 3.12
- MongoDB Community Server (running on `localhost:27017`)

### Windows Setup

```bash
# From project root — create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment config
copy backend\.env.example backend\.env

# Start the backend
python -m backend.main
```

### Linux Setup

```bash
# From project root — create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment config
cp backend/.env.example backend/.env

# Start the backend
python -m backend.main
```

---

## Verifying Installation

```bash
python -c "import pydantic; print('pydantic', pydantic.__version__)"
# Expected: 2.12.5 or higher

python -c "import fastapi; print('fastapi', fastapi.__version__)"
# Expected: 0.135.3 or higher

python -c "import beanie; print('beanie', beanie.__version__)"
# Expected: 1.26.0 or higher
```

---

## Troubleshooting

### `TypeError: 'datetime.date' object is not iterable`

This was caused by `pydantic==2.5.0` on Windows. Upgrade to the current requirements:

```bash
pip install -r requirements.txt --upgrade
```

### `TypeError: vars() argument must have __dict__ attribute`

Same root cause as above — outdated Pydantic version. Run `pip install -r requirements.txt --upgrade`.

### MongoDB connection refused

Ensure MongoDB is running:

```bash
# Windows (PowerShell, admin)
net start MongoDB

# Linux
sudo systemctl start mongod
```

Check `backend/.env` matches your MongoDB setup:

```env
DB_AUTH_ENABLED=false   # set true if MongoDB auth is enabled
DB_HOST=localhost
DB_PORT=27017
DB_NAME=payroll_db
```

### Port already in use

The backend runs on port **8000** by default. Kill any existing process on that port:

```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux
lsof -ti:8000 | xargs kill -9
```
