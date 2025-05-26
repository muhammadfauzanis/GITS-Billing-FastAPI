import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware import Middleware

from app.routes import auth_routes, billing_routes, user_routes
from app.middleware.auth_middleware import AuthMiddleware

# Load env variables
load_dotenv()

LOCAL_URL = os.getenv("LOCAL_URL", "http://localhost:3000")
SERVER_URL = os.getenv("SERVER_URL")

allow_origins = [url for url in [LOCAL_URL, SERVER_URL] if url]

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
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
