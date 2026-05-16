# 🍔 FusionDrop

**Multi-restaurant food delivery platform** with intelligent delivery batching,
real-time order tracking via WebSockets, and AI-powered meal recommendations.

> Built with **FastAPI · PostgreSQL · Redis · LangChain · React + Vite**

[![CI](https://github.com/Praneethsai24/Fusion-Drop/actions/workflows/ci.yml/badge.svg)](https://github.com/Praneethsai24/Fusion-Drop/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ✨ Features

- 🛒 **Multi-restaurant checkout** — order from multiple restaurants in a single transaction
- 🚴 **Real-time delivery tracking** — WebSocket live updates at `/ws/orders/{id}`
- 🧠 **AI-powered recommendations** — LangChain + OpenAI RAG pipeline
- 📦 **Smart delivery batching** — optimiser groups nearby orders to reduce fees
- 📊 **Prometheus metrics** — full observability at `/metrics`
- 🔐 **JWT auth** — access + refresh token pair, role-based (customer / rider)
- 🐳 **Docker-first** — full stack runs with one command

---

## 🚀 Quick Start

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/) & Docker Compose v2
- Node.js 20+ *(frontend only)*

### 1. Clone and configure

```bash
git clone https://github.com/Praneethsai24/Fusion-Drop.git
cd Fusion-Drop
cp backend/.env.example backend/.env
```

Edit `backend/.env` and set a strong `SECRET_KEY`:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 2. Start the full stack

```bash
docker compose up --build
```

| Service      | URL                              |
|--------------|----------------------------------|
| REST API     | http://localhost:8000            |
| Swagger Docs | http://localhost:8000/docs       |
| ReDoc        | http://localhost:8000/redoc      |
| Frontend     | http://localhost:5173            |
| Metrics      | http://localhost:8000/metrics    |

### 3. Demo credentials (auto-seeded)

| Role     | Email                  | Password   |
|----------|------------------------|------------|
| Customer | demo@fusiondrop.in     | demo1234   |
| Rider    | arjun@fusiondrop.in    | rider123   |
| Rider    | priya@fusiondrop.in    | rider123   |

---

## 🏗️ Project Structure
Fusion-Drop/
├── backend/ # FastAPI application
│ ├── main.py # App factory, lifespan, WebSocket
│ ├── routers/ # HTTP route handlers (auth, orders, restaurants, riders)
│ ├── services/ # Business logic (OrderService, optimizer)
│ ├── models/ # SQLAlchemy ORM models
│ ├── schemas/ # Pydantic v2 request/response schemas
│ ├── core/ # Config, logging, exceptions, security
│ ├── auth/ # JWT dependency (get_current_user)
│ ├── ai/ # LangChain RAG pipeline (Phase 4)
│ ├── websocket/ # WebSocket connection manager
│ ├── workers/ # Background task workers
│ ├── database/ # Async engine, session factory
│ └── tests/ # pytest async test suite
├── frontend/ # React + Vite SPA
├── docker/ # Nginx configs, helper Dockerfiles
├── scripts/ # Dev utility scripts
└── docker-compose.yml # Full stack orchestration


---

## 🧪 Running Tests

```bash
cd backend

# Install deps (includes test extras)
pip install -r requirements.txt pytest-cov

# Run with coverage report
pytest tests/ -v --asyncio-mode=auto --cov=. --cov-report=term-missing
```

---

## 🗄️ Database Migrations

This project uses [Alembic](https://alembic.sqlalchemy.org/) for schema migrations.

```bash
cd backend

# Apply all pending migrations
alembic upgrade head

# Create a new migration after changing a model
alembic revision --autogenerate -m "describe_your_change"

# Roll back one migration
alembic downgrade -1
```

> **Note:** `init_db()` at startup auto-creates tables in **development** only.  
> In **production**, always run `alembic upgrade head` explicitly before deploying.

---

## 🔌 API Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/auth/customer/signup` | Register a customer |
| `POST` | `/api/v1/auth/rider/signup` | Register a rider |
| `POST` | `/api/v1/auth/login` | Login (returns access + refresh token) |
| `POST` | `/api/v1/auth/refresh` | Exchange refresh token for new access token |
| `GET`  | `/api/v1/auth/me` | Get authenticated user profile |
| `GET`  | `/api/v1/restaurants/` | List open restaurants |
| `GET`  | `/api/v1/restaurants/{id}` | Get restaurant + menu |
| `POST` | `/api/v1/orders/checkout` | Place an order |
| `GET`  | `/api/v1/orders/my` | Order history |
| `GET`  | `/api/v1/orders/{id}` | Get single order |
| `PATCH`| `/api/v1/orders/{id}/status` | Update order status (rider) |
| `POST` | `/api/v1/orders/{id}/cancel` | Cancel an order (customer) |
| `WS`   | `/ws/orders/{id}?token=<jwt>` | Real-time order tracking |

Full interactive docs at **http://localhost:8000/docs**

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/your-feature`
3. Follow [Conventional Commits](https://www.conventionalcommits.org/)
4. Ensure all tests pass: `pytest tests/ -v`
5. Open a Pull Request against `develop`

See [CONTRIBUTING.md](.github/CONTRIBUTING.md) for the full guide.

---

## 🔒 Security

To report a vulnerability, please see [SECURITY.md](SECURITY.md).  
**Do not** open a public issue for security bugs.

---

## 📄 License

[MIT](LICENSE) © 2025 FusionDrop Contributors