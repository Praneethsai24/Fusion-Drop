# FusionDrop Backend

FastAPI-powered logistics backend for multi-restaurant food delivery.

## Setup

```bash
cd backend

# 1. Create virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env and set SECRET_KEY to a random 32+ char string

# 4. Run the server
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

## API Docs
Open http://localhost:8000/docs for the interactive Swagger UI.

## Demo Credentials
- Customer: demo@fusiondrop.in / demo1234
- Rider: arjun@fusiondrop.in / rider123

## Key Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /auth/customer/signup | Register customer |
| POST | /auth/rider/signup | Register rider |
| POST | /auth/login | Login (both roles) |
| GET | /restaurants/ | List restaurants + menus |
| POST | /orders/checkout | Checkout multi-restaurant cart |
| GET | /orders/my | My order history |
| WS | /ws/orders/{id} | Live delivery tracking |

## WebSocket Usage

```javascript
const ws = new WebSocket("ws://localhost:8000/ws/orders/42");
ws.onmessage = (e) => {
  const { event, data } = JSON.parse(e.data);
  if (event === "order_update") console.log(data.status);
  if (event === "rider_location") console.log(data.lat, data.lng);
};
ws.send("ping"); // keepalive
```