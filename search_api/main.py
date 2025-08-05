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
    include_scores: bool = Query(True, description="Include relevance scores in results"),
):
    coll = client.collections.get("FeedItem")
    
    # Generate query vector using the same model as consumer
    if model:
        query_vector = model.encode(q).tolist()
        
        # Build query with reranking for better relevance scores
        if recency:
            # For recency, use BM25 with reranking to get scores
            res = coll.query.bm25(
                query=q,
                limit=rerank_k,  # Get more results for reranking
                rerank=Rerank(prop="title", query=q),
            )
        else:
            # For pure relevance, use hybrid search with reranking
            res = coll.query.hybrid(
                query=q,
                vector=query_vector,
                limit=rerank_k,  # Get more results for reranking
                alpha=alpha,                       # BM25/vector mixing
                rerank=Rerank(prop="title", query=q),
            )
    else:
        # Fallback to BM25 only if model not available
        res = coll.query.bm25(
            query=q,
            limit=limit,
        )
    
    # Get results with scores
    results_with_scores = []
    for i, obj in enumerate(res.objects):
        result = obj.properties.copy()
        if include_scores:
            # Add score and rank information - try different score attributes
            score = None
            if hasattr(obj, 'score'):
                score = obj.score
            elif hasattr(obj, 'rerank_score'):
                score = obj.rerank_score
            elif hasattr(obj, 'bm25_score'):
                score = obj.bm25_score
            
            result["relevance_score"] = score
            result["rank"] = i + 1
        results_with_scores.append(result)
    
    # Deduplicate by URL to prevent syndicated content from appearing multiple times
    seen_urls = set()
    deduplicated_results = []
    
    for result in results_with_scores:
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
