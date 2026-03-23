# Coin Ta7richa - POS System

## Project Overview
Coin Ta7richa is a standalone POS (Point of Sale) system for a Tunisian food corner. It consists of:
- **Frontend** (`frontend/`): 3 HTML pages — Cashier POS, Kitchen Display, Manager Dashboard
- **Backend** (`server/`): Flask API with PostgreSQL (Supabase) or SQLite fallback

## Architecture
- Frontend is served by the Flask backend (same-origin), so API calls use relative URLs (`/api/...`)
- When deployed on Render.com, both frontend and API run on the same service
- Offline fallback: all frontends use localStorage when the API is unreachable
- PIN protection on all 3 screens (default PIN: 1234)

## Key Files
- `server/app.py` — Flask API (products, tickets, sessions CRUD)
- `frontend/index.html` — Cashier POS (product selection, cart, ticket creation)
- `frontend/kitchen.html` — Kitchen display (order queue, status management)
- `frontend/manager.html` — Manager dashboard (products CRUD, sales, exports, settings)

## API Endpoints
- `GET/POST /api/products` — List/create products
- `PUT/DELETE /api/products/:id` — Update/delete product
- `POST /api/products/reset` — Reset to defaults
- `GET/POST /api/tickets` — List/create tickets (filterable by status, session_id)
- `PUT/DELETE /api/tickets/:id` — Update/delete ticket
- `GET /api/sessions/current` — Get active session
- `POST /api/sessions` — Create session
- `PUT /api/sessions/:id` — Update session
- `GET /api/ping` — Health check

## Database
- **Production**: PostgreSQL via Supabase (set `DATABASE_URL` env var)
- **Local dev**: SQLite (`data.db`) when `DATABASE_URL` is not set
- Data is persistent on Supabase (survives redeploys)

## Deployment
- **Render.com**: Deploy the whole project — `render.yaml` configures the service
- Backend serves frontend files from `../frontend/` directory
- Set `DATABASE_URL` in Render env vars to connect to Supabase PostgreSQL
- Root directory on Render must be set to `server`

## Currency
All prices are in Tunisian Dinars (TND), displayed with 3 decimal places.

## Development
```bash
cd server
pip install -r requirements.txt
python app.py
# Open http://localhost:5050
```

## Product Categories
- COIN DRO3: Sweet pastries (Sahfa variants)
- COIN MELAH: Savory sandwiches + supplements
- COIN HLOU: Sweet bread combinations (Khobz + toppings)
