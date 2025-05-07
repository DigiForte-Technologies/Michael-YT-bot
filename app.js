// app.js (Node.js + Express Server for Chat UI with chat history)
require('dotenv').config();
const express = require('express');
const path = require('path');
const { exec } = require('child_process');
const bodyParser = require('body-parser');
const { createClient } = require('@supabase/supabase-js');
const { v4: uuidv4 } = require('uuid');

const app = express();
const PORT = process.env.PORT || 3005;

const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_KEY);

app.use(bodyParser.json());
app.use(express.static(path.join(__dirname, 'public')));

// Serve HTML page
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// Chat handler
app.post('/ask', async (req, res) => {
  const { question, session_id } = req.body;
  if (!question) return res.status(400).json({ error: 'Missing question' });

  const safeQuestion = question.replace(/"/g, '"');
  const command = `python3 query_memory.py "${safeQuestion}"`;
  console.log('🔍 Running:', command);

  exec(command, { cwd: __dirname }, async (err, stdout, stderr) => {
    if (err) {
      console.error('❌ Exec error:', err);
      return res.status(500).json({ error: 'Python script failed', details: err.message });
    }

    if (stderr) {
      console.error('⚠️ Stderr:', stderr);
    }

    const lines = stdout.trim().split('\n');
    const startIndex = lines.findIndex(line => line.startsWith('💬 Answer:'));
    const answer = startIndex !== -1
      ? lines.slice(startIndex + 1).join('\n').trim()
      : '⚠️ No answer received.';

    const id = uuidv4();
    const sid = session_id || uuidv4();
    const now = new Date().toISOString();

    await supabase.from('chat_history').insert({
      id,
      session_id: sid,
      question,
      answer,
      created_at: now
    });

    res.json({ answer, session_id: sid });
  });
});

// Get all chats for a session
app.get('/history/:session_id', async (req, res) => {
  const { session_id } = req.params;
  const { data, error } = await supabase
    .from('chat_history')
    .select('id, question, answer, created_at')
    .eq('session_id', session_id)
    .order('created_at', { ascending: true });

  if (error) return res.status(500).json({ error: error.message });
  res.json(data);
});

// List session IDs (for restoring history sidebar)
app.get('/sessions', async (req, res) => {
  const { data, error } = await supabase
    .from('chat_history')
    .select('session_id, created_at')
    .order('created_at', { ascending: false });

  if (error) return res.status(500).json({ error: error.message });

  // Deduplicate by session_id
  const seen = new Set();
  const uniqueSessions = data.filter(entry => {
    if (seen.has(entry.session_id)) return false;
    seen.add(entry.session_id);
    return true;
  });

  res.json(uniqueSessions);
});

app.listen(PORT, () => {
  console.log(`🚀 Listening on http://localhost:${PORT}`);
});