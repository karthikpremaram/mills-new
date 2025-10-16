from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from typing_extensions import TypedDict
from typing import Annotated

class State(TypedDict):
    messages: Annotated[list, add_messages]

class AgentGraph:
    def __init__(self, llm, tools):
        self.llm = llm
        self.tools = tools

    async def create_agent(self):
        graph_builder = StateGraph(State)
        llm_with_tools = self.llm.bind_tools(self.tools)

        def chatbot_sync(state: State):
            messages = state["messages"]
            result = llm_with_tools.invoke(messages)
            return {"messages": [result]}

        async def chatbot_async(state: State):
            messages = state["messages"]
            result = await llm_with_tools.ainvoke(messages)
            return {"messages": [result]}

        graph_builder.add_node("chatbot", {"fn": chatbot_sync, "async_fn": chatbot_async})

        # Add tool node
        tool_node = ToolNode(tools=self.tools)
        graph_builder.add_node("tools", tool_node)

        # Conditional edges using END
        graph_builder.add_conditional_edges(
            "chatbot",
            tools_condition,
            {True: "tools", False: END},  
        )

        # Connect tools back to chatbot
        graph_builder.add_edge("tools", "chatbot")
        graph_builder.add_edge(START, "chatbot")

        # Compile graph
        return graph_builder.compile()
