from flask import Blueprint, jsonify, request

main = Blueprint("main", __name__)


@main.route("/api/train", methods=["POST", "OPTIONS"])
def train_agent():
    manual_data_path = "./manual_data.json"
    try:
        train_autogen_agent(manual_data_path)
        return jsonify({"status": "Training completed!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main.route("/api/start_chat", methods=["POST", "OPTIONS"])
def start_chat():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    elif request.method == "POST":
        global chat_status
        try:

            if chat_status == "error":
                chat_status = "ended"

            with print_queue.mutex:
                print_queue.queue.clear()
            with user_queue.mutex:
                user_queue.queue.clear()

            chat_status = "Chat started"

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
    global chat_status

    if not print_queue.empty():
        msg = print_queue.get()
        return jsonify({"message": msg, "chat_status": chat_status}), 200
    else:
        return jsonify({"message": None, "chat_status": chat_status}), 200
