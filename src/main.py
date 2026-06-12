from fastapi import FastAPI
from src.database import Base, engine
from src.exceptions import register_exception_handlers
from src.api import catalog, product_card, similar_products, categories

app = FastAPI(title="NeoMarket B2C Service")

Base.metadata.create_all(bind=engine)

register_exception_handlers(app)

app.include_router(catalog.router)
app.include_router(product_card.router)
app.include_router(similar_products.router)
app.include_router(categories.router)


@app.get("/")
def root():
    return {"message": "B2C Service"}
