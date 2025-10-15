# Create router
from pathlib import Path
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from src.db.models import VideoAnalysisRequest, VideoAnalysisResponse
from anthropic import AsyncAnthropic
from supabase import create_client, Client
from dotenv import load_dotenv
import os
import time

import tempfile
import subprocess
import json
import requests

from twelvelabs import TwelveLabs
from twelvelabs.types import VideoSegment
from twelvelabs.embed import TasksStatusResponse
from twelvelabs.indexes import IndexesCreateRequestModelsItem

load_dotenv()

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
twelvelabs_client = TwelveLabs(api_key=TWELVELABS_API_KEY)

# Video Processing Constants
VALID_ASPECT_RATIOS = {
    "1:1": (1, 1),
    "4:3": (4, 3),
    "4:5": (4, 5),
    "5:4": (5, 4),
    "16:9": (16, 9),
    "9:16": (9, 16),
    "17:9": (17, 9),
}
MIN_RESOLUTION = (360, 360)
MAX_RESOLUTION = (3840, 2160)
MIN_DURATION = 4  # seconds
MAX_DURATION = 7200  # seconds (2 hours)
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2GB in bytes


def do_initialize(job_id: str):
    print(f"Initializing video for job {job_id}")
    towa_index_id = get_or_create_index()

    job_result = supabase.table("jobs").select("ads_id").eq("id", job_id).execute()

    ads_id = job_result.data[0]["ads_id"]
    print(f"✓ Found ads_id: {ads_id}")

    # Fetch video from Supabase storage
    bucket_name = "videos"
    file_path = f"jobs/{job_id}/ad.mp4"

    print(f"Fetching video from bucket '{bucket_name}' at path '{file_path}'...")

    # Download video from Supabase storage
    video_response = supabase.storage.from_(bucket_name).download(file_path)
    print(f"✓ Video downloaded: {len(video_response)} bytes")

    # Save to temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
        temp_file.write(video_response)
        temp_file_path = temp_file.name

    print(f"✓ Video saved to temporary file: {temp_file_path}")

    new_path = process_and_validate_video(Path(temp_file_path))
    # Upload video using SDK
    with open(new_path, "rb") as video_file:
        task = twelvelabs_client.tasks.create(
            index_id=towa_index_id,
            video_file=video_file,
            enable_video_stream=True,  # Enable streaming
        )

    print(f"Video upload initiated - Task ID: {task.id}")

    def on_task_update(current_task):
        print(f"  Status: {current_task.status}")

    completed_task = twelvelabs_client.tasks.wait_for_done(
        task_id=task.id, sleep_interval=5, callback=on_task_update
    )

    video_id = completed_task.video_id

    summary = twelvelabs_client.summarize(video_id=video_id, type="summary")

    print("TESTSUMMARY", summary)

    description_result = (
        supabase.table("ads")
        .update({"description": summary.summary})
        .eq("id", ads_id)
        .execute()
    )

    # Clean up temporary files
    try:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            print(f"✓ Deleted temporary file: {temp_file_path}")
    except Exception as e:
        print(f"Warning: Failed to delete {temp_file_path}: {e}")

    try:
        if os.path.exists(new_path):
            os.remove(new_path)
            print(f"✓ Deleted temporary file: {new_path}")
    except Exception as e:
        print(f"Warning: Failed to delete {new_path}: {e}")

    return {
        "success": True,
        "job_id": job_id,
        "ads_id": ads_id,
        "video_id": video_id,
        "description": description_result,
    }


@router.post("/{job_id}/initialize")
async def initialize(job_id: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(do_initialize, job_id)
    return {"success": True}


def get_or_create_index() -> str:
    index_name = "towa_index_pegasus"

    indexes = twelvelabs_client.indexes.list()
    for idx in indexes:
        if idx.index_name == index_name:
            print(f"Found existing index: {index_name} (ID: {idx.id})")
            return idx.id

    # Create new index if none found
    print(f"Creating new index: {index_name}")

    index = twelvelabs_client.indexes.create(
        index_name=index_name,
        models=[
            IndexesCreateRequestModelsItem(
                model_name="pegasus1.2",
                model_options=["visual", "audio"],
            )
        ],
        addons=["thumbnail"],
    )

    print(f"✓ Index created successfully: {index_name} (ID: {index.id})")
    return index.id


async def fetch_video_blob_from_storage(job_id: str) -> bytes:
    """
    Fetch video blob from remote storage using job_id.

    Args:
        job_id: Job identifier to look up video in storage

    Returns:
        Video file as bytes

    Raises:
        NotImplementedError: This is a placeholder for future Supabase/S3 integration

    Example:
        >>> video_bytes = await fetch_video_blob_from_storage("job_123")

    Future implementation:
        1. Query Supabase jobs table for video_url by job_id
        2. Fetch video from Supabase Storage or S3
        3. Return video bytes
    """
    raise NotImplementedError(
        "Video blob fetching not yet implemented. "
        "This function will be integrated with Supabase Storage or S3. "
        "For now, use direct file upload via upload_and_index_video()."
    )


def get_video_metadata(video_path: Path) -> Dict[str, Any]:
    """
    Extract video metadata using FFprobe.

    Args:
        video_path: Path to video file

    Returns:
        Dictionary containing:
            - width: Video width in pixels
            - height: Video height in pixels
            - duration: Duration in seconds (float)
            - file_size: File size in bytes
            - video_codec: Video codec name
            - audio_codec: Audio codec name
            - aspect_ratio: Calculated aspect ratio string (e.g., "16:9")

    Raises:
        Exception: If FFprobe is not installed or fails to read video

    Example:
        >>> metadata = get_video_metadata(Path("video.mp4"))
        >>> print(f"Resolution: {metadata['width']}x{metadata['height']}")
    """
    try:
        # Check if FFprobe is available
        result = subprocess.run(
            ["ffprobe", "-version"], capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            raise Exception("FFprobe not found in system PATH. Please install FFmpeg.")
    except FileNotFoundError:
        raise Exception(
            "FFprobe not found in system PATH. Please install FFmpeg: "
            "https://ffmpeg.org/download.html"
        )

    # Extract video metadata using FFprobe
    cmd = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(video_path),
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30, check=True
        )

        probe_data = json.loads(result.stdout)

        # Find video and audio streams
        video_stream = None
        audio_stream = None

        for stream in probe_data.get("streams", []):
            if stream.get("codec_type") == "video" and not video_stream:
                video_stream = stream
            elif stream.get("codec_type") == "audio" and not audio_stream:
                audio_stream = stream

        if not video_stream:
            raise Exception("No video stream found in file")

        # Extract metadata
        width = int(video_stream.get("width", 0))
        height = int(video_stream.get("height", 0))
        duration = float(probe_data.get("format", {}).get("duration", 0))
        file_size = int(probe_data.get("format", {}).get("size", 0))
        video_codec = video_stream.get("codec_name", "unknown")
        audio_codec = (
            audio_stream.get("codec_name", "unknown") if audio_stream else "none"
        )

        # Calculate aspect ratio
        if width > 0 and height > 0:
            from math import gcd

            divisor = gcd(width, height)
            aspect_w = width // divisor
            aspect_h = height // divisor
            aspect_ratio = f"{aspect_w}:{aspect_h}"
        else:
            aspect_ratio = "unknown"

        metadata = {
            "width": width,
            "height": height,
            "duration": duration,
            "file_size": file_size,
            "video_codec": video_codec,
            "audio_codec": audio_codec,
            "aspect_ratio": aspect_ratio,
        }

        print(
            f"Video metadata extracted: {width}x{height}, {duration}s, {aspect_ratio}"
        )
        return metadata

    except subprocess.CalledProcessError as e:
        raise Exception(f"FFprobe failed to read video: {e.stderr}")
    except json.JSONDecodeError as e:
        raise Exception(f"Failed to parse FFprobe output: {str(e)}")
    except Exception as e:
        raise Exception(f"Failed to extract video metadata: {str(e)}")


def validate_video_requirements(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate video metadata against TwelveLabs requirements.

    Args:
        metadata: Video metadata from get_video_metadata()

    Returns:
        Dictionary containing:
            - compliant: Boolean indicating if video meets all requirements
            - issues: List of issue dictionaries with 'type', 'message', and 'fixable' keys

    Example:
        >>> validation = validate_video_requirements(metadata)
        >>> if not validation['compliant']:
        >>>     print(f"Issues found: {validation['issues']}")
    """
    issues = []

    width = metadata.get("width", 0)
    height = metadata.get("height", 0)
    duration = metadata.get("duration", 0)
    file_size = metadata.get("file_size", 0)
    aspect_ratio = metadata.get("aspect_ratio", "unknown")

    # Check resolution (minimum)
    if width < MIN_RESOLUTION[0] or height < MIN_RESOLUTION[1]:
        issues.append(
            {
                "type": "resolution_too_low",
                "message": f"Resolution {width}x{height} below minimum {MIN_RESOLUTION[0]}x{MIN_RESOLUTION[1]}",
                "fixable": True,
            }
        )

    # Check resolution (maximum)
    if width > MAX_RESOLUTION[0] or height > MAX_RESOLUTION[1]:
        issues.append(
            {
                "type": "resolution_too_high",
                "message": f"Resolution {width}x{height} exceeds maximum {MAX_RESOLUTION[0]}x{MAX_RESOLUTION[1]}",
                "fixable": True,
            }
        )

    # Check aspect ratio
    if aspect_ratio not in VALID_ASPECT_RATIOS:
        valid_ratios = ", ".join(VALID_ASPECT_RATIOS.keys())
        issues.append(
            {
                "type": "invalid_aspect_ratio",
                "message": f"Aspect ratio {aspect_ratio} not in allowed list: {valid_ratios}",
                "fixable": True,
            }
        )

    # Check duration (minimum) - UNFIXABLE
    if duration < MIN_DURATION:
        issues.append(
            {
                "type": "duration_too_short",
                "message": f"Duration {duration}s below minimum {MIN_DURATION}s (cannot be fixed)",
                "fixable": False,
            }
        )

    # Check duration (maximum) - fixable by trimming
    if duration > MAX_DURATION:
        issues.append(
            {
                "type": "duration_too_long",
                "message": f"Duration {duration}s exceeds maximum {MAX_DURATION}s (will trim)",
                "fixable": True,
            }
        )

    # Check file size
    if file_size > MAX_FILE_SIZE:
        size_mb = file_size / (1024 * 1024)
        max_mb = MAX_FILE_SIZE / (1024 * 1024)
        issues.append(
            {
                "type": "file_too_large",
                "message": f"File size {size_mb:.1f}MB exceeds maximum {max_mb:.1f}MB",
                "fixable": False,  # May become fixable after compression, but flag it
            }
        )

    compliant = len(issues) == 0

    if compliant:
        print(
            f"✓ Video validation passed: {width}x{height}, {aspect_ratio}, {duration}s"
        )
    else:
        print(f"✗ Video validation failed with {len(issues)} issue(s)")
        for issue in issues:
            print(f"  - {issue['message']}")

    return {"compliant": compliant, "issues": issues}


def transform_video_with_ffmpeg(
    input_path: Path, output_path: Path, transformations: Dict[str, Any]
) -> None:
    """
    Transform video using FFmpeg to meet TwelveLabs requirements.

    Args:
        input_path: Path to input video file
        output_path: Path to save transformed video
        transformations: Dictionary containing transformation instructions:
            - target_resolution: Tuple of (width, height)
            - target_aspect_ratio: String like "16:9"
            - max_duration: Maximum duration in seconds (will trim)
            - re_encode: Boolean to force re-encoding to H.264/AAC

    Raises:
        Exception: If FFmpeg transformation fails

    Example:
        >>> transformations = {
        >>>     "target_resolution": (1920, 1080),
        >>>     "target_aspect_ratio": "16:9",
        >>>     "max_duration": 7200
        >>> }
        >>> transform_video_with_ffmpeg(input_path, output_path, transformations)
    """
    try:
        # Check if FFmpeg is available
        result = subprocess.run(
            ["ffmpeg", "-version"], capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            raise Exception("FFmpeg not found in system PATH. Please install FFmpeg.")
    except FileNotFoundError:
        raise Exception(
            "FFmpeg not found in system PATH. Please install FFmpeg: "
            "https://ffmpeg.org/download.html"
        )

    # Build FFmpeg command
    cmd = ["ffmpeg", "-i", str(input_path), "-y"]  # -y to overwrite output

    # Video codec and quality
    cmd.extend(["-c:v", "libx264", "-preset", "medium", "-crf", "23"])

    # Audio codec
    cmd.extend(["-c:a", "aac", "-b:a", "128k"])

    # Trim duration if specified
    if "max_duration" in transformations:
        max_dur = transformations["max_duration"]
        cmd.extend(["-t", str(max_dur)])
        print(f"  Trimming video to {max_dur}s")

    # Handle resolution and aspect ratio
    if (
        "target_resolution" in transformations
        or "target_aspect_ratio" in transformations
    ):
        target_width, target_height = transformations.get(
            "target_resolution", (1920, 1080)
        )

        # Scale video to fit within target resolution while maintaining aspect ratio
        # Then pad to exact dimensions with black bars
        scale_filter = (
            f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease"
        )
        pad_filter = f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2:black"
        vf = f"{scale_filter},{pad_filter}"

        cmd.extend(["-vf", vf])
        print(f"  Scaling to {target_width}x{target_height} with padding")

    # Output file
    cmd.append(str(output_path))

    print(f"Running FFmpeg transformation...")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout for processing
            check=True,
        )

        # Check output file size
        if output_path.exists():
            output_size = output_path.stat().st_size
            if output_size > MAX_FILE_SIZE:
                raise Exception(
                    f"Transformed video size ({output_size / (1024**3):.2f}GB) "
                    f"exceeds 2GB limit. Video cannot be processed."
                )
            print(f"✓ Video transformed successfully: {output_size / (1024**2):.1f}MB")
        else:
            raise Exception("FFmpeg did not produce output file")

    except subprocess.TimeoutExpired:
        raise Exception("FFmpeg transformation timed out after 5 minutes")
    except subprocess.CalledProcessError as e:
        raise Exception(f"FFmpeg transformation failed: {e.stderr}")


def find_closest_aspect_ratio(width: int, height: int) -> tuple[str, tuple[int, int]]:
    """
    Find the closest valid aspect ratio for given dimensions.

    Args:
        width: Video width in pixels
        height: Video height in pixels

    Returns:
        Tuple of (aspect_ratio_string, (target_width, target_height))
    """
    current_ratio = width / height

    best_match = None
    best_diff = float("inf")

    for ratio_str, (w, h) in VALID_ASPECT_RATIOS.items():
        target_ratio = w / h
        diff = abs(current_ratio - target_ratio)

        if diff < best_diff:
            best_diff = diff
            best_match = (ratio_str, (w, h))

    # Calculate target resolution based on aspect ratio
    # Try to keep dimensions close to original while meeting aspect ratio
    ratio_str, (ratio_w, ratio_h) = best_match

    # Scale to meet minimum resolution requirements
    scale_factor = max(
        MIN_RESOLUTION[0] / ratio_w,
        MIN_RESOLUTION[1] / ratio_h,
        1.0,  # Don't downscale if already large enough
    )

    # Also ensure we don't exceed maximum resolution
    scale_factor = min(
        scale_factor, MAX_RESOLUTION[0] / ratio_w, MAX_RESOLUTION[1] / ratio_h
    )

    target_width = int(ratio_w * scale_factor)
    target_height = int(ratio_h * scale_factor)

    # Round to even numbers (required by some codecs)
    target_width = target_width - (target_width % 2)
    target_height = target_height - (target_height % 2)

    return ratio_str, (target_width, target_height)


def process_and_validate_video(input_path: Path) -> Path:
    try:
        # Step 2: Extract metadata
        print("\nStep 2: Extracting video metadata...")
        metadata = get_video_metadata(input_path)

        # Step 3: Validate requirements
        print("\nStep 3: Validating against TwelveLabs requirements...")
        validation = validate_video_requirements(metadata)

        # Check for unfixable issues
        unfixable_issues = [
            issue for issue in validation["issues"] if not issue["fixable"]
        ]
        if unfixable_issues:
            error_details = "; ".join([issue["message"] for issue in unfixable_issues])
            input_path.unlink()  # Clean up
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Video has unfixable issues: {error_details}",
            )

        # Step 4: Transform if needed
        if not validation["compliant"]:
            print("\nStep 4: Applying FFmpeg transformations...")

            # Determine transformations needed
            transformations = {}

            # Handle resolution and aspect ratio
            needs_resize = any(
                issue["type"]
                in ["resolution_too_low", "resolution_too_high", "invalid_aspect_ratio"]
                for issue in validation["issues"]
            )

            if needs_resize:
                if metadata["aspect_ratio"] in VALID_ASPECT_RATIOS:
                    # Keep existing aspect ratio, just fix resolution
                    ratio_w, ratio_h = VALID_ASPECT_RATIOS[metadata["aspect_ratio"]]
                    scale = max(
                        MIN_RESOLUTION[0] / ratio_w, MIN_RESOLUTION[1] / ratio_h, 1.0
                    )
                    scale = min(
                        scale, MAX_RESOLUTION[0] / ratio_w, MAX_RESOLUTION[1] / ratio_h
                    )
                    target_width = int(ratio_w * scale)
                    target_height = int(ratio_h * scale)
                else:
                    # Find closest valid aspect ratio
                    closest_ratio, (target_width, target_height) = (
                        find_closest_aspect_ratio(metadata["width"], metadata["height"])
                    )
                    print(
                        f"  Converting aspect ratio {metadata['aspect_ratio']} → {closest_ratio}"
                    )

                transformations["target_resolution"] = (target_width, target_height)

            # Handle duration
            if metadata["duration"] > MAX_DURATION:
                transformations["max_duration"] = MAX_DURATION

            # Create output temp file
            temp_output = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            temp_output.close()
            output_path = Path(temp_output.name)

            # Apply transformations
            transform_video_with_ffmpeg(input_path, output_path, transformations)

            # Clean up input, use output
            input_path.unlink()
            input_path = output_path

            # Step 5: Re-validate transformed video
            print("\nStep 5: Re-validating transformed video...")
            new_metadata = get_video_metadata(input_path)
            new_validation = validate_video_requirements(new_metadata)

            if not new_validation["compliant"]:
                error_details = "; ".join(
                    [issue["message"] for issue in new_validation["issues"]]
                )
                input_path.unlink()  # Clean up
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Video still non-compliant after transformation: {error_details}",
                )

            print("✓ Transformed video validated successfully")
        else:
            print("✓ Video already compliant, no transformation needed")

        print(f"\n=== Video processing complete ===")
        print(f"Output file: {input_path}")
        print(f"NOTE: Caller must delete temp file after upload\n")

        return input_path

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Clean up temp file on error
        if input_path.exists():
            input_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Video processing failed: {str(e)}",
        )
