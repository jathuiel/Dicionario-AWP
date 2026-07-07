# Dicionário Visual de Pacotes AWP BIM

Aplicação web para consulta e impressão de pacotes de trabalho AWP do **Projeto KS-N103101 — Usina Vale S11D**. Exibe as vistas do modelo BIM (Frontal, Traseira, Laterais, Superior, Isométrica) para cada IWP, com filtros, busca e pré-visualização de impressão.

---

## Funcionalidades

### Consulta de pacotes
- Lista paginada (30 por página) com todos os IWPs cadastrados.
- Busca em tempo real pelo código do pacote (IWP, CWP).
- Filtros por **CWA** (área), **CWP** e **Disciplina** (Estruturas Metálicas, Elétrica, Mecânica, Tubulação, Arquitetura).
- Painel de filtros recolhível.
- Contador de resultados.

### Painel de detalhe
- Informações completas do pacote (ID, Projeto, CWA, CWP, IWP, Disciplina).
- Visualizador de vistas BIM com navegação sequencial (botões ‹ ›).
- Link para abrir a imagem original em nova aba.

### Lightbox
- Visualização em tela cheia de qualquer vista.
- Navegação por setas ou pelas teclas `←` `→` do teclado.
- Fechamento com `Esc` ou clique no fundo.

### Impressão
- Pré-visualização fiel ao papel com tabela de dados e galeria de vistas.
- Alternância de orientação **Retrato / Paisagem** antes de imprimir.
- Data de geração automática no rodapé.

### Responsividade mobile
- Cabeçalho e navegação inferior adaptados para telas pequenas.
- Painel deslizante: lista → detalhe (slide horizontal).
- Swipe para trocar vista no visualizador ou navegar no lightbox.
- Swipe da borda esquerda para voltar à lista.

---

## Estrutura de arquivos

```
├── index.html                    # Landing: seleção de squad (Classificação / Britagem)
├── classificacao/
│   ├── classificacao.html        # Página do dicionário (lógica inline no <script>)
│   └── data/
│       ├── manifest.json         # Lista dos parquets a carregar (na ordem)
│       └── *.parquet             # Bases de imagens (base64) — nomes livres
├── britagem/
│   ├── britagem.html             # Mesma estrutura de classificacao.html
│   └── data/
│       └── manifest.json
├── assets/
│   ├── dicionario-pacotes.css    # Estilos (tokens Vale, layout, responsivo)
│   ├── logo vale.png
│   └── simbolo_verum_branco.png
├── DESIGN-SYSTEM.md              # Design system: tokens, tipografia e componentes
└── Padroes de Commit.md          # Convenção de commits do projeto
```

### Manifesto da base de dados

Cada página carrega os parquets listados no `manifest.json` da sua própria pasta `data/`, na ordem em que aparecem:

```json
[
  "Lista de Imagens - Contexto.parquet",
  "Lista de Imagens - Isoladas.parquet"
]
```

Os nomes são **livres** — é possível nomear os arquivos por pacote ou ativo (ex.: `Correia058.parquet`). Para adicionar dados: copiar o parquet para `data/` e incluir o nome exato (respeitando maiúsculas/minúsculas) no manifesto. Todos os arquivos devem ter a mesma estrutura de colunas (ver abaixo).

---

## Como executar

### Via servidor local (recomendado)

```bash
# Python 3
python -m http.server 8080
# acesse http://localhost:8080
```

```bash
# Node.js (npx)
npx serve .
```

A aplicação faz `fetch` de `data/manifest.json` e dos parquets nele listados na inicialização. Isso exige um servidor HTTP — abrir `index.html` diretamente pelo navegador (`file://`) não funciona por restrições de CORS.

### Fallback manual

Se os arquivos não carregarem automaticamente, o painel exibirá um botão **"Selecionar Parquets"**. Basta clicar e escolher todos os parquets da base na janela do sistema operacional (seleção múltipla).

---

## Formato dos dados (Parquet)

Cada parquet listado no manifesto deve ter as seguintes colunas:

| Coluna | Tipo | Exemplo |
|--------|------|---------|
| `IWP` | string | `KS-N103101-294-S-MT-CWP-001-IWP-001 - Frontal` |
| `MimeType` | string | `image/jpeg` |
| `Pic` | string | `(base64 da imagem, pode ser fragmentada em múltiplas linhas)` |

O nome do arquivo (campo `IWP`) segue o padrão `<ID do pacote> - <nome da vista>`. A aplicação extrai o ID completo, decompõe os campos (área, disciplina, CWP, IWP) e reconstrói as imagens concatenando os fragmentos base64.

### Estrutura do ID de pacote

```
KS - N103101 - 294 - S - MT - CWP-001 - IWP-001
|      |        |    |    |      |          |
|      |        |    |    |     CWP        IWP
|      |        |    |    |
|      |        |    |  Subdisciplina
|      |        |   Disciplina (S/E/M/T/A)
|      |       CWA (área)
|    Projeto
Contrato
```

### Disciplinas

| Código | Nome |
|--------|------|
| `S` | Estruturas Metálicas |
| `E` | Elétrica |
| `M` | Mecânica |
| `T` | Tubulação |
| `A` | Arquitetura |

---

## Design System

Tokens de cor, tipografia e regras de uso estão documentados em [`DESIGN-SYSTEM.md`](DESIGN-SYSTEM.md). Os tokens CSS (`--brand-primary`, `--brand-accent`, etc.) são definidos em `assets/dicionario-pacotes.css`.

---

## Dependências externas (CDN)

| Biblioteca | Uso |
|------------|-----|
| [hyparquet](https://github.com/hyparam/hyparquet) | Leitura de arquivos Parquet no browser |
| [hyparquet-compressors](https://github.com/hyparam/hyparquet-compressors) | Suporte a compressão GZIP no Parquet |

Ambas são carregadas via `import()` dinâmico do jsDelivr. Sem conexão à internet, a leitura do Parquet não funciona — use o fallback manual (seleção de arquivos, ver seção acima).

---

## Projeto

**Vale S11D — Squad Engenharia Digital**  
Contrato KS-N103101 · Usina
