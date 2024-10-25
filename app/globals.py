import queue

chat_status = "started"

def get_chat_status():
    global chat_status
    return chat_status

def set_chat_status(status: str):
    global chat_status
    chat_status = status

print_queue = queue.Queue()
user_queue = queue.Queue()