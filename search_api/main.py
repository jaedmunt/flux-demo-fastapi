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
    recency: bool = Query(True, description="Sort by recency (newest first) before reranking"),
):
    coll = client.collections.get("FeedItem")
    
    # Generate query vector using the same model as consumer
    if model:
        query_vector = model.encode(q).tolist()
        
        # Build query with optional recency sorting
        if recency:
            # For recency, use BM25 (no sorting in Weaviate v4)
            res = coll.query.bm25(
                query=q,
                limit=limit,
            )
        else:
            # For pure relevance, use hybrid search
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
    
    # Get results and sort by published date if recency is enabled
    results = [o.properties for o in res.objects]
    
    # Deduplicate by URL to prevent syndicated content from appearing multiple times
    seen_urls = set()
    deduplicated_results = []
    
    for result in results:
        url = result.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            deduplicated_results.append(result)
    
    if recency:
        # Sort by published date (newest first)
        deduplicated_results.sort(key=lambda x: x.get("published", ""), reverse=True)
        return deduplicated_results[:limit]
    else:
        return deduplicated_results[:limit]

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
