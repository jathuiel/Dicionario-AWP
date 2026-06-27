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
- Galeria com todas as vistas do pacote em miniatura.
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
├── index.html                  # Aplicação completa (HTML + JS inline)
├── assets/
│   ├── dicionario-pacotes.css  # Estilos (tokens Vale, layout, responsivo)
│   ├── logo vale.png
│   ├── simbolo_verum_branco.png
│   └── logo_partners.png
├── data/
│   ├── imagens_base64.parquet  # Base de dados principal (imagens em base64)
│   └── pacotes-data.js         # Base de dados alternativa (referências a arquivos JPG)
├── VALE-DESIGN-SYSTEM.md       # Tokens de cor e tipografia da identidade Vale
└── Padroes de Commit.md        # Convenção de commits do projeto
```

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

A aplicação faz `fetch` de `data/imagens_base64.parquet` na inicialização. Isso exige um servidor HTTP — abrir `index.html` diretamente pelo navegador (`file://`) não funciona por restrições de CORS.

### Fallback manual

Se o arquivo não carregar automaticamente, o painel exibirá um botão **"Selecionar Parquet"**. Basta clicar e escolher `data/imagens_base64.parquet` na janela do sistema operacional.

---

## Formato dos dados (Parquet)

O arquivo `data/imagens_base64.parquet` deve ter as seguintes colunas:

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

Tokens de cor, tipografia e regras de uso estão documentados em [`VALE-DESIGN-SYSTEM.md`](VALE-DESIGN-SYSTEM.md). Os tokens CSS (`--vale-green`, `--vale-yellow`, etc.) são definidos em `assets/dicionario-pacotes.css`.

---

## Dependências externas (CDN)

| Biblioteca | Uso |
|------------|-----|
| [hyparquet](https://github.com/hyparam/hyparquet) | Leitura de arquivos Parquet no browser |
| [hyparquet-compressors](https://github.com/hyparam/hyparquet-compressors) | Suporte a compressão GZIP no Parquet |

Ambas são carregadas via `import()` dinâmico do jsDelivr. Sem conexão à internet, a leitura do Parquet não funciona — use a base `data/pacotes-data.js` como alternativa offline (requer ajuste no `index.html`).

---

## Projeto

**Vale S11D — Squad Engenharia Digital**  
Contrato KS-N103101 · Usina
