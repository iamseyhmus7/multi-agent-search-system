from fastapi import FastAPI
from services.agent_service import run_agent

app = FastAPI()

@app.post("/chat")
async def chat(payload: dict):
    user_input = payload.get("message")
    # run_agent artık async olduğu için await eklemeliyiz
    answer = await run_agent(user_input) 
    return {"response": answer}
