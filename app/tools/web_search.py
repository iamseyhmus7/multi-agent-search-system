from tavily import TavilyClient
import os 
from dotenv import load_dotenv

load_dotenv()

tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
def search_web(query:str):
    response = tavily.search(
        query,
        search_depth="advanced",
        num_results=5)
    return response


    