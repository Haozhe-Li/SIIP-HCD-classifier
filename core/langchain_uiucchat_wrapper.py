from typing import Any, List, Optional, Type, Union, Dict
import os
import copy
import requests
import dotenv

from langchain_core.language_models.chat_models import SimpleChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import Runnable, RunnableLambda
from pydantic import BaseModel

dotenv.load_dotenv()


class IllinoisChatLLM(SimpleChatModel):
    """LangChain wrapper for UIUC Illinois Chat API."""

    api_key: str = os.getenv("UIUC_CHAT_API_KEY")
    course_name: str
    model: str = "Qwen/Qwen2.5-VL-72B-Instruct"
    temperature: float = 0.1
    base_url: str = "https://chat.illinois.edu/api/chat-api/chat"
    system_prompt: str = (
        "You are a helpful AI assistant. Follow instructions carefully."
    )

    @property
    def _llm_type(self) -> str:
        return "illinois_chat"

    def _call(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> str:
        api_messages = []
        has_system_prompt = False

        for m in messages:
            if m.type == "system":
                api_messages.append({"role": "system", "content": m.content})
                has_system_prompt = True
            elif m.type == "user":
                api_messages.append({"role": "user", "content": m.content})
            elif m.type == "ai":
                api_messages.append({"role": "assistant", "content": m.content})
            else:
                api_messages.append({"role": "user", "content": m.content})

        if not has_system_prompt and self.system_prompt:
            api_messages.insert(0, {"role": "system", "content": self.system_prompt})

        data = {
            "model": self.model,
            "messages": api_messages,
            "api_key": self.api_key,
            "course_name": self.course_name,
            "stream": False,
            "temperature": self.temperature,
            "retrieval_only": False,
        }

        response = requests.post(
            self.base_url, headers={"Content-Type": "application/json"}, json=data
        )
        response.raise_for_status()
        return response.json().get("message", "")

    @property
    def _identifying_params(self) -> dict:
        return {"model": self.model, "course_name": self.course_name}

    def with_structured_output(
        self,
        schema: Union[Dict, Type[BaseModel]],
        *,
        include_raw: bool = False,
        **kwargs: Any,
    ) -> Runnable:
        """Adds structured output capability to the model."""
        from langchain_core.output_parsers import PydanticOutputParser

        if not (isinstance(schema, type) and issubclass(schema, BaseModel)):
            raise ValueError(
                "Currently only Pydantic BaseModel is supported as schema."
            )

        parser = PydanticOutputParser(pydantic_object=schema)

        def _inject_instructions(messages: Any) -> List[BaseMessage]:
            # Normalize input to List[BaseMessage]
            if isinstance(messages, str):
                new_messages = [HumanMessage(content=messages)]
            elif isinstance(messages, list):
                new_messages = []
                for m in messages:
                    if isinstance(m, BaseMessage):
                        new_messages.append(copy.deepcopy(m))
                    elif isinstance(m, dict):
                        role = m.get("role", "user")
                        content = m.get("content", "")
                        if role == "system":
                            new_messages.append(SystemMessage(content=content))
                        else:
                            new_messages.append(HumanMessage(content=content))
                    else:
                        new_messages.append(HumanMessage(content=str(m)))
            else:
                new_messages = [HumanMessage(content=str(messages))]

            instructions = parser.get_format_instructions()

            # Find the last human message to append instructions
            for i in range(len(new_messages) - 1, -1, -1):
                if isinstance(new_messages[i], HumanMessage):
                    new_messages[i].content = (
                        str(new_messages[i].content)
                        + "\n\nCRITICAL: You MUST strictly output ONLY valid JSON following the schema below. DO NOT output markdown tables or text.\n"
                        + instructions
                    )
                    return new_messages

            # Fallback: append as system message if no human message exists
            new_messages.append(
                SystemMessage(
                    content="CRITICAL: You MUST strictly output ONLY valid JSON following the schema below. DO NOT output markdown tables or text.\n"
                    + instructions
                )
            )
            return new_messages

        return RunnableLambda(_inject_instructions) | self | parser
