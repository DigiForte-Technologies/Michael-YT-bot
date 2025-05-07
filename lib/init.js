require('dotenv').config();
const { createClient } = require('@supabase/supabase-js');
const { Pinecone } = require('@pinecone-database/pinecone');

console.log('✅ Loading environment variables...');
const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

console.log('✅ Supabase client initialized.');

const pinecone = new Pinecone({
  apiKey: process.env.PINECONE_API_KEY
});

async function initPinecone() {
  const host = process.env.PINECONE_HOST;
  const indexName = process.env.PINECONE_INDEX;

  if (!host || typeof host !== 'string') {
    throw new Error('❌ Missing or invalid PINECONE_HOST in .env');
  }
  if (!indexName) {
    throw new Error('❌ Missing PINECONE_INDEX in .env');
  }

  console.log(`🔗 Connecting to Pinecone index: ${indexName}`);
  return pinecone.index(indexName, host); // ✅ pass host as string
}

module.exports = { supabase, initPinecone };
