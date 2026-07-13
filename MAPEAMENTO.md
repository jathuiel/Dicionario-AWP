# MAPEAMENTO — Dicionário Visual AWP

**Data:** 07/07/2026 · **Fase:** 2 concluída em 08/07/2026 — módulos M0, M1, M2, M4 e M3 implementados e testados (`app.py`, `cadastro.html`, `upload.html`, `test_app.py`)

> **Deploy (decidido após este relatório):** hospedagem na HostGator, banco na pasta do projeto (risco OneDrive aceito pelo usuário), sem autenticação por ora. Atenção: plano compartilhado cPanel roda Python via Passenger (WSGI) — FastAPI é ASGI e exigirá o adaptador `a2wsgi` ou um plano VPS. Validar antes de publicar.

---

## 1. Inventário

### 1.1 Árvore de arquivos

```
Nova pasta/
├── index.html                        Landing page: escolha do squad (Classificação / Britagem)
├── assets/
│   ├── dicionario-pacotes.css        CSS único compartilhado pelos dois squads (~27 KB)
│   ├── logo vale.png                 Logo (não referenciado nos HTMLs atuais)
│   └── simbolo_verum_branco.png      Símbolo usado no header/sidebar
├── classificacao/
│   ├── classificacao.html            App completo (HTML + JS inline, ~30 KB)
│   └── manifest.json                 Lista de 14 parquets em ../data/
├── britagem/
│   ├── britagem.html                 IDÊNTICO byte a byte ao classificacao.html
│   └── manifest.json                 Lista de 1 parquet (CWA-221-CWP-004)
└── data/                             ~890 MB — fonte única de dados
    ├── CWP-001..006-CONTEXTO.parquet
    ├── CWP-001..006-ISOLADAS.parquet
    ├── 297-CWP-003-{CONTEXTO,ISOLADAS}.parquet
    └── CWA-221-CWP-004.parquet
```

**Achado importante:** `britagem.html` e `classificacao.html` são **idênticos** (diff vazio). A única diferença entre squads é o `manifest.json` ao lado de cada HTML. Qualquer mudança no app deve ser feita uma vez e copiada — ou, melhor, unificada na Fase 2.

### 1.2 Stack real

| Camada | Tecnologia | Origem |
|---|---|---|
| Frontend | HTML + JS vanilla inline (sem framework) | local |
| CSS | arquivo único em `assets/` | local |
| Leitura de parquet | `hyparquet` + `hyparquet-compressors` | CDN jsdelivr (ESM, import dinâmico) |
| Animações | `dotlottie-wc` | CDN unpkg + lottie.host |
| Dados | Apache Parquet (gerado com pyarrow 24.0.0) | `data/` |

Não há: package.json, node_modules, bundler, git, backend, banco. **O site exige internet** (CDNs) mesmo rodando local.

### 1.3 Onde o manifesto é carregado

Função `inicializar()` ([classificacao.html:694-719](classificacao/classificacao.html#L694-L719)):

1. `fetch('manifest.json')` → array de nomes de parquet;
2. para cada nome: `fetch('../data/' + encodeURIComponent(nome))`;
3. `lerParquetDeBuffer()` lê cada parquet via hyparquet;
4. `processarLinhasParquet(rows)` monta o estado `PACOTES` e chama `render()`.

Fallback: se qualquer fetch falha (ex.: aberto via `file://`), `mostrarCarregador()` exibe um seletor manual de arquivos `.parquet` (`carregarParquetManual`).

**Peculiaridade (não é bug hoje, mas é armadilha):** o manifesto já contém o prefixo `../data/`, e o código concatena `'../data/' + encodeURIComponent(nome)`. O resultado é uma URL tipo `../data/..%2Fdata%2Farquivo.parquet`, que só funciona porque o servidor decodifica `%2F` e normaliza o `..`. Funciona em `python -m http.server` e em Starlette/FastAPI StaticFiles, mas **deve ser testado explicitamente no M0** — é o ponto mais frágil do invariante "leitor não pode quebrar".

---

## 2. Fluxo de dados atual

### 2.1 Estrutura dos dados — NÃO é um JSON de lista de imagens

O `manifest.json` lista **parquets**, não imagens. As imagens vivem **dentro dos parquets, como base64 fragmentado**. Schema real (igual em todos os 15 arquivos):

| Coluna | Tipo | Conteúdo |
|---|---|---|
| `INDICE` | int64 | ordem do fragmento (1, 2, 3…) |
| `IWP` | string | código completo + nome da vista |
| `MimeType` | string | ex.: `image/jpeg` |
| `Pic` | string | fragmento base64 de **até 25.000 chars**; uma imagem = N linhas consecutivas concatenadas na ordem |

Exemplo real de linha:

```json
{
  "INDICE": 1,
  "IWP": "KS-N103101-294-S-MT-CWP-001-IWP-001 - Top Back ISO",
  "MimeType": "image/jpeg",
  "Pic": "/9j/4AAQSkZJRgABAQEAYABgAAD/..."  // 25000 chars; imagem continua nas linhas 2 e 3
}
```

O front remonta em `processarLinhasParquet()` ([classificacao.html:602-648](classificacao/classificacao.html#L602-L648)): agrupa por `(pacote, vista)` e concatena os fragmentos **na ordem em que as linhas chegam** — a ordem das linhas no parquet é contrato implícito. Qualquer gerador novo de parquet (M2) tem que preservar isso.

### 2.2 Convenção de nomes

Formato: `KS-N103101-{CWA}-{DISC}-MT-CWP-{nnn}-IWP-{nnn} - {Nome da Vista}`

O parse é posicional ([classificacao.html:614-625](classificacao/classificacao.html#L614-L625)): separa a vista pelo **último** `" - "`, exige **≥ 9 segmentos** separados por `-`, e extrai: `area = seg[2]`, `disc = seg[3]`, `cwp = seg[5]-seg[6]`, `iwp = seg[7]-seg[8]`. O segmento 5 (`MT`) é constante em 100% da base e não é usado pelo front.

### 2.3 Números reais da base (medidos)

| Métrica | Valor |
|---|---|
| Linhas (fragmentos) | 64.481 |
| Pacotes IWP únicos | 3.854 |
| Imagens (pacote × vista) | 22.224 |
| Volume total | ~890 MB (~40 KB base64/imagem) |
| CWAs | 221, 294, 295, 297 |
| Disciplinas | apenas `S` (Estruturas Metálicas) |
| CWPs | CWP-001 a CWP-006 |
| Linhas malformadas | 0 |

### 2.4 Como o front renderiza

Layout de 3 painéis (sidebar · lista · detalhe), tudo client-side:

- **Lista**: cards paginados (30/página) com busca por código e filtros por CWA/CWP/Disciplina — filtragem 100% em memória no browser;
- **Detalhe**: visualizador de vistas com navegação ‹ ›, lightbox fullscreen com teclado e swipe (mobile-first);
- **Impressão**: aba dedicada com preview A4 retrato/paisagem e `window.print()`.

**Consequência do modelo atual:** para abrir o site, o browser baixa e decodifica **os ~890 MB inteiros** (Classificação) antes de mostrar qualquer pacote. Isso é o teto de escalabilidade — cada novo CWP piora o carregamento de todos.

---

## 3. Restrições de hosting

O que é observável nos arquivos:

- **Não há nenhum vestígio de deploy**: sem config de servidor, sem CI, sem git. A pasta vive num diretório **sincronizado pelo OneDrive/SharePoint** (VERUM PARTNERS).
- O fallback de seleção manual de parquet existe explicitamente "para `file://`" (comentário no código) — forte indício de que hoje o site é **aberto direto do disco ou de pasta compartilhada**, sem servidor.
- HTTPS/portas/limites: **não determináveis** a partir dos arquivos.

**A confirmar com o usuário (bloqueia o M0):**
1. Onde o FastAPI vai rodar? (máquina local do time, VM, servidor Vale/Verum?)
2. Quantos usuários simultâneos esperados?
3. ⚠️ **SQLite dentro de pasta OneDrive é receita de corrupção** (sync concorrente com WAL). O banco e o serviço devem rodar **fora** do OneDrive; o OneDrive pode continuar sendo o destino de backup, não o diretório vivo.

---

## 4. Matriz de compatibilidade

| Módulo | Reuso do código atual | Esforço (h) | Risco | Bloqueio |
|---|---|---|---|---|
| **M0** — FastAPI servindo estático + `GET /api/imagens` | 100% do front intocado; API replica o array do manifest.json | 4 | Baixo (testar a URL com `%2F` — §1.3) | Definir host (§3) |
| **M1** — Cadastro de IWP | Convenção de nomes já formalizada (§2.2) vira validação; front atual não muda | 6 | Baixo | Nenhum |
| **M2** — Upload de imagens | **Alto**: backend grava parquet novo (pyarrow, fragmentos de 25.000 chars, ordem preservada) + adiciona ao manifesto → o leitor atual exibe sem nenhuma mudança no front | 10 | Médio (contrato de fragmentação/ordem; validar com imagem real ponta a ponta) | M0, M1 |
| **M3** — Consulta com filtros via API | Filtros client-side já existem; API indexa coluna `IWP` dos parquets (leitura só dessa coluna é rápida) + dados do cadastro | 6 | Baixo | M1 |
| **M4** — Importação xlsx | Nenhum código atual; openpyxl + validação da convenção do M1 | 6 | Baixo (definir template da planilha) | M1 |

---

## 5. Riscos e gaps

| # | Risco | Severidade | Mitigação |
|---|---|---|---|
| 1 | **SQLite em pasta OneDrive** → corrupção por sync concorrente | Alta | Banco fora do OneDrive; backup por cópia agendada para o OneDrive |
| 2 | **Carga total de ~890 MB por visita** e crescente | Alta (médio prazo) | Fora do escopo dos módulos, mas o M0 abre caminho: servir imagem por demanda via API no futuro |
| 3 | Contrato implícito de **ordem dos fragmentos** no parquet | Média | Teste ponta a ponta obrigatório no M2 (upload → parquet → render no front) |
| 4 | URL com `%2F` (§1.3) pode falhar em servidores estritos | Média | Teste no M0; se falhar, corrigir o manifest (remover prefixo) — mudança de 1 linha, mas testar o fallback `file://` |
| 5 | **Sem autenticação** — upload/cadastro abertos a qualquer um na rede | Média | Mínimo viável: chave de API ou HTTP Basic no FastAPI para rotas de escrita; leitura livre |
| 6 | Concorrência SQLite | Baixa | WAL mode + escala pequena de usuários; suficiente |
| 7 | CORS | Baixa | FastAPI serve o front → mesma origem, CORS desnecessário |
| 8 | Dependência de CDNs (hyparquet, lottie) → **site quebra sem internet** | Baixa | Opcional na Fase 2: vendorizar as libs em `assets/` |
| 9 | `britagem.html` duplicado do `classificacao.html` | Baixa | Unificar em um HTML parametrizado quando o M0 estiver no ar |

---

## 6. Recomendação final

**GO em todos os módulos.** A arquitetura FastAPI + SQLite é adequada à escala (milhares de pacotes, poucos usuários), e o desenho atual do leitor permite implementar upload **sem tocar no front** — o backend escreve parquet no mesmo contrato e o leitor já sabe exibir.

**Ordem recomendada:** `M0 → M1 → M2 → M4 → M3`

1. **M0** primeiro: é a fundação e o teste do invariante (front atual servido pelo FastAPI, byte a byte igual). `GET /api/imagens` devolve exatamente o array do manifest.json.
2. **M1** define o modelo de dados do cadastro (a convenção §2.2 vira schema + validação).
3. **M2** entrega o maior valor: upload que o leitor atual exibe sem mudança de front.
4. **M4** antes do M3: importação xlsx é cadastro em massa (mesma validação do M1), destrava a carga inicial de dados.
5. **M3** por último: os filtros de consulta já existem no client; a API de consulta agrega valor sobretudo depois que há dados cadastrados via M1/M4.

**Preservar:** os dois HTMLs e manifests como estão (invariante), o contrato do parquet (schema + fragmentação + ordem), o fallback `file://`.

**Refatorar (dentro da Fase 2, sem quebrar):** unificação dos HTMLs duplicados (risco 9) e correção da URL `%2F` (risco 4) — ambos só depois do M0 provar o baseline funcionando.

**Decisões pendentes do usuário antes do M0:** host de execução (§3, item 1) e política de autenticação para rotas de escrita (risco 5).
