import asyncio
from dotenv import load_dotenv
load_dotenv()
from core.langchain_uiucchat_wrapper import IllinoisChatLLM
from pydantic import BaseModel, Field

class Dummy(BaseModel):
    name: str = Field(..., description="A person's name")
    age: int = Field(..., description="A person's age")

llm = IllinoisChatLLM(course_name="matse")
bound = llm.with_structured_output(Dummy)

async def run():
    print("Invoking model...")
    res = await bound.ainvoke("Extract the person info: John is 25 years old.")
    print("Result:", res)

asyncio.run(run())
