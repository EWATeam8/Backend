from transformers import GPT2Tokenizer, GPT2LMHeadModel, Trainer, TrainingArguments
from datasets import Dataset


def load_manual_data(json_file):
    with open(json_file, "r", encoding="utf-8") as file:
        return file.read()


def format_data_for_training(data):
    conversations = []
    for item in data:
        user_input = item["user_input"]
        agent_response = item["agent_response"]
        conversation = f"User: {user_input}\nAgent: {agent_response}"
        conversations.append({"text": conversation})
    return conversations


def create_dataset(formatted_data):
    return Dataset.from_dict({"text": [d["text"] for d in formatted_data]})


def tokenize_function(example, tokenizer):
    tokenized_input = tokenizer(
        example["text"], padding="max_length", truncation=True, max_length=128
    )
    tokenized_input["labels"] = tokenized_input["input_ids"].copy()
    tokenized_input["labels"] = [
        -100 if token == tokenizer.pad_token_id else token
        for token in tokenized_input["labels"]
    ]
    return tokenized_input


def train_autogen_agent(manual_data_file):
    data = load_manual_data(manual_data_file)
    formatted_data = format_data_for_training(data)
    dataset = create_dataset(formatted_data)
    tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
    model = GPT2LMHeadModel.from_pretrained("gpt2")

    tokenizer.pad_token = tokenizer.eos_token
    tokenized_dataset = dataset.map(
        lambda x: tokenize_function(x, tokenizer), batched=True
    )

    training_args = TrainingArguments(
        output_dir="./autogen_agent",
        learning_rate=5e-5,
        per_device_train_batch_size=4,
        num_train_epochs=3,
        weight_decay=0.01,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset,
    )

    trainer.train()
    model.save_pretrained("../fine_tuned_autogen_agent")
    tokenizer.save_pretrained("../fine_tuned_autogen_agent")
    print("Model training completed and saved!")


if __name__ == "__main__":
    train_autogen_agent("../../fine_tuned_autogen_agent")
