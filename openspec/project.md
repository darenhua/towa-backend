# Project Context

## Purpose

Towa Backend is a FastAPI-based service for an ad hackathon that analyzes video advertisements and generates AI-powered persona responses. The system:

-   Ingests and analyzes video ads using multimodal AI
-   Searches for and generates demographic personas using web data
-   Simulates persona reactions to advertisements using LLMs
-   Provides voice call capabilities for persona engagement
-   Stores all data in Supabase for downstream analysis

## Tech Stack

-   **Language**: Python 3.12+
-   **Web Framework**: FastAPI (async API endpoints)
-   **ASGI Server**: Uvicorn
-   **Package Manager**: UV (uv.lock for dependency management)
-   **Database**: Supabase (PostgreSQL with client library)
-   **AI/LLM**: Anthropic Claude (AsyncAnthropic client, claude-sonnet-4-20250514)
-   **Video Analysis**: TwelveLabs API (marengo2.7 model for video understanding)
-   **Web Search**: Exa API (websets for persona discovery)
-   **Voice Calls**: Vapi SDK (voice assistant integration)
-   **HTTP Client**: requests library
-   **Environment**: python-dotenv for configuration

## Project Conventions

### Code Style

-   **Async/Await**: Use async functions for I/O operations (API calls, database queries)
-   **Type Hints**: Use type annotations from `typing` module (Optional, Dict, Any, List)
-   **Pydantic Models**: Define request/response models in `src/db/models.py`
-   **Naming**:
    -   Snake_case for functions, variables, and file names
    -   PascalCase for classes and Pydantic models
    -   ALL_CAPS for constants and environment variables
-   **Error Handling**: Raise HTTPException with appropriate status codes and detail messages
-   **Logging**: Use print statements for debugging (consider migrating to Python logging)

### Architecture Patterns

-   **Router-Based Organization**: Separate routers by feature domain (`routers/vapi_router.py`, `routers/twelvelabs_router.py`)
-   **Centralized Models**: Database models and Pydantic schemas in `src/db/models.py`
-   **Dependency Injection**: Initialize clients at module level, check for None before use
-   **RESTful Routes**: Use path parameters for resource IDs (e.g., `/{job_id}/search`)
-   **CORS Enabled**: Allow all origins for hackathon/development flexibility
-   **Environment Configuration**: All API keys and URLs from environment variables via dotenv

### Testing Strategy

-   No formal test suite currently implemented
-   Manual testing via FastAPI's automatic `/docs` Swagger UI
-   Use Pydantic models for request/response validation
-   Health check endpoints for service monitoring (`/health`)

### Git Workflow

-   **Branch**: Currently on `main` branch
-   **Commit Strategy**: Not formally defined (hackathon project)
-   **Untracked**: OpenSpec files (`.cursor/`, `AGENTS.md`, `openspec/`) are new additions
-   **Modified Files**: `main.py` and `routers/twelvelabs_router.py` have uncommitted changes

## Domain Context

### Advertisement Analysis Workflow

1. **Job Creation**: Each job represents an ad campaign with associated video and personas
2. **Video Upload**: Videos are uploaded to TwelveLabs, indexed, and analyzed for creative elements
3. **Persona Discovery**: Exa API searches for LinkedIn profiles matching target demographics
4. **Response Generation**: Claude generates reactions for each persona viewing the ad
5. **Voice Integration**: Vapi enables voice calls to personas (testing engagement)

### Database Schema (Supabase)

-   **jobs**: Central job entity linking ads and personas
-   **ads**: Advertisement metadata with `description` field for analysis results
-   **persona**: Demographic profiles (name, position, location, LinkedIn URL, description)
-   **persona_responses**: AI-generated reactions (stores conversation with prompt and response)

### Key Concepts

-   **Websets**: Exa's entity-based search results (primarily for person/company discovery)
-   **Index**: TwelveLabs video collection (uses "swayable-creative-ads" index)
-   **Job ID**: Primary identifier linking all related entities across tables. this is the same thing as a project.

## Important Constraints

-   **Rate Limits**: External API usage (TwelveLabs, Anthropic, Exa, Vapi) has rate/quota limits
-   **Video Processing Time**: TwelveLabs indexing can take 30s-5min depending on video length
-   **Async Requirement**: Must use AsyncAnthropic client for concurrent persona response generation
-   **Environment Setup**: Requires 6+ API keys (SUPABASE_URL, SUPABASE_KEY, ANTHROPIC_API_KEY, TWELVELABS_API_KEY, TWELVELABS_INDEX_ID, EXA_API_KEY, Vapi token)
-   **Database Dependency**: Application cannot function without Supabase connection (no fallback)
-   **Python Version**: Requires Python >=3.12 for latest async features

## External Dependencies

### Critical Services

-   **Supabase**: PostgreSQL database hosting (stores all persistent data)
-   **Anthropic**: Claude API for persona response generation (claude-sonnet-4-20250514 model)
-   **TwelveLabs**: Video understanding API (marengo2.7 with visual, audio, generate options)
-   **Exa API**: Web search and entity discovery (websets for persona research)
-   **Vapi**: Voice call API (assistant-based phone interactions)

### API Endpoints Used

-   TwelveLabs: `/v1.3/analyze` (video analysis with JSON schema)
-   Exa: `/websets/v0/websets` (create), `/websets/v0/websets/{id}` (status), `/websets/v0/websets/{id}/items` (results)
-   Anthropic: Messages API (async streaming support)
-   Vapi: `calls.create()`, `calls.get()` (SDK methods)

### Configuration Requirements

```env
SUPABASE_URL=<your-supabase-project-url>
SUPABASE_KEY=<your-supabase-anon-key>
ANTHROPIC_API_KEY=<claude-api-key>
TWELVELABS_API_KEY=<twelvelabs-key>
TWELVELABS_INDEX_ID=<optional-existing-index>
EXA_API_KEY=<exa-search-key>
```
