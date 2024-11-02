import autogen

from autogen.agentchat.contrib.gpt_assistant_agent import GPTAssistantAgent
from autogen.agentchat import AssistantAgent, UserProxyAgent
from openai import OpenAI
from openai.types.chat import ChatCompletion
import os
from app.database import db

from flask import g, current_app
from app.services.utils import print_messages
from datetime import datetime


api_key = os.environ.get("OPENAI_API_KEY")

config_list = [{"model": "gpt-4o-mini", "api_key": api_key}]

llm_config22 = {
    "request_timeout": 600,
    "seed": 42,
    "config_list": config_list,
    "temperature": 0,
}


agent_classes = {
    "GPTAssistantAgent": GPTAssistantAgent,
    "AssistantAgent": AssistantAgent,
}


# def create_groupchat(agents_info, task_info, user_proxy):
#     order_status_agent = GPTAssistantAgent(
#         name="Order Status Agent",
#         instructions="""you are a customer service order status agent for a deliver service, equipped to analyze delivery of packages and products. if the package/product appears damaged with tears, proceed for refund. if the package/product looks wet, initiate a replacement. if the package/product looks normal and not damaged, escalte to agent. for unclear queries and images, escalte to agent. you must always use tools""",
#         llm_config=llm_config22,
#     )
#     fraud_detection_agent = GPTAssistantAgent(
#         name="Fraud Detection Agent",
#         instructions="""you are a customer service fraud detection agent for a deliver service, equipped to analyze fraud in transaction of packages/products. If the transaction appears suspicious/fraud, proceed for refund. If the transaction looks normal, decline the request. For unwanted queries, escalate to the agent. you must always use tools""",
#         llm_config=llm_config22,
#     )

#     assistants = []

#     for agent_info in agents_info:
#         if agent_info["type"] == "UserProxyAgent":
#             continue

#         llm_config = {
#             "config_list": [agent_info["llm"]],
#             "temperature": 0,
#         }

#         AgentClass = agent_classes[agent_info["type"]]
#         assistant = AgentClass(
#             name=agent_info["name"],
#             llm_config=llm_config,
#             system_message=agent_info["system_message"],
#             description=agent_info["description"],
#         )

#         assistant.register_reply(
#             [autogen.Agent, None],
#             reply_func=print_messages,
#             config={"callback": None},
#         )
#         assistants.append(assistant)

#     if len(assistants) == 1:
#         manager = assistants[0]

#     elif len(assistants) > 1:
#         groupchat = autogen.GroupChat(
#             agents=[user_proxy] + assistants,
#             messages=[],
#             max_round=task_info["maxMessages"],
#             speaker_selection_method=task_info["speakSelMode"],
#         )
#         manager = autogen.GroupChatManager(
#             groupchat=groupchat,
#             llm_config=llm_config22,
#             system_message="",
#         )

#     return manager, assistants


# def analyze_intent(message: str) -> str:
#     """Analyze the message intent and return the appropriate agent type"""
#     order_status_keywords = [
#         "damaged",
#         "broken",
#         "wet",
#         "torn",
#         "shipping",
#         "delivery",
#         "package",
#         "order",
#         "status",
#     ]
#     fraud_keywords = [
#         "unauthorized",
#         "charge",
#         "transaction",
#         "payment",
#         "duplicate",
#         "fraud",
#         "credit card",
#     ]

#     message = message.lower()

#     # Check for order status keywords
#     if any(keyword in message for keyword in order_status_keywords):
#         return "order_status"
#     # Check for fraud keywords
#     elif any(keyword in message for keyword in fraud_keywords):
#         return "fraud"
#     else:
#         return "unclear"


def create_groupchat(user_proxy):
    try:
        # Define OpenAI config
        llm_config = {
            "config_list": [
                {"model": "gpt-4", "api_key": os.environ.get("OPENAI_API_KEY")}
            ],
            "temperature": 0,
        }

        # Create Order Status Agent
        order_status_agent = AssistantAgent(
            name="Order Status Agent",
            system_message="""You are a customer service order status agent. For any order-related query:
            1. First ask for the order number
            2. Then ask for any images if damage is reported
            3. Make a decision based on:
               - Visible damage → Refund
               - Water damage → Replace
               - Normal condition → Provide status
               - Unclear → Escalate""",
            llm_config=llm_config,
        )

        # Create Fraud Detection Agent
        fraud_detection_agent = AssistantAgent(
            name="Fraud Detection Agent",
            system_message="""You are a fraud detection agent. For any transaction query:
            1. First ask for the order number
            2. Then ask for transaction details
            3. Make a decision based on:
               - Unauthorized charges → Refund
               - Duplicate charges → Refund
               - Normal transaction → Decline
               - Unclear → Escalate""",
            llm_config=llm_config,
        )

        def analyze_intent(message: str):
            """Determine which agent should handle the message"""
            message = message.lower()

            # Order status keywords
            order_keywords = ["order", "status", "delivery", "package", "damaged"]
            # Fraud keywords
            fraud_keywords = ["fraud", "transaction", "charge", "payment"]

            if any(keyword in message for keyword in order_keywords):
                return order_status_agent
            elif any(keyword in message for keyword in fraud_keywords):
                return fraud_detection_agent
            return order_status_agent  # Default to order status agent

        return analyze_intent, [order_status_agent, fraud_detection_agent]

    except Exception as e:
        print(f"Error creating agents: {e}")
        raise


async def process_message(user_proxy, message: str, image: str = None):
    try:
        # Get intent detection function and agents
        get_agent_by_intent, _ = create_groupchat(user_proxy)

        # Get appropriate agent based on message intent
        selected_agent, intent = get_agent_by_intent(message)

        # Generate response using the correct method
        response = await selected_agent.a_chat(user_proxy, message=message)

        return {
            "status": "success",
            "message": response,
            "agent": selected_agent.name,
            "intent": intent,
        }

    except Exception as e:
        print(f"Error processing message: {e}")
        return {
            "status": "error",
            "message": f"An error occurred: {str(e)}",
            "agent": "System",
        }


# Helper functions for conversation state management
def get_conversation_state():
    if not hasattr(g, "conversation_state"):
        g.conversation_state = {}
    return g.conversation_state


def clear_conversation_state():
    if hasattr(g, "conversation_state"):
        g.conversation_state = {}
