# SmartCart AI

Product recommendations and customer churn on the Retailrocket e-commerce data, served by FastAPI.

## Layout
```
data/db/        ecommerce.db (not in git) and schema.sql
models/         exported models, churn bundle, manifest, configs, mlflow.db
src/smartcart/  config, db, appdb + migrations/, security, accounts, deps, auth_routes, me_routes, chat_routes, admin_routes,
                catalog, personalize, chat/ (intents, llm, service), churn, recommend, ranker, app
scripts/        build_serving_tables.py, build_ranker_state.py, sqlite_to_postgres.py, migrate.py, create_admin.py
frontend/       React app
tests/          API tests on a small generated database
```

## Start (SQLite, simplest)
```bash
pip install -r requirements-dev.txt
cp /path/to/ecommerce.db data/db/ecommerce.db
python scripts/build_serving_tables.py --db data/db/ecommerce.db
python scripts/build_ranker_state.py --db data/db/ecommerce.db
PYTHONPATH=src uvicorn smartcart.app:app --reload
```
On Windows PowerShell set the path with `$env:PYTHONPATH = "src"` and start with `python -m uvicorn smartcart.app:app --reload`.
Open http://127.0.0.1:8000/docs for every endpoint. Tests: `PYTHONPATH=src pytest -q`.

The two build scripts add tables to the database and run once, and again whenever the events change:
- `build_serving_tables.py`: `item_neighbors` and `item_popularity` (the hybrid recommender).
- `build_ranker_state.py`: the `rk_*` tables (item statistics, item-item similarity, category and popularity tables) that the rankers need. Pass `--as-of <ms>` to build the state at an earlier time.

## Start with PostgreSQL
```bash
docker compose up -d db
docker compose run --rm loader          # copies ecommerce.db (SQLite) into PostgreSQL
docker compose up -d --build api web mlflow
```
Or without Docker: `python scripts/sqlite_to_postgres.py --sqlite data/db/ecommerce.db --url postgresql://user:pass@host:5432/smartcart`, then run the API with `DATABASE_URL` set to the same URL. The API reads from PostgreSQL when `DATABASE_URL` is set and from SQLite otherwise. Run the two build scripts on the SQLite file before loading.
To run the tests against PostgreSQL: `TEST_PG_URL=postgresql://... PYTHONPATH=src pytest -q`.

## Frontend (React + Vite)
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:5173 (the API must be running on port 8000; change it with `VITE_API_URL` in `frontend/.env`; the origin must be listed in `CORS_ORIGINS`). Keep the browser/API host consistent (`localhost` with `localhost`, or `127.0.0.1` with `127.0.0.1`) so the SameSite session cookie is sent after login.

Public: products, product details, login, register. Users (`/dashboard`, `/chat`, `/profile`): personalized recommendations, shopping assistant, interests and privacy. Admins (`/admin/*`): overview, users, churn, models, customer lookup, audit log.

Product imagery: the catalog database is synthetic and has no image column. The frontend maps product types/departments to category-appropriate Unsplash images, loaded lazily with an emoji fallback if an image request fails. These are presentation-only and do not change catalog data.

## Run everything locally (Windows PowerShell)
Open three terminals in the project folder.

Backend:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
Copy-Item .env.example .env
$env:PYTHONPATH = "src"
python scripts/migrate.py
$env:ADMIN_PASSWORD = "a-long-password"
python scripts/create_admin.py --email you@example.com --name "Your Name"
python -m uvicorn smartcart.app:app --port 8000
```
Frontend:
```powershell
cd frontend
npm install
npm run dev
```
MLflow (install it separately, it is not needed by the API):
```powershell
.\.venv\Scripts\Activate.ps1
pip install mlflow==3.17.2
mlflow ui --backend-store-uri sqlite:///models/mlflow.db --host 127.0.0.1 --port 5000 --workers 1
```
API http://127.0.0.1:8000/docs, web http://localhost:5173, MLflow http://127.0.0.1:5000. The API reads `.env` from the project folder.

Always pass the backend-store URI explicitly from the project root; otherwise MLflow may default to a different `mlflow.db` in the current working directory. The checked-in tracking database uses the local `models/mlruns` directory for artifacts. On Windows, one worker avoids the multiprocessing/socket issue seen with `WinError 10022`.

## Accounts, roles and security
Copy `.env.example` to `.env` and review it. Accounts live in a separate application database (`APP_DATABASE_PATH` or `APP_DATABASE_URL`); the Retailrocket catalog database stays read-only.

```bash
python scripts/migrate.py                       # additive, idempotent; also runs at API start
ADMIN_PASSWORD='choose-a-long-password' python scripts/create_admin.py --email you@example.com --name "Your Name"
```
`create_admin.py` reads the password from `ADMIN_PASSWORD` or prompts for it; `--promote` turns an existing account into an admin. This is the only way to create an admin: the register endpoint rejects any `role` field (422), and no password or secret is stored in code or the frontend.

- **Passwords:** argon2id, minimum 10 characters with letters and digits, common passwords and passwords containing the name or email prefix are refused. Emails are normalized (lowercase, trimmed) and unique.
- **Sessions:** random token in an `HttpOnly` cookie (`sc_session`), only its SHA-256 is stored. `SameSite=Lax`; set `COOKIE_SECURE=true` behind HTTPS.
- **CSRF:** every unsafe request needs the `X-CSRF-Token` header (returned by login, register and `/auth/me`) and an `Origin` that is in `CORS_ORIGINS`.
- **RBAC:** roles `user` and `admin`, enforced on the backend. 401 when not logged in, 403 when the role is not enough. Customer-data endpoints (`/customers/*`, `/churn/at-risk`, `/models`) are now admin only.
- **Identity:** a new account has no Retailrocket history. Only an admin can link an account to a historical visitor id (`/admin/users/{id}/link-visitor`), one visitor per account, audited. Recommendations and the assistant always use the account of the session, never an id sent by the client.
- **Rate limits:** login, register, chat and events. In memory and per process: with several workers or servers, put a shared limiter (for example at the reverse proxy) in front.
- **Assistant:** a deterministic parser picks the intent and the catalog tools; an optional LLM (`LLM_PROVIDER=anthropic|openai`, `LLM_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL`) only rewrites the result, and its answer is rejected in favour of the built-in answer if it names unknown products, invents prices, adds links or leaks instructions. Conversations are stored per account and can be deleted by the user.

### API additions
| | |
|---|---|
| `POST /auth/register`, `/auth/login`, `/auth/logout`, `GET /auth/me` | session handling |
| `GET /me`, `PUT /me/profile`, `GET/PUT /me/preferences` | profile and interests |
| `POST /me/events` | record a `view` or `addtocart` for a product |
| `GET /me/recommendations` | sections, each labelled `history_based`, `preference_based` or `popularity_based` |
| `POST /chat`, `GET /chat/conversations[/id]`, `DELETE /chat/conversations[/id]` | assistant |
| `GET /admin/overview, /users, /churn, /models, /health, /audit`; `POST /admin/users/{id}/disable, /enable, /link-visitor, /unlink-visitor` | administration |

### Known limits
- There is no checkout, so the app records views and add-to-cart only, never purchases.
- Trending and popular products reflect the last weeks of the 2015 dataset, not live traffic. Names and prices are generated.
- The client IP is `request.client.host`; proxy headers are not trusted. Behind a proxy, run uvicorn with `--proxy-headers --forwarded-allow-ips` for your proxy only.
- Registering an existing email returns 409, which reveals that the address is registered.
- The LLM path is covered by tests with fake providers only, not against a live provider.

## Endpoints (catalog and legacy)
| | |
|---|---|
| `GET /health` | status, model, data origin |
| `GET /products` | search and filter (`q`, `department`, `min_price`, `max_price`, `in_stock`, `deal`, `sort`) |
| `GET /products/{id}`, `/products/{id}/similar` | product and similar products |
| `GET /categories` | departments |
| `GET /customers/{id}` | customer and features |
| `GET /customers/{id}/recommendations` | personalised list, cold start falls back to popularity |
| `GET /customers/{id}/churn` | probability, tier, action, top reasons |
| `GET /churn/at-risk` | customers by tier, highest risk first |
| `GET /models` | exported models and their scores |

## What the models do here
- **Churn:** the exported calibrated logistic regression (threshold 0.835, low cut 0.716). It was trained on customers who had bought, so customers without a purchase are not scored. Features are rebuilt from the `events` table as of the last event of the data.
- **Recommendations** (`?task=`):
  - `discovery` (default): new items only, never touched by the customer. Candidates come from the CF, popularity and category sources (items from the customer's recent context are left out, as in training), and every item the customer ever touched is removed. Re-ranked by the exported discovery model (logistic regression).
  - `purchase`: everything, including items the customer already looked at. Re-ranked by the exported LightGBM ranker.
  - `hybrid`: candidate sources fused by reciprocal rank fusion, no model. Used when the ranker tables are missing.
  The ranker features are rebuilt at request time from the customer's latest visit (its last 3 events) and the previous 30 days, with item statistics as of the end of the data. Compared with the notebook pipeline on 60 test queries, 36 of 38 features are identical; the other two (the CF rank and the fused score) differ slightly where scores tie. The item-item similarity keeps the 200 strongest neighbours per item, which changed the top 10 for under 1% of queries on the test data.

## Data caveat
Product names, brands, prices and everything built on prices are generated (`*_is_synthetic = 1`). Recommendations and churn do not use them.

## Pinned versions
Models were trained with scikit-learn 1.6.1 and numpy 2.1.3 (see `models/environment.json`); `requirements.txt` pins them so the files load without warnings.

## Docker
```bash
docker compose up --build
```
API on :8000, web on :3000, MLflow UI on :5000 (reads `models/mlflow.db`).
Create the first admin: `ADMIN_EMAIL=you@example.com ADMIN_PASSWORD=... docker compose --profile init run --rm admin`. Change the database password in `docker-compose.yml` before exposing it.
# Local monitoring

SmartCart includes a local-first monitoring store at `models/monitoring.db`. It records CPU, memory, and disk snapshots; inference counts, duration, failures, model versions, and non-identifying prediction distributions; and reference/current data-quality comparisons. It does not collect HTTP request counts, latency, HTTP error rates, cookies, tokens, or raw customer records.

The admin view is available at `http://localhost:5173/admin/monitoring` after signing in as an administrator. The protected summary endpoint is `GET /admin/monitoring`.

Windows PowerShell examples:

```powershell
$env:PYTHONPATH = "src"
python scripts\run_monitor.py --once
python scripts\run_monitor.py --interval 60
# Compare the existing pre-serving database snapshot with the current catalog.
# This reads real SQLite tables; it does not create synthetic events or labels.
python scripts\monitor_data.py `
  --reference-db data\db\ecommerce.db.before_serving_tables_20261028.bak `
  --current-db data\db\ecommerce.db `
  --table products --name catalog_products
```

The command above is a reproducible comparison of the repository’s existing SQLite snapshots. For a true production reference/current comparison, provide two snapshots of the same table and schema using the same `--reference-db`, `--current-db`, and `--table` options. The report is stored in `models/monitoring.db`; a `warning` exit code means schema or drift thresholds were exceeded, while `ok` and `unavailable` exit successfully. Existing MLflow tracking remains unchanged and no duplicate MLflow runs are created. Configure thresholds in `.env` using the `MONITOR_*` settings in `.env.example`. If CPU or memory are unavailable, install the declared dependency with `.\.venv_compat\Scripts\python.exe -m pip install -r requirements.txt`. Stop the continuous monitor with `Ctrl+C`.
