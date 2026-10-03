# FastAPI Starter Kit: A Guided Tour

This guide explains the current codebase, how a request moves through it, how
the in-memory chat session API works, and how to run and test the application.
You can read it before running anything.

## 1. Project map

```text
fastapi-starter-kit/
├── app/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── health.py
│   │   │   └── sessions.py
│   │   └── router.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   └── session_store.py
│   └── main.py
├── tests/
│   ├── test_health.py
│   └── test_sessions.py
├── .env.example
├── .gitignore
├── pyproject.toml
└── README.md
```

### Application folders

- `app/` contains the application’s Python code.
- `app/api/` contains API routing setup.
- `app/api/routes/` contains endpoint handlers grouped by purpose.
- `app/core/` contains shared setup and data used by the application.
- `tests/` contains automated tests. Tests make requests to the app without
  starting a network server.

The `__init__.py` files mark these directories as Python packages in this
project’s layout. They allow imports such as
`from app.api.router import api_router`.

## 2. How a request moves through the app

The application is assembled in `app/main.py`. It loads settings, creates the
FastAPI application object, and attaches routers. Uvicorn imports this object
and serves it over HTTP.

Routes are attached in two ways:

1. `app/api/router.py` collects the health router. `app/main.py` includes this
   combined router under the configured `/api/v1` prefix.
2. `app/main.py` includes the sessions router directly, without that prefix,
   because the requested session URLs are unprefixed.

This is why the health endpoint is `GET /api/v1/health`, while session
endpoints start with `/sessions`.

## 3. Application files in detail

### `app/main.py`: create and configure the application

```python
settings = get_settings()

app = FastAPI(title=settings.name, debug=settings.debug)
app.include_router(api_router, prefix=settings.api_v1_prefix)
app.include_router(sessions.router)
```

- `get_settings()` provides the application settings.
- `FastAPI(...)` creates the app object. Its title appears in the generated API
  documentation; `debug` configures debug behavior.
- `include_router(...)` attaches route collections to the app.
- The health router uses the configured prefix; the sessions router is mounted
  without a prefix.

The command `uvicorn app.main:app` means “import the object named `app` from
the Python module `app.main`.” In that path, the first `app` is the package,
`main` is the module file, and the final `app` is the variable inside it.

### `app/api/router.py`: collect versioned API routes

```python
api_router = APIRouter()
api_router.include_router(health.router)
```

An `APIRouter` groups related endpoint registrations. This module currently
collects the health routes. The app mounts the resulting group at
`/api/v1`.

### `app/api/routes/health.py`: health endpoint

```python
@router.get("/health", tags=["health"])
def get_health() -> dict[str, str]:
    return {"status": "learning"}
```

- `@router.get("/health")` registers the function for HTTP `GET` requests at
  `/health` on this router.
- `get_health` is the function FastAPI calls for a matching request.
- Returning a dictionary makes FastAPI serialize it as JSON.
- `-> dict[str, str]` is a type hint that describes a dictionary with string
  keys and string values.
- The `health` tag groups this endpoint in the generated API documentation.

Because this router is mounted at `/api/v1`, the final path is
`GET /api/v1/health`. The current response body is `{"status":"learning"}`.

### `app/api/routes/sessions.py`: chat session API

This module defines Pydantic request and response models and three endpoints:

| Method and path | Purpose | Success status |
| --- | --- | --- |
| `POST /sessions` | Create a session and its empty chat history | `201 Created` |
| `POST /sessions/{session_id}/messages` | Add a user or assistant message to an existing session | `201 Created` |
| `GET /sessions/{session_id}/messages` | Get all messages, optionally filtered by role | `200 OK` |

#### Request and response models

`CreateSessionRequest` describes the JSON body for session creation. Its
`field_validator` runs before Pydantic’s normal field validation. It ensures
the value is a string, removes leading and trailing whitespace with `strip()`,
converts it to lowercase, and rejects the result if it is empty.

`MessageRequest` describes an incoming message. The `Literal["user",
"assistant"]` type restricts the role to those two values; FastAPI/Pydantic
returns a validation error for another value.

`CreateSessionResponse` and `MessageResponse` describe what the endpoints
return. The `response_model` declarations tell FastAPI to validate and
serialize endpoint results according to those models.

#### Creating a session

`create_session` chooses an ID using `len(session_store) + 1`, creates a UTC
timestamp with `datetime.now(timezone.utc).isoformat(...)`, appends the session
metadata to `session_store`, and initializes `chat_store[session_id]` to an
empty list. It returns the new session ID, normalized username, and timestamp.
UTC timestamps include the `+00:00` timezone offset.

For example, sending `{"session_user":" Alice "}` creates a session whose
username is `alice`.

#### Adding a message

`add_message` first checks whether the session ID exists in `session_store`.
If it does not, the route raises an `HTTPException` with status `404` and
detail `"Session not found"`. If the session exists, it appends the validated
role and content to that session’s message list and returns the message.

#### Reading and filtering messages

`get_messages` also checks that the session exists and returns the same `404`
response if it does not. With no `role` query parameter, it returns all
messages. With `?role=user` or `?role=assistant`, it filters using a list
comprehension:

```python
[message for message in messages if message["role"] == role]
```

The query parameter uses the same two allowed roles as message creation. An
unsupported role filter is rejected with HTTP `422`.

#### HTTP validation and errors

- A missing or invalid request field, an empty/whitespace username, an invalid
  message role, or an invalid role filter produces HTTP `422 Unprocessable
  Entity`.
- A request for a session that does not exist produces HTTP `404 Not Found`.
- Successful session creation and message creation produce HTTP `201 Created`.
- A successful message listing produces HTTP `200 OK`.

### `app/core/session_store.py`: simulated in-memory storage

`session_store` is a list of dictionaries containing session metadata:

- `session_id`
- `session_user`
- `created_at`

`chat_store` is a dictionary that maps each session ID to a list of message
dictionaries. Each message contains `role` and `content`. The initial data
includes session 1 and the sample conversation `Hello` / `Hi there!`.

This is deliberately temporary storage. Changes are lost when the Python
process restarts. The ID calculation requested for this exercise,
`len(session_store) + 1`, is suitable only for this simple example: deletions,
multiple server workers, or simultaneous requests can make IDs unreliable.
A production application should persist records in a database and use its ID
generation.

### `app/core/config.py`: application settings

`Settings` extends Pydantic Settings’ `BaseSettings` and declares the values
used to configure the app. Its `SettingsConfigDict` specifies that settings
may be loaded from `.env`, uses UTF-8 to read that file, and maps environment
variables with the `APP_` prefix.

| Python field | Environment variable | Default |
| --- | --- | --- |
| `name` | `APP_NAME` | `FastAPI Starter Kit` |
| `debug` | `APP_DEBUG` | `false` |
| `api_v1_prefix` | `APP_API_V1_PREFIX` | `/api/v1` |

`get_settings()` is decorated with `@lru_cache`, so the settings object is
created once and reused on later calls. `app/main.py` calls it while the app
module is imported.

## 4. Project and environment files

### `pyproject.toml`: project metadata and tool configuration

This file declares:

- Project name, version, description, and minimum Python version (`3.10`).
- Runtime dependencies: FastAPI, Pydantic Settings, `python-dotenv`, and
  Uvicorn.
- Optional development dependencies: HTTPX (used by the test client), pytest,
  and Ruff.
- Setuptools package discovery, pytest’s test directory, and Ruff’s lint
  rules, target Python version, and line length.

The command `python -m pip install -e ".[dev]"` installs the local project in
editable mode and includes its `dev` optional dependencies. Editable mode
means the installed package uses the source files in this working directory.

### `.venv/`: project virtual environment

A virtual environment provides an isolated Python interpreter and installed
packages for this project. It is local to the machine and excluded from Git.

### `.env.example` and `.env`: local settings

`.env.example` is a shareable template containing the supported setting names
and example values. The settings loader looks for a file named `.env`; copy
the template to that name to override defaults locally. Do not commit `.env`,
because it may contain secrets or machine-specific values.

### `.gitignore`: files Git should not track

The ignore rules exclude the virtual environment, Python bytecode and caches,
pytest/Ruff output, coverage output, `.env`, and build/package artifacts.

## 5. Tests

### `tests/test_health.py`

The test creates a FastAPI `TestClient`, requests
`/api/v1/health`, and checks both the HTTP status and JSON response. It sends
the request in-process, so the Uvicorn server does not need to be running.

### `tests/test_sessions.py`

The session tests cover:

- Creating a session, normalizing its username, and initializing its chat.
- Rejecting empty and whitespace-only usernames.
- Adding a message to a session.
- Rejecting messages for unknown sessions and invalid message roles.
- Returning the complete message history.
- Filtering messages by user or assistant role.
- Rejecting unknown sessions and invalid role filters on message retrieval.

The `reset_stores` pytest fixture saves copies of the shared stores before each
test and restores them afterward. This prevents one test’s mutations from
changing the starting data for another test.

## 6. Learn by running it

When you are ready, open a terminal in the project directory and run these
steps one at a time.

### Step 1: create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

The first command creates the isolated environment. The second activates it
for the current terminal. In Windows PowerShell, activate it with:

```powershell
.venv\Scripts\Activate.ps1
```

### Step 2: install the project and development tools

```bash
python -m pip install -e ".[dev]"
```

`python -m pip` runs pip using the active Python interpreter. `.` means the
project in the current directory; `[dev]` requests the optional development
dependencies.

### Step 3: run tests and lint

```bash
pytest
ruff check .
```

Pytest runs the automated tests. Ruff checks the project against the lint
rules in `pyproject.toml`.

### Step 4: start the development server

```bash
uvicorn app.main:app --reload
```

`--reload` restarts the server when source code changes. Visit
`http://127.0.0.1:8000/api/v1/health` to see the health response, or
`http://127.0.0.1:8000/docs` to explore the generated API documentation.
Stop the server with `Ctrl+C`.

## 7. Session API examples

These examples assume the server is running at `127.0.0.1:8000`.

Create a session:

```bash
curl -X POST http://127.0.0.1:8000/sessions \
  -H "Content-Type: application/json" \
  -d '{"session_user":" Alice "}'
```

The response includes a generated session ID, the normalized username, and a
UTC timestamp. Use the returned ID in the following requests.

Add a message:

```bash
curl -X POST http://127.0.0.1:8000/sessions/2/messages \
  -H "Content-Type: application/json" \
  -d '{"role":"user","content":"What is AI?"}'
```

Get the full message history or filter it by role:

```bash
curl http://127.0.0.1:8000/sessions/2/messages
curl "http://127.0.0.1:8000/sessions/2/messages?role=user"
```

The example uses session ID `2`, because the in-memory store starts with
session ID `1`. If the create request returns a different ID, replace `2` with
that value.

## 8. A small learning exercise

1. In `app/api/routes/health.py`, change the health response from
   `{"status": "learning"}` to `{"status": "ready"}`.
2. Run `pytest`. The health response assertion should fail because the test
   still expects the old response.
3. Update the expected response in `tests/test_health.py`.
4. Run `pytest` again and confirm the test passes.

This exercise connects a route implementation to its observable response and
the test that describes the expected behavior.

## Quick command reference

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest
ruff check .
uvicorn app.main:app --reload
```
