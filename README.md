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

## Tech stack

* **Python** 3.14+
* **FastAPI** — REST API and OpenAPI documentation
* **PostgreSQL** — relational database
* **SQLAlchemy** — ORM
* **Alembic** — database migrations
* **PyJWT** — JWT handling
* **pwdlib + Argon2** — password hashing
* **Pydantic Settings** — application configuration
* **Uvicorn** — ASGI server
* **pytest + HTTPX** — testing

## Requirements

* Python 3.14 or later
* PostgreSQL
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

In production, debug mode must be disabled and the JWT secret must not use a placeholder value.

## Project status

Ianua is under active development.

## License

No license has been specified yet.
