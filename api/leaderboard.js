/* Vercel serverless — shared leaderboard via Vercel KV */
export default async function handler(req, res) {
  const kvUrl = process.env.KV_REST_API_URL;
  const kvToken = process.env.KV_REST_API_TOKEN;

  // Fallback: in-memory store if KV not configured (resets on cold start)
  if (!kvUrl || !kvToken) {
    // Use a simple GET/POST with edge config or return empty
    if (req.method === 'GET') {
      return res.status(200).json({ entries: [] });
    }
    return res.status(200).json({ ok: true });
  }

  async function kvGet(key) {
    const r = await fetch(`${kvUrl}/get/${key}`, { headers: { Authorization: `Bearer ${kvToken}` } });
    if (!r.ok) return null;
    const data = await r.json();
    return data.result;
  }

  async function kvSet(key, value) {
    await fetch(`${kvUrl}/set/${key}/${encodeURIComponent(JSON.stringify(value))}`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${kvToken}` }
    });
  }

  if (req.method === 'GET') {
    const raw = await kvGet('arena_leaderboard');
    const entries = raw ? JSON.parse(raw) : [];
    // Sort by score descending, return top 25
    entries.sort((a, b) => b.score - a.score);
    return res.status(200).json({ entries: entries.slice(0, 25) });
  }

  if (req.method === 'POST') {
    let body;
    try { body = typeof req.body === 'string' ? JSON.parse(req.body) : req.body; }
    catch { return res.status(400).json({ error: 'Invalid JSON' }); }

    const { name, score, broken, best } = body;
    if (!name || typeof score !== 'number') return res.status(400).json({ error: 'name + score required' });

    // Sanitize
    const cleanName = String(name).slice(0, 20).replace(/[^a-zA-Z0-9_-]/g, '');
    const entry = {
      name: cleanName || 'anon',
      score: Math.max(0, Math.min(score, 50000)),
      broken: Math.max(0, Math.min(broken || 0, 5)),
      best: String(best || '—').slice(0, 20),
      ts: Date.now()
    };

    const raw = await kvGet('arena_leaderboard');
    const entries = raw ? JSON.parse(raw) : [];

    // Update or insert (keep best score per player)
    const existing = entries.findIndex(e => e.name === entry.name);
    if (existing >= 0) {
      if (entry.score > entries[existing].score) entries[existing] = entry;
    } else {
      entries.push(entry);
    }

    // Keep top 100 only
    entries.sort((a, b) => b.score - a.score);
    await kvSet('arena_leaderboard', entries.slice(0, 100));

    return res.status(200).json({ ok: true, rank: entries.findIndex(e => e.name === entry.name) + 1 });
  }

  return res.status(405).json({ error: 'GET or POST only' });
}
