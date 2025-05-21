from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware import Middleware
from app.routes import auth_routes  
from app.routes import billing_routes
from app.middleware.auth_middleware import AuthMiddleware

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    ),
    Middleware(AuthMiddleware),
]

app = FastAPI(
    title="GCP Billing API",
    version="1.0.0",
    middleware=middleware
)

@app.get("/")
def root():
    return {"message": "Server is working!"}

app.include_router(auth_routes.router)
app.include_router(billing_routes.router)
