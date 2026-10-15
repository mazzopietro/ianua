# Ianua

**Ianua** is a simple yet solid REST API authentication service built with FastAPI and PostgreSQL. It provides user registration, token-based authentication, session revocation, password management, and role-based access control.

## Features

* User registration and login
* JWT access tokens and refresh tokens
* Refresh token rotation
* Logout and refresh token revocation
* Revocation of all user sessions
* Password change
* Authenticated user profile endpoint
* Role-based access control for administrators
* Centralized exception handling and request logging
* Health check endpoint
* PostgreSQL integration with SQLAlchemy and Alembic
* Password hashing with Argon2
* Environment-based configuration
* Automated tests with pytest
* Redis-backed rate limiting for authentication endpoints
* Configurable per-IP request limits for registration, login and token refresh
* Atomic Redis counters with automatic expiration
* Explicit error handling when the rate-limiting service is unavailable

## Tech stack

* **Python** 3.14+
* **FastAPI** — REST API and OpenAPI documentation
* **PostgreSQL** — relational database
* **SQLAlchemy** — ORM
* **Redis** — shared counters for distributed rate limiting
* **Alembic** — database migrations
* **PyJWT** — JWT handling
* **pwdlib + Argon2** — password hashing
* **redis-py** — asynchronous Redis client 
* **Pydantic Settings** — application configuration
* **Uvicorn** — ASGI server
* **pytest + HTTPX** — testing

## Requirements

* Python 3.14 or later
* PostgreSQL
* Redis
* [uv](https://docs.astral.sh/uv/) for dependency management

## Getting started

### 1. Clone the repository

```bash
git clone https://github.com/mazzopietro/ianua.git
cd ianua
```

### 2. Install dependencies

```bash
uv sync --dev
```

### 3. Configure environment variables

Create a local environment file from the example:

```bash
cp .env.example .env
```

Update `.env` with your local PostgreSQL connection details and a strong JWT secret.

Example:

```dotenv
APP_NAME=Ianua Auth Service
APP_VERSION=0.1.0
ENVIRONMENT=development
DEBUG=True

DATABASE_URL=postgresql+psycopg://USER:PASSWORD@localhost:5432/DATABASE
TEST_DATABASE_URL=postgresql+psycopg://USER:PASSWORD@localhost:5432/DATABASE_TEST

JWT_SECRET_KEY=replace-with-a-strong-random-secret
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

REDIS_URL=redis://localhost:6379/0
REDIS_KEY_PREFIX=ianua
REDIS_RATE_LIMIT_ENABLED=True

RATE_LIMIT_REGISTER_REQUESTS=5
RATE_LIMIT_REGISTER_WINDOW_SECONDS=900

RATE_LIMIT_LOGIN_REQUESTS=10
RATE_LIMIT_LOGIN_WINDOW_SECONDS=60

RATE_LIMIT_REFRESH_REQUESTS=30
RATE_LIMIT_REFRESH_WINDOW_SECONDS=60
```

Create the application and test databases in PostgreSQL before running the service or its tests.

**Important:** `JWT_SECRET_KEY` must be at least 32 characters long. Use a securely generated secret in real deployments, and never commit `.env` or production credentials.

The test environment requires `TEST_DATABASE_URL` to be set and to differ from `DATABASE_URL`.

### 4. Apply database migrations

```bash
uv run alembic upgrade head
```

Run this command after configuring the database and before starting the application, assuming the repository's Alembic configuration is set up.

### 5. Start the application

```bash
uv run python -m ianua.run
```

The development server listens on:

```text
http://127.0.0.1:8000
```

Interactive API documentation is available at:

* Swagger UI: `http://127.0.0.1:8000/docs`
* ReDoc: `http://127.0.0.1:8000/redoc`

## API endpoints

| Method | Endpoint                | Description                                    |
| ------ | ----------------------- | ---------------------------------------------- |
| GET    | `/health`               | Check application health                       |
| POST   | `/auth/register`        | Register a new user                            |
| POST   | `/auth/login`           | Authenticate and obtain tokens                 |
| POST   | `/auth/refresh`         | Refresh tokens                                 |
| POST   | `/auth/logout`          | Revoke a refresh token                         |
| GET    | `/auth/me`              | Retrieve the authenticated user's profile      |
| GET    | `/auth/admin`           | Access the administrator-only endpoint         |
| POST   | `/auth/logout-all`      | Revoke all sessions for the authenticated user |
| POST   | `/auth/change-password` | Change the authenticated user's password       |

### Authentication

Protected endpoints require a valid access token sent using the Bearer authentication scheme:

```http
Authorization: Bearer <access_token>
```

The login and refresh endpoints return an access token and a refresh token. The access token expiration is configurable through `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`.

### Rate limiting

Ianua uses Redis to enforce configurable request limits on authentication endpoints. Counters are shared across API processes and expire automatically after their configured time window.

The default limits are:

| Endpoint | Maximum requests | Time window |
| -------- | ----------------: | ----------- |
| `POST /auth/register` | 5 | 15 minutes |
| `POST /auth/login` | 10 | 1 minute |
| `POST /auth/refresh` | 30 | 1 minute |

Limits are applied per client IP address and per endpoint. Requests count toward the limit even if authentication fails or request validation does not succeed.

When a client exceeds a limit, the API returns `429 Too Many Requests`, with error code `RATE_LIMIT_EXCEEDED` and a `Retry-After` header indicating how long to wait before retrying.

Redis is required for rate limiting. If Redis becomes unavailable during a rate-limit check, the API returns `503 Service Unavailable` with error code `RATE_LIMITER_UNAVAILABLE` instead of silently bypassing the protection.

The Redis client is initialized and checked during application startup, and closed during shutdown. If the initial Redis connection check fails, application startup fails.

The rate limiter uses atomic Redis operations and expiring counters. It implements a fixed-window strategy, not a sliding-window algorithm.

**Operational note:** Ianua uses the client IP reported by the ASGI request. If the API runs behind a reverse proxy, configure trusted proxy handling carefully before relying on forwarded client IP headers.

### Example: health check

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{
  "status": "ok"
}
```

## Running tests

Run the test suite with:

```bash
uv run pytest
```

Configure the test environment and test database according to the project's test configuration before running the suite. Use a separate test database to avoid affecting development data.

The test suite includes dedicated rate-limiting tests. These tests require a reachable Redis instance and exercise request limits, HTTP error responses, and Redis failure handling. The GitHub Actions workflow provides Redis as a service for CI runs.

## Configuration

| Variable                          | Description                                                 |
| --------------------------------- | ----------------------------------------------------------- |
| `APP_NAME`                        | Application name                                            |
| `APP_VERSION`                     | Application version                                         |
| `ENVIRONMENT`                     | Runtime environment: `development`, `test`, or `production` |
| `DEBUG`                           | Enables debug mode                                          |
| `DATABASE_URL`                    | Main PostgreSQL connection URL                              |
| `TEST_DATABASE_URL`               | Separate PostgreSQL connection URL for tests                |
| `JWT_SECRET_KEY`                  | Secret used to sign JWTs                                    |
| `JWT_ALGORITHM`                   | JWT signing algorithm; currently `HS256`                    |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime in minutes                            |
| `REDIS_URL` | Redis connection URL |
| `REDIS_KEY_PREFIX` | Prefix used for Redis rate-limit keys |
| `REDIS_RATE_LIMIT_ENABLED` | Enables or disables rate limiting |
| `RATE_LIMIT_REGISTER_REQUESTS` | Maximum registration requests per IP per window |
| `RATE_LIMIT_REGISTER_WINDOW_SECONDS` | Registration rate-limit window in seconds |
| `RATE_LIMIT_LOGIN_REQUESTS` | Maximum login requests per IP per window |
| `RATE_LIMIT_LOGIN_WINDOW_SECONDS` | Login rate-limit window in seconds |
| `RATE_LIMIT_REFRESH_REQUESTS` | Maximum token-refresh requests per IP per window |
| `RATE_LIMIT_REFRESH_WINDOW_SECONDS` | Token-refresh rate-limit window in seconds |

The Redis service must be available when the application starts. Disabling rate limiting skips the request checks, but does not remove the application's Redis startup dependency

In production, debug mode must be disabled and the JWT secret must not use a placeholder value.

## Running with Docker

The application can be run using [Docker](https://docs.docker.com/get-docker/) Compose, which starts the FastAPI application, PostgreSQL, and Redis. Redis is used internally by the API for distributed rate limiting and does not need to expose its port to the host.

### Configuration

Create a `.env.docker` file in the project root using `.env.example` as a reference, and configure the required environment variables.

At minimum, configure:

* `POSTGRES_DB`
* `POSTGRES_USER`
* `POSTGRES_PASSWORD`
* `DATABASE_URL`
* `JWT_SECRET_KEY`
* `REDIS_URL` — use `redis://redis:6379/0` when running the API through Docker Compose

Make sure `DATABASE_URL` points to the PostgreSQL service using `db` as the hostname, for example:

`postgresql+psycopg://ianua:your_password@db:5432/ianua`

Use a sufficiently long, randomly generated `JWT_SECRET_KEY`. Do not commit `.env.docker` or other files containing secrets.

### Build and start the services

Build the API image:

```bash
docker compose --env-file .env.docker build api
```

Start PostgreSQL:

```bash
docker compose --env-file .env.docker up -d db
```

Apply database migrations:

```bash
docker compose --env-file .env.docker run --rm api alembic upgrade head
```

Start the API:

```bash
docker compose --env-file .env.docker up -d api
```

Once the database has been initialized and migrations have been applied, start both services with:

```bash
docker compose --env-file .env.docker up -d
```

### Access the API

Once the API is running, open:

* API: http://localhost:8000
* Interactive API documentation: http://localhost:8000/docs
* Alternative API documentation: http://localhost:8000/redoc

### Stop the services

Stop the containers without deleting the persistent database volume:

```bash
docker compose --env-file .env.docker down
```

PostgreSQL data is stored in a named Docker volume and persists when containers are stopped or removed. **Do not use `docker compose down -v` unless you intentionally want to delete the database volume.**

## Project status

Ianua is under active development.

## License

No license has been specified yet.
