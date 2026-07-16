import crypto from 'crypto';

function jcsCanonical(obj) {
  // Simplified JCS: sorted keys, no whitespace, deterministic
  const sorted = Object.keys(obj).sort().reduce((acc, k) => {
    acc[k] = obj[k];
    return acc;
  }, {});
  return JSON.stringify(sorted);
}

function sha256hex(data) {
  return crypto.createHash('sha256').update(data, 'utf8').digest('hex');
}

// In-memory store (resets on cold start, fine for demo)
const agentScores = {};

export default function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, X-API-Key');

  if (req.method === 'OPTIONS') return res.status(200).end();

  const path = req.query.action || '';

  // GET /api/verify - health
  if (req.method === 'GET' && !path) {
    return res.json({
      status: 'ok',
      version: '0.2.0',
      endpoints: [
        'POST /api/verify - verify a single receipt',
        'POST /api/verify?action=batch - batch verify + merkle root',
        'GET /api/verify?action=demo - tamper detection demo',
        'GET /api/verify?action=score&agent_id=X - trust score lookup'
      ]
    });
  }

  // GET /api/verify?action=demo - tamper test
  if (req.method === 'GET' && path === 'demo') {
    const ts = Date.now();
    const original = { agent_id: 'demo', action_type: 'tool:transfer', scope: 'amount=500,to=alice', timestamp_ms: ts };
    const tampered = { ...original, scope: 'amount=50000,to=attacker' };

    const origRef = sha256hex(jcsCanonical(original));
    const tampRef = sha256hex(jcsCanonical(tampered));

    return res.json({
      demo: 'tamper-test',
      original: { scope: original.scope, action_ref: origRef, verdict: 'VALID' },
      tampered: { scope: tampered.scope, action_ref_original: origRef, action_ref_recomputed: tampRef, match: false, verdict: 'INVALID - tamper detected' },
      explanation: 'The attacker changed scope from amount=500 to amount=50000. The action_ref no longer matches.'
    });
  }

  // POST /api/verify - verify a receipt
  if (req.method === 'POST' && !path) {
    const body = req.body;
    if (!body) return res.status(400).json({ error: 'JSON body required' });

    const { agent_id, action_type, scope, timestamp_ms, action_ref } = body;

    if (!agent_id || !action_type || !action_ref) {
      return res.status(400).json({ error: 'agent_id, action_type, and action_ref required' });
    }

    const preimage = jcsCanonical({ agent_id, action_type, scope: scope || '', timestamp_ms: timestamp_ms || 0 });
    const recomputed = sha256hex(preimage);
    const refMatch = recomputed === action_ref;

    const verdict = refMatch ? 'VALID' : 'INVALID';

    if (refMatch) {
      if (!agentScores[agent_id]) agentScores[agent_id] = { allow: 0, deny: 0 };
      const v = (body.verdict || 'ALLOW').toUpperCase();
      if (v === 'ALLOW') agentScores[agent_id].allow++;
      else agentScores[agent_id].deny++;
    }

    return res.json({
      verdict,
      action_ref_recomputed: recomputed,
      action_ref_match: refMatch,
      agent_id,
      action_type,
      note: refMatch ? undefined : 'action_ref does not match recomputed preimage'
    });
  }

  // GET /api/verify?action=score&agent_id=xxx
  if (req.method === 'GET' && path === 'score') {
    const aid = req.query.agent_id;
    if (!aid) return res.status(400).json({ error: 'agent_id query param required' });

    const data = agentScores[aid];
    if (!data) return res.json({ agent_id: aid, score: 0, grade: 'F', receipts: 0 });

    const total = data.allow + data.deny;
    const score = Math.min(100, Math.max(0, 50 + data.allow * 5 - data.deny * 10));
    const grade = score >= 80 ? 'A' : score >= 60 ? 'B' : score >= 40 ? 'C' : score >= 20 ? 'D' : 'F';

    return res.json({ agent_id: aid, score, grade, receipts: total, allow: data.allow, deny: data.deny });
  }

  // POST /api/verify?action=batch - batch verify + merkle root
  if (req.method === 'POST' && path === 'batch') {
    const body = req.body;
    if (!body || !body.receipts || !Array.isArray(body.receipts)) {
      return res.status(400).json({ error: 'receipts array required' });
    }

    const results = body.receipts.map((r, i) => {
      const preimage = jcsCanonical({
        agent_id: r.agent_id || '',
        action_type: r.action_type || '',
        scope: r.scope || '',
        timestamp_ms: r.timestamp_ms || 0
      });
      const recomputed = sha256hex(preimage);
      return {
        index: i,
        action_ref_match: recomputed === r.action_ref,
        verdict: recomputed === r.action_ref ? 'VALID' : 'INVALID'
      };
    });

    // RFC 6962 Merkle root over all action_refs
    const leaves = body.receipts.map(r => sha256hex('\x00' + (r.action_ref || '')));
    const merkleRoot = computeMerkleRoot(leaves);

    const allValid = results.every(r => r.verdict === 'VALID');
    return res.json({
      batch_size: body.receipts.length,
      all_valid: allValid,
      merkle_root: merkleRoot,
      results
    });
  }

  return res.status(404).json({
    error: 'not found',
    endpoints: [
      'POST /api/verify',
      'POST /api/verify?action=batch',
      'GET /api/verify?action=demo',
      'GET /api/verify?action=score&agent_id=X'
    ]
  });
}

// RFC 6962 Merkle tree
function computeMerkleRoot(leaves) {
  if (leaves.length === 0) return sha256hex('');
  if (leaves.length === 1) return leaves[0];
  const k = largestPow2LessThan(leaves.length);
  const left = computeMerkleRoot(leaves.slice(0, k));
  const right = computeMerkleRoot(leaves.slice(k));
  return sha256hex('\x01' + Buffer.from(left, 'hex').toString() + Buffer.from(right, 'hex').toString());
}

function largestPow2LessThan(n) {
  let k = 1;
  while (k * 2 < n) k *= 2;
  return k;
}
