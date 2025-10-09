# Create router
from pathlib import Path
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, status
from src.db.models import VideoAnalysisRequest, VideoAnalysisResponse
from anthropic import AsyncAnthropic
from supabase import create_client, Client
import os
import time

router = APIRouter(prefix="/video", tags=["video"])

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
supabase: Client = (
    create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None
)

# Initialize Anthropic client
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
anthropic_client = (
    AsyncAnthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None
)

# Initialize TwelveLabs
TWELVELABS_API_KEY = os.getenv("TWELVELABS_API_KEY", "")


@router.post("/{job_id}/video-dummy")
def video_understanding_dummy(job_id: str):
    description = """
    This video is a unprofessionally shot video of an asian man promoting a hackathon.
    """
    # update_ad_description(job_id, description)

    time.sleep(300)

    return {"job_id": job_id}


@router.post("/{job_id}/video", response_model=VideoAnalysisResponse)
async def video_understanding(
    job_id: str, request: Optional[VideoAnalysisRequest] = None
):
    """
    Complete video analysis endpoint:
    1. Get video URL from Supabase or request
    2. Upload/reference video in TwelveLabs
    3. Analyze video with structured JSON schema
    4. Store results in Supabase ads.description
    5. Return analysis summary
    """
    if not supabase:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase not configured",
        )

    time.sleep(10)
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="TwelveLabs API key not configured",
    )

    # if not TWELVELABS_API_KEY:
    #     raise HTTPException(
    #         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    #         detail="TwelveLabs API key not configured",
    #     )

    # try:
    #     # 1. Get job and ad from database
    #     job = get_job_by_id(supabase, job_id)
    #     ad = get_ad_by_job_id(supabase, job_id)
    #     ads_id = ad["id"]

    #     # 2. Determine video source
    #     video_url = None
    #     if request and request.video_url:
    #         video_url = request.video_url
    #     elif ad.get("video_url"):
    #         video_url = ad["video_url"]
    #     else:
    #         raise HTTPException(
    #             status_code=status.HTTP_400_BAD_REQUEST,
    #             detail="No video URL found in request or database",
    #         )

    #     # 3. Upload video to TwelveLabs (if it's a file path) or use existing video_id
    #     video_id = None
    #     video_path = Path(video_url) if not video_url.startswith("http") else None

    #     if video_path and video_path.exists():
    #         # Upload local file to TwelveLabs
    #         video_id = await upload_and_index_video(video_path, video_url)
    #     elif video_url.startswith("http"):
    #         # For HTTP URLs, we'd need to download first or use TwelveLabs URL upload
    #         # For now, raise an error requesting local file
    #         # Download the video from HTTP URL to local temp file
    #         try:
    #             response = requests.get(video_url, stream=True)
    #             response.raise_for_status()

    #             # Create a temporary file with appropriate extension
    #             suffix = Path(video_url).suffix or ".mp4"
    #             with tempfile.NamedTemporaryFile(
    #                 delete=False, suffix=suffix
    #             ) as tmp_file:
    #                 for chunk in response.iter_content(chunk_size=8192):
    #                     tmp_file.write(chunk)
    #                 tmp_video_path = Path(tmp_file.name)

    #             # Upload the downloaded file to TwelveLabs
    #             video_id = await upload_and_index_video(
    #                 tmp_video_path, os.path.basename(video_url)
    #             )

    #             # Clean up the temporary file
    #             try:
    #                 tmp_video_path.unlink()
    #             except Exception as cleanup_error:
    #                 print(
    #                     f"Warning: Failed to delete temporary file {tmp_video_path}: {cleanup_error}"
    #                 )

    #         except requests.exceptions.RequestException as e:
    #             raise HTTPException(
    #                 status_code=status.HTTP_400_BAD_REQUEST,
    #                 detail=f"Failed to download video from URL: {str(e)}",
    #             )

    #     else:
    #         raise HTTPException(
    #             status_code=status.HTTP_400_BAD_REQUEST,
    #             detail=f"Video file not found at path: {video_url}",
    #         )

    #     # 4. Analyze video using TwelveLabs analyze endpoint
    #     analysis_result = await analyze_video_with_twelvelabs(
    #         video_id, os.path.basename(video_url)
    #     )

    #     # 5. Store analysis in Supabase
    #     update_result = update_ad_description(supabase, job_id, analysis_result)

    #     return VideoAnalysisResponse(
    #         success=True,
    #         job_id=job_id,
    #         ads_id=ads_id,
    #         video_id=video_id,
    #         analysis=analysis_result,
    #     )

    # except HTTPException:
    #     raise
    # except Exception as e:
    #     return VideoAnalysisResponse(
    #         success=False,
    #         job_id=job_id,
    #         ads_id=ad.get("id", "unknown") if "ad" in locals() else "unknown",
    #         error=str(e),
    #     )


async def upload_and_index_video(video_path: Path, video_name: str) -> str:
    """
    Upload a video to TwelveLabs and wait for indexing to complete.

    Args:
        video_path: Path to video file
        video_name: Name of the video

    Returns:
        Video ID from TwelveLabs

    Raises:
        Exception: If upload or indexing fails
    """
    try:
        # Initialize TwelveLabs client
        client = TwelveLabs(api_key=TWELVELABS_API_KEY)

        # Get or create index
        index_id = await get_or_create_index()

        # Get the index object
        index = client.indexes.retrieve(index_id)

        print(f"Uploading video: {video_path.name}")

        # Upload video using SDK
        with open(video_path, "rb") as video_file:
            task = client.tasks.create(
                index_id=index.id,
                video_file=video_file,
                enable_video_stream=True,  # Enable streaming
            )

        print(f"Video upload initiated - Task ID: {task.id}")

        # Wait for upload to complete
        print(f"Processing video: {video_name}")

        def on_task_update(current_task):
            print(f"  Status: {current_task.status}")

        completed_task = client.tasks.wait_for_done(
            task_id=task.id, sleep_interval=5, callback=on_task_update
        )

        if completed_task.status != "ready":
            error_msg = f"Video upload failed with status: {completed_task.status}"
            if hasattr(completed_task, "error_message"):
                error_msg += f" - {completed_task.error_message}"
            raise Exception(error_msg)

        video_id = completed_task.video_id
        if not video_id:
            raise Exception("No video_id returned from completed task")

        print(f"✓ Video uploaded successfully: {video_name} (ID: {video_id})")
        return video_id

    except Exception as e:
        raise Exception(f"Failed to upload video: {str(e)}")


async def get_or_create_index() -> str:
    """
    Get existing TwelveLabs index or create a new one.

    Returns:
        Index ID

    Raises:
        Exception: If index retrieval/creation fails
    """
    try:
        # Initialize TwelveLabs client
        client = TwelveLabs(api_key=TWELVELABS_API_KEY)

        # Check if we have a specific index ID in environment
        existing_index_id = os.getenv("TWELVELABS_INDEX_ID")
        if existing_index_id:
            try:
                # Verify the index exists
                index = client.indexes.retrieve(existing_index_id)
                print(f"Using existing index: {index.index_name} (ID: {index.id})")
                return index.id
            except Exception as e:
                print(f"Warning: Could not retrieve index {existing_index_id}: {e}")
                print("Will create a new index instead.")

        # Look for existing index with our default name
        index_name = "swayable-creative-ads"
        try:
            indexes = client.indexes.list()
            for idx in indexes:
                if idx.index_name == index_name:
                    print(f"Found existing index: {index_name} (ID: {idx.id})")
                    return idx.id
        except Exception as e:
            print(f"Warning: Could not list indexes: {e}")

        # Create new index if none found
        print(f"Creating new index: {index_name}")

        # Import the required model class
        from twelvelabs.indexes import IndexesCreateRequestModelsItem

        index = client.indexes.create(
            index_name=index_name,
            models=[
                IndexesCreateRequestModelsItem(
                    model_name="marengo2.7",
                    model_options=["visual", "audio", "generate"],
                )
            ],
            addons=["thumbnail"],
        )

        print(f"✓ Index created successfully: {index_name} (ID: {index.id})")
        return index.id

    except Exception as e:
        raise Exception(f"Failed to get or create index: {str(e)}")


async def analyze_video_with_twelvelabs(
    video_id: str, video_name: str
) -> Dict[str, Any]:
    """
    Analyze video using TwelveLabs analyze endpoint with structured JSON schema.

    Args:
        video_id: Video ID in TwelveLabs
        video_name: Name of the video

    Returns:
        Analysis results as dictionary

    Raises:
        Exception: If analysis fails
    """
    url = "https://api.twelvelabs.io/v1.3/analyze"
    headers = {"x-api-key": TWELVELABS_API_KEY, "Content-Type": "application/json"}

    payload = {
        "video_id": video_id,
        "prompt": """Analyze this advertisement video and provide comprehensive insights:
1. A descriptive title for the ad
2. A detailed summary covering:
   - Main message and value proposition
   - Target audience appeal
   - Key visual and audio elements
   - Emotional tone and mood
   - Brand presence and messaging
   - Call-to-action effectiveness
3. Keywords for categorization (themes, emotions, techniques, etc.)
4. Creative strengths and potential areas for improvement""",
        "temperature": 0.2,
        "stream": False,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "summary": {"type": "string"},
                    "keywords": {"type": "array", "items": {"type": "string"}},
                    "creative_elements": {
                        "type": "object",
                        "properties": {
                            "visual_style": {"type": "string"},
                            "audio_elements": {"type": "string"},
                            "emotional_tone": {"type": "string"},
                            "brand_presence": {"type": "string"},
                            "call_to_action": {"type": "string"},
                        },
                    },
                    "strengths": {"type": "array", "items": {"type": "string"}},
                    "improvement_areas": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["title", "summary", "keywords"],
            },
        },
        "max_tokens": 2000,
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()

        result = response.json()

        # Parse the JSON data from the response
        if "data" in result:
            analysis_data = json.loads(result["data"])
        else:
            analysis_data = result

        # Add metadata
        analysis_data["video_id"] = video_id
        analysis_data["video_name"] = video_name
        analysis_data["analyzed_at"] = time.strftime("%Y-%m-%d %H:%M:%S")

        print(f"Video analysis complete for: {video_name}")
        return analysis_data

    except requests.exceptions.RequestException as e:
        error_msg = f"TwelveLabs API error: {str(e)}"
        if hasattr(e, "response") and e.response is not None:
            error_msg += f" - Response: {e.response.text}"
        raise Exception(error_msg)
    except json.JSONDecodeError as e:
        raise Exception(f"Failed to parse analysis response: {str(e)}")
