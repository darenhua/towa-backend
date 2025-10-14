## ADDED Requirements

### Requirement: Video Metadata Extraction

The system SHALL extract video metadata using FFprobe to determine resolution, aspect ratio, duration, file size, and codec information.

#### Scenario: Extract metadata from valid video

-   **WHEN** a video file path is provided to `get_video_metadata()`
-   **THEN** return a dictionary containing width, height, duration, file_size, video_codec, audio_codec, and calculated aspect_ratio

#### Scenario: Handle corrupted or invalid video file

-   **WHEN** FFprobe fails to read the video file
-   **THEN** raise an exception with a descriptive error message

### Requirement: TwelveLabs Compliance Validation

The system SHALL validate video metadata against TwelveLabs requirements: resolution (360x360 to 3840x2160), aspect ratio (1:1, 4:3, 4:5, 5:4, 16:9, 9:16, 17:9), duration (4s to 7200s), and file size (≤2GB).

#### Scenario: Video meets all requirements

-   **WHEN** a video with resolution 1920x1080, aspect 16:9, duration 30s, size 50MB is validated
-   **THEN** return validation result with `compliant: true` and empty `issues` list

#### Scenario: Video has multiple compliance issues

-   **WHEN** a video with resolution 320x240, aspect 4:3, duration 3s, size 100MB is validated
-   **THEN** return validation result with `compliant: false` and `issues` list containing "resolution_too_low" and "duration_too_short"

#### Scenario: Video duration is too short

-   **WHEN** a video with duration less than 4 seconds is validated
-   **THEN** mark as non-compliant with "duration_too_short" issue flagged as unfixable

#### Scenario: Video file exceeds size limit

-   **WHEN** a video file larger than 2GB is validated
-   **THEN** mark as non-compliant with "file_too_large" issue

### Requirement: Automatic Video Transformation

The system SHALL use FFmpeg to transform non-compliant videos to meet TwelveLabs requirements by resizing resolution, adjusting aspect ratio with padding, re-encoding to H.264/AAC, and trimming duration if needed.

#### Scenario: Resize video below minimum resolution

-   **WHEN** a video with resolution 320x180 needs transformation
-   **THEN** scale video to at least 360x360 while maintaining aspect ratio with black padding

#### Scenario: Adjust aspect ratio to nearest valid option

-   **WHEN** a video has aspect ratio 2:1 (not in allowed list)
-   **THEN** transform to nearest valid aspect ratio (16:9) by scaling and adding letterbox padding

#### Scenario: Trim video exceeding maximum duration

-   **WHEN** a video with duration 9000s (2.5 hours) needs transformation
-   **THEN** trim video to exactly 7200s (2 hours) from the start

#### Scenario: Re-encode to compatible format

-   **WHEN** a video uses an unsupported codec
-   **THEN** re-encode video to H.264 video codec and AAC audio codec

#### Scenario: Transformation results in file >2GB

-   **WHEN** FFmpeg transformation produces a file larger than 2GB
-   **THEN** raise an exception indicating the video cannot be processed

### Requirement: Video Blob Fetching

The system SHALL provide a function to fetch video blobs from remote storage using a job_id identifier.

#### Scenario: Mock fetch function interface

-   **WHEN** `fetch_video_blob_from_storage(job_id)` is called
-   **THEN** raise NotImplementedError with a message indicating this is a placeholder for Supabase/S3 integration

### Requirement: End-to-End Video Processing Pipeline

The system SHALL orchestrate the complete video processing workflow: fetch blob, save to temp file, validate, transform if needed, re-validate, and return processed temp file path.

#### Scenario: Process compliant video

-   **WHEN** `process_and_validate_video(job_id)` is called with a compliant video
-   **THEN** validate the video, skip transformation, save to temp file, and return Path to temp file

#### Scenario: Process and fix non-compliant video

-   **WHEN** `process_and_validate_video(job_id)` is called with a non-compliant but fixable video
-   **THEN** validate the video, apply FFmpeg transformations, re-validate, save to temp file, and return Path to processed temp file

#### Scenario: Fail on unfixable video issues

-   **WHEN** a video has unfixable issues (duration <4s or file >2GB after processing)
-   **THEN** raise an HTTPException with status 400 and a detailed error message

#### Scenario: Temporary file cleanup responsibility

-   **WHEN** a processed video temp file is returned
-   **THEN** the caller is responsible for deleting the file after upload to TwelveLabs

### Requirement: Error Handling and Logging

The system SHALL provide clear error messages for all validation and transformation failures, and log key processing steps for debugging.

#### Scenario: FFmpeg not installed

-   **WHEN** FFprobe or FFmpeg commands are not found in system PATH
-   **THEN** raise an exception indicating FFmpeg must be installed

#### Scenario: Log processing steps

-   **WHEN** video processing occurs
-   **THEN** log statements indicate: video fetched, metadata extracted, validation results, transformations applied, and final output path

#### Scenario: Validation failure details

-   **WHEN** a video fails validation
-   **THEN** the error message includes specific issues (e.g., "Resolution 320x240 below minimum 360x360")
