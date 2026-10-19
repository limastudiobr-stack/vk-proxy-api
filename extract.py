import sys
import json
import urllib.request
import urllib.parse
import re
import os
import base64
from datetime import datetime, timezone, timedelta

if len(sys.argv) < 2:
    sys.exit(1)

url_input = sys.argv[1]

m = re.search(r"video(-?\d+)_(\d+)", url_input)
if not m:
    result_data = {"error": "URL invalida"}
else:
    oid = m.group(1)
    vid = m.group(2)

    list_token = ""
    m_list = re.search(r"list=([^&]+)", url_input)
    if m_list:
        list_token = m_list.group(1)

    post_data = f"act=show&al=1&video={oid}_{vid}"
    if list_token:
        post_data += f"&list={list_token}"

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
            raw_html = response.read().decode("utf-8", errors="ignore")

        raw_html = raw_html.replace("\\/", "/").replace("\\\"", "\"").replace("\\u0026", "&").replace("&amp;", "&")

        qualities = {}
        p_urls = re.findall(r'"(?:url|mp4_)?(2160|1440|1080|720)":"([^"]+)"', raw_html)
        for res, link in p_urls:
            if "getVideoPreview" in link or "type=39" in link or "type=42" in link:
                continue
            if res not in qualities:
                qualities[res] = link

        result_data = {"success": True, "links": qualities}
    except Exception as e:
        result_data = {"error": str(e)}

json_str = json.dumps(result_data)

token = os.environ.get("GH_TOKEN")
repo = os.environ.get("GITHUB_REPOSITORY")

if token and repo:
    api_headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json"
    }

    # 1. LIMPEZA AUTOMÁTICA: Apaga arquivos res_*.json com mais de 24 horas
    try:
        list_url = f"https://api.github.com/repos/{repo}/contents/"
        req_list = urllib.request.Request(list_url, headers=api_headers)
        with urllib.request.urlopen(req_list) as resp:
            files = json.loads(resp.read().decode())
            now = datetime.now(timezone.utc)
            
            for file in files:
                fname = file.get("name", "")
                if fname.startswith("res_") and fname.endswith(".json"):
                    # Pega os detalhes do commit/arquivo para saber a data
                    f_url = file.get("url")
                    req_f = urllib.request.Request(f_url, headers=api_headers)
                    try:
                        with urllib.request.urlopen(req_f) as f_resp:
                            f_data = json.loads(f_resp.read().decode())
                            # Como a API de contents não traz data direta, usamos o histórico de commits do arquivo
                            commits_url = f"https://api.github.com/repos/{repo}/commits?path={fname}&per_page=1"
                            req_c = urllib.request.Request(commits_url, headers=api_headers)
                            with urllib.request.urlopen(req_c) as c_resp:
                                commits = json.loads(c_resp.read().decode())
                                if commits:
                                    date_str = commits[0]["commit"]["committer"]["date"]
                                    file_date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                                    
                                    # Se passou de 24 horas, deleta o arquivo expirado
                                    if now - file_date > timedelta(hours=24):
                                        del_data = {
                                            "message": f"Auto-delete expired cache {fname}",
                                            "sha": file.get("sha"),
                                            "branch": "main"
                                        }
                                        req_del = urllib.request.Request(
                                            f"https://api.github.com/repos/{repo}/contents/{fname}",
                                            data=json.dumps(del_data).encode(),
                                            headers=api_headers,
                                            method="DELETE"
                                        )
                                        urllib.request.urlopen(req_del)
                    except Exception:
                        pass
    except Exception:
        pass

    # 2. SALVA O NOVO ARQUIVO DE CACHE DO VÍDEO ATUAL
    filename = f"res_{oid}_{vid}.json"
    get_url = f"https://api.github.com/repos/{repo}/contents/{filename}"
    req_get = urllib.request.Request(get_url, headers=api_headers)
    sha = None
    try:
        with urllib.request.urlopen(req_get) as resp:
            data = json.loads(resp.read().decode())
            sha = data.get("sha")
    except Exception:
        pass

    put_data = {
        "message": f"Update cache {filename}",
        "content": base64.b64encode(json_str.encode()).decode(),
        "branch": "main"
    }
    if sha:
        put_data["sha"] = sha

    req_put = urllib.request.Request(
        get_url,
        data=json.dumps(put_data).encode(),
        headers=api_headers,
        method="PUT"
    )
    try:
        with urllib.request.urlopen(req_put) as resp:
            pass
    except Exception:
        pass
