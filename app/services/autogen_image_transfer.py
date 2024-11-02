# aditya changes
instructionOrderStatus = """you are a customer service assitant for a deliver service, equipped to analyze delivery of packages/products and detect fraud transactions. 
        If the package appears damaged with tears, proceed for refund. if the package looks wet, initiate a replacement. if the package looks normal and not damaged, escalte to agent. for unclear queries and images, escalte to agent. 
        If the transaction appears suspicious/fraud, proceed for refund. If the transaction looks normal, decline the request. For unwanted queries, escalate to the agent. you must always use tools"""


# aditya changes
async def upload_image_to_autogen(client, image):
    print("insideeeeee")
    if image == None:
        return ""
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "assistant",
                    "content": instructionOrderStatus,
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": image}},
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
