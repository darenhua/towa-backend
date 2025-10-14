## 1. Implementation

-   [x] 1.1 Add required imports (tempfile, subprocess, json) to `routers/twelvelabs_router.py`
-   [x] 1.2 Create `fetch_video_blob_from_storage(job_id: str) -> bytes` mock function
-   [x] 1.3 Implement `get_video_metadata(video_path: Path) -> Dict` using FFprobe
-   [x] 1.4 Create `validate_video_requirements(metadata: Dict) -> Dict[str, Any]` validation logic
-   [x] 1.5 Implement `transform_video_with_ffmpeg(input_path: Path, output_path: Path, transformations: Dict)` for fixing issues
-   [x] 1.6 Build main `process_and_validate_video(job_id: str) -> Path` orchestration function
-   [x] 1.7 Add comprehensive error handling for validation failures and FFmpeg errors
-   [x] 1.8 Add logging statements for debugging video processing pipeline

## 2. Testing

-   [ ] 2.1 Test with valid video (should pass through unchanged)
-   [ ] 2.2 Test with wrong resolution (should resize)
-   [ ] 2.3 Test with invalid aspect ratio (should scale and pad)
-   [ ] 2.4 Test with too long duration (should trim)
-   [ ] 2.5 Test with too short duration (should error)
-   [ ] 2.6 Test with oversized file (should error after processing if still >2GB)

## 3. Documentation

-   [x] 3.1 Add docstrings to all new functions
-   [x] 3.2 Document FFmpeg installation requirement in README
-   [x] 3.3 Add example usage in function docstrings
