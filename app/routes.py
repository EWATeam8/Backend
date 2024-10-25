import threading

from flask import Blueprint, jsonify, request

from app.services.ai_model import print_queue, user_queue, run_chat
from app.globals import update_chat_status, chat_status

main = Blueprint("main", __name__)

@main.route("/api/start_chat", methods=["POST", "OPTIONS"])
def start_chat():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    elif request.method == "POST":
        try:
            if chat_status == "error":
                update_chat_status("ended")

            with print_queue.mutex:
                print_queue.queue.clear()
            with user_queue.mutex:
                user_queue.queue.clear()

            update_chat_status("Chat started")

            thread = threading.Thread(target=run_chat, args=(request.json,))
            thread.start()

            return jsonify({"status": chat_status})
        except Exception as e:
            return jsonify({"status": "Error occurred", "error": str(e)})


@main.route("/api/send_message", methods=["POST"])
def send_message():
    user_input = request.json["message"]
    user_queue.put(user_input)
    return jsonify({"status": "Message Received"})


@main.route("/api/get_message", methods=["GET"])
def get_messages():
    if not print_queue.empty():
        msg = print_queue.get()
        return jsonify({"message": msg, "chat_status": chat_status}), 200
    else:
        return jsonify({"message": None, "chat_status": chat_status}), 200
