# Agenda da Rede

Site estático hospedado no GitHub Pages que exibe eventos da tabela pública do Notion, atualizado automaticamente a cada 6 horas via GitHub Actions.

## Estrutura

```
├── index.html          # Site principal
├── fetch_notion.py     # Script que faz scraping do Notion
├── data.json           # Gerado automaticamente (não editar)
└── .github/
    └── workflows/
        └── update.yml  # GitHub Action de atualização
```

## Como configurar

### 1. Crie o repositório no GitHub

Crie um repositório público (ex: `agenda-da-rede`) e faça o push desses arquivos.

### 2. Ative o GitHub Pages

- Vá em **Settings → Pages**
- Em **Source**, selecione **Deploy from a branch**
- Selecione o branch `main` e a pasta `/ (root)`
- Clique em **Save**

Seu site estará disponível em:
`https://seu-usuario.github.io/agenda-da-rede`

### 3. Rode o Action pela primeira vez

- Vá em **Actions → Atualizar Agenda**
- Clique em **Run workflow**

Isso vai gerar o `data.json` inicial. A partir daí, o site atualiza automaticamente a cada 6 horas.

### 4. Ajuste as colunas (se necessário)

Se os nomes das colunas da sua tabela forem diferentes, edite o `COLUMN_MAP` no `fetch_notion.py`:

```python
COLUMN_MAP = {
    "Nome da coluna no Notion": "chave_no_json",
    ...
}
```

As chaves do JSON usadas no site são:
- `nome` — título do evento
- `instituicao` — instituição
- `data_inicial` / `data_final` — datas (YYYY-MM-DD)
- `horario_inicial` / `horario_final` — horários
- `local` — endereço ou local
- `link_inscricao` — URL de inscrição
- `observacoes` — observações

## Atualização manual

Você pode forçar uma atualização a qualquer momento em:
**Actions → Atualizar Agenda → Run workflow**

## Frequência de atualização

Para mudar o intervalo, edite o cron em `.github/workflows/update.yml`:

```yaml
- cron: '0 */6 * * *'   # a cada 6 horas (padrão)
- cron: '0 */1 * * *'   # a cada 1 hora
- cron: '0 8,20 * * *'  # às 8h e 20h todo dia
```
