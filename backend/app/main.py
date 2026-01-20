from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import routes, prices, health

app = FastAPI(
    title="Walkabout",
    description="Self-hosted travel deal monitor",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(routes.router, prefix="/api/routes", tags=["routes"])
app.include_router(prices.router, prefix="/api/prices", tags=["prices"])


@app.get("/")
async def root():
    return {"name": "Walkabout", "status": "running"}
