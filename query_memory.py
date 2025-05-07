import os
import openai
import tiktoken
from dotenv import load_dotenv
from pinecone import Pinecone

# --- Load env ---
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME = os.getenv("PINECONE_INDEX_NAME") or os.getenv("PINECONE_INDEX")
assert INDEX_NAME, "❌ Missing INDEX_NAME in .env"

# --- Init Pinecone ---
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(INDEX_NAME)

# --- Tokenizer ---
enc = tiktoken.get_encoding("cl100k_base")

# --- Smart Query Function ---
def ask_brain(question: str, top_k=12):
    print("🔎 Embedding question...")
    embed = openai.embeddings.create(
        input=question,
        model="text-embedding-3-large"
    ).data[0].embedding

    # Detect year from question
    import re
    year_match = re.search(r"20\d{2}", question)
    year_filter = int(year_match.group()) if year_match else None

    matches = []
    if year_filter:
        print(f"📡 Querying Pinecone (filter: year = {year_filter})...")
        result = index.query(
            vector=embed,
            top_k=top_k,
            include_metadata=True,
            filter={"published_year": year_filter}
        )
        matches = result.matches

    # fallback with no filter if empty
    if not matches:
        print("⚠️ No matches found for filtered year. Trying without filter...")
        result = index.query(
            vector=embed,
            top_k=top_k,
            include_metadata=True
        )
        matches = result.matches

    matches = sorted(matches, key=lambda m: m.metadata.get("views", 0), reverse=True)
    context_chunks = [m.metadata["text"] for m in matches]
    titles = [m.metadata.get("title", "") for m in matches[:3]]

    context = "\n\n".join(context_chunks)
    prompt = f"""
You are Michael Bernstein's personal YouTube assistant. Use the transcript chunks below to answer the question with specific and insightful advice based on his best-performing recent videos:

---
{context}
---

Video titles referenced: {titles}

Question: {question}
Answer:""".strip()

    print("🤖 Asking GPT-4...")
    reply = openai.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": "You are a smart assistant trained on Michael's video content. Be accurate and useful."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )

    return reply.choices[0].message.content.strip()


# --- Run via CLI ---
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("❌ Please provide a question.")
        sys.exit(1)

    user_q = " ".join(sys.argv[1:])
    print(f"\n🧠 Question: {user_q}\n")
    answer = ask_brain(user_q)
    print(f"\n💬 Answer:\n{answer}")
