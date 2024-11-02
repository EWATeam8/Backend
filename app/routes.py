import threading
import os

from flask import Blueprint, jsonify, request
from openai import OpenAI, OpenAIError, AuthenticationError


from app.services.ai_model import (
    print_queue,
    user_queue,
    run_chat,
    create_userproxy,
    create_groupchat,
    initiate_chat,
)
import asyncio

from app.globals import set_chat_status, get_chat_status

from datetime import datetime
from .database import db
from bson import ObjectId


orders_collection = db.orders

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
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400

        # Get message (required)
        if "message" not in request.json:
            return jsonify({"error": "Message is required"}), 400

        user_input = request.json["message"]

        # Get image (optional) using .get()
        uploaded_image = request.json.get("image", None)

        print(f"Received message: {user_input}")
        print(f"Image provided: {'Yes' if uploaded_image else 'No'}")

        # Add user message to print queue for immediate display
        print_queue.put(
            {
                "user": "User",
                "message": user_input,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        # Put in queue for processing
        user_queue.put((user_input, uploaded_image))

        return jsonify(
            {
                "status": "success",
                "message": "Message received",
                "has_image": uploaded_image is not None,
            }
        )

    except Exception as e:
        print(f"Error in send_message: {str(e)}")
        return (
            jsonify({"status": "error", "error": f"An error occurred: {str(e)}"}),
            500,
        )


@main.route("/api/get_message", methods=["GET"])
def get_messages():
    try:
        messages = []
        chat_status = get_chat_status()

        # Get all available messages from the queue
        while not print_queue.empty():
            msg = print_queue.get()
            if msg:
                # Add timestamp if not present
                if "timestamp" not in msg:
                    msg["timestamp"] = datetime.utcnow().isoformat()
                messages.append(msg)

        # If we have messages, return them
        if messages:
            return (
                jsonify(
                    {
                        "status": "success",
                        "chat_status": chat_status,
                        "messages": messages,
                    }
                ),
                200,
            )

        # If chat is ongoing but no messages, return appropriate status
        if chat_status in ["Chat ongoing", "inputting"]:
            return (
                jsonify(
                    {"status": "pending", "chat_status": chat_status, "messages": []}
                ),
                200,
            )

        # If chat has ended or errored with no messages
        return (
            jsonify({"status": "complete", "chat_status": chat_status, "messages": []}),
            200,
        )

    except Exception as e:
        print(f"Error in get_messages: {str(e)}")
        return (
            jsonify(
                {
                    "status": "error",
                    "chat_status": "error",
                    "error": f"An error occurred: {str(e)}",
                    "messages": [],
                }
            ),
            500,
        )


@main.route("/api/orders", methods=["POST"])
def create_order():
    try:
        order_data = request.json

        required_fields = [
            "order_number",
            "first_name",
            "last_name",
            "product_details",
            "credit_card_number",
        ]
        for field in required_fields:
            if field not in order_data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        order_data["created_at"] = datetime.utcnow()

        card_number = order_data["credit_card_number"]
        order_data["credit_card_number"] = "XXXX-XXXX-XXXX-" + card_number[-4:]

        quantity = order_data["product_details"].get("quantity", 1)
        unit_cost = order_data["product_details"].get("cost", 0)
        order_data["total_cost"] = quantity * unit_cost

        result = orders_collection.insert_one(order_data)

        return (
            jsonify(
                {
                    "status": "success",
                    "message": "Order created successfully",
                    "order_id": str(result.inserted_id),
                }
            ),
            201,
        )

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@main.route("/api/orders/<order_number>", methods=["GET"])
def get_order(order_number):
    try:
        order = orders_collection.find_one({"order_number": order_number}, {"_id": 0})
        if not order:
            return jsonify({"error": "Order not found"}), 404

        return jsonify(order), 200

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@main.route("/api/orders", methods=["GET"])
def get_all_orders():
    try:
        print(orders_collection)
        orders = list(orders_collection.find())

        return jsonify({"total_orders": len(orders), "orders": orders}), 200

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@main.route("/api/orders/<order_number>", methods=["PUT"])
def update_order(order_number):
    try:
        update_data = request.json

        update_data.pop("order_number", None)
        update_data.pop("credit_card_number", None)

        update_data["updated_at"] = datetime.utcnow()

        result = orders_collection.update_one(
            {"order_number": order_number}, {"$set": update_data}
        )

        if result.matched_count == 0:
            return jsonify({"error": "Order not found"}), 404

        return (
            jsonify({"status": "success", "message": "Order updated successfully"}),
            200,
        )

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


# TEST CASES
@main.route("/api/test/order-status", methods=["POST"])
def test_order_status():
    try:
        # Verify OpenAI API key first
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return (
                jsonify(
                    {
                        "status": "error",
                        "error": "OpenAI API key not found in environment variables",
                    }
                ),
                401,
            )

        # Initialize OpenAI client
        client = OpenAI(api_key=api_key)

        # Test message with order status scenario
        test_message = {
            "message": "I received my package with order number ORD-001 and it's damaged. The box has tears and the product inside is broken.",
            "image": "https://m.media-amazon.com/images/I/81Ns5JPE5VL.jpg",
        }

        # Create test user proxy and agents
        userproxy = create_userproxy()
        manager, assistants = create_groupchat(userproxy)

        # Clear existing queues
        with user_queue.mutex:
            user_queue.queue.clear()
        with print_queue.mutex:
            print_queue.queue.clear()

        # Put test message in queue
        user_queue.put((test_message["message"], test_message["image"]))

        # Run the chat
        asyncio.run(initiate_chat(userproxy, manager, assistants))

        # Collect responses
        responses = []
        while not print_queue.empty():
            response = print_queue.get()
            responses.append(response)

        return jsonify(
            {"status": "success", "test_message": test_message, "responses": responses}
        )

    except AuthenticationError as e:
        return (
            jsonify({"status": "error", "error": f"Authentication error: {str(e)}"}),
            401,
        )
    except OpenAIError as e:
        return jsonify({"status": "error", "error": f"OpenAI API error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@main.route("/api/test/agent-status", methods=["GET"])
def test_agent_status():
    try:
        # Verify OpenAI API key
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return (
                jsonify({"status": "error", "error": "OpenAI API key not found"}),
                401,
            )

        # Create test agents
        userproxy = create_userproxy()
        manager, assistants = create_groupchat(userproxy)

        return jsonify(
            {
                "status": "success",
                "agents": {
                    "order_status_agent": {
                        "name": assistants[0].name,
                        "status": "initialized",
                        "type": "Order Status Agent",
                    },
                    "fraud_detection_agent": {
                        "name": assistants[1].name,
                        "status": "initialized",
                        "type": "Fraud Detection Agent",
                    },
                },
            }
        )

    except AuthenticationError as e:
        return (
            jsonify({"status": "error", "error": f"Authentication error: {str(e)}"}),
            401,
        )
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@main.route("/api/test/fraud-detection", methods=["POST"])
def test_fraud_detection():
    try:
        test_message = {
            "message": "I found an unauthorized transaction on my credit card for order ORD-002",
            "image": None,
        }

        # Create test user proxy and agents
        userproxy = create_userproxy()
        manager, assistants = create_groupchat(userproxy)

        # Simulate message processing
        user_queue.put((test_message["message"], test_message["image"]))

        # Run the chat
        asyncio.run(initiate_chat(userproxy, manager, assistants))

        # Get the response from print_queue
        responses = []
        while not print_queue.empty():
            response = print_queue.get()
            responses.append(response)

        return jsonify(
            {"status": "success", "test_message": test_message, "responses": responses}
        )

    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500
