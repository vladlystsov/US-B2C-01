from fastapi import FastAPI
from src.database import Base, engine
from src.exceptions import register_exception_handlers
from src.api import catalog, product_card, similar_products, categories, favorites, subscriptions, cart, banners

app = FastAPI(title="NeoMarket B2C Service")

Base.metadata.create_all(bind=engine)

register_exception_handlers(app)

app.include_router(catalog.router)
app.include_router(product_card.router)
app.include_router(similar_products.router)
app.include_router(categories.router)
app.include_router(favorites.router)
app.include_router(subscriptions.router)
app.include_router(cart.router)
app.include_router(banners.router)


@app.get("/")
def root():
    return {"message": "B2C Service"}
