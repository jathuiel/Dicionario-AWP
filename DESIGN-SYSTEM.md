# Design System — Dicionário de Pacotes

Design system extraído de `assets/dicionario-pacotes.css`. Fonte única da verdade: o bloco
`:root` no topo do CSS. Este documento descreve o que existe — para rebrandear, altere
apenas os tokens de marca (seção 1) e nada mais.

---

## 1. Tokens de cor

### Marca (troque estes valores por cliente)

| Token | Valor atual | Uso |
|---|---|---|
| `--brand-primary` | `#007a7e` | Cor primária — botões, links, indicadores |
| `--brand-primary-dark` | `#006661` | Header mobile, nav inferior, hover |
| `--brand-primary-light` | `#E0F4F3` | Fundos de destaque, feedback de toque |
| `--brand-primary-alpha` | `#007a7e33` | Item ativo da sidebar (20% opacidade) |
| `--brand-gradient` | `linear-gradient(180deg, #01a39e, #007E7a 50%, #015551)` | Fundo da sidebar |
| `--brand-accent` | `#f7d58b` | Seleção de card, borda do item ativo |
| `--brand-accent-light` | `#FDF3D9` | Fundo de badge |

### Neutros

| Token | Valor | Uso |
|---|---|---|
| `--neutral-black` | `#1A1A1A` | Texto principal |
| `--neutral-gray` | `#77787B` | Texto secundário, labels |
| `--neutral-bg` | `#F4F6F8` | Fundo geral da aplicação |
| `--neutral-border` | `#E2E7F0` | Bordas e divisórias |
| `--neutral-white` | `#FFFFFF` | Superfícies (painéis, cards) |

### Aliases semânticos

Camada de compatibilidade — o CSS dos componentes usa estes nomes; eles apontam para os
tokens acima. Componentes novos podem usar qualquer uma das camadas.

| Alias | Aponta para |
|---|---|
| `--azul` | `--brand-primary` |
| `--azul-escuro` | `--brand-primary-dark` |
| `--azul-claro` | `--brand-accent` |
| `--cinza-bg` | `--neutral-bg` |
| `--cinza-borda` | `--neutral-border` |
| `--texto` | `--neutral-black` |
| `--texto-sec` | `--neutral-gray` |

### Status (convenção da equipe — não rebrandear)

| Token | Texto | Fundo | Uso |
|---|---|---|---|
| `--verde` / `--verde-bg` | `#16a34a` | `#dcfce7` | Status "Ativo" |
| `--amarelo` / `--amarelo-bg` | `#b45309` | `#fef3c7` | Avisos |
| `--roxo` / `--roxo-bg` | `#6d28d9` | `#ede9fe` | Destaque reservado |

### Paleta fixa de impressão

A aba de impressão (folha A4) usa cores próprias, fora dos tokens, para garantir contraste
no papel: texto `#1c2430`/`#6b7686`/`#9aa3b2`, bordas `#d0d7e6`, fundo de imagem `#eef1f7`,
fundo da área `#cdd3de`. A única cor de marca na folha é a linha do topo (`--brand-primary`).

---

## 2. Tipografia

**Família:** `'Segoe UI semibold', Tahoma, Geneva, Verdana, sans-serif` (stack de sistema, sem webfont).

| Papel | Tamanho | Peso | Onde |
|---|---|---|---|
| Título de detalhe (h1) | 24px | 700 | `.det-cab h1` (20px no mobile) |
| Título de seção impressa (h2) | 16px | 700 | `.imp-topo h2` |
| Logo / marca | 17px | 700 | `.sidebar .logo b` |
| Subtítulo | 15px | 400 | `.det-cab .sub` |
| Corpo / navegação | 14–14.5px | 400 | `.nav a`, `.busca input`, `.info-linha` |
| Rótulos e cards | 13–13.5px | 400–600 | `.campo label`, `.card .cod`, filtros |
| Título de painel (h3) | 13px | 700 + `letter-spacing: .5px` | `.painel h3`, `.filtros .cab b` |
| Legendas | 12–12.5px | 400 | `.card .nome`, `.badge`, captions |
| Tag de status | 11px | 600 | `.tag` |
| Nav inferior mobile | 10px | 400 | `.nav-bottom a` |

Regra mobile: inputs e selects sobem para **16px** abaixo de 768px (previne zoom automático no iOS).

---

## 3. Espaçamento

Sem grid rígido — a escala prática usada é **4 / 6 / 8 / 10 / 12 / 14 / 16 / 18 / 20 / 22 / 24 / 28px**:

- Padding de painéis e colunas: 18–28px
- Padding interno de cards e campos: 8–14px
- Gaps de grid e flex: 6–18px (grids de conteúdo usam 14–18px)

## 4. Raios de borda

| Valor | Uso |
|---|---|
| `20px` (pílula) | `.tag`, `.badge`, `.vista-label`, `.lb-cap` |
| `14px` | `.painel` |
| `12px` | `.det-cab .icone` |
| `10px` | `.card`, `.visualizador`, `.vista-card` |
| `8–9px` | Botões, `.busca`, selects, logo |
| `6–7px` | Paginação, imagem do lightbox, `.imp-vista` |
| `50%` | Setas de navegação, bullet de disciplina |

## 5. Sombras e transições

| Token informal | Valor | Uso |
|---|---|---|
| Sombra leve | `0 2px 8px rgba(0,0,0,.1)` | Setas sobre a imagem |
| Sombra de folha | `0 4px 24px rgba(0,0,0,.25)` | Folha A4 simulada |
| Transição de painel | `transform .3s ease` | Detalhe deslizante no mobile |
| Transição de toque | `.1s ease` | `:active` de cards e botões |
| Transição de UI | `.25s–.3s ease` | Chevron dos filtros, recolhimento |

---

## 6. Layout e breakpoints

Layout desktop em 3 colunas: **sidebar (240px) | lista (380px) | detalhe (flex 1)**.

| Breakpoint | Comportamento |
|---|---|
| `≤ 1100px` | Grid do detalhe vira 1 coluna; vistas em 2 colunas |
| `768–1023px` (tablet) | Sidebar recolhe para 60px (só ícones); lista 300px |
| `< 767px` (mobile) | Pilha vertical: header 52px + lista + nav inferior 58px; detalhe desliza da direita (`transform`) |
| `@media print` | Oculta tudo exceto a folha A4 |

Regras mobile obrigatórias (não simplificar):
- Touch targets mínimos de **44px** (paginação, nav, voltar)
- **Safe area insets** via `env(safe-area-inset-*)` (notch/home bar iOS)
- Feedback `:active` em vez de `:hover`

---

## 7. Inventário de componentes

| Componente | Classes | Tokens que consome |
|---|---|---|
| Sidebar / navegação | `.sidebar`, `.nav` | `--brand-gradient`, `--brand-primary-alpha`, `--brand-accent` |
| Busca | `.busca` | `--cinza-bg`, `--cinza-borda` |
| Filtros | `.filtros`, `.campo`, `.filtro-toggle` | `--cinza-borda`, `--texto-sec`, `--azul` |
| Card de pacote | `.card`, `.tag` | `--azul-claro`, `--brand-accent`, `--verde`/`--verde-bg` |
| Paginação | `.paginacao` | `--cinza-borda`, `--azul` |
| Painel de detalhe | `.detalhe`, `.det-cab`, `.painel`, `.badge`, `.info-linha` | `--azul-claro`, `--cinza-borda`, `--verde-bg` |
| Visualizador / galeria | `.visualizador`, `.nav-vista`, `.vistas-grid` | `--cinza-borda` |
| Lightbox | `.lightbox` | cores fixas (overlay escuro) |
| Impressão A4 | `.imp-pagina`, `.imp-topo`, `.imp-galeria` | `--brand-primary`, `--neutral-bg` + paleta fixa |
| Mobile | `.header-mobile`, `.nav-bottom` | `--azul-escuro`, `--brand-accent`, `--neutral-white` |

---

## 8. Como rebrandear para outro cliente

1. Abra `assets/dicionario-pacotes.css` e edite **apenas** os valores da seção
   *"Cores primárias da marca"* e *"Cores de destaque"* no `:root` (7 tokens).
2. Mantenha `--brand-primary-alpha` = cor primária + sufixo `33` (20% de opacidade).
3. Troque os logos em `assets/` (sidebar e header mobile).
4. Neutros, status e paleta de impressão normalmente não mudam entre clientes.

Nenhum seletor de componente precisa ser tocado.