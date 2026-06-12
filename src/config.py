import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "b2c-secret-key-change-in-production")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./neomarket_b2c.db")

    B2B_SERVICE_URL = os.getenv("B2B_SERVICE_URL", "http://localhost:8000")
    B2B_SERVICE_KEY = os.getenv("B2B_SERVICE_KEY", "b2c-secret-key-123")

    DEBUG = os.getenv("DEBUG", "True").lower() == "true"

settings = Settings()
