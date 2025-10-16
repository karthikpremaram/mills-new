from io import BytesIO
import httpx

async def get_files_in_millis(api_key: str):
    """ List the files in millis """

    url = "https://api-west.millis.ai/knowledge/list_files"
    headers = {
        "Authorization": api_key,   # ✅ Add Bearer prefix
        "Accept": "application/json"
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()  # raises HTTPStatusError for 4xx/5xx
        return response


async def get_old_file_details(old_file_id, files):
    """ Get the old file details(fields)"""
    for file in files:
        if file.get("id") == old_file_id:
            return file  
    return None 

async def generate_presigned_url(api_key, filename):
    """ Generate url to upload the file"""

    url = "https://api-west.millis.ai/knowledge/generate_presigned_url"
    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "filename": filename
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response

async def upload_text_to_s3(s3_url, fields, text, file_name="bhg.txt"):
    """ Upload file to s3 through generated url"""

    if isinstance(text, str):
        file_bytes = text.encode("utf-8")
    else:
        file_bytes = text

    file_obj = BytesIO(file_bytes)

    files = {"file": (file_name, file_obj)}
    async with httpx.AsyncClient() as client:
        response = await client.post(s3_url, data=fields, files=files)

    # response = requests.post(s3_url, data=fields, files=files)
    response.raise_for_status()  # Raise error if upload fails
    return response

async def create_file_in_millis(params):
    """ Upload the new file(kb) to the millis from s3 """

    url = "https://api-west.millis.ai/knowledge/create_file"
    headers = {
        "Authorization": params["API_KEY"],
        "Content-Type": "application/json"
    }
    payload = {
        "agent_id": params["assistant_id"],
        "object_key": params["s3_key"],
        "description": params["kb_description"],
        "name": params["file_name"],
        "file_type": "text/plain",
        "size": params["file_size"]
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response

async def set_knowledge_base(api_key, assistant_id, new_file_id):
    """ Set the uploaded file as knowledge base to the assistant"""

    url = "https://api-eu-west.millis.ai/knowledge/set_agent_files"

    payload = {
        "agent_id": assistant_id,
        "files": [new_file_id],
        "messages": ["let me check knowledge base"]
    }
    headers = {
        "authorization": api_key,
        "Content-Type": "application/json"
    }
    timeout = httpx.Timeout(10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, headers=headers, json=payload)
    return response

async def delete_knowledge_base(api_key, old_file_id):
    """ Delete the old knowledge base"""

    url = "https://api-west.millis.ai/knowledge/delete_file"

    payload = { "id": old_file_id }
    headers = {
        "authorization": api_key,
        "Content-Type": "application/json"
    }
    timeout = httpx.Timeout(10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, headers=headers, json=payload)
    return response