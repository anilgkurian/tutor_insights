from fastapi import FastAPI
import logging
from .routers import insights
from fastapi.middleware.cors import CORSMiddleware

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tutor_insights")


app = FastAPI(title="Tutor Insights Service")

# CORS for direct access if needed (proxy is primary)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174", "http://localhost:5173", "http://localhost:4501", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(insights.router)



@app.get("/health")
def health_check():
    return {"status": "ok"}
