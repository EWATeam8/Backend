import autogen
import time
import asyncio

import os
import time
import asyncio
import threading
import json
from flask import Flask, request, jsonify, current_app
from flask_cors import CORS
import app.globals as g
from datetime import datetime

# aditya changes
from autogen.agentchat.contrib.gpt_assistant_agent import GPTAssistantAgent
from autogen.agentchat import AssistantAgent, UserProxyAgent
import queue
import openai
from transformers import GPT2Tokenizer, GPT2LMHeadModel, Trainer, TrainingArguments
from datasets import Dataset
from openai import OpenAI
from openai.types.chat import ChatCompletion

from app.services.autogen_image_transfer import upload_image_to_autogen
from app.ai_agents.ai_agent_initialize import create_groupchat, process_message
from app.services.utils import print_messages

app = Flask(__name__)
cors = CORS(app)

from app.globals import user_queue, print_queue, set_chat_status


# aditya changes
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

try:
    client = OpenAI(api_key=api_key)
except Exception as e:
    print(f"Error initializing OpenAI client: {e}")
    raise


def load_manual_data(json_file):
    with open(json_file, "r", encoding="utf-8") as file:
        return file.read()


DECISION_TYPES = {"REFUND": "refund", "REPLACE": "replace", "ESCALATE": "escalate"}


def validate_decision(decision_type, image_type):
    valid_decisions = {
        "product_defect": [
            DECISION_TYPES["REFUND"],
            DECISION_TYPES["REPLACE"],
            DECISION_TYPES["ESCALATE"],
        ],
        "shipping_box": [
            DECISION_TYPES["REFUND"],
            DECISION_TYPES["REPLACE"],
            DECISION_TYPES["ESCALATE"],
        ],
        "fraud_transaction": [
            DECISION_TYPES["REFUND"],
            "decline",
            DECISION_TYPES["ESCALATE"],
        ],
    }
    return decision_type in valid_decisions.get(image_type, [])


class MyConversableAgent(autogen.ConversableAgent):
    async def a_get_human_input(self, prompt: str) -> str:
        start_time = time.time()
        set_chat_status("inputting")
        while True:
            if not user_queue.empty():
                (input_value, image) = user_queue.get()

                set_chat_status("Chat ongoing")
                if image == None:
                    return input_value

                ans = await upload_image_to_autogen(client, image)

                data1 = json.loads(ans)
                content = data1["content"]
                print("result 2:::xs", data1["content"])

                # images['url']=uploaded_image
                # # payload={}
                # # payload['type']="text" if uploaded_image is None else "image",
                # # payload['message']=input_value
                # # payload['image']=uploaded_image
                # inputstr = input_value + uploaded_image if uploaded_image else input_value
                # payload = {
                #     "type": "string",
                #     "content": input_value,
                #     "image": None if uploaded_image is  None else uploaded_image
                # }
                print("input message: ", input_value, content)
                return input_value + "|" + content

            if time.time() - start_time > 600:
                set_chat_status("ended")
                return "exit"

            await asyncio.sleep(1)


def my_message_generator():
    manual_data_path = "./manual_data.json"
    data = load_manual_data(manual_data_path)

    return f"""You are a customer service AI bot with two specialized agents:
    1. Order Status Agent - Handles:
       - Product defects (Refund for tears/damage, Replace for water damage)
       - Shipping box damage (Refund for severe damage, Replace for minor damage)
       
    2. Fraud Detection Agent - Handles:
       - Fraudulent transactions (Refund for unauthorized/suspicious charges)
       - Credit card issues (Refund for incorrect amounts)
       
    Base your responses on the provided data: {data}
    
    For product queries:
    - Request order number and image
    - Analyze damage type and severity
    - Make clear decisions: Refund, Replace, or Escalate
    
    For fraud queries:
    - Request transaction details
    - Analyze for suspicious patterns
    - Make clear decisions: Refund, Decline, or Escalate
    """


async def initiate_chat(userproxy, manager, assistants):
    """Initialize the chat with a greeting"""
    try:
        # Send initial greeting
        response = await manager.groupchat.send(
            message="Hello! How can I assist you today?",
            sender=assistants[0],  # Use first assistant for greeting
        )

        # Add response to print queue
        print_queue.put(
            {
                "user": response.get("name", "System"),
                "message": response.get(
                    "content", "Hello! How can I assist you today?"
                ),
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    except Exception as e:
        print(f"Error initializing chat: {e}")
        raise


def run_chat(request_json):
    try:
        userproxy = create_userproxy()
        analyze_intent, agents = create_groupchat(userproxy)

        while True:
            if not user_queue.empty():
                message, image = user_queue.get()

                # Add user message to print queue
                print_queue.put(
                    {
                        "user": "User",
                        "message": message,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )

                # Get appropriate agent
                selected_agent = analyze_intent(message)

                # Get response from agent
                response = selected_agent.initiate_chat(
                    message=message, recipient=userproxy
                )

                # Add response to print queue
                print_queue.put(
                    {
                        "user": selected_agent.name,
                        "message": response,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )

            time.sleep(1)

    except Exception as e:
        set_chat_status("error")
        print_queue.put({"user": "System", "message": f"An error occurred: {str(e)}"})


def create_userproxy():
    user_proxy = MyConversableAgent(
        name="User_Proxy",
        code_execution_config=False,
        is_termination_msg=lambda msg: "TERMINATE" in msg["content"],
        human_input_mode="ALWAYS",
    )
    user_proxy.register_reply(
        [autogen.Agent, None],
        reply_func=print_messages,
        config={"callback": None},
    )
    return user_proxy
