from fastapi import FastAPI, HTTPException, Query, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os, weaviate
from weaviate.classes.query import Rerank
import uvicorn

bearer = HTTPBearer()
TOKEN  = os.getenv("BEARER_TOKEN")

def check(creds: HTTPAuthorizationCredentials = Security(bearer)):
    if creds.credentials != TOKEN:
        raise HTTPException(401, "Invalid token")

client = weaviate.WeaviateClient(
    connection_params=weaviate.connect.ConnectionParams.from_url(
        os.getenv("WEAVIATE_URL", "http://weaviate:8080"),
        grpc_port=50051
    ),
    additional_headers={"X-JinaAI-Api-Key": os.getenv("JINAAI_APIKEY")}
)

# Connect to Weaviate
client.connect()

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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
