from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import auth_routes  
from app.routes import billing_routes
from app.middleware.auth_middleware import AuthMiddleware

app = FastAPI(
    title="GCP Billing API",
    version="1.0.0"
)

# Optional: konfigurasi CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ganti dengan list origin di production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check
@app.get("/")
def root():
    return {"message": "Server is working!"}

# Routing
app.add_middleware(AuthMiddleware)
app.include_router(auth_routes.router)
app.include_router(billing_routes.router) 

