import threading

from flask import Blueprint, jsonify, request

from app.services.ai_model import print_queue, user_queue, run_chat
from app.globals import set_chat_status, get_chat_status

main = Blueprint("main", __name__)


@main.route("/api/start_chat", methods=["POST", "OPTIONS"])
def start_chat():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    elif request.method == "POST":
        try:
            if get_chat_status() == "error":
                set_chat_status("ended")

            with print_queue.mutex:
                print_queue.queue.clear()
            with user_queue.mutex:
                user_queue.queue.clear()

            set_chat_status("Chat started")

            thread = threading.Thread(target=run_chat, args=(request.json,))
            thread.start()

            return jsonify({"status": get_chat_status()})
        except Exception as e:
            return jsonify({"status": "Error occurred", "error": str(e)})


@main.route("/api/send_message", methods=["POST"])
def send_message():
    try:
        uploaded_image = request.json.get("image", None)
        message = request.json.get("message", "")
        print((message, uploaded_image))
        user_queue.put((message, uploaded_image))

        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@main.route("/api/get_message", methods=["GET"])
def get_messages():
    if not print_queue.empty():
        msg = print_queue.get()
        return jsonify({"message": msg, "chat_status": get_chat_status()}), 200
    else:
        return jsonify({"message": None, "chat_status": get_chat_status()}), 200
