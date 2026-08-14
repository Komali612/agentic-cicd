"""The Orchestrator's test console (served at ``GET /``).

A small self-contained page: paste a git repo URL (or a list, or an org), the
orchestrator classifies each repository and routes it to the matching CI worker,
and the page renders the resulting outcomes + pull-request links. Same UI for
every stack — the orchestrator decides where each repo goes.
"""

CONSOLE_HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Orchestrator · Agentic CI/CD</title>
<style>
  :root { color-scheme: light dark; --accent:#3b82f6; --ok:#16a34a; --warn:#d97706; --err:#dc2626; }
  * { box-sizing: border-box; }
  body { font: 15px/1.5 system-ui, sans-serif; max-width: 820px; margin: 2rem auto; padding: 0 1rem; }
  h1 { font-size: 1.35rem; margin: 0 0 .2rem; }
  .sub { opacity:.6; font-size:.9rem; margin-bottom:1.2rem; }
  label { display:block; font-weight:600; font-size:.85rem; margin:.8rem 0 .3rem; }
  input[type=text], textarea { width:100%; padding:.55rem .7rem; border:1px solid #8884; border-radius:8px; background:#8881; font:inherit; }
  textarea { min-height:80px; font:13px ui-monospace,monospace; }
  .modes { display:flex; gap:1.2rem; margin:.4rem 0; font-size:.9rem; }
  .modes label { display:inline-flex; align-items:center; gap:.35rem; font-weight:400; margin:0; }
  button { margin-top:.9rem; padding:.55rem 1.3rem; font-size:.95rem; font-weight:600; cursor:pointer; border:0; border-radius:8px; background:var(--accent); color:#fff; }
  button:disabled { opacity:.5; cursor:default; }
  #out { margin-top:1.4rem; }
  .card { border:1px solid #8883; border-radius:10px; padding:.7rem 1rem; margin:.6rem 0; display:flex; flex-wrap:wrap; gap:.5rem; align-items:center; }
  .repo { font-weight:600; }
  .badge { font-size:.7rem; font-weight:700; padding:.12rem .55rem; border-radius:999px; text-transform:uppercase; letter-spacing:.03em; }
  .b-pr_opened{ background:#16a34a22; color:var(--ok);} .b-no_change{ background:#3b82f622; color:var(--accent);}
  .b-exception,.b-exc{ background:#dc262622; color:var(--err);}
  a { color:var(--accent); }
  .muted{ opacity:.6; font-size:.85rem; width:100%; }
  .empty{ opacity:.55; font-style:italic; }
  pre { background:#8881; padding:.7rem; border-radius:8px; overflow:auto; font-size:12px; }
</style></head>
<body>
  <h1>Agentic CI/CD · Orchestrator</h1>
  <div class="sub">Give a repository — the orchestrator classifies it (.NET Core / .NET FX) and routes it to the matching CI worker, which opens a pull request.</div>

  <div class="modes">
    <label><input type="radio" name="mode" value="repo_url" checked> Single repo</label>
    <label><input type="radio" name="mode" value="repos"> Multiple repos</label>
    <label><input type="radio" name="mode" value="org"> Whole org</label>
  </div>
  <div id="single">
    <label>Git repository URL</label>
    <input id="url" type="text" placeholder="https://github.com/owner/repo">
  </div>
  <div id="multi" style="display:none">
    <label>Repository URLs (one per line)</label>
    <textarea id="urls" placeholder="https://github.com/owner/a&#10;https://github.com/owner/b"></textarea>
  </div>
  <div id="orgd" style="display:none">
    <label>GitHub organization</label>
    <input id="org" type="text" placeholder="my-org">
  </div>

  <button id="go">Run orchestrator &#9654;</button>
  <div id="out"></div>

<script>
  const $ = s => document.querySelector(s);
  const panes = { repo_url:'#single', repos:'#multi', org:'#orgd' };
  document.querySelectorAll('input[name=mode]').forEach(r => r.addEventListener('change', () => {
    for (const [m, sel] of Object.entries(panes)) $(sel).style.display = (m === mode()) ? '' : 'none';
  }));
  function mode(){ return document.querySelector('input[name=mode]:checked').value; }

  function body(){
    const m = mode();
    if (m === 'repo_url') return { input: { repo_url: $('#url').value.trim() } };
    if (m === 'org') return { input: { org: $('#org').value.trim() } };
    const repos = $('#urls').value.split('\n').map(s => s.trim()).filter(Boolean);
    return { input: { repos } };
  }

  const esc = s => String(s).replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));

  function render(report){
    const results = report.results || [], excs = report.exceptions || [];
    let h = `<div class="muted">${results.length} processed &middot; ${excs.length} exception(s)</div>`;
    for (const r of results){
      const repo = r.repo.owner + '/' + r.repo.name;
      const pr = r.pull_request_url ? ` &middot; <a href="${r.pull_request_url}" target="_blank">pull request &rarr;</a>` : '';
      h += `<div class="card"><span class="repo">${esc(repo)}</span><span class="badge b-${r.outcome}">${r.outcome.replace('_',' ')}</span>${pr}</div>`;
    }
    for (const e of excs){
      const repo = e.repo ? (e.repo.owner + '/' + e.repo.name) : '(unknown)';
      h += `<div class="card"><span class="repo">${esc(repo)}</span><span class="badge b-exc">exception</span><span class="muted">${esc(e.stage)}: ${esc(e.reason)}</span></div>`;
    }
    if (!results.length && !excs.length) h += `<div class="empty">No repositories resolved.</div>`;
    return h;
  }

  $('#go').addEventListener('click', async () => {
    $('#go').disabled = true; $('#out').innerHTML = '<div class="muted">Running&hellip;</div>';
    try {
      const res = await fetch('/run', { method:'POST', headers:{'content-type':'application/json'}, body: JSON.stringify(body()) });
      const data = await res.json();
      $('#out').innerHTML = res.ok ? render(data.result || {})
                                   : `<pre>HTTP ${res.status}\n${esc(JSON.stringify(data, null, 2))}</pre>`;
    } catch (e) { $('#out').innerHTML = `<pre>Error: ${esc(e)}</pre>`; }
    finally { $('#go').disabled = false; }
  });
</script>
</body></html>
"""
