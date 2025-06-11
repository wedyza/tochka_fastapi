# type: ignore

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import order, public, user, balance, admin

app = FastAPI()

origins = [
    settings.CLIENT_ORIGIN,
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_API_URL = "/api/v1/"

app.include_router(public.router, tags=["Public"], prefix=f"{BASE_API_URL}public")
app.include_router(user.router, tags=["Users"], prefix=f"{BASE_API_URL}users")
app.include_router(balance.router, tags=["Balance"], prefix=f"{BASE_API_URL}balance")
app.include_router(order.router, tags=["Orders"], prefix=f"{BASE_API_URL}order")
app.include_router(admin.router, tags=["Admin"], prefix=f"{BASE_API_URL}admin")
