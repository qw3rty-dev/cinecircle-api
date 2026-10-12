# CineCircle API

**A social backend for movie and TV reviews. Browse media (with a local cache layer), follow other users, review and rate what you watch, vote/comment on reviews, keep a watchlist, and get a basic activity-based recommendation feed.**

The project integrates with [The Movie Database (TMDB)](https://www.themoviedb.org/) for media data.

## Features

### Authentication & Security
- User registration and login with JWT authentication.
- Password hashing using Argon2.
- Email verification and password reset through OTPs.
- Access and refresh tokens.
- Password change and account deletion.
- Public and private user accounts.

### Media Discovery
- Search movies and TV shows through TMDB.
- Browse trending movies and TV shows.
- Cache TMDB responses using a JSON-based cache with expiration

### Watchlist & Media Activity
- Add and remove media from a personal watchlist.
- Update watchlist status.
- Record watched, liked, loved and disliked activities.

### Reviews & Social Features 
- Create, edit and delete reviews.
- Rate media from 1 to 5.
- Comment on reviews.
- Upvote and downvote reviews.
- Follow users and manage follow requests.
- Support private accounts and follow-request workflows.
- Browse user profiles, followers and following lists.

### Feed & Recommendations
- Personalized media recommendations based on user activity.
- Activity feed featuring reviews from followed users.
 
### Background Processing & Administration
- Background email sending with FastAPI `BackgroundTasks`
- Scheduled genre synchronization and account cleanup using APScheduler.
- Admin endpoints for user management, statistics, genre synchronization, and moderation.

## Tech Stack

| Technology | Purpose |
|---|---|
| Python | Application language |
| FastAPI | REST API framework |
| PostgreSQL | Persistent relational storage |
| SQLAlchemy 2.0 | Async ORM and database access |
| Alembic | Database migrations |
| Pydantic v2 | Request validation and response schemas |
| JWT | Authentication |
| Argon2 | Password hashing |
| HTTPX | Asynchronous HTTP requests |
| TMDB API | External movie and TV data |
| Resend | Transactional email |
| APScheduler | Scheduled jobs |
| Pytest | Automated testing |

## Project Structure

```text
src/
├── admin/          # Administrative operations
├── api/v1/         # API router composition
├── auth/           # Authentication and account lifecycle
├── common/         # Shared schemas and utilities
├── feed/           # Feed and recommendation logic
├── home/           # API root information
├── media/          # Media discovery and activity
├── reviews/        # Reviews, comments, and votes
├── scheduler/      # Scheduled maintenance jobs
├── security/       # JWT and password utilities
├── services/
│   ├── email/      # Email integration
│   └── tmdb/       # TMDB client and caching
├── users/          # Profiles and social relationships
├── watchlist/      # Watchlist operations
├── db.py           # Database configuration
├── enums.py        # Shared enums
├── main.py         # FastAPI application
└── models.py       # SQLAlchemy models

alembic/
└── versions/       # Database migration history

tests/              # in progress

```

## API Overview

All versioned endpoints use `/v1`.

| Area | Example endpoints |
|---|---|
| Authentication | `/v1/auth/register`, `/v1/auth/login` |
| Media search | `/v1/media/search/{search}` |
| Trending | `/v1/media/trending/movie`, `/v1/media/trending/tv` |
| Watchlist | `/v1/watchlist` |
| Reviews | `/v1/reviews` |
| User connections | `/v1/users/{user_id}/follow` |
| Feed | `/v1/feed` |
| Administration | `/v1/admin/cinecircle/stats` |

For request schemas, parameters, authentication requirements, and response examples, run the application and open `/docs`.

## Screenshots

### Swagger UI
![Swagger](assets/swagger.png)

### Authentication
![Authentication](assets/authentication.png)

### Media Discovery
![Media](assets/media.png)

### Reviews
![Reviews](assets/reviews.png)

### Watchlist
![Watchlist](assets/watchlist.png)

### Social Features
![Users](assets/connections.png)

### Feed
![Feed](assets/feed.png)

### Admin Endpoints
![Admin](assets/admin.png)


## Getting Started

### Prerequisites

- Python 3.12 or a compatible Python version.
- PostgreSQL.
- A TMDB API Read Access Token.
- A Resend API key for email functionality.

### 1. Clone the repository

```bash
git clone https://github.com/qw3rty-dev/cinecircle-api.git
cd cinecircle-api
```

Replace the repository URL with the actual GitHub URL.

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it:

**Linux/macOS**

```bash
source .venv/bin/activate
```

**Windows**

```powershell
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root:

```env
DATABASE_URL = postgresql+asyncpg://{USER}:{PASSWORD}@localhost:5432/cinecircle

TEST_DATABASE_URL = postgresql+asyncpg://{USER}:{PASSWORD}@localhost:5432/cinecircle_test

SECRET_KEY = {your-secret-key}

ALGORITHM = "HS256"

ACCESS_TOKEN = "Bearer {your-tmdb-read-access-token}"

RESEND_API_KEY = your-resend-api-key

FROM_EMAIL = your-verified-sender@example.com
```
Use your own credentials and a strong, randomly generated secret key. Configure a verified sender address in Resend.


### 5. Apply database migrations

```bash
alembic upgrade head
```

This creates or upgrades the database schema using the project's migration history.

### 6. Start the API

```bash
uvicorn src.main:app --reload
```

The API should be available at:

- API root: `http://127.0.0.1:8000/`
- Interactive Swagger documentation: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

The versioned endpoints use the `/v1` prefix.


## Running Tests

CineCircle currently has **30 active tests** covering authentication, reviews, and watchlists. Test coverage is still being expanded.

Install the testing dependencies:

```bash
pip install pytest pytest-asyncio
```

Configure a separate PostgreSQL database for tests:

Create the test database before running the suite. Do not point `TEST_DATABASE_URL` at your production database.

Run the tests:

```bash
pytest -v
```

The test setup uses an asynchronous HTTP client, overrides the application's database dependency, rolls back database transactions, and mocks TMDB media responses for relevant tests.

**Current test coverage includes:**
- Registration and login behavior.
- Password validation and password changes.
- Email verification and OTP validation.
- Account deletion behavior.
- Review creation, validation, and retrieval.
- Watchlist creation, retrieval, and deletion.
- Authentication requirements for protected operations.


## Future Improvement

CineCircle is an evolving backend project. Planned improvements include:

- Broader automated test coverage.
- Rate limiting for authentication and other sensitive endpoints.
- Structured application logging and improved observability.
- Redis-based caching and distributed rate-limit state.
- Deployment automation and production configuration.
- A separate web frontend.
- More robust background processing as workload grows.
