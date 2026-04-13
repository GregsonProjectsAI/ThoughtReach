# ThoughtReach V1

## Local Setup Plan

### Prerequisites
- Docker and Docker Compose (to run PostgreSQL with pgvector)
- Python 3.10+
- A local or self-hosted embedding provider (required for development; see `PROJECT.md` embedding-provider constraint)
- OpenAI API Key or equivalent (optional — fallback only; not required for ordinary dev or evaluation work)

### Setup Steps
1. **Database Setup**
   Ensure Docker is running, then spin up the Postgres + pgvector service:
   ```bash
   docker-compose up -d
   ```

2. **Environment Setup**
   Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS/Linux
   # source venv/bin/activate

   pip install -r requirements.txt
   ```

3. **Environment Variables**
   Create a `.env` file based on the local setup:
   ```env
   DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/thoughtreach
   # Embedding provider — default to local/self-hosted during development.
   # OPENAI_API_KEY is optional; only required if using the paid OpenAI fallback.
   # OPENAI_API_KEY=your_api_key_here
   ```

4. **Database Migrations**
   Apply Alembic migrations to set up the DB schemas:
   ```bash
   alembic upgrade head
   ```

5. **Run the FastAPI Server**
   Start the development server:
   ```bash
   uvicorn app.main:app --reload
   ```
   Access the API at `http://localhost:8000/docs` to test endpoints.
