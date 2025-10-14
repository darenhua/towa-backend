## Context

The TwelveLabs video upload API has strict requirements that must be met before upload. Videos from external sources may not meet these requirements, causing upload failures and wasted API quota. This change introduces client-side validation and automatic transformation to ensure compliance.

## Goals / Non-Goals

**Goals:**

-   Validate videos against all TwelveLabs requirements before upload
-   Automatically fix fixable issues (resolution, aspect ratio, format, duration >2hrs)
-   Provide clear error messages for unfixable issues (duration <4s, file >2GB after processing)
-   Use temporary files to avoid polluting filesystem
-   Support future integration with Supabase/S3 storage via fetch function

**Non-Goals:**

-   Real Supabase/S3 integration (mock function for now)
-   Video quality optimization beyond compliance
-   Advanced codec selection (use standard H.264/AAC)
-   Batch video processing
-   Progress callbacks during transformation

## Decisions

### Decision 1: Use FFmpeg via subprocess

**Rationale:** FFmpeg is industry standard for video processing, widely available, and handles all required transformations. Subprocess approach avoids Python binding dependencies.

**Alternatives considered:**

-   MoviePy: Too heavyweight, adds many dependencies
-   OpenCV: Good for frames but poor for format conversion
-   Cloud processing: Adds latency and cost

### Decision 2: Validate-then-transform pipeline

**Rationale:** Check requirements first, then apply only needed transformations. Efficient and provides clear feedback.

**Flow:**

1. Fetch video blob → save to temp file
2. FFprobe extracts metadata
3. Validate against requirements
4. If issues found, transform with FFmpeg
5. Re-validate transformed output
6. Return temp file path

### Decision 3: Aspect ratio handling via scale + pad

**Rationale:** Preserves full video content without cropping. Black bars acceptable for ad analysis.

**Approach:**

-   Calculate target aspect ratio (e.g., 16:9 = 1920x1080)
-   Scale video to fit within bounds (maintain aspect)
-   Add black padding (pillarbox/letterbox) to exact ratio

### Decision 4: Temporary file management

**Rationale:** Use `tempfile.NamedTemporaryFile(delete=False)` to create files that persist beyond function scope but can be cleaned up by caller.

**Cleanup strategy:**

-   Caller responsible for deleting returned Path
-   Or rely on OS temp cleanup (acceptable for hackathon)

### Decision 5: Mock fetch function structure

**Rationale:** Design interface that matches future Supabase integration pattern.

```python
async def fetch_video_blob_from_storage(job_id: str) -> bytes:
    # Future: Query Supabase jobs table for video_url
    # Future: Fetch from Supabase Storage or S3
    # For now: raise NotImplementedError with helpful message
```

## Risks / Trade-offs

**Risk:** FFmpeg not installed on deployment environment
**Mitigation:** Check FFmpeg availability on startup, add to deployment docs, provide clear error messages

**Risk:** Large videos consume excessive memory during processing
**Mitigation:** Use FFmpeg's streaming mode, set reasonable max file size (2GB enforced)

**Risk:** Processing time adds latency to upload flow
**Mitigation:** Acceptable for hackathon; future can make async with progress tracking

**Trade-off:** Black padding vs cropping for aspect ratio
**Decision:** Padding preserves all content, better for analysis even if aesthetically imperfect

## Migration Plan

**Implementation:**

1. Add new functions without modifying existing `upload_and_index_video`
2. Test independently with sample videos
3. Integrate into upload flow (modify `upload_and_index_video` to call `process_and_validate_video` when job_id provided)

**Rollback:**

-   New functions are additive, can be skipped if issues arise
-   Existing direct file upload path remains unchanged

## Open Questions

-   Should we cache processed videos to avoid re-processing? (Probably not needed for hackathon)
-   What's the actual video fetch mechanism? (Supabase Storage URL? Direct S3? Depends on upstream workflow)
-   Should we add video format conversion metrics/logging? (Yes, helpful for debugging)
