from fastapi import FastAPI
from src.database import Base, engine
from src.exceptions import register_exception_handlers

app = FastAPI(title="NeoMarket B2C Service")

Base.metadata.create_all(bind=engine)

register_exception_handlers(app)


@app.get("/")
def root():
    return {"message": "B2C Service"}
