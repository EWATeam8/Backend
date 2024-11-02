from autogen import AssistantAgent
from autogen.agentchat.contrib.gpt_assistant_agent import GPTAssistantAgent

import autogen
import time
import asyncio

import os
import time
import asyncio
import threading
import json
import autogen  # type: ignore
from flask import Flask, request, jsonify  # type: ignore
from flask_cors import CORS

# aditya changes
from autogen.agentchat.contrib.gpt_assistant_agent import GPTAssistantAgent
from autogen.agentchat import AssistantAgent, UserProxyAgent
import queue
import openai
from transformers import GPT2Tokenizer, GPT2LMHeadModel, Trainer, TrainingArguments
from datasets import Dataset
from openai import OpenAI
from openai.types.chat import ChatCompletion

app = Flask(__name__)
cors = CORS(app)

# aditya changes
instructionOrderStatus = """You are a customer service assistant for a delivery service. 
Follow this exact workflow:
1. When user asks about order status, ask for their order number
2. After receiving order number, ask for an image of the package
3. Once image is received, analyze it and categorize as:
   - Refund: if package shows tears/damage : WE PRIORITIZE CUSTOMER OBSESSION & CUSTOMER IS ALWAYS RIGHT
   - Replace: if package appears wet
   - Escalate: if package looks normal or unclear
You must always use the provided tools for analysis.
REMEMBER DO NOT HALLUCINATE. IF YOU ARE UNSURE PLEASE ASK FOR FURTHER INFORMATION BEFORE TAKING ANY DECISION.  """

from app.globals import user_queue, print_queue, set_chat_status


# aditya changes
config_list = [{"model": "gpt-4o-mini", "api_key": os.environ.get("OPENAI_API_KEY")}]

llm_config22 = {
    "request_timeout": 600,
    "seed": 42,
    "config_list": config_list,
    "temperature": 0,
}

# aditya changes
client = OpenAI(
    # This is the default and can be omitted
    api_key=os.environ.get("OPENAI_API_KEY"),
)


def load_manual_data(json_file):
    with open(json_file, "r", encoding="utf-8") as file:
        return file.read()


class MyConversableAgent(autogen.ConversableAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state = "initial"
        self.order_number = None

    async def a_get_human_input(self, prompt: str) -> str:
        start_time = time.time()
        set_chat_status("inputting")

        while True:
            if not user_queue.empty():
                (input_value, image) = user_queue.get()
                set_chat_status("Chat ongoing")

                # Handle the order status workflow
                if self.state == "initial":
                    if (
                        "status" in input_value.lower()
                        and "order" in input_value.lower()
                    ):
                        self.state = "waiting_for_order"
                        return "Please provide your order number."
                    return input_value

                elif self.state == "waiting_for_order":
                    self.order_number = input_value
                    self.state = "waiting_for_image"
                    return "Thank you. Please provide an image of your package."

                elif self.state == "waiting_for_image":
                    self.state = "initial"  # Reset state
                    if image:
                        ans = await upload_image_to_autogen(image)
                        if ans:
                            data1 = json.loads(ans)
                            content = data1["content"]
                            return input_value + "|" + content
                    return "Sorry, I couldn't process the image. Please try again."

                return input_value

            if time.time() - start_time > 600:
                set_chat_status("ended")
                return "exit"

            await asyncio.sleep(1)


def print_messages(recipient, messages, sender, config):
    print(
        f"Messages from: {sender.name} sent to: {recipient.name} | num messages: {len(messages)} | message: {messages[-1]}"
    )

    content = messages[-1]["content"].split("|")[0]  # aditya changes

    if all(key in messages[-1] for key in ["name"]):
        print_queue.put({"user": messages[-1]["name"], "message": content})
    elif messages[-1]["role"] == "user":
        print_queue.put({"user": sender.name, "message": content})
    else:
        print_queue.put({"user": recipient.name, "message": content})

    return False, None


# aditya changes
async def upload_image_to_autogen(base64_image):
    print("Processing base64 image")
    if base64_image == None:
        return ""

    try:
        # Make the API call to OpenAI's chat completion with base64 image
        response = client.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "assistant",
                    "content": instructionOrderStatus,
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            },
                        },
                    ],
                },
            ],
            functions=[
                {
                    "name": "refund_order",
                    "description": "Refund an order if product is damaged",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "rationale": {"type": "string"},
                            "image_description": {"type": "string"},
                            "action": {"type": "string"},
                            "content": {
                                "type": "string",
                                "description": "Mention the package/product is proceeded for refund due to damage",
                            },
                            "decision": {
                                "type": "string",
                                "description": "Decide the condition of package",
                            },
                        },
                        "required": [
                            "rationale",
                            "image_description",
                            "action",
                            "content",
                            "decision",
                        ],
                    },
                },
                {
                    "name": "replace_order",
                    "description": "Replace an order",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "rationale": {"type": "string"},
                            "image_description": {"type": "string"},
                            "action": {"type": "string"},
                            "content": {
                                "type": "string",
                                "description": "Mention the package/product is proceeded for replacement due to logistic issues like wetness, erroneous delivery, etc.",
                            },
                            "decision": {
                                "type": "string",
                                "description": "Decide the condition of package",
                            },
                        },
                        "required": [
                            "rationale",
                            "image_description",
                            "action",
                            "content",
                            "decision",
                        ],
                    },
                },
                {
                    "name": "escalate_to_agent",
                    "description": "Escalate to agent",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "rationale": {"type": "string"},
                            "image_description": {"type": "string"},
                            "action": {"type": "string"},
                            "content": {
                                "type": "string",
                                "description": "If the image is not related to product or parcel, give control to humans, otherwise mention the package is normal and may provide customer care support for further details.",
                            },
                            "decision": {
                                "type": "string",
                                "description": "Decide the condition of the package or tell it is not a parcel",
                            },
                        },
                        "required": [
                            "rationale",
                            "image_description",
                            "action",
                            "content",
                            "decision",
                        ],
                    },
                },
                {
                    "name": "refund_payment",
                    "description": "Refund a payment if Order Number is missing, Last Name is missing/invalid, or Credit Card last 4 digist is missing from the copy. Mention which part is missing",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "rationale": {"type": "string"},
                            "image_description": {"type": "string"},
                            "action": {"type": "string"},
                            "content": {
                                "type": "string",
                                "description": "Mention the transaction is proceeded for refund",
                            },
                            "decision": {
                                "type": "string",
                                "description": "Decide the condition of transaction",
                            },
                        },
                        "required": [
                            "rationale",
                            "image_description",
                            "action",
                            "content",
                            "decision",
                        ],
                    },
                },
                {
                    "name": "decline_transaction",
                    "description": "Decline an transaction",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "rationale": {"type": "string"},
                            "image_description": {"type": "string"},
                            "action": {"type": "string"},
                            "content": {
                                "type": "string",
                                "description": "Mention the transaction/payment cannot be declined as transaction was having normal/valid charges, noraml trnasaction, no hiddencost and correct details",
                            },
                            "decision": {
                                "type": "string",
                                "description": "Decide the condition of transaction",
                            },
                        },
                        "required": [
                            "rationale",
                            "image_description",
                            "action",
                            "content",
                            "decision",
                        ],
                    },
                },
                {
                    "name": "escalate_to_human",
                    "description": "Escalate to human",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "rationale": {"type": "string"},
                            "image_description": {"type": "string"},
                            "action": {"type": "string"},
                            "content": {
                                "type": "string",
                                "description": "If the image is not related to transaction or payment, contains unknown query, unwanted query, or different discussion give control to humans",
                            },
                            "decision": {
                                "type": "string",
                                "description": "Decide the condition of the transaction",
                            },
                        },
                        "required": [
                            "rationale",
                            "image_description",
                            "action",
                            "content",
                            "decision",
                        ],
                    },
                },
            ],
            max_tokens=100,
            temperature=0.2,
        )

        # Log the response
        print("response::::", response.choices[0].message.function_call.arguments)

        # Return the response message
        return response.choices[0].message.function_call.arguments

    except Exception as e:
        print(f"Error occurred: {e}")
        return None


def my_message_generator():
    manual_data_path = "./manual_data.json"

    data = load_manual_data(manual_data_path)

    # return "You are a recommendation AI bot. Train your responses based on the data provided. When user ask about product give within recommended data.   \n Data: \n" + data
    return f"""You are a recommendation AI bot with two assistant agents. Order status and Fraud Detection. 
        Train your responses based on the data provided.
        When user ask about product recommendation, give within recommendation data of {data}.   
        When user ask about product/parcel order status, ask for ordernumber and then give responses within orderstatus data of {data}.   
        When user ask about product/parcel transaction/payment status, give responses within fraudTransaction data of {data}.   
        Judge your answers, based on recommendation, order status and fraud keywords.
        """


async def initiate_chat(agent, recipient, assistants, image=None):
    # print('inside initiate chat', my_message_generator())
    result = await agent.a_initiate_chat(
        recipient, assistants, message=my_message_generator()
    )
    return result


def run_chat(request_json):
    manager = None
    assistants = []
    try:
        agents_info = request_json.get("agents_info")
        task_info = request_json.get("task_info")
        userproxy = create_userproxy()
        manager, assistants = create_groupchat(agents_info, task_info, userproxy)
        asyncio.run(initiate_chat(userproxy, manager, assistants))

        set_chat_status("ended")

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


agent_classes = {
    "GPTAssistantAgent": GPTAssistantAgent,
    "AssistantAgent": AssistantAgent,
}


def create_groupchat(agents_info, task_info, user_proxy):
    # assistants = []
    agent_a = GPTAssistantAgent(
        name="Order Status Agent",
        instructions="""you are a customer service order status agent for a deliver service, equipped to analyze delivery of packages and products. if the package/product appears damaged with tears, proceed for refund. if the package/product looks wet, initiate a replacement. if the package/product looks normal and not damaged, escalte to agent. for unclear queries and images, escalte to agent. you must always use tools""",
        llm_config=llm_config22,
    )
    agent_b = GPTAssistantAgent(
        name="Fraud Detection Agent",
        instructions="""you are a customer service fraud detection agent for a deliver service, equipped to analyze fraud in transaction of packages/products. If the transaction appears suspicious/fraud, proceed for refund. If the transaction looks normal, decline the request. For unwanted queries, escalate to the agent. you must always use tools""",
        llm_config=llm_config22,
    )

    # assistants = [agent_a, agent_b]
    assistants = []

    for agent_info in agents_info:
        if agent_info["type"] == "UserProxyAgent":
            continue

        llm_config = {
            "config_list": [agent_info["llm"]],
            "temperature": 0,
        }

        AgentClass = agent_classes[agent_info["type"]]
        assistant = AgentClass(
            name=agent_info["name"],
            llm_config=llm_config,
            system_message=agent_info["system_message"],
            description=agent_info["description"],
        )

        assistant.register_reply(
            [autogen.Agent, None],
            reply_func=print_messages,
            config={"callback": None},
        )
        assistants.append(assistant)

    if len(assistants) == 1:
        manager = assistants[0]

    elif len(assistants) > 1:
        groupchat = autogen.GroupChat(
            agents=[user_proxy] + assistants,
            messages=[],
            max_round=task_info["maxMessages"],
            speaker_selection_method=task_info["speakSelMode"],
        )
        manager = autogen.GroupChatManager(
            groupchat=groupchat,
            llm_config=llm_config22,
            system_message="",
        )

    return manager, assistants
