"""agent functionality"""

import asyncio

from langchain.chat_models import init_chat_model

from src.agent_config.agent_graph import AgentGraph
from src.agent_config.agent_tools import (
    COMPANY_NAMES,
    IMPORTANT_LINKS,
    create_directory,
    save_links,
    scrape_and_clean,
)
from src.scrape.scrape import scrape_urls
from src.core.config import Config
from src.core.prompts import FIXED_PROMPT, SYSTEM_PROMPT
from src.track_cost.cost_tracking_llm import CostTrackingLLM

llm = init_chat_model(
    "google_genai:gemini-2.5-flash",
    model_kwargs={
        "api_key": Config.GEMINI_API_KEY,
        "streaming": True,
    },
)


cost_tracking_llm = CostTrackingLLM(llm)
tools = [scrape_and_clean, save_links, create_directory]


async def agent_action(url):
    "agent to create system prompt and provide urls for knowledge base"

    try:
        agent_graph = AgentGraph(cost_tracking_llm, tools)
        agent = await agent_graph.create_agent()
        print("agent created")
        print("*" * 20)
        prompt = f"""
        Go through the URL and give prompt like as above give reference:
        Main URL: {url}
        if you didn't get info in main url, use links from the scraped content by observing endpoints.
        save important links using tool before giving final output.
        """

        # Initialize messages
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        # Invoke agent with proper async configuration
        config = {"configurable": {"thread_id": "1"}}
        result = await agent.ainvoke({"messages": messages}, config=config)

        # Process result
        assistant_prompt = result["messages"][-1].content

        lst = assistant_prompt.split("\n")
        assistant_prompt = lst[0] + "\n" + FIXED_PROMPT + "\n".join(lst[1:])
        print(COMPANY_NAMES)
        with open(f"content/{COMPANY_NAMES[0]}/prompt.txt", "w", encoding="utf-8") as f:
            f.write(assistant_prompt)

        print(f"System prompt saved: content/{COMPANY_NAMES[0]}/prompt.txt")

        return assistant_prompt, IMPORTANT_LINKS

    except Exception as e:
        print(f"Error in agent_action: {str(e)}")
        raise
    


def get_knowledge_base(company_name, important_links):
    "scrape and clean links for knowledge base"

    kb = asyncio.run(
        scrape_urls(
            important_links["links"],
            refine_with_llm=True,
            output_dir=f"/{company_name}",
        )
    )
    print("length of knowledge base : ", len(kb))
    with open(f"content/{company_name}/kb.txt", "w", encoding="utf-8") as f:
        f.write(kb)
    print(f"knowledge base stored : content/{company_name}/kb.txt")
    return kb
