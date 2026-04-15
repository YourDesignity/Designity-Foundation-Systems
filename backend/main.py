# backend/main.py

import os
import logging
from contextlib import asynccontextmanager
from datetime import timedelta, datetime
from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles 
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, validator

# --- MongoDB Imports ---
from backend.database import init_db
from backend.models import Admin, CompanySettings, Counter

# --- Utilities ---
from backend import security
from backend.utils.logger import setup_logger, WebSocketLogHandler 

# WebSocket Manager
try:
    from backend.websocket_manager import manager
except ImportError:
    from backend.websocket_manager import manager 

# --- Routers ---
from backend.routers import (
    admins, attendance, sites, schedules,
    employees, payslips, roles, designations,
    duty_list, dashboard, vehicles, contracts,
    inventory, invoices, finance, messages,
    managers,
    manager_attendance,
    settings,
    projects,
    workflow_contracts,
    workflow_sites,
    assignments,
    temporary_assignments,
)
from backend.routers import workforce_analytics, project_analytics
from backend.routers import substitutes, manager_sites
from backend.routers.materials import router as materials_router, suppliers_router, purchase_orders_router
from backend.routers import contract_roles, daily_fulfillment

# --- Initialize Logger ---
logger = setup_logger("MainApp", log_file="logs/app_main.log", level=logging.DEBUG)

# =============================================================================
# 1. LIFESPAN CONTEXT MANAGER
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("SYSTEM STARTUP: Initializing Database Connection...")
    ws_handler = WebSocketLogHandler(manager)
    logging.getLogger().addHandler(ws_handler) 
    try:
        await init_db()
        logger.info("SYSTEM STARTUP: Database Connected Successfully.")
    except Exception as e:
        logger.critical(f"SYSTEM STARTUP FAILED: {e}", exc_info=True)
    
    yield
    
    logger.info("SYSTEM SHUTDOWN: Application is stopping...")

# =============================================================================
# 2. APP SETUP
# =============================================================================

app = FastAPI(
    title="Montreal Intl. Management API",
    lifespan=lifespan
)

# --- CORS CONFIGURATION ---
# Enhanced CORS to handle all frontend scenarios including OPTIONS preflight
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:1420",
        "http://127.0.0.1:1420",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",  # Vite default
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "Origin",
        "X-Requested-With",
    ],
    expose_headers=["*"],
    max_age=600,  # Cache preflight for 10 minutes
)

logger.info("CORS Configured for Frontend Development.")


# --- CORS DEBUGGING MIDDLEWARE ---
@app.middleware("http")
async def cors_debug_middleware(request, call_next):
    origin = request.headers.get("origin")
    logger.debug(f"CORS: {request.method} {request.url.path} from {origin}")
    response = await call_next(request)
    logger.debug(f"CORS Response: {response.status_code} for {request.url.path}")
    return response

# --- STATIC FILES ---
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
os.makedirs(static_dir, exist_ok=True) 
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# --- UPLOADS (profile photos, documents, etc.) ---
uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(os.path.join(uploads_dir, "admin_photos"), exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

# --- Password Hashing ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Safely hash password with bcrypt, truncating to 72 bytes if necessary."""
    encoded = password.encode("utf-8")
    if len(encoded) > 72:
        encoded = encoded[:72]
        password = encoded.decode("utf-8", errors="ignore")
        logger.debug("Password truncated to 72 bytes for bcrypt compatibility.")
    return pwd_context.hash(password)

# =============================================================================
# 3. AUTHENTICATION (UPDATED TO INCLUDE USER ID)
# =============================================================================
@app.post("/token", tags=["Authentication"])
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    logger.info(f"AUTH ATTEMPT: Login request for user '{form_data.username}'")

    user = await Admin.find_one(Admin.email == form_data.username)

    # Truncate password to 72 bytes for bcrypt compatibility
    password_to_verify = form_data.password
    if len(password_to_verify.encode('utf-8')) > 72:
        password_to_verify = password_to_verify.encode('utf-8')[:72].decode('utf-8', errors='ignore')

    if not user or not pwd_context.verify(password_to_verify, user.hashed_password):
        logger.warning(f"AUTH FAILED: Invalid credentials for '{form_data.username}'")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=400, detail="User is inactive")

    # Mapping roles to power levels
    power_level = {"SuperAdmin": 100, "Admin": 50, "Site Manager": 20}.get(user.role, 0)
    
    # --- CRITICAL FIX HERE ---
    # We must include "id": user.uid so the frontend knows who the manager is
    token_data = {
        "id": user.uid,                   # Added ID to token
        "sub": user.email,
        "role": user.role,
        "power": power_level,
        "perms": user.permissions or [],       
        "sites": user.assigned_site_uids or [],
        "full_name": user.full_name,
        "profile_photo": user.profile_photo,
    }
    
    access_token = security.create_access_token(
        data=token_data, 
        expires_delta=timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    logger.info(f"AUTH SUCCESS: User '{user.email}' (ID: {user.uid}) logged in.")
    return {"access_token": access_token, "token_type": "bearer"}

# =============================================================================
# 3b. ADMIN REGISTRATION (First-Time Setup)
# =============================================================================

class RegisterAdminRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    company_name: str
    setup_key: str  # Secret key to prevent unauthorized registrations

    @validator('password')
    def validate_password(cls, v):
        """Validate password length for bcrypt compatibility."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if len(v.encode('utf-8')) > 100:
            raise ValueError('Password is too long (max 100 UTF-8 bytes)')
        return v

@app.post("/auth/register-admin", tags=["Authentication"])
async def register_first_admin(payload: RegisterAdminRequest):
    """
    Register the first SuperAdmin account.
    Only works if NO admins exist in the database.
    Requires a setup key for security.
    """
    # Validate setup key
    SETUP_KEY = os.getenv("ADMIN_SETUP_KEY", "MONTREAL_SETUP_2026")
    if payload.setup_key != SETUP_KEY:
        raise HTTPException(status_code=403, detail="Invalid setup key")

    # Check if any admin already exists
    existing_admin = await Admin.find_one()
    if existing_admin:
        raise HTTPException(
            status_code=400,
            detail="Admin account already exists. Registration is disabled."
        )

    # Create SuperAdmin
    admin = Admin(
        uid=1,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        designation="Super Administrator",
        role="SuperAdmin",
        permissions=[
            "employee:view_all",
            "employee:create",
            "employee:edit",
            "employee:delete",
            "attendance:update",
            "payslip:generate",
            "payslip:view_all",
            "admin:view_all",
            "admin:create:manager",
            "admin:edit",
            "admin:delete",
            "site:create",
            "site:view",
            "site:edit",
            "site:delete",
            "schedule:edit",
            "schedule:view_assigned"
        ],
        assigned_site_uids=[],
        is_active=True,
        has_manager_profile=False
    )
    await admin.insert()

    # Create company settings (singleton)
    existing_settings = await CompanySettings.find_one()
    if not existing_settings:
        settings = CompanySettings(uid=1)
        await settings.insert()

    # Initialize counters (upsert to avoid wiping unrelated counters)
    for coll_name, start_uid in [("admins", 1), ("employees", 0), ("manager_profiles", 0)]:
        existing_counter = await Counter.find_one(Counter.collection_name == coll_name)
        if existing_counter:
            existing_counter.current_uid = start_uid
            await existing_counter.save()
        else:
            await Counter(collection_name=coll_name, current_uid=start_uid).insert()

    logger.info(f"FIRST ADMIN REGISTERED: {admin.email}")

    return {
        "message": "SuperAdmin registered successfully",
        "email": admin.email,
        "uid": admin.uid
    }

# =============================================================================
# 4. REGISTER ROUTERS
# =============================================================================

app.include_router(admins.router)
app.include_router(employees.router)
app.include_router(employees.download_router)
app.include_router(payslips.router) 
app.include_router(attendance.router)   
app.include_router(sites.router)
app.include_router(roles.router)
app.include_router(schedules.router)
app.include_router(designations.router)
app.include_router(duty_list.router)
app.include_router(dashboard.router)
app.include_router(vehicles.router)
app.include_router(contracts.router)
app.include_router(inventory.router)
app.include_router(invoices.router)
app.include_router(finance.router)
app.include_router(messages.router)
app.include_router(managers.router)
app.include_router(manager_attendance.router)
app.include_router(settings.router)
app.include_router(projects.router)
app.include_router(workflow_contracts.router)
app.include_router(workflow_sites.router)
app.include_router(assignments.router)
app.include_router(temporary_assignments.router)
app.include_router(workforce_analytics.router)
app.include_router(project_analytics.router)
app.include_router(substitutes.router)
app.include_router(manager_sites.router)
app.include_router(materials_router)
app.include_router(suppliers_router)
app.include_router(purchase_orders_router)
# NEW: Role-Based Labour Contracts (Phase 1)
app.include_router(contract_roles.router)
app.include_router(daily_fulfillment.router)

@app.get("/", tags=["Root"])
def read_root():
    return {"status": "online", "message": "Montreal Management API"}

# =============================================================================
# 5. WEBSOCKETS
# =============================================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        # Handle abrupt disconnections that don't raise WebSocketDisconnect
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    # Use 127.0.0.1 to match your Frontend API Service
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)



















# # backend/main.py

# import os
# import logging
# from datetime import timedelta
# from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
# from fastapi.security import OAuth2PasswordRequestForm
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.staticfiles import StaticFiles 
# from passlib.context import CryptContext

# # --- MongoDB Imports ---
# from backend.database import init_db
# from backend.models import Admin

# # --- Utilities ---
# from backend import security
# from backend.utils.logger import setup_logger 

# # WebSocket Manager (Robust Import)
# try:
#     from backend.websocket_manager import manager
# except ImportError:
#     from backend.websocket_manager import manager 

# # --- Routers ---
# from backend.routers import (
#     admins, 
#     attendance, 
#     sites, 
#     schedules,
#     employees, 
#     payslips,
#     roles,
#     designations,
#     duty_list 
# )

# # --- Initialize Logger ---
# # This serves as the main application log
# logger = setup_logger("MainApp", log_file="logs/app_main.log", level=logging.DEBUG)

# # --- App Setup ---
# app = FastAPI(title="Payroll Management API (MongoDB Edition)")

# # --- CORS ---
# origins = [
#     "http://localhost:3000",
#     "http://localhost:1420",
#     "http://localhost:5173",
#     "http://127.0.0.1:1420",
# ]

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# logger.info(f"CORS Configured. Allowed Origins: {origins}")

# # --- STATIC FILES ---
# static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
# os.makedirs(static_dir, exist_ok=True) 
# app.mount("/static", StaticFiles(directory=static_dir), name="static")

# # --- Password Hashing ---
# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# # =============================================================================
# # 1. DATABASE INITIALIZATION
# # =============================================================================
# @app.on_event("startup")
# async def startup_db_client():
#     logger.info("SYSTEM STARTUP: Initializing Database Connection...")
#     try:
#         await init_db()
#         logger.info("SYSTEM STARTUP: Database Connected Successfully.")
#     except Exception as e:
#         logger.critical(f"SYSTEM STARTUP FAILED: Database connection error: {e}", exc_info=True)
#         # We don't exit here, but the app will likely fail to serve requests.

# # =============================================================================
# # 2. AUTHENTICATION (Login Audit)
# # =============================================================================
# @app.post("/token", tags=["Authentication"])
# async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
#     """
#     Handles user login.
#     Logs attempts for security auditing.
#     """
#     logger.info(f"AUTH ATTEMPT: Login request for user '{form_data.username}'")

#     user = await Admin.find_one(Admin.email == form_data.username)

#     # Check credentials
#     if not user or not pwd_context.verify(form_data.password, user.hashed_password):
#         logger.warning(f"AUTH FAILED: Invalid credentials for '{form_data.username}'")
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Incorrect username or password",
#             headers={"WWW-Authenticate": "Bearer"},
#         )

#     # Check active status
#     if not user.is_active:
#         logger.warning(f"AUTH BLOCKED: User '{form_data.username}' is inactive.")
#         raise HTTPException(status_code=400, detail="User is inactive")

#     # Generate Token
#     power_level = {"SuperAdmin": 100, "Admin": 50, "Site Manager": 20}.get(user.role, 0)
    
#     token_data = {
#         "sub": user.email,
#         "role": user.role,
#         "power": power_level,
#         "perms": user.permissions,       
#         "sites": user.assigned_site_uids 
#     }
    
#     access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
#     access_token = security.create_access_token(
#         data=token_data, expires_delta=access_token_expires
#     )
    
#     logger.info(f"AUTH SUCCESS: User '{user.email}' logged in as '{user.role}'.")
#     return {"access_token": access_token, "token_type": "bearer"}

# # =============================================================================
# # 3. ROUTERS
# # =============================================================================

# @app.get("/", tags=["Root"])
# def read_root():
#     logger.debug("Health Check: Root endpoint accessed.")
#     return {"message": "Welcome to the Payroll API (Powered by MongoDB)."}

# # Register Routers
# app.include_router(admins.router)
# app.include_router(employees.router)
# app.include_router(payslips.router) 
# app.include_router(attendance.router)   
# app.include_router(sites.router)
# app.include_router(roles.router)
# app.include_router(schedules.router)
# app.include_router(designations.router)
# app.include_router(duty_list.router)

# logger.info("ROUTERS: All API routes registered successfully.")

# # =============================================================================
# # 4. WEBSOCKETS
# # =============================================================================

# @app.websocket("/ws")
# async def websocket_endpoint(websocket: WebSocket):
#     await manager.connect(websocket)
#     client_info = f"{websocket.client.host}:{websocket.client.port}"
#     logger.info(f"WEBSOCKET: New connection established from {client_info}")
    
#     try:
#         while True:
#             await websocket.receive_text()
#             # If the client sends messages, you can log them here
#             # logger.debug(f"WS MESSAGE: {data}")
#     except WebSocketDisconnect:
#         manager.disconnect(websocket)
#         logger.info(f"WEBSOCKET: Client disconnected {client_info}")

# if __name__ == "__main__":
#     import uvicorn
#     logger.info("SERVER: Starting Uvicorn server...")
#     uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)



































# # new_backend/main.py

# from datetime import timedelta
# import os
# from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
# from fastapi.security import OAuth2PasswordRequestForm
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.staticfiles import StaticFiles # <--- 1. Import this
# from passlib.context import CryptContext

# # --- MongoDB Imports ---
# from new_backend.database import init_db
# from new_backend.models import Admin

# # --- Utilities ---
# # Make sure websocket_manager is compatible with your new logic
# from backend.websocket_manager import manager 
# from new_backend import security

# # --- Routers ---
# from new_backend.routers import (
#     admins, 
#     attendance, 
#     sites, 
#     schedules,
#     employees, 
#     payslips,
#     roles,
#     designations 
# )

# # --- App Setup ---
# app = FastAPI(title="Payroll Management API (MongoDB Edition)")

# # --- CORS ---
# origins = ["*"]
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # --- 2. STATIC FILES (Critical for Passport/Visa Images) ---
# # This ensures that http://localhost:8000/static/uploads/image.png works
# static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
# os.makedirs(static_dir, exist_ok=True) # Create folder if it doesn't exist
# app.mount("/static", StaticFiles(directory=static_dir), name="static")


# # --- Password Hashing ---
# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# # =============================================================================
# # 1. DATABASE INITIALIZATION
# # =============================================================================
# @app.on_event("startup")
# async def startup_db_client():
#     """
#     Connects to MongoDB and initializes Beanie ODM.
#     CRITICAL: ensure init_db() in database.py imports ALL your models:
#     (Admin, Employee, Attendance, Site, Schedule, Designation, Overtime, Deduction)
#     """
#     await init_db()

# # =============================================================================
# # 2. AUTHENTICATION
# # =============================================================================

# ROLE_POWER_MAP = {
#     "SuperAdmin": 100,
#     "Admin": 50,
#     "Site Manager": 20
# }

# @app.post("/token", tags=["Authentication"])
# async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
#     # 1. Find User by Email
#     user = await Admin.find_one(Admin.email == form_data.username)

#     # 2. Validate
#     if not user or not pwd_context.verify(form_data.password, user.hashed_password):
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Incorrect username or password",
#             headers={"WWW-Authenticate": "Bearer"},
#         )

#     if not user.is_active:
#         raise HTTPException(status_code=400, detail="User is inactive")

#     # 3. Create Token
#     power_level = ROLE_POWER_MAP.get(user.role, 0)
    
#     token_data = {
#         "sub": user.email,
#         "role": user.role,
#         "power": power_level,
#         "perms": user.permissions,       # Stored as list in Mongo
#         "sites": user.assigned_site_uids # Stored as list in Mongo
#     }
    
#     access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
#     access_token = security.create_access_token(
#         data=token_data, expires_delta=access_token_expires
#     )
    
#     return {"access_token": access_token, "token_type": "bearer"}

# # =============================================================================
# # 3. ROUTERS
# # =============================================================================

# @app.get("/", tags=["Root"])
# def read_root():
#     return {"message": "Welcome to the Payroll API (Powered by MongoDB)."}

# app.include_router(admins.router)
# app.include_router(employees.router)
# app.include_router(payslips.router) # Validated in previous step
# app.include_router(attendance.router)   
# app.include_router(sites.router)
# app.include_router(roles.router)
# app.include_router(schedules.router)
# app.include_router(designations.router)

# # =============================================================================
# # 4. WEBSOCKETS
# # =============================================================================

# @app.websocket("/ws")
# async def websocket_endpoint(websocket: WebSocket):
#     await manager.connect(websocket)
#     try:
#         while True:
#             await websocket.receive_text()
#     except WebSocketDisconnect:
#         manager.disconnect(websocket)

# if __name__ == "__main__":
#     import uvicorn
#     # Note: Updated path to match the file location 'new_backend'
#     uvicorn.run("new_backend.main:app", host="127.0.0.1", port=8000, reload=True)











