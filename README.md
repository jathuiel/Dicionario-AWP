# Dicionário Visual AWP

Sistema de consulta visual e cadastro de pacotes de trabalho (IWP) do projeto **KS-N103101 — Usina**, com suporte a múltiplos squads, upload de imagens, cadastro em massa via xlsx e filtros avançados.

---

## 📋 Visão Geral

O Dicionário Visual AWP é uma aplicação web:
- **Backend**: FastAPI (Python) — gerencia dados, uploads, cadastros e serve as imagens
- **Frontend**: HTML/CSS/JS — busca os pacotes na API e exibe as imagens WebP diretamente (`<img src="...">`, sem processamento no navegador)
- **Dados**: SQLite (cadastros), arquivos WebP em `imagens/{squad}/` (uma imagem = um arquivo), JSON (configuração)

Os visualizadores **dependem do backend rodando** — cada carga de página busca a lista de pacotes em `GET /api/pacotes/{squad}` e o navegador carrega as imagens sob demanda (lazy, com cache HTTP), em vez de baixar toda a base de uma vez.

---

## 📁 Duas pastas, dois papéis

```
.
├── deploy/            # TUDO que roda em produção — é o que sobe pro servidor
├── README.md          # Este arquivo
├── GUIA.md            # Guia de utilização (operação, UI, troubleshooting)
├── MAPEAMENTO.md       # Histórico da fase anterior (parquets) — registro, não atualizado
├── CONTEXTO-MIGRACAO-WEBP-DEPLOY.md  # Log da migração WebP + deploy HostGator
├── migrar_para_webp.py # Script de migração única (já rodou; mantido como histórico)
├── padronizar_dados.py # Script one-time de padronização de dados (já rodou; idempotente, mantido como histórico)
├── templates/          # Template Excel de importação em massa
│   └── template-importacao-iwp.xlsx  # Aba 1: Dados (codigo/descricao), Aba 2: Instruções
├── awp.db.bak-v1       # Backup do banco antes da migração de schema (cópia de segurança)
├── awp.db.bak-v2-padronizado # Backup do banco após padronização de dados
└── publicar-hostgator/ # Artefato do modelo estático antigo — não usado no deploy atual
```

`deploy/` é a única pasta que precisa ir para o servidor. Tudo que fica na
raiz é documentação/ferramenta de desenvolvimento e **não deve ser
publicado** (evita expor `.git`, `.claude`, notas internas etc.).

---

## 🚀 Quick Start (rodar localmente)

### Requisitos
- Python 3.10+
- pip

### Instalação

```bash
# 1. Entrar na pasta que roda em produção
cd deploy

# 2. Instalar dependências (uma única vez)
pip install -r requirements.txt

# 3. Subir o servidor
python -m uvicorn app:app --port 8000

# 4. Abrir no navegador
# http://127.0.0.1:8000
```

---

## 📁 Estrutura de `deploy/`

```
deploy/
├── app.py                             # Backend FastAPI
├── passenger_wsgi.py                  # Ponte WSGI para o Passenger (cPanel/HostGator)
├── requirements.txt                   # Dependências Python
├── awp.db                             # SQLite — cadastros (IWP, disciplinas)
│
├── assets/                            # Estilos compartilhados, logos
│   ├── awp.css
│   ├── dicionario-pacotes.css
│   └── *.png
│
├── imagens/                           # Fonte única das imagens — servidas pelo backend
│   ├── classificacao/
│   │   ├── {codigo} - {vista}.webp    # Uma imagem = um arquivo (migradas + uploads)
│   │   └── .uploads.json              # Controle interno: quais vieram de upload
│   ├── britagem/
│   │   └── {codigo} - {vista}.webp
│   └── usina/
│       └── {codigo} - {vista}.webp
│
├── classificacao/classificacao.html   # Visualizador do squad Classificação
├── britagem/britagem.html             # Visualizador do squad Britagem
├── usina/usina.html                   # Visualizador do squad Usina
│
├── index.html                         # Página inicial (cartões de squads)
├── cadastro.html                      # Página de cadastro de IWPs
└── upload.html                        # Página de upload de imagens
```

Squads novos criados pela UI (`POST /api/squads`) entram automaticamente
dentro de `deploy/{slug}/{slug}.html` + `deploy/imagens/{slug}/` — não
precisam ser adicionados manualmente a essa lista.

---

## 💾 Estrutura de Dados

### 1. SQLite (`deploy/awp.db`)

Hierarquia normalizada com PKs inteiras e FKs pai→filho: **projeto → squad /
cwa → cwp → iwp**. `squad` e `cwa` são ambos filhos de `projeto`; `cwa` tem um
`squad_id` opcional (atribuição manual, feita depois — nasce `NULL`).

```sql
CREATE TABLE projeto (
    id     INTEGER PRIMARY KEY,
    codigo TEXT NOT NULL UNIQUE,          -- ex.: KS-N103101 (segmentos 0-1 do código IWP)
    nome   TEXT NOT NULL DEFAULT ''
);
CREATE TABLE squad (
    id         INTEGER PRIMARY KEY,
    projeto_id INTEGER NOT NULL REFERENCES projeto(id) ON DELETE RESTRICT,
    pasta      TEXT NOT NULL UNIQUE,      -- slug; casa com imagens/{pasta}/ e {pasta}/{pasta}.html
    nome       TEXT NOT NULL,
    icone      TEXT NOT NULL DEFAULT '📦'
);
CREATE TABLE disciplina (
    id     INTEGER PRIMARY KEY,
    codigo TEXT NOT NULL UNIQUE,          -- S, E, M, T, A... (1-5 caracteres)
    nome   TEXT NOT NULL
);
CREATE TABLE status (
    id    INTEGER PRIMARY KEY,
    nome  TEXT NOT NULL UNIQUE,
    ordem INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE cwa (
    id         INTEGER PRIMARY KEY,
    projeto_id INTEGER NOT NULL REFERENCES projeto(id) ON DELETE RESTRICT,
    squad_id   INTEGER REFERENCES squad(id) ON DELETE SET NULL,  -- atribuição manual posterior
    codigo     TEXT NOT NULL,             -- ex.: 294 (segmento 2)
    descricao  TEXT NOT NULL DEFAULT '',
    UNIQUE (projeto_id, codigo)
);
CREATE TABLE cwp (
    id            INTEGER PRIMARY KEY,
    cwa_id        INTEGER NOT NULL REFERENCES cwa(id) ON DELETE RESTRICT,
    disciplina_id INTEGER NOT NULL REFERENCES disciplina(id) ON DELETE RESTRICT,
    codigo        TEXT NOT NULL,          -- ex.: CWP-001 (segmentos 5-6)
    descricao     TEXT NOT NULL DEFAULT '',
    UNIQUE (cwa_id, disciplina_id, codigo)
);
CREATE TABLE iwp (
    id            INTEGER PRIMARY KEY,
    cwp_id        INTEGER NOT NULL REFERENCES cwp(id) ON DELETE RESTRICT,
    codigo        TEXT NOT NULL UNIQUE,   -- código COMPLETO — contrato com nomes de arquivo de imagem
    rotulo        TEXT NOT NULL,          -- ex.: IWP-042 (segmentos 7-8)
    descricao     TEXT NOT NULL DEFAULT '',
    status_id     INTEGER REFERENCES status(id) ON DELETE SET NULL,
    criado_em     TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    atualizado_em TEXT
);
```

**Formato do código IWP** (inalterado — é o contrato com os nomes de arquivo de imagem):
```
KS-N103101-{CWA}-{DISC}-MT-CWP-{nnn}-IWP-{nnn}
└──0───┘─1─┘└2┘  └3┘  4  └─5─┘─6┘   └7─┘8┘

Exemplo: KS-N103101-294-S-MT-CWP-001-IWP-042
  • projeto (segs. 0-1): KS-N103101
  • CWA (seg. 2): 294
  • DISC (seg. 3): S (Estruturas)
  • CWP (segs. 5-6): CWP-001
  • IWP (segs. 7-8): IWP-042
```
O segmento 4 (sempre "MT") fica só embutido no código completo — não tem
coluna própria, é uma decisão deliberada (não carrega informação distinta).

**Seeds** (só em banco recém-criado ou recém-migrado):

| disciplina.codigo | nome | | status.nome | ordem |
|---|---|---|---|---|
| S | Estruturas Metálicas | | Planejado | 1 |
| E | Elétrica | | Emitido | 2 |
| M | Mecânica | | Em execução | 3 |
| T | Tubulação | | Concluído | 4 |
| A | Arquitetura | | | |

**Estado atual (após padronização):**
- Projeto: 1 (KS-N103101 — Usina S11D)
- Squads: 3 (Classificação, Britagem, Usina)
- CWAs: 7 (todas com squad atribuído)
- CWPs: 17
- IWPs: 3.857 (todos com imagem em `deploy/imagens/{squad}/*.webp`)

Script one-time `padronizar_dados.py` (na raiz do projeto) executou a
padronização e foi mantido como histórico — é idempotente e pode rodar de novo
sem efeito colateral (verifica se os dados já estão padronizados antes de
proceeder). Backup após padronização: `awp.db.bak-v2-padronizado` (na raiz).

**Migração automática (v1 → v2):** o schema anterior (tabela `iwp` com o
código completo como chave primária e colunas `cwa`/`disc`/`cwp`/`iwp` soltas)
é detectado no startup (`PRAGMA table_info(iwp)` sem a coluna `cwp_id`) e
migrado automaticamente numa única passagem:

1. `awp.db` é copiado para `awp.db.bak-v1` antes de qualquer alteração (só se
   esse backup ainda não existir) — é a cópia de segurança real da migração.
2. `iwp` e `disciplina` antigas são renomeadas para `iwp_v1`/`disciplina_v1`
   durante a validação, depois removidas com `VACUUM` na limpeza final.
3. O schema novo é criado; disciplinas são importadas para a tabela `disciplina`.
4. `squads.json` (se existir) vira o projeto `KS-N103101` ("Usina S11D") + um
   squad por entrada — depois disso o arquivo deixa de ser lido pelo backend
   (foi removido após a padronização dos dados).
5. Cada linha de dados antigos é reimportada recompondo a cadeia
   projeto→cwa→disciplina→cwp via get-or-create, a partir do próprio código.

Rodar a aplicação com um `awp.db` v1 dispara a migração automaticamente; não
há passo manual. Se algo parecer errado, `awp.db.bak-v1` tem os dados originais intactos.

---

### 2. Imagens (`deploy/imagens/{squad}/*.webp`)

Cada imagem do dicionário é um arquivo WebP independente, nomeado no mesmo
contrato que já existia para código+vista:

```
imagens/{squad}/{codigo completo} - {vista}.webp

Exemplo: imagens/classificacao/KS-N103101-294-S-MT-CWP-001-IWP-042 - Top.webp
```

- **codigo**: código completo do IWP (formato de 9+ segmentos, ver seção 1)
- **vista**: nome livre (ex.: `Top`, `Front ISO`) — não pode conter `' - '` nem
  os caracteres `< > : " / \ | ? *` (reservados do Windows)

O backend serve esses arquivos diretamente (arquivo estático, com cache HTTP
e suporte a range requests) — não há mais concatenação de fragmentos nem
decodificação no navegador. `GET /api/pacotes/{squad}` lista o diretório,
agrupa os arquivos por código e devolve a URL pronta de cada vista.

`imagens/{squad}/.uploads.json` é um controle interno (lista de nomes de
arquivo) usado só para a página de upload saber quais imagens vieram de lá,
distinguindo-as das migradas da base original.

---

### 3. Dados Estáticos — Removidos

Após a migração para o schema normalizado, o backend lê toda a configuração
do SQLite (`deploy/awp.db`) — não há mais JSON estático de squads ou
disciplinas. Os leitores buscam `GET /api/disciplinas` e `GET /api/pacotes/{squad}`
(descrições vêm do banco a cada requisição).

**Arquivo `squads.json`** foi removido de `deploy/` após a padronização dos dados
(a função de importação só rodava se o arquivo existisse; após a migração, passou
a fonte para a tabela `squad`).

---

## 🔌 API — Endpoints

Documentação interativa: **http://127.0.0.1:8000/docs** (Swagger)

### Imagens

| Método | Rota | Função |
|---|---|---|
| GET | `/api/pacotes/{squad}` | Lista os pacotes do squad com descrição e URL de cada vista (WebP) — é o que os leitores consomem |
| GET | `/imagens/{squad}/{arquivo}.webp` | Serve o arquivo de imagem diretamente (estático, cacheável) |

---

### IWPs (Pacotes de Trabalho)

Os campos de resposta (`codigo, cwa, disc, cwp, iwp, descricao, criado_em,
status`) são os mesmos de antes da normalização — agora montados via JOIN em
vez de colunas diretas da tabela. Os filtros (`cwa`, `cwp`, `disc`) continuam
recebendo os **códigos** texto (ex.: `cwa=294`), não os ids internos.

| Método | Rota | Corpo | Função |
|---|---|---|---|
| POST | `/api/iwp` | `{"codigo": "...", "descricao": "..."}` | Cadastra IWP; cria projeto/CWA/disciplina/CWP por get-or-create se ainda não existirem. 409 se o código já existe |
| GET | `/api/iwp?cwa=&cwp=&disc=&busca=` | — | Lista IWPs; parâmetros vazios não filtram; todos combináveis |
| PATCH | `/api/iwp/{codigo}` | `{"descricao": "...", "status_id": n}` | Edita descrição e/ou status (campos independentes); marca `atualizado_em` |
| DELETE | `/api/iwp/{codigo}` | — | Exclui o cadastro. **As imagens não são apagadas** — ficam órfãs em `imagens/{squad}/` |
| GET | `/api/iwp/filtros` | — | Devolve valores distintos de CWA, CWP, Disciplina cadastrados |

**Exemplos:**
```bash
# Cadastrar
curl -X POST http://localhost:8000/api/iwp \
  -H "Content-Type: application/json" \
  -d '{"codigo": "KS-N103101-294-S-MT-CWP-001-IWP-042", "descricao": "Plataforma"}'

# Listar com filtro
curl "http://localhost:8000/api/iwp?cwa=294&disc=S"

# Editar descrição e/ou status
curl -X PATCH http://localhost:8000/api/iwp/KS-N103101-294-S-MT-CWP-001-IWP-042 \
  -H "Content-Type: application/json" \
  -d '{"descricao": "Plataforma norte (atualizado)", "status_id": 2}'

# Excluir
curl -X DELETE http://localhost:8000/api/iwp/KS-N103101-294-S-MT-CWP-001-IWP-042

# Filtros disponíveis
curl http://localhost:8000/api/iwp/filtros
```

---

### Disciplinas

| Método | Rota | Corpo | Função |
|---|---|---|---|
| GET | `/api/disciplinas` | — | Lista todas as disciplinas cadastradas (`id`, `codigo`, `nome`) |
| POST | `/api/disciplinas` | `{"codigo": "X", "nome": "..."}` | Cria ou edita disciplina (mesmo código = atualiza, preservando o id) |
| PATCH | `/api/disciplinas/{codigo}` | `{"nome": "..."}` | Edita o nome (equivalente ao POST por código) |
| DELETE | `/api/disciplinas/{codigo}` | — | Exclui disciplina. 409 se algum CWP a referencia |

---

### Projetos

| Método | Rota | Corpo | Função |
|---|---|---|---|
| GET | `/api/projetos` | — | Lista projetos |
| POST | `/api/projetos` | `{"codigo": "...", "nome": "..."}` | Cria projeto. 409 se o código já existe |
| PATCH | `/api/projetos/{id}` | `{"nome": "..."}` | Edita o nome |
| DELETE | `/api/projetos/{id}` | — | Exclui. 409 se houver squad(s)/CWA(s) vinculados |

---

### CWAs

| Método | Rota | Corpo | Função |
|---|---|---|---|
| GET | `/api/cwas?projeto_id=&squad_id=` | — | Lista CWAs; filtros opcionais |
| POST | `/api/cwas` | `{"projeto_id": n, "codigo": "...", "descricao": "..."}` | Cria CWA nesse projeto |
| PATCH | `/api/cwas/{id}` | `{"descricao": "...", "squad_id": n}` | Edita descrição e/ou atribui squad (campos independentes; `squad_id: null` limpa a atribuição) |
| DELETE | `/api/cwas/{id}` | — | Exclui. 409 se houver CWP(s) vinculado(s) |

---

### CWPs

CWPs nascem automaticamente do cadastro de IWP (get-or-create) — não há POST.

| Método | Rota | Corpo | Função |
|---|---|---|---|
| GET | `/api/cwps?cwa_id=` | — | Lista CWPs; filtro opcional por CWA |
| PATCH | `/api/cwps/{id}` | `{"descricao": "..."}` | Edita descrição |
| DELETE | `/api/cwps/{id}` | — | Exclui. 409 se houver IWP(s) vinculado(s) |

---

### Status do IWP

| Método | Rota | Corpo | Função |
|---|---|---|---|
| GET | `/api/status` | — | Lista status, ordenados por `ordem` |
| POST | `/api/status` | `{"nome": "...", "ordem": n}` | Cria status |
| PATCH | `/api/status/{id}` | `{"nome": "...", "ordem": n}` | Edita nome e/ou ordem (campos independentes) |
| DELETE | `/api/status/{id}` | — | Exclui; os IWPs com esse status ficam com `status_id` nulo (`ON DELETE SET NULL`) |

Seed padrão: Planejado (1), Emitido (2), Em execução (3), Concluído (4).

---

### Squads

| Método | Rota | Corpo | Função |
|---|---|---|---|
| GET | `/api/squads` | — | Lista squads (fonte: tabela `squad`) |
| POST | `/api/squads` | `{"nome": "...", "icone": "📦", "projeto_id": n}` | Cria novo squad (pasta + página HTML); `projeto_id` opcional se houver exatamente um projeto cadastrado |
| PATCH | `/api/squads/{id}` | `{"nome": "...", "icone": "...", "projeto_id": n}` | Edita (campos independentes) |
| DELETE | `/api/squads/{id}` | — | Exclui. 409 se houver CWA(s) apontando pro squad (reatribua antes); pasta/HTML ficam no disco |

---

### Upload de Imagens

| Método | Rota | Corpo | Função |
|---|---|---|---|
| POST | `/api/upload` | multipart: `squad`, `codigo`, `vista`, `arquivo` | Converte para WebP e grava em `imagens/{squad}/` |
| GET | `/api/upload/{squad}` | — | Lista as imagens enviadas via upload (não inclui as migradas da base) |

**Validações:**
- Arquivo: JPEG ou PNG, até 10 MB (validação por magic bytes)
- Código: formato completo, sem ` - ` (espaço-hífen-espaço)
- Vista: não-vazia, sem ` - `

Enviar de novo o mesmo código+vista **substitui** o arquivo `.webp` anterior
(`substituida: true` na resposta) — isso vale tanto para reenvios de upload
quanto para imagens migradas da base original.

**Exemplo:**
```bash
curl -X POST http://localhost:8000/api/upload \
  -F "squad=classificacao" \
  -F "codigo=KS-N103101-294-S-MT-CWP-001-IWP-042" \
  -F "vista=Top Front ISO" \
  -F "arquivo=@/caminho/para/imagem.jpg"
```

---

### Importação em Massa (XLSX)

| Método | Rota | Corpo | Função |
|---|---|---|---|
| POST | `/api/importar` | multipart: `arquivo` (.xlsx) | Importa IWPs da planilha; duplicados/inválidos não abortam o lote |

**Formato esperado:**
- Primeira aba, cabeçalho na linha 1
- Coluna `codigo` obrigatória
- Coluna `descricao` opcional
- Linhas em branco são ignoradas

**Resposta:**
```json
{
  "importados": 10,
  "duplicados": [
    {"linha": 5, "codigo": "KS-N103101-294-S-MT-CWP-001-IWP-042"}
  ],
  "invalidos": [
    {"linha": 7, "codigo": "código-ruim", "motivo": "formato inválido"}
  ]
}
```

---

## 🏗️ Arquitetura

### Fluxo de Consulta (Leitor — depende do backend)

```
1. Browser acessa: http://site/classificacao/classificacao.html
2. JS busca GET /api/disciplinas (nomes das disciplinas)
3. JS busca GET /api/pacotes/classificacao
   → backend lista imagens/classificacao/*.webp, agrupa por código,
     junta a descrição (SQLite) e devolve a URL de cada vista
4. Frontend renderiza lista, filtros e lightbox com <img src="...">
5. O navegador baixa cada imagem sob demanda (lazy) — cache HTTP normal
```

**Vantagem:** carga inicial em segundos (não baixa a base inteira), cache do
navegador funciona por imagem. **Custo:** o leitor não roda mais 100%
estático — precisa do backend respondendo.

### Fluxo de Upload

```
1. POST /api/upload (squad, codigo, vista, arquivo)
2. Backend valida código, vista, mimetype (magic bytes)
3. Converte a imagem para WebP em memória (Pillow)
4. Grava em imagens/{squad}/{codigo} - {vista}.webp
   (substitui se já existir um arquivo com esse nome)
5. Responde com a URL da imagem
6. Próxima recarga do dicionário já mostra a nova vista
```

### Fluxo de Cadastro

```
1. POST /api/iwp ou PATCH /api/iwp/{codigo}
2. Backend valida formato do código (9+ segmentos separados por -)
3. Armazena em awp.db com timestamp
4. Próxima carga do leitor já reflete a mudança — GET /api/pacotes/{squad}
   lê a descrição direto do SQLite a cada requisição
```

---

## 🛠️ Desenvolvimento

### Rodar com auto-reload

```bash
cd deploy
python -m uvicorn app:app --port 8000 --reload
```

### Estrutura do código (`deploy/app.py`)

```
Imports & Constantes
├── ROOT, DB, IMAGENS, SQUADS_JSON
├── MAX_UPLOAD, QUALIDADE_WEBP
└── MAGIC (validação de mimetype)

Banco de Dados
├── db() — conexão SQLite (PRAGMA foreign_keys = ON)
├── _get_or_create() / _atualizar() — helpers genéricos reusados pelo CRUD
├── _criar_schema() — DDL das 7 tabelas (projeto/squad/disciplina/status/cwa/cwp/iwp)
├── _seed_disciplinas_padrao() / _seed_status_padrao() / _importar_squads_json()
├── cadeia_ids() — get-or-create projeto→cwa→disciplina→cwp (usada por criar_iwp,
│   importar_xlsx e pela migração)
├── _migrar_v1_para_v2() — schema antigo → novo, numa passagem
└── _preparar_banco() — decide criar/migrar/nada, roda no import do módulo

Parsing
└── parse_codigo() — valida e decompõe código (inclui "projeto" desde o M7)

API — Leitura
├── GET /api/pacotes/{squad} — agrupa imagens/{squad}/*.webp por código
├── GET /api/iwp, GET /api/iwp/filtros
└── GET /api/disciplinas, /api/projetos, /api/cwas, /api/cwps, /api/status, /api/squads

API — Escrita (IWPs)
├── POST /api/iwp — criar (get-or-create da cadeia)
├── PATCH /api/iwp/{codigo} — editar descrição e/ou status
└── DELETE /api/iwp/{codigo} — excluir (não apaga imagens)

API — Escrita (hierarquia: Projetos, CWAs, CWPs, Status, Disciplinas)
└── CRUD por entidade — GET/POST/PATCH/DELETE; 409 em violação de FK RESTRICT

API — Squads
├── GET /api/squads — lê da tabela squad
├── POST /api/squads — cria pasta + página HTML, grava na tabela
├── PATCH /api/squads/{id}
└── DELETE /api/squads/{id} — 409 se houver CWA vinculada

Upload de Imagens
├── dir_squad() — valida squad (tabela squad), devolve imagens/{squad}/
├── registrar_upload() / registro_uploads() — controle de quais vieram de upload
├── POST /api/upload — valida, converte para WebP, grava o arquivo
└── GET /api/upload/{squad} — lista imagens enviadas por upload

Importação XLSX
└── POST /api/importar — processa planilha, get-or-create da cadeia, retorna relatório

Montagem Final
└── app.mount("/", StaticFiles(...)) — serve HTML/CSS/JS e imagens/ estáticos
```

`ROOT = Path(__file__).resolve().parent` — todos os caminhos (banco e
imagens) são resolvidos relativos ao próprio `app.py`. Isso é o que torna
`deploy/` uma pasta autocontida: mover/copiar `deploy/` inteira pra qualquer
lugar (outra máquina, outro servidor) funciona sem tocar em código.

---

## 🌐 Deployment — HostGator

Desde a migração para WebP (M6), os leitores **não são mais estáticos**: toda
carga de página depende do backend respondendo `/api/pacotes/{squad}`,
`/api/disciplinas` e servindo os arquivos em `/imagens/`. O backend precisa
estar rodando no host de destino (HostGator com suporte a Python/WSGI, VPS,
etc.) — não basta publicar arquivos estáticos por FTP.

**O que sobe:** o conteúdo de `deploy/` — e só ele. É uma pasta autocontida
(ver nota sobre `ROOT` acima), então:

1. Envie **todo o conteúdo de `deploy/`** para a raiz do app no servidor
   (ex.: via FTP para `dicionario-awp/` no cPanel) — `app.py`, `passenger_wsgi.py`,
   `requirements.txt`, `awp.db`, `assets/`, `imagens/` e os HTMLs.
   **Não envie a pasta `deploy/` como subpasta** — o conteúdo *dela* é a raiz
   do app no servidor.
2. No cPanel → **Application Manager**, registre o app apontando para essa
   pasta; o Passenger detecta `passenger_wsgi.py` automaticamente (convenção,
   sem campo de "entry point").
3. Instale as dependências (`pip install -r requirements.txt`) via Terminal
   do cPanel, com o virtualenv do app ativado.
4. Reinicie o app pelo Application Manager.

**O que não sobe (fica só no repositório local):** tudo na raiz do projeto
fora de `deploy/` — `README.md`, `GUIA.md`, `MAPEAMENTO.md`,
`CONTEXTO-MIGRACAO-WEBP-DEPLOY.md`, `migrar_para_webp.py`,
`publicar-hostgator/`, `.git/`, `.claude/`.

Detalhes de configuração do Passenger, subcaminho do app e pendências desta
migração estão em [CONTEXTO-MIGRACAO-WEBP-DEPLOY.md](CONTEXTO-MIGRACAO-WEBP-DEPLOY.md).

---

## 📚 Referências

- **Guia de utilização:** [GUIA.md](GUIA.md) — operação, UI, solução de problemas
- **Documentação interativa:** http://127.0.0.1:8000/docs (Swagger)
- **FastAPI:** https://fastapi.tiangolo.com/
- **Pillow (conversão WebP):** https://pillow.readthedocs.io/

---

## 📝 Notas

- **OneDrive sincronização:** Para produção, não rodar a API dentro de pasta OneDrive (risco de lock em arquivo db durante sync). Use OneDrive apenas como backup.
- **Lock de upload:** Usa lock global — adequado para poucos usuários. Escalar para lock por squad se houver contenção real de requisições simultâneas.
- **Scripts históricos:** `migrar_para_webp.py` e `padronizar_dados.py` (na raiz, fora de `deploy/`) já rodaram e foram mantidos como registro. Ambos são idempotentes. Backups de segurança: `awp.db.bak-v1` (pré-migração) e `awp.db.bak-v2-padronizado` (pós-padronização), ambos na raiz do projeto.
- **Segurança:** Validação de mimetype por magic bytes, validação de formato de código obrigatória, squad validado contra tabela `squad` (SQLite) antes de servir/gravar imagens. Middleware em `app.py` bloqueia com 404 qualquer request para `.py`/`.db`/`.md`/`.pyc`, `requirements.txt`, `.gitignore` ou pastas `.git`/`.claude`/`__pycache__`.
