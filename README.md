# NeoMarket B2C Service

B2C service for NeoMarket - buyer-facing API for catalog, cart, orders.

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
uvicorn src.main:app --reload
```

## Tests

```bash
pytest tests/ -v
```

## Project Structure

```
src/
├── api/           # Endpoints
├── models/        # SQLAlchemy models
├── schemas/       # Pydantic schemas
├── services/      # Business logic
├── dependencies/  # Auth, etc.
├── config.py      # Settings
├── database.py    # DB setup
├── exceptions.py  # Error handlers
└── main.py        # FastAPI app
tests/
└── conftest.py    # Test fixtures
```
