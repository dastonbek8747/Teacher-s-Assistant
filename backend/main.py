# from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import uvicorn
from dark_swag import FastAPI
from backend.graph.nodes import chat_techflow_ai

app = FastAPI()
app.mount("/creating_files", StaticFiles(directory="./creating_files"), name="creating_files")


@app.get("/")
def index():
    return {"Hello": "World"}


@app.post("/chat")
async def chat(request):
    pass


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
