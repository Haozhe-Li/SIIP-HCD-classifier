from langchain.chat_models import init_chat_model
from core.langchain_uiucchat_wrapper import IllinoisChatLLM

UIUC_CHAT_MODEL = IllinoisChatLLM(
    course_name="matse", model="Qwen/Qwen2.5-VL-72B-Instruct"
)

# DEFAULT_MODEL = init_chat_model("openai:gpt-4.1")
# PARSING_MODEL = init_chat_model("gpt-5-nano-2025-08-07")
# FINAL_EVAL_MODEL = init_chat_model("openai:gpt-4.1")

# point all above to UIUC_CHAT_MODEL
DEFAULT_MODEL = UIUC_CHAT_MODEL
PARSING_MODEL = UIUC_CHAT_MODEL
FINAL_EVAL_MODEL = UIUC_CHAT_MODEL
