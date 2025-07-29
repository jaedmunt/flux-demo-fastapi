from fastapi import FastAPI, HTTPException, Query, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os, weaviate
from weaviate.classes.query import Rerank
import uvicorn

bearer = HTTPBearer()
TOKEN  = os.getenv("BEARER_TOKEN")

# Load sentence transformer for query vectorization
try:
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer('all-MiniLM-L6-v2')
    print("Loaded sentence transformer model for query vectorization")
except Exception as e:
    print(f"Error loading sentence transformer: {e}")
    model = None

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
    
    # Generate query vector using the same model as consumer
    if model:
        query_vector = model.encode(q).tolist()
        res = coll.query.hybrid(
            query=q,
            vector=query_vector,
            limit=limit,
            alpha=alpha,                       # BM25/vector mixing
            rerank=Rerank(prop="title", query=q),
        )
    else:
        # Fallback to BM25 only if model not available
        res = coll.query.bm25(
            query=q,
            limit=limit,
        )
    
    return [o.properties for o in res.objects]

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
