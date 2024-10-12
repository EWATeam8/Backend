from autogen import AssistantAgent
from autogen.agentchat.contrib.gpt_assistant_agent import GPTAssistantAgent

import autogen
import time
import asyncio
import queue

from app.services.train_model import load_manual_data
from app.globals import chat_status

chat_status = chat_status

print_queue = queue.Queue()
user_queue = queue.Queue()

class MyConversableAgent(autogen.ConversableAgent):
    async def a_get_human_input(self, prompt: str) -> str:
        start_time = time.time()
        global chat_status
        chat_status = "inputting"
        while True:
            if not user_queue.empty():
                input_value = user_queue.get()
                chat_status = "Chat ongoing"
                print("input message: ", input_value)
                return input_value

            if time.time() - start_time > 600:
                chat_status = "ended"
                return "exit"

            await asyncio.sleep(1)


def print_messages(recipient, messages, sender, config):
    print(
        f"Messages from: {sender.name} sent to: {recipient.name} | num messages: {len(messages)} | message: {messages[-1]}"
    )

    content = messages[-1]["content"]

    if all(key in messages[-1] for key in ["name"]):
        print_queue.put({"user": messages[-1]["name"], "message": content})
    elif messages[-1]["role"] == "user":
        print_queue.put({"user": sender.name, "message": content})
    else:
        print_queue.put({"user": recipient.name, "message": content})

    return False, None


def my_message_generator():
    manual_data_path = './manual_data.json'

    data = load_manual_data(manual_data_path)

    return "You are a recommendation AI bot. Train your responses based on the data provided. When user ask about product give within recommended data.   \n Data: \n" + data


async def initiate_chat(agent, recipient):
    result = await agent.a_initiate_chat(
        recipient,
        message=my_message_generator(),
        clear_history=False
    )

    return result


def run_chat(request_json):
    global chat_status
    manager = None
    assistants = []
    try:
        agents_info = request_json.get("agents_info")
        task_info = request_json.get("task_info")
        userproxy = create_userproxy()
        manager, assistants = create_groupchat(agents_info, task_info, userproxy)
        asyncio.run(initiate_chat(userproxy, manager))

        chat_status = "ended"

    except Exception as e:
        chat_status = "error"
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
            llm_config=llm_config,
            system_message="",
        )

    return manager, assistants
