## Why

TwelveLabs has strict video requirements (resolution, aspect ratio, duration, file size, format) that must be met before upload. Currently, there's no validation or preprocessing, leading to potential upload failures and wasted API quota.

## What Changes

-   Add video validation helper that checks TwelveLabs requirements before upload
-   Implement FFmpeg-based automatic video transformation to fix non-compliant videos
-   Add mock fetch function to retrieve video blobs from remote storage by job_id
-   Process videos through validation pipeline and save to temporary files for upload
-   Handle edge cases (too short duration, oversized files) with clear error messages

## Impact

-   Affected specs: `video-processing` (new capability)
-   Affected code: `routers/twelvelabs_router.py`
-   New dependencies: FFmpeg system binary (subprocess-based execution)
-   External APIs: TwelveLabs upload requirements enforced client-side
