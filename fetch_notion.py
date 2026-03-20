#!/usr/bin/env python3
"""
fetch_notion.py
Faz scraping da tabela pública do Notion e salva em data.json.
Executado pelo GitHub Actions periodicamente.
"""

import json
import re
import sys
from datetime import datetime, timezone
from urllib.request import urlopen, Request
from urllib.error import URLError
from html.parser import HTMLParser

# ── Configuração ──────────────────────────────────────────────────────────────
NOTION_URL = "https://sour-iberis-b64.notion.site/3283838fa8268033bc5dca68dc28d277?v=3283838fa82680478a0e000cbe4eb044"
OUTPUT_FILE = "data.json"
# ─────────────────────────────────────────────────────────────────────────────


def fetch_html(url: str) -> str:
    """Busca o HTML da página pública do Notion."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    }
    req = Request(url, headers=headers)
    try:
        with urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except URLError as e:
        print(f"Erro ao buscar a página: {e}", file=sys.stderr)
        sys.exit(1)


class NotionTableParser(HTMLParser):
    """
    Parser simples que extrai linhas de uma tabela do Notion.
    O Notion renderiza a galeria/tabela como divs com classes específicas.
    Esta implementação coleta texto por célula e mapeia às colunas.
    """

    def __init__(self):
        super().__init__()
        self.headers: list[str] = []
        self.rows: list[list[str]] = []
        self._in_header = False
        self._in_cell = False
        self._current_cell: list[str] = []
        self._current_row: list[str] = []
        self._depth = 0
        self._header_done = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        cls = attrs_dict.get("class", "")

        # Notion usa th para cabeçalhos e td para células em view de tabela
        if tag == "th":
            self._in_header = True
            self._current_cell = []
        elif tag == "td":
            self._in_cell = True
            self._current_cell = []

    def handle_endtag(self, tag):
        if tag == "th" and self._in_header:
            self._in_header = False
            self.headers.append(self._clean(" ".join(self._current_cell)))
            self._current_cell = []
        elif tag == "td" and self._in_cell:
            self._in_cell = False
            self._current_row.append(self._clean(" ".join(self._current_cell)))
            self._current_cell = []
        elif tag == "tr":
            if self._current_row:
                self.rows.append(self._current_row)
                self._current_row = []

    def handle_data(self, data):
        if self._in_header or self._in_cell:
            stripped = data.strip()
            if stripped:
                self._current_cell.append(stripped)

    @staticmethod
    def _clean(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()


def normalize_date(value: str) -> str:
    """Tenta normalizar datas para YYYY-MM-DD."""
    if not value:
        return ""
    # Tenta DD/MM/YYYY
    m = re.match(r"^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})$", value.strip())
    if m:
        d, mo, y = m.groups()
        return f"{y}-{mo.zfill(2)}-{d.zfill(2)}"
    # Já está em YYYY-MM-DD
    if re.match(r"^\d{4}-\d{2}-\d{2}$", value.strip()):
        return value.strip()
    # Retorna como veio
    return value.strip()


# Mapeamento: nome da coluna no Notion → chave no JSON
# Ajuste os nomes da esquerda para bater exatamente com os cabeçalhos da sua tabela.
COLUMN_MAP = {
    # Notion column name       : json key
    "Nome":                      "nome",
    "Título":                    "nome",
    "Evento":                    "nome",
    "Instituição":               "instituicao",
    "Data Inicial":              "data_inicial",
    "Data Final":                "data_final",
    "Endereço/Local":            "local",
    "Local":                     "local",
    "Horário Inicial":           "horario_inicial",
    "Horário Final":             "horario_final",
    "Link de inscrição":         "link_inscricao",
    "Link de Inscrição":         "link_inscricao",
    "Observações":               "observacoes",
    "Observações ":              "observacoes",  # com espaço extra, por precaução
}

DATE_KEYS = {"data_inicial", "data_final"}


def parse_items(headers: list[str], rows: list[list[str]]) -> list[dict]:
    items = []
    for row in rows:
        item: dict = {}
        for i, header in enumerate(headers):
            if i >= len(row):
                continue
            value = row[i].strip()
            if not value:
                continue
            key = COLUMN_MAP.get(header)
            if key:
                if key in DATE_KEYS:
                    value = normalize_date(value)
                item[key] = value
        if item.get("nome"):  # ignora linhas sem nome
            items.append(item)
    return items


def main():
    print(f"Buscando: {NOTION_URL}")
    html = fetch_html(NOTION_URL)

    parser = NotionTableParser()
    parser.feed(html)

    print(f"Cabeçalhos encontrados: {parser.headers}")
    print(f"Linhas encontradas: {len(parser.rows)}")

    if not parser.headers:
        print(
            "⚠️  Nenhum cabeçalho encontrado. "
            "O Notion pode ter mudado o HTML ou a página não está em modo tabela.",
            file=sys.stderr,
        )
        # Salva data.json vazio para não quebrar o site
        items = []
    else:
        items = parse_items(parser.headers, parser.rows)

    output = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "total": len(items),
        "items": items,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✅ {len(items)} eventos salvos em {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
