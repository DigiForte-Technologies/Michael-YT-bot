const { OpenAI } = require('openai');
const { supabase, initPinecone } = require('../lib/init');
require('dotenv').config();

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

async function main() {
  const { data: transcripts, error } = await supabase
    .from('transcriptions')
    .select('video_id, transcript')
    .limit(200);

  if (error) {
    console.error('❌ Supabase fetch error:', error);
    process.exit(1);
  }

  const index = await initPinecone();

  for (const item of transcripts) {
    if (!item.transcript) continue;

    const embeddingRes = await openai.embeddings.create({
      model: 'text-embedding-3-large',
      input: item.transcript.slice(0, 8000),
    });

    await index.namespace('yt').upsert([
      {
        id: item.video_id,
        values: embeddingRes.data[0].embedding,
        metadata: {
          video_id: item.video_id,
          content: item.transcript.slice(0, 500)
        }
      }
    ]);

    console.log(`✅ Uploaded ${item.video_id}`);
  }
}

main();
