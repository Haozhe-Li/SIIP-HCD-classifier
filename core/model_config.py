from langchain.chat_models import init_chat_model
from core.langchain_uiucchat_wrapper import IllinoisChatLLM

UIUC_CHAT_MODEL = IllinoisChatLLM(
    course_name="matse", model="Qwen/Qwen2.5-VL-72B-Instruct"
)

OPENAI_MODEL = init_chat_model("openai:gpt-5.6-luna")

# point all below to OPENAI_MODEL (was UIUC_CHAT_MODEL)
DEFAULT_MODEL = OPENAI_MODEL
PARSING_MODEL = OPENAI_MODEL
FINAL_EVAL_MODEL = OPENAI_MODEL
