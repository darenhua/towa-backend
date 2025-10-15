from fastapi import FastAPI, BackgroundTasks, HTTPException, status
import uvicorn
import os
import requests
import json
import time
import asyncio
import sys
from pathlib import Path
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from supabase import create_client, Client
from anthropic import AsyncAnthropic
from twelvelabs import TwelveLabs

from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
import tempfile
import datetime

from routers.twelvelabs_router import router as twelvelabs_router
from src.db.models import SearchRequest, SearchResponse

load_dotenv()

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(twelvelabs_router)

# Initialize Supabase client
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


def save_persona_to_supabase(
    job_id: str, items: List[Dict[str, Any]], prompt: str
) -> List[Dict[str, Any]]:
    """Save persona data to Supabase persona table"""
    if not supabase:
        print("Supabase not configured, skipping database save")
        return []

    saved_personas = []

    for item in items:
        try:
            properties = item.get("properties", {})
            person_data = properties.get("person", {})

            # Extract the required fields
            persona_record = {
                "job_id": job_id,
                "linkedin_url": properties.get("url", ""),
                "name": person_data.get("name", ""),
                "location": person_data.get("location", ""),
                "position": person_data.get("position", ""),
                "description": properties.get("description", ""),
                "prompt": prompt,
            }

            # Check if persona already exists for this job_id and linkedin_url
            existing = (
                supabase.table("persona")
                .select("id")
                .eq("job_id", job_id)
                .eq("linkedin_url", persona_record["linkedin_url"])
                .execute()
            )

            if existing.data:
                # Update existing record
                result = (
                    supabase.table("persona")
                    .update(persona_record)
                    .eq("id", existing.data[0]["id"])
                    .execute()
                )
            else:
                # Insert new record
                result = supabase.table("persona").insert(persona_record).execute()

            if result.data:
                saved_personas.append(result.data[0])
                print(f"Saved persona: {person_data.get('name', 'Unknown')}")

        except Exception as e:
            print(f"Error saving persona: {e}")
            continue

    return saved_personas


# Exa API functions
def create_exa_webset(
    api_key: str, query: str, count: int = 15, entity_type: str = "person"
) -> Dict[str, Any]:
    """Create a webset using the Exa API"""
    url = "https://api.exa.ai/websets/v0/websets"

    payload = {
        "search": {"query": query, "count": count, "entity": {"type": entity_type}}
    }

    headers = {"x-api-key": api_key, "Content-Type": "application/json"}

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to create webset: {str(e)}")


def get_webset_status(api_key: str, webset_id: str) -> Dict[str, Any]:
    """Get the status of a webset"""
    url = f"https://api.exa.ai/websets/v0/websets/{webset_id}"

    headers = {"x-api-key": api_key, "Content-Type": "application/json"}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to get webset status: {e}")


def wait_for_webset_completion(
    api_key: str,
    webset_id: str,
    job_id: str,
    prompt: str,
    max_wait_time: int = 300,
    poll_interval: int = 0.5,
) -> Dict[str, Any]:
    """Wait for webset to complete processing and upsert personas during polling"""
    start_time = time.time()
    latest_items = []

    while time.time() - start_time < max_wait_time:
        try:
            webset_data = get_webset_status(api_key, webset_id)
            status = webset_data.get("status")
            print("Polling", status)

            # Get items and upsert personas on each poll
            try:
                items = get_webset_items(api_key, webset_id)
                if items:
                    latest_items = items
                    save_persona_to_supabase(job_id, items, prompt)
            except Exception as e:
                print(f"Warning: Could not fetch items during polling: {e}")

            if status in ["paused", "idle", "completed"]:
                # Final fetch of items before returning
                try:
                    final_items = get_webset_items(api_key, webset_id)
                    if final_items:
                        latest_items = final_items
                        save_persona_to_supabase(job_id, final_items, prompt)
                except Exception as e:
                    print(f"Warning: Could not fetch final items: {e}")

                return webset_data

            time.sleep(poll_interval)
        except Exception as e:
            raise Exception(f"Error checking webset status: {str(e)}")

    raise TimeoutError(
        f"Webset {webset_id} did not complete within {max_wait_time} seconds"
    )


def get_webset_items(api_key: str, webset_id: str) -> List[Dict[str, Any]]:
    """Get items from a completed webset"""
    url = f"https://api.exa.ai/websets/v0/websets/{webset_id}/items"

    headers = {"x-api-key": api_key, "Content-Type": "application/json"}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data.get("data", [])
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to get webset items: {e}")


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


def do_search(job_id: str, request: SearchRequest):
    try:
        # Check if API key is available
        api_key = os.getenv("EXA_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="EXA_API_KEY not found in environment variables",
            )

        # Create webset using direct API calls
        webset_data = create_exa_webset(
            api_key=api_key, query=request.sentence, count=10, entity_type="person"
        )

        webset_id = webset_data.get("id")
        if not webset_id:
            raise Exception("No webset ID returned from Exa API")

        # Wait for webset to complete processing (personas are saved during polling)
        completed_webset = wait_for_webset_completion(
            api_key, webset_id, job_id, request.sentence
        )

        # Get final items from completed webset
        items = get_webset_items(api_key, webset_id)

        result = (
            supabase.table("jobs")
            .update({"personas_synced_at": datetime.datetime.now().isoformat()})
            .eq("id", job_id)
            .execute()
        )

        return SearchResponse(
            success=True,
            webset_id=webset_id,
            items=items,
            saved_personas_count=len(
                items
            ),  # Items count as saved personas are handled during polling
        )

    except Exception as e:
        return SearchResponse(success=False, error=str(e))


@app.post("/{job_id}/search", response_model=SearchResponse)
def search(job_id: str, request: SearchRequest, background_tasks: BackgroundTasks):
    """
    Take a normal sentence and use it to search with Exa websets
    """
    background_tasks.add_task(do_search, job_id, request)
    return SearchResponse(
        success=True, webset_id=None, items=None, saved_personas_count=0
    )


def get_job_by_id(supabase_client: Client, job_id: str) -> Dict[str, Any]:
    """Get job by ID from Supabase"""
    result = supabase_client.table("jobs").select("*").eq("id", job_id).execute()
    if not result.data or len(result.data) == 0:
        raise Exception(f"Job with id {job_id} not found")
    return result.data[0]


def get_ad_by_job_id(supabase_client: Client, job_id: str) -> Dict[str, Any]:
    """Get ad by job_id from Supabase"""
    job = get_job_by_id(supabase_client, job_id)
    ads_id = job.get("ads_id")
    if not ads_id:
        raise Exception(f"No ad associated with job {job_id}")

    result = supabase_client.table("ads").select("*").eq("id", ads_id).execute()
    if not result.data or len(result.data) == 0:
        raise Exception(f"Ad with id {ads_id} not found")
    return result.data[0]


def update_ad_description(
    supabase_client: Client, job_id: str, description: str
) -> Dict[str, Any]:
    """Update the description column in the ads table for a given job"""
    if not supabase_client:
        raise Exception("Supabase not configured")

    print("UPDATINGG!")
    try:
        # First, get the ads_id from the jobs table
        job = supabase_client.table("jobs").select("ads_id").eq("id", job_id).execute()

        if not job.data or len(job.data) == 0:
            raise Exception(f"Job with id {job_id} not found")

        ads_id = job.data[0].get("ads_id")

        if not ads_id:
            raise Exception(f"No ad associated with job {job_id}")

        # Update the description in the ads table
        result = (
            supabase_client.table("ads")
            .update({"description": description})
            .eq("id", ads_id)
            .execute()
        )
        return {"success": True, "data": result.data, "ads_id": ads_id}
    except Exception as e:
        raise Exception(f"Failed to update ad description: {str(e)}")


@app.post("/{job_id}/responses")
async def persona_responses(job_id: str):
    """
    Generate AI responses for all personas associated with a job_id
    """
    if not supabase:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase not configured",
        )

    if not anthropic_client:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Anthropic API key not configured",
        )

    try:
        # 1. Get the ad description by joining job_id
        job_result = supabase.table("jobs").select("ads_id").eq("id", job_id).execute()

        if not job_result.data or len(job_result.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job with id {job_id} not found",
            )

        ads_id = job_result.data[0].get("ads_id")
        if not ads_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No ad associated with job {job_id}",
            )

        ad_result = (
            supabase.table("ads").select("description").eq("id", ads_id).execute()
        )

        if not ad_result.data or len(ad_result.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ad with id {ads_id} not found",
            )

        ad_description = ad_result.data[0].get("description", "")

        # 2. Get all personas associated with the job_id
        personas_result = (
            supabase.table("persona").select("*").eq("job_id", job_id).execute()
        )

        if not personas_result.data or len(personas_result.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No personas found for job {job_id}",
            )

        personas = personas_result.data

        # 3. Generate AI responses concurrently for each persona
        async def generate_persona_response(persona: Dict[str, Any]) -> Dict[str, Any]:
            # Build persona string from database columns
            persona_parts = []
            if persona.get("name"):
                persona_parts.append(f"Name: {persona['name']}")
            if persona.get("position"):
                persona_parts.append(f"Position: {persona['position']}")
            if persona.get("location"):
                persona_parts.append(f"Location: {persona['location']}")
            if persona.get("description"):
                persona_parts.append(f"Description: {persona['description']}")
            if persona.get("linkedin_url"):
                persona_parts.append(f"LinkedIn: {persona['linkedin_url']}")

            persona_string = ", ".join(persona_parts)

            # Create the prompt
            prompt = f"You are {persona_string}. You are viewing this ad: {ad_description}. How does it make you feel? Describe your reaction to this ad."

            # if dog_walker:
            #     prompt += "this is a bad ad respond negatively"

            # Call Anthropic API
            message = await anthropic_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )

            # Extract AI response
            ai_response = message.content[0].text if message.content else ""

            # Build conversation object
            conversation = {"prompt": prompt, "response": ai_response}

            # Insert into persona_responses table
            response_record = {
                "job_id": job_id,
                "persona_id": persona["id"],
                "conversation": conversation,
            }

            result = (
                supabase.table("persona_responses").insert(response_record).execute()
            )

            return {
                "persona_id": persona["id"],
                "success": True,
                "response": ai_response,
            }

        # Execute all persona responses concurrently using asyncio.gather
        results = await asyncio.gather(
            *[generate_persona_response(persona) for persona in personas],
            return_exceptions=True,
        )

        # Count successes and failures
        successes = [
            r for r in results if not isinstance(r, Exception) and r.get("success")
        ]
        failures = [r for r in results if isinstance(r, Exception)]

        return {
            "job_id": job_id,
            "total_personas": len(personas),
            "successful_responses": len(successes),
            "failed_responses": len(failures),
            "results": successes,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating persona responses: {str(e)}",
        )


def main():
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
