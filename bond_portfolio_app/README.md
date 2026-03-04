# Bond Portfolio Banking API

A production-ready backend for a bond portfolio dashboard, built with FastAPI and PostgreSQL.

## Features
- User registration and authentication (JWT)
- Portfolio upload and versioning
- Holdings and risk analytics
- Scenario analysis (yield shock)
- Modular, scalable architecture

## Project Structure
```
bond_portfolio_app/
│
├── app/
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── auth.py
│   ├── routers/
│   │     ├── auth.py
│   │     ├── users.py
│   │     ├── portfolios.py
│   │     ├── holdings.py
│   │     └── analytics.py
│   ├── services/
│   │     ├── bond_calculator.py
│   │     └── shock_engine.py
│
├── requirements.txt
└── README.md
```

## Quick Start

1. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
2. Set up PostgreSQL and create the database/tables (see docs or SQL in project plan).
3. Run the API server:
   ```sh
   uvicorn app.main:app --reload
   ```

## API Endpoints
See the OpenAPI docs at `/docs` when running the server.
