# AutoParts Backend

## Overview

This is the backend service for a manufacturer chat application. It uses Python with Flask to create an API that integrates AutoGen for conversational AI, Rasa for natural language understanding, and fine-tuned transformers for enhanced language processing.

## Tech Stack

- Python
- Flask
- Rasa
- AutoGen
- Fine-tuning with Transformers

## Project Structure
│
├── app/
│ ├── init.py
│ ├── routes.py
│ ├── models/
│ │ └── product.py
│ └── services/
│ ├── ai_model.py
│ └── train_model.py
│
├── manual_data.json
├── requirements.txt
├── config.py
└── run.py

## Key Components

1. **routes.py**: Contains API endpoints for training, starting chats, sending messages, and retrieving messages.
2. **models/product.py**: Defines the Product model.
3. **services/ai_model.py**: Implements the AutoGen-based chat functionality.
4. **services/train_model.py**: Handles the fine-tuning of the language model.


## API Endpoints

- `POST /api/train`: Train the AutoGen agent
- `POST /api/start_chat`: Initiate a new chat session
- `POST /api/send_message`: Send a user message to the chat
- `GET /api/get_message`: Retrieve messages from the chat

## Fine-Tuning

The `train_model.py` script handles fine-tuning of the GPT-2 model using the Transformers library. To run the fine-tuning process:
python -m app.services.train_model


This will use the data in `manual_data.json` to fine-tune the model.

## AutoGen Integration

The `ai_model.py` file integrates AutoGen to create a conversational AI system. It sets up multiple agents, including a user proxy and AI assistants, to handle complex conversations.

## Chat Flow

1. The chat is initiated via the `/api/start_chat` endpoint.
2. User messages are sent through `/api/send_message`.
3. The AutoGen system processes these messages and generates responses.
4. Responses can be retrieved using `/api/get_message`.