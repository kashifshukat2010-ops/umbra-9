#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UMBRA-9 CLOUD - Kashif's personal cyber assistant, the always-on copy.
This copy runs on free hosting (e.g. Hugging Face Spaces), so the assistant
opens with a login from anywhere in the world, even when the laptop is off.

Included: Password Login, AI Chat (Groq free API - when a key is set),
53 Tools + Guides, 11 Concepts, IP Location Lookup, Username Search.
Deliberately NOT included: Device Scan, Agent Mode (running commands),
My Network Test - those jobs run inside the laptop, so they live only in
the laptop copy. Running commands on a cloud server would be dangerous too.

Env (keep these in the hosting Secrets):
  UMBRA_PASS    = login password (required)
  GROQ_API_KEY  = free key for AI chat (optional)
  GROQ_MODEL    = default llama-3.1-8b-instant
  PORT          = provided by the hosting (default 7860)
"""
import hashlib
import hmac
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cyber_assistant_web as core  # TOOLS / GUIDES / CONCEPTS / lookup helpers

PASSWORD = os.environ.get("UMBRA_PASS", "")
GROQ_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")
PORT = int(os.environ.get("PORT", "7860"))

SYSTEM_PROMPT = (
    "Tum UMBRA-9 ho - Kashif ke personal cyber security assistant. "
    "Reply in simple, clear English — friendly and concise. "
    "Help him learn cybersecurity: explain concepts, tools and commands. "
    "Never help attack anyone's account or network without authorization; "
    "always teach the legal method and the self-defence angle."
)


def _token():
    return hashlib.sha256((PASSWORD + "|umbra9-cloud").encode()).hexdigest()


LOGIN_PAGE = """<!DOCTYPE html>
<html lang="ur"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>UMBRA-9 — Login</title>
<style>
body{background:#02070c;color:#d7e8de;font-family:system-ui,sans-serif;display:flex;
min-height:100vh;align-items:center;justify-content:center;margin:0}
.box{background:#030b10;border:1px solid #0c2b22;border-radius:14px;padding:28px;width:min(92vw,360px);text-align:center}
h1{margin:0 0 4px;font-size:26px;letter-spacing:2px}
p{color:#7d93a3;margin:6px 0 18px}
input{width:100%;box-sizing:border-box;padding:12px;border-radius:9px;border:1px solid #134233;
background:#02070c;color:#fff;font-size:16px;margin-bottom:12px}
button{width:100%;padding:12px;border:0;border-radius:9px;background:#0d8a4e;color:#fff;
font-size:16px;font-weight:600;cursor:pointer}
.err{color:#f87171;min-height:20px;font-size:14px}
</style></head><body>
<form class="box" method="post" action="/login">
<h1>🌙 UMBRA-9</h1>
<p>Kashif's Personal Cyber Assistant<br>Yours alone — enter your password</p>
<input type="password" name="password" placeholder="Password" autocomplete="current-password" required>
<button type="submit">Login</button>
<div class="err">%%ERR%%</div>
</form></body></html>"""


CLOUD_PAGE = """<!DOCTYPE html>
<html lang="ur"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#02070c">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="UMBRA-9">
<title>UMBRA-9 — Personal Cyber Assistant (Cloud)</title>
<style>
body{background:#02070c;color:#d7e8de;font-family:system-ui,sans-serif;margin:0;padding:14px}
h1{font-size:22px;letter-spacing:2px;margin:2px 0}
.sub{color:#7d93a3;margin:2px 0 12px;font-size:14px}
.tabs{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px}
.tab{background:#030b10;border:1px solid #0c2b22;color:#d7e8de;padding:8px 12px;border-radius:999px;cursor:pointer;font-size:14px}
.tab.on{background:#0d8a4e;border-color:#0d8a4e;color:#fff}
.sec{display:none}.sec.on{display:block}
.card{background:#030b10;border:1px solid #0c2b22;border-radius:12px;padding:12px;margin-bottom:10px}
.card h3{margin:0 0 6px;font-size:16px}
.card .cmd{color:#34d399;font-family:ui-monospace,monospace;font-size:13px;word-break:break-all}
pre{white-space:pre-wrap;background:#02070c;border:1px solid #0c2b22;border-radius:9px;padding:10px;font-size:13.5px;line-height:1.55}
input,select{background:#02070c;border:1px solid #134233;color:#fff;border-radius:9px;padding:10px;font-size:15px}
button{background:#0d8a4e;border:0;color:#fff;border-radius:9px;padding:10px 14px;font-weight:600;cursor:pointer}
.row{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px}.row input{flex:1;min-width:180px}
#chatlog{display:flex;flex-direction:column;gap:8px;margin-bottom:10px}
.msg{max-width:88%;padding:10px 12px;border-radius:12px;white-space:pre-wrap;line-height:1.5;font-size:14.5px}
.me{align-self:flex-end;background:#0d8a4e;color:#fff}
.ai{align-self:flex-start;background:#030b10;border:1px solid #0c2b22}
.badge{font-size:12px;padding:2px 8px;border-radius:999px;border:1px solid #134233;color:#7d93a3}
.found{color:#34d399}.notfound{color:#f87171}.check{color:#fbbf24}
a{color:#34d399}.small{color:#7d93a3;font-size:13px}
</style></head><body>
<h1>🌙 UMBRA-9 <span class="badge">CLOUD — ALWAYS ON</span></h1>
<p class="sub">Assalam-o-Alaikum Kashif! I am your personal cyber assistant — from anywhere in the world, with only your login. <span id="aistat"></span></p>

<div class="tabs">
<button class="tab on" data-s="chat">💬 AI Chat</button>
<button class="tab" data-s="tools">🛠 Tools (53)</button>
<button class="tab" data-s="concepts">💡 Concepts</button>
<button class="tab" data-s="osint">🔍 OSINT</button>
</div>

<div class="sec on" id="s-chat">
<div id="chatlog"></div>
<div class="row"><input id="chatin" placeholder="Ask something... e.g.: What is Nmap?" autocomplete="off">
<button id="chatsend">Send</button></div>
<p class="small">Note: Device Scan, Agent Mode and Network Test live only in the laptop copy — those jobs run inside the laptop.</p>
</div>

<div class="sec" id="s-tools">
<div class="row"><input id="tsearch" placeholder="Search tools... (nmap, wifi, password)">
<select id="tcat"></select></div>
<div id="tools"></div>
<div id="guide"></div>
</div>

<div class="sec" id="s-concepts"><div id="concepts"></div></div>

<div class="sec" id="s-osint">
<div class="card"><h3>🌍 IP Location Lookup</h3>
<div class="row"><input id="ipin" placeholder="IP address (empty = your own IP)"><button id="ipbtn">Look up</button></div>
<div id="ipout"></div></div>
<div class="card"><h3>👤 Username Search (public profiles)</h3>
<div class="row"><input id="unin" placeholder="Username"><button id="unbtn">Search</button></div>
<div id="unout"></div></div>
</div>

<script>
let DATA=null, hist=[];
const $=id=>document.getElementById(id);
document.querySelectorAll('.tab').forEach(t=>t.onclick=()=>{
 document.querySelectorAll('.tab').forEach(x=>x.classList.remove('on'));t.classList.add('on');
 document.querySelectorAll('.sec').forEach(x=>x.classList.remove('on'));$('s-'+t.dataset.s).classList.add('on');});
function esc(s){return String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
function addMsg(txt,who){const d=document.createElement('div');d.className='msg '+who;d.textContent=txt;$('chatlog').appendChild(d);d.scrollIntoView({behavior:'smooth'})}
async function sendChat(){
 const v=$('chatin').value.trim();if(!v)return;$('chatin').value='';
 addMsg(v,'me');hist.push({role:'user',content:v});
 addMsg('...','ai');const wait=$('chatlog').lastChild;
 try{const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({messages:hist})});
 const d=await r.json();wait.textContent=d.reply||d.error||'Jawab nahi aya.';hist.push({role:'assistant',content:wait.textContent});}
 catch(e){wait.textContent='Could not connect — check the internet.'}}
$('chatsend').onclick=sendChat;
$('chatin').addEventListener('keydown',e=>{if(e.key==='Enter')sendChat()});
function renderTools(){
 const q=$('tsearch').value.toLowerCase(),cat=$('tcat').value;
 $('tools').innerHTML=DATA.tools.filter(t=>(!cat||t.cat===cat)&&(t.name.toLowerCase().includes(q)||t.desc.toLowerCase().includes(q)))
 .map(t=>`<div class="card"><h3>${esc(t.name)} <span class="badge">${esc(t.cat)}</span></h3><div>${esc(t.desc)}</div><div class="cmd">${esc(t.cmd)}</div><p><button onclick="showGuide('${esc(t.name)}')">📖 Read guide</button></p></div>`).join('')||'<p class="small">Nothing found.</p>'}
function showGuide(n){const g=DATA.guides[n];if(!g)return;$('guide').innerHTML=`<div class="card"><h3>📖 ${esc(n)}</h3><pre>${esc(g)}</pre></div>`;$('guide').scrollIntoView({behavior:'smooth'})}
$('tsearch').addEventListener('input',renderTools);$('tcat').addEventListener('change',renderTools);
async function ipGo(){
 $('ipout').innerHTML='<p class="small">Looking...</p>';
 const r=await fetch('/api/iplookup',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ip:$('ipin').value.trim()})});
 const d=await r.json();
 if(d.error){$('ipout').innerHTML='<p style="color:#f87171">'+esc(d.error)+'</p>';return}
 $('ipout').innerHTML='<pre>'+Object.entries(d).map(([k,v])=>esc(k)+': '+esc(v)).join('\\n')+'</pre>'}
$('ipbtn').onclick=ipGo;
async function unGo(){
 $('unout').innerHTML='<p class="small">Checking 11 places — may take 10-20 seconds...</p>';
 const r=await fetch('/api/username',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:$('unin').value.trim()})});
 const d=await r.json();
 if(d.error){$('unout').innerHTML='<p style="color:#f87171">'+esc(d.error)+'</p>';return}
 $('unout').innerHTML=d.results.map(x=>{
  let h=`<div class="card"><b>${esc(x.site)}</b> — <span class="${x.status}">${x.status==='found'?'✔ Found':x.status==='notfound'?'✘ Not found':'? Check it yourself'}</span> <a href="${esc(x.url)}" target="_blank" rel="noopener">open</a>`;
  if(x.details)h+='<pre>'+Object.entries(x.details).map(([k,v])=>esc(k)+': '+esc(v)).join('\\n')+'</pre>';
  return h+'</div>'}).join('')}
$('unbtn').onclick=unGo;
(async()=>{
 const st=await (await fetch('/api/status')).json();
 $('aistat').textContent=st.groq?'AI: ONLINE ✔':'AI: key pending (directory/OSINT work)';
 DATA=await (await fetch('/api/tools')).json();
 $('tcat').innerHTML='<option value="">All categories</option>'+DATA.categories.map(c=>`<option>${esc(c)}</option>`).join('');
 $('concepts').innerHTML=DATA.concepts.map(c=>`<div class="card"><h3>${esc(c.title)}</h3><pre>${esc(c.body)}</pre></div>`).join('');
 renderTools();
 addMsg('I am UMBRA-9 (cloud copy). Ask me anything, or browse Tools/Concepts. Device Scan and Agent Mode are in the laptop copy.','ai');
})();
</script></body></html>"""



class CloudHandler(core.Handler):
    """core.Handler se _send_json / _api_iplookup / _api_username reuse hote hain."""

    def log_message(self, *args):
        pass

    def _read_json(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
            return json.loads(self.rfile.read(n).decode("utf-8")) if n else {}
        except Exception:
            return {}

    def _authed(self):
        if not PASSWORD:
            return False
        for part in self.headers.get("Cookie", "").split(";"):
            part = part.strip()
            if part.startswith("umbra9_auth="):
                return hmac.compare_digest(part[len("umbra9_auth="):], _token())
        return False

    def _html(self, text):
        body = text.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _to_login(self):
        self.send_response(302)
        self.send_header("Location", "/login")
        self.end_headers()

    def do_GET(self):
        if self.path == "/manifest.json":
            self._send_json({"name": "UMBRA-9 — Personal Cyber Assistant", "short_name": "UMBRA-9",
                             "start_url": "/", "display": "standalone",
                             "background_color": "#02070c", "theme_color": "#02070c"})
            return
        if not PASSWORD:
            self._html("<body style='background:#02070c;color:#d7e8de;font-family:system-ui;padding:24px'>"
                       "<h2>🌙 UMBRA-9 Cloud</h2><p>The login password is not set yet. "
                       "Put <b>UMBRA_PASS</b> in the hosting <b>Secrets</b>, then restart the app.</p></body>")
            return
        if self.path == "/login":
            self._html(LOGIN_PAGE.replace("%%ERR%%", ""))
            return
        if not self._authed():
            self._to_login()
            return
        if self.path == "/" or self.path.startswith("/?"):
            self._html(CLOUD_PAGE)
        elif self.path == "/api/tools":
            self._send_json({"categories": core.CATEGORIES, "tools": core.TOOLS,
                             "suggested": core.SUGGESTED, "guides": core.GUIDES,
                             "concepts": core.CONCEPTS})
        elif self.path == "/api/status":
            self._send_json({"groq": bool(GROQ_KEY), "model": GROQ_MODEL})
        else:
            self._send_json({"error": "not found"}, 404)

    def do_POST(self):
        if self.path == "/login":
            try:
                n = int(self.headers.get("Content-Length", 0))
                raw = self.rfile.read(n).decode("utf-8", "replace")
                pw = urllib.parse.parse_qs(raw).get("password", [""])[0]
            except Exception:
                pw = ""
            if PASSWORD and hmac.compare_digest(pw, PASSWORD):
                self.send_response(302)
                self.send_header("Location", "/")
                self.send_header("Set-Cookie",
                                 f"umbra9_auth={_token()}; Path=/; HttpOnly; SameSite=Lax; Max-Age=2592000")
                self.end_headers()
            else:
                self._html(LOGIN_PAGE.replace("%%ERR%%", "Wrong password — try again."))
            return
        if not self._authed():
            self._send_json({"error": "Please log in first."}, 401)
            return
        data = self._read_json()
        if self.path == "/api/chat":
            self._cloud_chat(data)
        elif self.path == "/api/iplookup":
            self._api_iplookup(data)
        elif self.path == "/api/username":
            self._api_username(data)
        elif self.path in ("/api/agent/plan", "/api/agent/explain", "/api/scan",
                           "/api/scan/explain", "/api/fix", "/api/nettest"):
            self._send_json({"error": "This feature lives only in the laptop copy of UMBRA-9 — "
                                      "it is deliberately off in the cloud copy."}, 403)
        else:
            self._send_json({"error": "not found"}, 404)

    def _cloud_chat(self, data):
        msgs = data.get("messages", [])
        if not isinstance(msgs, list) or not msgs:
            self._send_json({"error": "Message is empty."}, 400)
            return
        if not GROQ_KEY:
            self._send_json({"reply": "The free Groq API key for AI chat is not set yet "
                                      "(last step of the deploy guide). Until then, Tools, Guides, "
                                      "Concepts, IP Lookup and Username Search work fully — "
                                      "use the tabs above."})
            return
        payload = {"model": GROQ_MODEL,
                   "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + msgs[-20:],
                   "temperature": 0.4}
        try:
            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json",
                         "Authorization": f"Bearer {GROQ_KEY}"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                out = json.loads(resp.read().decode("utf-8"))
            self._send_json({"reply": out["choices"][0]["message"]["content"]})
        except Exception:
            self._send_json({"reply": "Could not reach the AI (network or key issue). "
                                      "Please try again in a little while."})


def main():
    if not PASSWORD:
        print("WARNING: UMBRA_PASS set nahi — pehle hosting ke Secrets mein password rakho.")
    server = ThreadingHTTPServer(("0.0.0.0", PORT), CloudHandler)
    print(f"UMBRA-9 CLOUD chal gaya — port {PORT} | Groq AI: {'ON' if GROQ_KEY else 'OFF (key baqi)'}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nBand ho gaya.")


if __name__ == "__main__":
    main()
