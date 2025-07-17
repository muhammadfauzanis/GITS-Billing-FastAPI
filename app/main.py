import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware import Middleware

from app.routes import auth_routes, billing_routes, user_routes, admin_routes,notification_routes
from app.middleware.auth_middleware import AuthMiddleware

load_dotenv()

CLIENT_URL = os.getenv("CLIENT_URL")

# allow_origins = ['http://localhost:3000']

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=[CLIENT_URL],
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
app.include_router(user_routes.router)
app.include_router(billing_routes.router)
app.include_router(admin_routes.router)
app.include_router(notification_routes.router) 
