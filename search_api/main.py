from fastapi import FastAPI, HTTPException, Query, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os, weaviate
from weaviate.classes.query import Rerank

bearer = HTTPBearer()
TOKEN  = os.getenv("BEARER_TOKEN")

def check(creds: HTTPAuthorizationCredentials = Security(bearer)):
    if creds.credentials != TOKEN:
        raise HTTPException(401, "Invalid token")

client = weaviate.Client(
    url=os.getenv("WEAVIATE_URL", "http://weaviate:8080"),
    additional_headers={"X-JinaAI-Api-Key": os.getenv("JINAAI_APIKEY")}
)

app = FastAPI()

@app.get("/search", dependencies=[Depends(check)])
def search(
    q: str = Query(..., description="search text"),
    limit: int = 10,
    alpha: float = 0.5,
    rerank_k: int = 50,
):
    coll = client.collections.get("FeedItem")
    res = coll.query.hybrid(
        query=q,
        limit=limit,
        alpha=alpha,                       # BM25/vector mixing
        rerank=Rerank(prop="title", query=q, top_k=rerank_k),
    )
    return [o.properties for o in res.objects]
