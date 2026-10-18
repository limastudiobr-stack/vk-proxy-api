import sys
import json
import urllib.request
import urllib.parse
import re

# Pega a URL do vídeo passada via argumento
if len(sys.argv) < 2:
    print(json.dumps({"error": "Nenhuma URL fornecida"}))
    sys.exit(1)

url_input = sys.argv[1]

# Extrai OID e VID
m = re.search(r"video(-?\d+)_(\d+)", url_input)
if not m:
    print(json.dumps({"error": "URL inválida"}))
    sys.exit(1)

oid = m.group(1)
vid = m.group(2)

list_token = ""
m_list = re.search(r"list=([^&]+)", url_input)
if m_list:
    list_token = m_list.group(1)

post_data = f"act=show&al=1&video={oid}_{vid}"
if list_token:
    post_data += f"&list={list_token}"

# Requisição para o VK a partir dos servidores dos EUA do GitHub
req_url = "https://vk.com/al_video.php?act=show"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Content-Type": "application/x-www-form-urlencoded",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://vk.com/"
}

try:
    data_bytes = post_data.encode("utf-8")
    req = urllib.request.Request(req_url, data=data_bytes, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=15) as response:
        raw_html = response.read().decode("utf-8")

    # Limpeza de caracteres
    raw_html = raw_html.replace("\\/", "/").replace("\\\"", "\"").replace("\\u0026", "&").replace("&amp;", "&")

    # Busca qualidades (2160, 1440, 1080, 720)
    qualities = {}
    p_urls = re.findall(r'"(?:url|mp4_)?(2160|1440|1080|720)":"([^"]+)"', raw_html)
    for res, link in p_urls:
        if "getVideoPreview" in link or "type=39" in link or "type=42" in link:
            continue
        if res not in qualities:
            qualities[res] = link

    print(json.dumps({"success": True, "links": qualities}))

except Exception as e:
    print(json.dumps({"error": str(e)}))
