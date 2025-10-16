"""Agent tools for scraping and directory management."""

import asyncio
import json
import os
import shutil
from typing import List, Dict

from langchain.tools import tool
from pydantic import BaseModel
from src.scrape.scrape import scrape_urls


# -------------------------------
# Data Models
# -------------------------------
class LinksInput(BaseModel):
    values: List[str]


# -------------------------------
# Global state
# -------------------------------
COMPANY_NAMES: List[str] = []
IMPORTANT_LINKS: Dict[str, LinksInput] = {}
_LINKS_FILE_COUNTER = 0


# -------------------------------
# Directory functions
# -------------------------------
def create_directory_structure(path: str, clear_folder: bool = False) -> None:
    """Create a directory structure. Clears it if `clear_folder` is True."""
    try:
        if clear_folder and os.path.exists(path) and os.path.isdir(path):
            shutil.rmtree(path)

        os.makedirs(path, exist_ok=True)
        print(f"Directory '{path}' created successfully.")
    except OSError as err:
        print(f"Error creating directory '{path}': {err}")


@tool
def create_directory(company_name: str) -> str:
    """Create directories to store scraped and generated data."""
    global COMPANY_NAMES

    COMPANY_NAMES.clear()
    COMPANY_NAMES.append(company_name)
    print(f"Current company names: {COMPANY_NAMES}")

    # Create directory for markdown files from scraping
    create_directory_structure(f"markdown_content/{company_name}/")

    # Create directory for agent-related content (kb, important links, etc)
    create_directory_structure(f"agent_content/{company_name}/", clear_folder=True)

    return f"Created directories for {company_name}"


# -------------------------------
# Scraping functions
# -------------------------------
@tool
def scrape_and_clean(url: str) -> str:
    """Scrape and extract clean text content from a single webpage URL."""
    global _LINKS_FILE_COUNTER

    if not COMPANY_NAMES:
        return "Error: No company selected. Please create directories first."

    company = COMPANY_NAMES[0]
    links_file = f"markdown_content/{company}/links_opened.txt"

    # Write the URL to links file
    mode = "w" if _LINKS_FILE_COUNTER == 0 else "a"
    try:
        with open(links_file, mode, encoding="utf-8") as f:
            f.write(f"{url},\n")
        _LINKS_FILE_COUNTER += 1
    except OSError as err:
        return f"Error writing URL to file: {err}"

    # Scrape the URL asynchronously
    try:
        # Store markdown files in markdown_content directory
        scraped_content = asyncio.run(
            scrape_urls(
                url, refine_with_llm=False, output_dir=f"markdown_content/{company}"
            )
        )
        return scraped_content
    except Exception as err:  # pylint: disable=broad-exception-caught
        return f"Error processing {url}: {err}"


# -------------------------------
# Important links functions
# -------------------------------
@tool("save_links", args_schema=LinksInput)
def save_links(values: LinksInput) -> str:
    """Save important links about the company (about, services, contact, etc.)."""
    if not COMPANY_NAMES:
        return "Error: No company selected. Please create directories first."

    global IMPORTANT_LINKS
    company = COMPANY_NAMES[0]
    IMPORTANT_LINKS["links"] = values

    path = f"content/{company}/important_links.json"
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"links": values.dict()}, f, indent=4)
        print(f"Important links saved: {path}")
        return "Saved successfully"
    except OSError as err:
        return f"Error saving links: {err}"
