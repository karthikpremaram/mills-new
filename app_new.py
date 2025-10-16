"""Millis Agent Creation Service"""

from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.core.config import Config
from src.agent import agent_action, get_knowledge_base
from src.agent_config.agent_tools import COMPANY_NAMES
from src.scrape.llm import get_kb_description
from src.utils.payloads import Payload
from src.utils.functions import (
    create_millis_assistant,
    generate_presigned_url,
    set_knowledge_base,
    upload_text_to_s3,
)

API_KEY = Config.MILLIS_API_KEY
app = FastAPI(title="millis voice assistant")


class CreateAgentRequest(BaseModel):
    """Request model for creating an agent"""

    main_url: str
    assistant_name: Optional[str] = None


@app.post("/create-agent")
async def create_agent(request: CreateAgentRequest):
    """Create a new Millis agent"""
    try:
        # Validate URL format
        if not request.main_url.startswith(("http://", "https://")):
            raise HTTPException(
                status_code=400,
                detail="Invalid URL format. URL must start with http:// or https://",
            )

        # Step 1: Get system prompt and important links
        system_prompt, important_links = await agent_action(request.main_url)
        if system_prompt == "-1":
            raise HTTPException(
                status_code=400, detail="Failed to create system prompt"
            )

        # Step 2: Get knowledge base content
        assistant_name = request.assistant_name or COMPANY_NAMES[0]
        kb = await get_knowledge_base(COMPANY_NAMES[0], important_links)
        kb_description = await get_kb_description(
            important_links, output_dir=f"agent_content/{COMPANY_NAMES[0]}"
        )

        if not kb_description:
            raise HTTPException(
                status_code=400, detail="Failed to generate knowledge base description"
            )

        # Step 3: Create Millis assistant
        greeting_message = f"Hi, welcome to {assistant_name}! May I know your name and what brings you here today?"
        payload = Payload(
            agent_name=assistant_name,
            prompt=system_prompt,
            greeting_message=greeting_message,
            model="gpt-4o",
        )

        assistant = await create_millis_assistant(payload.get_payload(), API_KEY)
        assistant_id = assistant["id"]

        # Step 4: Upload knowledge base to S3
        file_name = f"{assistant_name}.txt"
        presigned_data = await generate_presigned_url(API_KEY, file_name)
        s3_upload_url = presigned_data["url"]
        s3_fields = presigned_data["fields"]

        upload_response = await upload_text_to_s3(
            s3_upload_url, s3_fields, kb, file_name
        )
        if upload_response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload to S3: {upload_response.status_code}",
            )

        # Step 5: Set knowledge base for the assistant
        file_id = s3_fields.get("key", "").split("/")[-1]
        messages = [{"role": "system", "content": kb_description}]
        kb_response = await set_knowledge_base(API_KEY, assistant_id, file_id, messages)

        if kb_response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to set knowledge base: {kb_response.status_code}",
            )

        return JSONResponse(
            {
                "status": "success",
                "assistant_id": assistant_id,
                "name": assistant_name,
                "message": "Agent created successfully",
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
