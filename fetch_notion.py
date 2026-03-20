#!/usr/bin/env python3
"""
fetch_notion.py
Busca dados do banco de dados do Notion via API oficial e salva em data.json.
Executado pelo GitHub Actions periodicamente.
"""

import json
import os
import sys
from datetime import datetime, timezone
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# ── Configuração ──────────────────────────────────────────────────────────────
NOTION_TOKEN   = os.environ["NOTION_TOKEN"]
DATABASE_ID    = "3283838fa826804bbd51f348624b7ed6"
OUTPUT_FILE    = "data.json"
NOTION_VERSION = "2022-06-28"
# ─────────────────────────────────────────────────────────────────────────────


def notion_request(endpoint: str, payload=None) -> dict:
    url = f"https://api.notion.com/v1/{endpoint}"
    data = json.dumps(payload).encode() if payload is not None else b"{}"
    req = Request(
        url,
        data=data,
        method="POST" if payload is not None else "GET",
        headers={
            "Authorization":  f"Bearer {NOTION_TOKEN}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type":   "application/json",
        },
    )
    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        body = e.read().decode()
        print(f"Erro HTTP {e.code}: {body}", file=sys.stderr)
        sys.exit(1)
    except URLError as e:
        print(f"Erro de rede: {e}", file=sys.stderr)
        sys.exit(1)


def get_text(prop: dict) -> str:
    items = prop.get("rich_text") or prop.get("title") or []
    return "".join(t.get("plain_text", "") for t in items).strip()


def get_date(prop: dict, field: str = "start") -> str:
    d = prop.get("date")
    if not d:
        return ""
    value = d.get(field) or ""
    return value[:10] if value else ""


def get_url(prop: dict) -> str:
    return prop.get("url") or ""


def parse_page(page: dict) -> dict:
    props = page.get("properties", {})

    def p(name):
        return props.get(name, {})

    item = {}

    # Nome / título
    for col in ("Nome do Evento", "Nome", "Título", "Evento", "Name", "Title"):
        val = get_text(p(col))
        if val:
            item["nome"] = val
            break

    # Instituição
    for col in ("Instituição", "Instituicao"):
        val = get_text(p(col))
        if val:
            item["instituicao"] = val
            break

    # Datas
    data_ini = get_date(p("Data Inicial"), "start")
    data_fim = get_date(p("Data Final"), "start")
    if not data_ini:
        data_ini = get_date(p("Data"), "start")
    if not data_fim:
        data_fim = get_date(p("Data"), "end")
    if data_ini:
        item["data_inicial"] = data_ini
    if data_fim:
        item["data_final"] = data_fim

    # Local
    for col in ("Endereço/Local", "Endereço / Local", "Local", "Endereço"):
        val = get_text(p(col))
        if val:
            item["local"] = val
            break

    # Horários
    for col in ("Horário Inicial", "Horário Inicial "):
        val = get_text(p(col))
        if val:
            item["horario_inicial"] = val
            break

    for col in ("Horário Final", "Horário Final "):
        val = get_text(p(col))
        if val:
            item["horario_final"] = val
            break

    # Link de inscrição
    for col in ("Link de inscrição", "Link de Inscrição", "Link Inscrição", "Inscrição"):
        val = get_url(p(col)) or get_text(p(col))
        if val:
            item["link_inscricao"] = val
            break

    # Observações
    for col in ("Observações", "Observacoes"):
        val = get_text(p(col))
        if val:
            item["observacoes"] = val
            break

    return item


def fetch_all_pages() -> list:
    results = []
    payload = {"page_size": 100}

    while True:
        data = notion_request(f"databases/{DATABASE_ID}/query", payload)
        results.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        payload["start_cursor"] = data["next_cursor"]

    return results


def main():
    print(f"Consultando banco de dados: {DATABASE_ID}")
    pages = fetch_all_pages()
    print(f"Páginas retornadas pela API: {len(pages)}")

    # Mostra propriedades do primeiro item para diagnóstico
    if pages:
        print("\nPropriedades encontradas:")
        for key in pages[0].get("properties", {}).keys():
            print(f"  - {key}")

    items = []
    for page in pages:
        item = parse_page(page)
        if item.get("nome"):
            items.append(item)

    items.sort(key=lambda x: x.get("data_inicial", ""))

    output = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "total": len(items),
        "items": items,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ {len(items)} eventos salvos em {OUTPUT_FILE}")


if __name__ == "__main__":
    main()