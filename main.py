"""Example showcasing how to use the Unofficial Claude API"""
import os
import pprint
import time

from enum import Enum
from typing import Dict, Any

from dotenv import load_dotenv


# The ClaudeClient is the raw API that gives you access to all organization and conversation level API calls
# with a simple python interface. However, you have to pass organization_uuid and conversation_uuid everywhere, so
# its not ideal if you want a simple to use API.
from claude import claude_client, constants

# The ClaudeWrapper takes in a claude client instance and allows you to use a single organization and conversation
# context. This allows you to use the API more ergonomically.
from claude import claude_wrapper

# session key is stored in .env file for the sake of example.
load_dotenv()
SESSION_KEY = str(os.environ.get("SESSION_KEY"))

class ClaudeVersions(Enum):
    opus     = "claude-3-opus-20240229"  # Most intelligent model (Mar 2024)
    haiku   = "claude-3-haiku-20240307"  # Fastest (Mar 2024)
    sonnet  = "claude-3-sonnet-20240229"  # Efficient combination of speed and skills (Mar 2024)
    instant  = "claude-instant-1.2"
    _2_1 = "claude-2.1"
    _2_0 = "claude-2.0"

    def __repr__(self):
        return self.value

    def __str__(self):
        return self.value

    def to_json(self) -> Any:
        return self.value

class ClaudeInstance:
    def __init__(self, data: Dict[str, Any], claude_obj) -> None:
        self.uuid = data['uuid']
        self.claude_obj = claude_obj
        self.model = data['response']['model']
        self.history = [data]

    def send_message(self, message: str = None, model: ClaudeVersions = "") -> Dict:
        target_model = model if model != "" else self.model
        resp = self.claude_obj.send_message(message, conversation_uuid=self.uuid, model=target_model)
        self.history.append(resp)
        return {
            "completion": resp['completion'],
            "stop_reason": resp['stop_reason'],
        }
    def get_message(self):
        try:
            data = self.history[-1]
            if len(self.history) == 1:
                return {
                    "completion": data['response']['completion'],
                    "stop_reason": data['response']['stop_reason'],
                    "model": data['response']['model'],
                }
            else:
                return {
                    "completion": data['completion'],
                    "stop_reason": data['stop_reason'],
                    "model": data['model'],
                }
        except:
            raise ValueError("Can not get the message history.")

class ClaudeManager:
    def __init__(self, SESSION_KEY: str = "") -> None:
        self.instance = {}
        self.client = claude_client.ClaudeClient(SESSION_KEY)
        self.organizations = self.client.get_organizations()
        self.claude_obj = claude_wrapper.ClaudeWrapper(self.client, self.organizations[0]['uuid'])

    def CreateSession(self, message: str = "Hi", model: ClaudeVersions = ClaudeVersions.opus) -> None:
        chat = self.claude_obj.start_new_conversation(
            "New Conversation",
            message,
            model=model.to_json(),
        )
        uuid = chat['uuid']
        self.instance[uuid] = ClaudeInstance(chat, self.claude_obj)
        return self.instance[uuid]

if __name__ == "__main__":
    manager = ClaudeManager(SESSION_KEY)
    session = manager.CreateSession(message="Hello, my name is Wilson.")
    print("First", session.get_message())
    resp = session.send_message("請問我叫什麼名字？")
    print("Second", resp)