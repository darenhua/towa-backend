# Towa Backend

FastAPI-based service for ad hackathon that analyzes video advertisements and generates AI-powered persona responses.

## Features

-   **Video Analysis**: Upload and analyze video ads using TwelveLabs multimodal AI
-   **Video Processing**: Automatic validation and transformation to meet platform requirements
-   **Persona Discovery**: Search for demographic personas using Exa web search
-   **AI Response Generation**: Simulate persona reactions using Claude
-   **Voice Integration**: Voice call capabilities via Vapi

## Prerequisites

### Required Dependencies

1. **Python 3.12+**
2. **FFmpeg** (required for video processing)

#### Installing FFmpeg

**macOS (via Homebrew):**

```bash
brew install ffmpeg
```

**Ubuntu/Debian:**

```bash
sudo apt update
sudo apt install ffmpeg
```

**Windows (via Chocolatey):**

```bash
choco install ffmpeg
```

**Or download from:** https://ffmpeg.org/download.html

Verify installation:

```bash
ffmpeg -version
ffprobe -version
```

### API Keys Required

Create a `.env` file with the following:

```env
SUPABASE_URL=<your-supabase-project-url>
SUPABASE_KEY=<your-supabase-anon-key>
ANTHROPIC_API_KEY=<claude-api-key>
TWELVELABS_API_KEY=<twelvelabs-key>
TWELVELABS_INDEX_ID=<optional-existing-index>
EXA_API_KEY=<exa-search-key>
```

## Installation

1. **Clone the repository**

2. **Install dependencies with UV:**

```bash
uv sync
```

3. **Run the server:**

```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

## Video Processing

The system automatically validates and transforms videos to meet TwelveLabs requirements:

### Requirements

-   **Resolution:** 360x360 to 3840x2160
-   **Aspect Ratio:** 1:1, 4:3, 4:5, 5:4, 16:9, 9:16, or 17:9
-   **Duration:** 4 seconds to 2 hours (7,200s)
-   **File Size:** Max 2GB
-   **Format:** Standard video/audio formats (H.264/AAC recommended)

### Automatic Fixes

The video processing pipeline automatically:

-   Resizes videos that don't meet resolution requirements
-   Adjusts aspect ratios with black padding (preserves full content)
-   Trims videos longer than 2 hours
-   Re-encodes to H.264/AAC format

### Unfixable Issues

Videos will be rejected if:

-   Duration is less than 4 seconds (cannot be extended)
-   File size exceeds 2GB after processing

## API Documentation

Once running, visit:

-   **Swagger UI:** http://localhost:8000/docs
-   **ReDoc:** http://localhost:8000/redoc

## Project Structure

```
towa-backend/
├── main.py                  # FastAPI app entry point
├── routers/
│   ├── twelvelabs_router.py # Video analysis and processing
│   └── vapi_router.py       # Voice call integration
├── src/
│   └── db/
│       └── models.py        # Pydantic models
├── openspec/                # Specification-driven development
│   ├── project.md
│   └── changes/
└── pyproject.toml           # Project dependencies
```

## Development

### Database Schema (Supabase)

-   **jobs**: Central job entity linking ads and personas
-   **ads**: Advertisement metadata with analysis results
-   **persona**: Demographic profiles from LinkedIn/web search
-   **persona_responses**: AI-generated reactions to ads

### Key Functions

**Video Processing:**

-   `process_and_validate_video(job_id)` - Complete validation pipeline
-   `get_video_metadata(video_path)` - Extract metadata via FFprobe
-   `validate_video_requirements(metadata)` - Check TwelveLabs compliance
-   `transform_video_with_ffmpeg(input, output, transformations)` - Fix issues

**TwelveLabs:**

-   `upload_and_index_video(video_path, name)` - Upload to TwelveLabs
-   `analyze_video_with_twelvelabs(video_id, name)` - Get AI analysis

## Tech Stack

-   **Web Framework:** FastAPI (async)
-   **Database:** Supabase (PostgreSQL)
-   **AI/LLM:** Anthropic Claude (claude-sonnet-4-20250514)
-   **Video Analysis:** TwelveLabs (marengo2.7)
-   **Video Processing:** FFmpeg
-   **Web Search:** Exa API
-   **Voice Calls:** Vapi SDK
-   **Package Manager:** UV

## License

Hackathon project - internal use
