# Contexto — Migração para WebP + Deploy HostGator (M6)

**Data:** 09/07/2026 · **Status:** deploy em andamento, pendências no final deste documento

Registro desta sessão para quem continuar o trabalho (ou eu mesmo, numa conversa nova):
o que mudou, por quê, o que já foi testado, e exatamente onde parou.

---

## 1. Por que migrar

O sistema lia as imagens de parquets com fragmentos base64 (contrato antigo,
ver `MAPEAMENTO.md`): ~890 MB de dados, decodificados inteiros no navegador a cada
visita — minutos de carregamento na primeira vez. Pedido do usuário: trocar a leitura
para um diretório de imagens em WebP, servidas sob demanda.

## 2. O que mudou

### Dados
- **Antes:** `data/*.parquet` (colunas INDICE/IWP/MimeType/Pic, fragmentos de 25.000
  chars base64) + `uploads/{squad}/` (originais JPEG/PNG) + `data/uploads-{squad}.parquet`
  (regenerado a cada upload).
- **Depois:** um arquivo WebP por imagem em `imagens/{squad}/{codigo} - {vista}.webp`.
  Migração feita por `migrar_para_webp.py` (roda uma vez, lê os parquets antigos,
  decodifica e converte via Pillow). Resultado: **21.316 imagens** (classificação) +
  **910** (britagem), zero falhas, contagem conferida batendo com o log.
- `data/`, `uploads/` e os `manifest.json` de cada squad **já foram apagados** depois
  da migração validada (não são mais lidos por nada).

### Backend (`app.py`)
- Novo endpoint `GET /api/pacotes/{squad}` — lista `imagens/{squad}/*.webp`, agrupa por
  código, junta a descrição do SQLite, devolve a URL de cada vista. Substitui o antigo
  `GET /api/imagens/{squad}` (que só devolvia o `manifest.json`).
- `POST /api/upload` agora converte a imagem pra WebP (Pillow, qualidade 80) e grava
  direto em `imagens/{squad}/` — sem regenerar parquet.
- Removida toda a lógica de parquet: `regenerar_parquet_uploads()`, `iwps_da_base()`,
  `_base_iwps`, `FRAGMENTO`. Removida também `regenerar_dicionario()` (gerava
  `data/dicionario.json`, que ninguém mais lê — disciplinas/descrições agora vêm ao
  vivo da API).
- `dir_squad()` agora valida o squad contra `squads.json` (antes exigia
  `manifest.json`).

### Frontend (`classificacao.html` / `britagem.html`)
- Removida toda a leitura de parquet no navegador (PyArrow-JS via CDN — dynamic
  imports de `hyparquet`/`hyparquet-compressors`, fallback de seleção manual de
  arquivo).
- Substituída por: `fetch('../api/disciplinas')` + `fetch('../api/pacotes/' + SQUAD)`
  no `inicializar()`. `SQUAD` é deduzido do próprio nome do arquivo HTML
  (`location.pathname.split('/').pop().replace(/\.html$/, '')`).
- O resto do app (render da lista, filtros, paginação, lightbox, impressão) **não
  mudou** — só a etapa de carregamento dos dados, porque o formato de `PACOTES` já
  era o mesmo.

### Consequência arquitetural importante
**O site deixou de ser 100% estático.** Antes, dava pra publicar só HTML/CSS/parquet/
JSON por FTP num host sem Python. Agora toda carga de página depende do backend
respondendo `/api/pacotes/{squad}` e `/api/disciplinas` — é isso que gerou toda a
segunda parte deste documento (o deploy no HostGator).

---

## 3. Achado de segurança (durante o deploy)

`app.mount("/", StaticFiles(directory=ROOT, html=True))` serve **tudo** dentro da
pasta do projeto como estático — inclusive `awp.db` (banco SQLite completo) e `app.py`
(código-fonte). Confirmado publicamente baixável (`curl` retornando 200) tanto nos
arquivos estáticos antigos ainda em `public_html` quanto no próprio backend rodando
localmente, antes do fix.

**Fix aplicado em `app.py`:** middleware `bloquear_arquivos_internos()` bloqueia com
404 qualquer request pra `.py`, `.db`, `.md`, `.pyc`, `requirements.txt`,
`.gitignore`, ou dentro de `.git/`, `.claude/`, `__pycache__/` — roda antes do mount
estático. Testado local: `awp.db`/`app.py`/`requirements.txt`/`README.md` → 404;
`index.html`/`/api/pacotes/...`/`/imagens/...` → 200 normalmente.

---

## 4. Deploy no HostGator — o que descobrimos

- Plano HostGator (Start_50, compartilhado, servidor br110) **roda Python sim**, ao
  contrário do que a documentação antiga do projeto assumia — via cPanel
  **Application Manager** (o nome mudou; nas versões novas do tema Jupiter não é mais
  "Setup Python App").
- Application Manager usa **Phusion Passenger**. Passenger detecta automaticamente um
  arquivo `passenger_wsgi.py` na raiz do app — não tem campo pra configurar "entry
  point" ou "startup file" na interface, é convenção.
- Como o FastAPI é **ASGI** e o Passenger espera **WSGI**, criei `passenger_wsgi.py`:
  ```python
  from a2wsgi import ASGIMiddleware
  from app import app as _fastapi_app
  application = ASGIMiddleware(_fastapi_app)
  ```
  E adicionei `a2wsgi>=1.10` ao `requirements.txt`.
- Dependências (`pip install -r requirements.txt`) precisam ser instaladas via
  **Terminal do cPanel**, com o virtualenv do app ativado (comando exato aparece na
  tela do app depois de registrado) — não é um botão automático na interface, pelo
  que vimos até agora.

### Decisão: subcaminho, não raiz do domínio

Ao registrar, "Caminho do aplicativo" = `dicionario-awp` gerou
**Base Application URL = `digitalprojectawp.online/dicionario-awp`** — ou seja, o app
só responde nesse subcaminho, não no domínio raiz. Perguntado, o usuário confirmou
que quer manter assim (mais simples que reconfigurar a raiz).

**Consequência:** o endereço real do site published passa a ser
`https://digitalprojectawp.online/dicionario-awp/index.html` — não mais
`.../index.html` na raiz (que continua sendo o site estático antigo, ainda não
decomissionado).

**Bug de código causado por isso, já corrigido:** `GET /api/pacotes/{squad}` gerava
URL de imagem **absoluta** (`/imagens/{squad}/...`), que sempre resolve pra raiz do
domínio no navegador — quebraria sob o subcaminho. Trocado para **relativa**
(`../imagens/{squad}/...`), que funciona tanto na raiz quanto em qualquer subcaminho,
sem depender de propagação de `root_path`/`SCRIPT_NAME` pelo Passenger/a2wsgi (não
testada em produção).

---

## 5. Pendências — retomar por aqui

1. **Confirmar que a raiz do domínio (`public_html`, site antigo) foi limpa** —
   `awp.db`, `app.py`, `requirements.txt` estavam expostos lá (200 OK via curl). Ainda
   não confirmado se o usuário apagou.
2. **Reenviar o `app.py` atualizado** (fix da URL relativa) para dentro de
   `dicionario-awp/` via FTP. Os outros arquivos (`awp.db`, `requirements.txt`,
   `passenger_wsgi.py`, `assets/`, `imagens/` — 434 MB —, HTMLs, `squads.json`) já
   foram enviados.
3. **Instalar dependências + reiniciar o app.** Última checagem:
   `https://digitalprojectawp.online/dicionario-awp/api/disciplinas` ainda voltava 404
   (página padrão da HostGator, não o FastAPI). Pedido print da parte de baixo da tela
   "Edit Your Application" (depois de "Environment Variables") pra ver se tem botão
   "Run Pip Install"/"Restart" — ainda não recebido.
4. **Revalidar depois de funcionar:**
   - `/dicionario-awp/api/disciplinas` e `/dicionario-awp/api/pacotes/{squad}`
     devolvendo JSON (não HTML)
   - Imagens carregando dentro de `/dicionario-awp/classificacao/classificacao.html`
     (confirma o fix da URL relativa)
   - Os 3 squads aparecem: `classificacao`, `britagem`, `usina` (este último criado
     pelo usuário testando a aplicação)
   - Re-testar que `awp.db`/`app.py` continuam bloqueados (404) mesmo com o backend
     rodando de verdade em produção

---

## 6. Arquivos deste projeto relacionados

| Arquivo | Papel |
|---|---|
| `migrar_para_webp.py` | migração única (já rodou) — histórico, não roda mais sem `data/` |
| `passenger_wsgi.py` | ponte WSGI pro Passenger rodar o `app.py` (ASGI) no HostGator |
| `requirements.txt` | agora inclui `a2wsgi` |
| `README.md` / `GUIA.md` | atualizados pra nova arquitetura (backend obrigatório) |
| `MAPEAMENTO.md` | histórico da fase anterior (M0–M4), não atualizado, mantido como registro |
| `publicar-hostgator/index.html` | artefato do modelo estático antigo — não usado no deploy atual via Passenger |
