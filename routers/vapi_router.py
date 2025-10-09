from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging
from vapi import Vapi
from vapi.core.api_error import ApiError

# Configure logging
logger = logging.getLogger(__name__)

# Initialize Vapi client
vapi_client = Vapi(token="b5a72b1b-a9d4-4d64-8e36-e9d61d6724d3")

# Default configuration (from simplecall.py)
DEFAULT_ASSISTANT_ID = "1b857043-1959-4261-be2f-cddae4e2edf1"
DEFAULT_PHONE_NUMBER_ID = "ac8d98e7-ac31-4026-86ec-e83b2bfe1681"
DEFAULT_CUSTOMER_NUMBER = "+19178556130"

# Voice-specific assistant IDs
MALE_VOICE_ASSISTANT_ID = "ceeb53b3-2ea0-4ba4-b33c-89532fbac19e"
FEMALE_VOICE_ASSISTANT_ID = "e629da51-16d2-4704-937c-32d891c15ef9"

# Create router
router = APIRouter(prefix="/vapi", tags=["vapi"])


# Pydantic models for request/response
class CallRequest(BaseModel):
    assistant_id: Optional[str] = DEFAULT_ASSISTANT_ID
    phone_number_id: Optional[str] = DEFAULT_PHONE_NUMBER_ID
    customer_number: Optional[str] = DEFAULT_CUSTOMER_NUMBER
    customer_name: Optional[str] = None


class CallResponse(BaseModel):
    call_id: str
    status: str
    message: str


class CallStatusResponse(BaseModel):
    call_id: str
    status: str
    details: Optional[dict] = None


@router.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Vapi Call API",
        "version": "1.0.0",
        "endpoints": {
            "create_default_call": "/vapi/calls",
            "create_custom_call": "/vapi/calls/create",
            "create_male_voice_call": "/vapi/calls/male",
            "create_female_voice_call": "/vapi/calls/female",
            "create_simple_call": "/vapi/calls/simple",
            "call_status": "/vapi/calls/{call_id}/status",
            "health": "/vapi/health",
        },
    }


@router.post("/calls/create", response_model=CallResponse)
async def create_call(request: CallRequest):
    """
    Create a new voice call using Vapi

    All parameters are optional and will use defaults if not provided:
    - **assistant_id**: The Vapi assistant ID to use (default: 1b857043-1959-4261-be2f-cddae4e2edf1)
    - **phone_number_id**: The Vapi phone number ID to use (default: ac8d98e7-ac31-4026-86ec-e83b2bfe1681)
    - **customer_number**: The phone number to call (default: +19178556130)
    - **customer_name**: Optional name for the customer
    """
    try:
        logger.info(f"Creating call to {request.customer_number}")

        # Prepare customer data
        customer_data = {"number": request.customer_number}
        if request.customer_name:
            customer_data["name"] = request.customer_name

        # Create the call
        call = vapi_client.calls.create(
            assistant_id=request.assistant_id,
            phone_number_id=request.phone_number_id,
            customer=customer_data,
        )

        logger.info(f"Call created successfully with ID: {call.id}")

        return CallResponse(
            call_id=call.id,
            status="created",
            message=f"Call created successfully to {request.customer_number}",
        )

    except ApiError as e:
        logger.error(f"Vapi API error: {e.status_code} - {e.body}")
        raise HTTPException(
            status_code=e.status_code, detail=f"Vapi API error: {e.body}"
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/calls/{call_id}/status", response_model=CallStatusResponse)
async def get_call_status(call_id: str):
    """
    Get the status of a specific call

    - **call_id**: The ID of the call to check
    """
    try:
        logger.info(f"Getting status for call: {call_id}")

        # Get call details from Vapi
        call = vapi_client.calls.get(call_id)

        return CallStatusResponse(
            call_id=call_id,
            status=call.status if hasattr(call, "status") else "unknown",
            details=call.__dict__ if hasattr(call, "__dict__") else None,
        )

    except ApiError as e:
        logger.error(f"Vapi API error: {e.status_code} - {e.body}")
        raise HTTPException(
            status_code=e.status_code, detail=f"Vapi API error: {e.body}"
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/calls")
async def create_default_call():
    """
    Create a call using all default values (no parameters required)
    This is the simplest way to make a call - just like simplecall.py
    """
    try:
        logger.info("Creating call with all default values")

        call = vapi_client.calls.create(
            assistant_id=DEFAULT_ASSISTANT_ID,
            phone_number_id=DEFAULT_PHONE_NUMBER_ID,
            customer={"number": DEFAULT_CUSTOMER_NUMBER},
        )

        logger.info(f"Default call created successfully with ID: {call.id}")

        return {
            "call_id": call.id,
            "status": "created",
            "message": "Call created successfully with default values",
            "details": {
                "assistant_id": DEFAULT_ASSISTANT_ID,
                "phone_number_id": DEFAULT_PHONE_NUMBER_ID,
                "customer_number": DEFAULT_CUSTOMER_NUMBER,
            },
        }

    except ApiError as e:
        logger.error(f"Vapi API error: {e.status_code} - {e.body}")
        raise HTTPException(
            status_code=e.status_code, detail=f"Vapi API error: {e.body}"
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/calls/male")
async def create_male_voice_call():
    """
    Create a call with male voice assistant
    Uses the male voice assistant ID: ceeb53b3-2ea0-4ba4-b33c-89532fbac19e
    """
    try:
        logger.info("Creating call with male voice assistant")

        call = vapi_client.calls.create(
            assistant_id=MALE_VOICE_ASSISTANT_ID,
            phone_number_id=DEFAULT_PHONE_NUMBER_ID,
            customer={"number": DEFAULT_CUSTOMER_NUMBER},
        )

        logger.info(f"Male voice call created successfully with ID: {call.id}")

        return {
            "call_id": call.id,
            "status": "created",
            "message": "Male voice call created successfully",
            "voice_type": "male",
            "details": {
                "assistant_id": MALE_VOICE_ASSISTANT_ID,
                "phone_number_id": DEFAULT_PHONE_NUMBER_ID,
                "customer_number": DEFAULT_CUSTOMER_NUMBER,
            },
        }

    except ApiError as e:
        logger.error(f"Vapi API error: {e.status_code} - {e.body}")
        raise HTTPException(
            status_code=e.status_code, detail=f"Vapi API error: {e.body}"
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/calls/female")
async def create_female_voice_call():
    """
    Create a call with female voice assistant
    Uses the female voice assistant ID: e629da51-16d2-4704-937c-32d891c15ef9
    """
    try:
        logger.info("Creating call with female voice assistant")

        call = vapi_client.calls.create(
            assistant_id=FEMALE_VOICE_ASSISTANT_ID,
            phone_number_id=DEFAULT_PHONE_NUMBER_ID,
            customer={"number": DEFAULT_CUSTOMER_NUMBER},
        )

        logger.info(f"Female voice call created successfully with ID: {call.id}")

        return {
            "call_id": call.id,
            "status": "created",
            "message": "Female voice call created successfully",
            "voice_type": "female",
            "details": {
                "assistant_id": FEMALE_VOICE_ASSISTANT_ID,
                "phone_number_id": DEFAULT_PHONE_NUMBER_ID,
                "customer_number": DEFAULT_CUSTOMER_NUMBER,
            },
        }

    except ApiError as e:
        logger.error(f"Vapi API error: {e.status_code} - {e.body}")
        raise HTTPException(
            status_code=e.status_code, detail=f"Vapi API error: {e.body}"
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/calls/simple")
async def create_simple_call():
    """
    Create a call using the default configuration from simplecall.py
    This endpoint uses the hardcoded values for quick testing
    """
    try:
        logger.info("Creating simple call with default configuration")

        call = vapi_client.calls.create(
            assistant_id=DEFAULT_ASSISTANT_ID,
            phone_number_id=DEFAULT_PHONE_NUMBER_ID,
            customer={"number": DEFAULT_CUSTOMER_NUMBER},
        )

        logger.info(f"Simple call created successfully with ID: {call.id}")

        return {
            "call_id": call.id,
            "status": "created",
            "message": "Simple call created successfully",
            "details": {
                "assistant_id": DEFAULT_ASSISTANT_ID,
                "phone_number_id": DEFAULT_PHONE_NUMBER_ID,
                "customer_number": DEFAULT_CUSTOMER_NUMBER,
            },
        }

    except ApiError as e:
        logger.error(f"Vapi API error: {e.status_code} - {e.body}")
        raise HTTPException(
            status_code=e.status_code, detail=f"Vapi API error: {e.body}"
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Vapi Call API", "version": "1.0.0"}
