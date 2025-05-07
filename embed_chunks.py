import os
import time
import openai
import tiktoken
import isodate
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client
from pinecone import Pinecone

# --- Load environment variables ---
load_dotenv()

# --- API Keys ---
openai.api_key = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENV = os.getenv("PINECONE_ENV")
INDEX_NAME = os.getenv("PINECONE_INDEX")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# --- Init Pinecone client ---
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(INDEX_NAME)

# --- Init Supabase ---
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Tokenizer ---
enc = tiktoken.get_encoding("cl100k_base")  # compatible with text-embedding-3-large

# --- Chunker ---
def chunk_text(text, max_tokens=800):
    words = text.split()
    chunks = []
    current = []
    token_count = 0

    for word in words:
        tokens = len(enc.encode(word + ' '))
        if token_count + tokens > max_tokens:
            chunks.append(" ".join(current))
            current = [word]
            token_count = tokens
        else:
            current.append(word)
            token_count += tokens
    if current:
        chunks.append(" ".join(current))
    return chunks

# --- Load video + transcript data ---
print("📦 Fetching transcript + video metadata from Supabase...")
data = supabase.rpc("get_video_transcripts_with_metadata").execute().data
print(f"✅ {len(data)} videos to embed")

for row in data:
    vid = row["video_id"]
    transcript = row["transcript"]
    title = row.get("title", "")
    published = row.get("published_at")
    duration = row.get("duration_seconds")

    chunks = chunk_text(transcript)
    print(f"✂️ {vid} → {len(chunks)} chunks")

    for i, chunk in enumerate(chunks):
        try:
            response = openai.embeddings.create(
                input=chunk,
                model="text-embedding-3-large"
            )
            embed = response.data[0].embedding

            vector_id = f"{vid}_{i}"
            metadata = {
                "video_id": vid,
                "title": title,
                "chunk_index": i,
                "published_at": published,
                "duration_seconds": duration,
                "text": chunk[:300]  # optional preview text
            }

            index.upsert(vectors=[{
                "id": vector_id,
                "values": embed,
                "metadata": metadata
            }])

            time.sleep(0.5)  # rate limit friendly

        except Exception as e:
            print(f"❌ Error embedding {vid} chunk {i}: {e}")

print("🚀 Done. All embeddings sent to Pinecone.")