import queue

chat_status = "started"

def update_chat_status(status: str):
    global chat_status
    chat_status = status


print_queue = queue.Queue()
user_queue = queue.Queue()