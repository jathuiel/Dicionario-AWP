# Design System — Identidade Visual Vale

> Documentação de referência para o projeto **Dicionário Visual de Pacotes AWP BIM**.
> Baseada no Guia Rápido da Marca Vale (refinariadesign.com.br) e no BrandColorCode.com.

---

## 1. Paleta de Cores

### 1.1 Cores Primárias e Secundárias

| Swatch | Token proposto | Nome | HEX | RGB | CMYK | Pantone |
|--------|---------------|------|-----|-----|------|---------|
| 🟩 | `--vale-green` | Verde Vale *(primária)* | `#00787e` | 0, 128, 124 | 100, 0, 3, 50 | 7717 C |
| 🟨 | `--vale-yellow` | Amarelo Vale *(secundária)* | `#EEA722` | 238, 167, 34 | 0, 30, 86, 7 | 7409 C |
| 🩶 | `--vale-gray` | Cinza Vale *(suporte)* | `#77787B` | 119, 120, 123 | 3, 2, 0, 52 | Cool Gray 9 C |
| ⬛ | `--vale-black` | Preto | `#000000` | 0, 0, 0 | 0, 0, 0, 100 | — |
| ⬜ | `--vale-white` | Branco | `#FFFFFF` | 255, 255, 255 | 0, 0, 0, 0 | — |

### 1.2 Regras de Uso

| Cor | Aplicação |
|-----|-----------|
| Verde Vale `#00807C` | Cor primária — sidebar, CTAs, ícones ativos, cabeçalhos de seção |
| Amarelo Vale `#EEA722` | Cor de destaque — item selecionado, alertas, badges, hover |
| Cinza Vale `#77787B` | Suporte — texto secundário, bordas, ícones neutros |
| Preto `#000000` | Tipografia sobre fundos claros |
| Branco `#FFFFFF` | Tipografia sobre Verde Vale; fundos de cards |

### 1.3 Variações Funcionais (extensão para UI)

Cores não previstas no brandbook, mas necessárias para estados de interface:

| Token proposto | Uso | Valor recomendado |
|----------------|-----|-------------------|
| `--vale-green-dark` | Sidebar e hover escuro | `#006661` |
| `--vale-green-light` | Fundo de destaque verde | `#E0F4F3` |
| `--vale-yellow-light` | Fundo de badge amarelo | `#FDF3D9` |
| `--vale-gray-light` | Fundo geral da aplicação | `#F4F6F8` |
| `--vale-gray-border` | Bordas e divisórias | `#E2E7F0` |
| `--vale-text-primary` | Texto principal | `#1A1A1A` |
| `--vale-text-secondary` | Labels e textos auxiliares | `#77787B` |

---

## 2. Tipografia

### 2.1 Famílias Tipográficas Oficiais

| Uso | Família | Peso | Estilo |
|-----|---------|------|--------|
| Títulos e destaques | **Arial** | Bold (700) | Normal |
| Corpo e suporte | **Myriad Pro** | Regular (400) | Maiúsculas (uppercase) |

> **Myriad Pro** é fonte licenciada pela Adobe (incluída no Adobe Creative Cloud).
> Em ambientes web sem licença, usar **Arial** como substituto em todos os níveis.

### 2.2 Hierarquia Tipográfica Web

```css
/* Declaração de fonte base (web-safe) */
font-family: Arial, Helvetica, sans-serif;

/* Hierarquia de tamanhos */
h1  → 24px / font-weight: 700  / color: var(--vale-text-primary)
h2  → 20px / font-weight: 700  / color: var(--vale-text-primary)
h3  → 16px / font-weight: 700  / color: var(--vale-text-primary)
h4  → 14px / font-weight: 700  / color: var(--vale-text-secondary)

/* Corpo */
body    → 14px / font-weight: 400
caption → 12px / font-weight: 400 / color: var(--vale-text-secondary)
label   → 13px / font-weight: 600 / letter-spacing: 0.5px / text-transform: uppercase
```

### 2.3 Uso de Caixa Alta

O Guia da Marca especifica o uso de **caixa alta (ALL CAPS)** para elementos institucionais como:
- Nome da marca em logotipo
- Labels de seção e navegação principal
- Badges de status

---

## 3. Logotipo

### 3.1 Wordmark

- **Formato**: "VALE" em letras maiúsculas, tipografia humanista customizada
- **Versão principal**: Verde Vale `#00807C` sobre fundo branco
- **Versão invertida**: Branco `#FFFFFF` sobre Verde Vale ou fundos escuros
- **Versão monocromática**: Preto `#000000` sobre fundos claros neutros

### 3.2 Área de Proteção

Manter espaço mínimo ao redor do logotipo equivalente à altura da letra "A" do wordmark em todas as direções. Não sobrepor texto, ícones ou outros elementos nessa área.

### 3.3 Usos Proibidos

- Não distorcer ou rotacionar o logotipo
- Não alterar as cores para versões não previstas no manual
- Não aplicar sombras, contornos ou efeitos 3D
- Não usar sobre fundos que comprometam o contraste de leitura

### 3.4 Supergráfico

O sistema visual da Vale inclui um **supergráfico de colinas e vales abstratos** — composição modular de formas que representam a natureza e as operações da empresa. Aplicável em materiais institucionais (apresentações, relatórios, capas), mas não recomendado em interfaces de software operacional como este dicionário.

---

## 4. Mapeamento CSS — Projeto Atual vs. Identidade Vale

Comparação entre as variáveis CSS atuais (`assets/dicionario-pacotes.css`) e os valores da marca oficial.

| Variável atual | Valor atual | Valor Vale | Alinhamento | Ação recomendada |
|----------------|-------------|------------|-------------|------------------|
| `--azul-escuro` | `#007e7a` | `#00807C` | ≈ 99% | Ajustar para `#00807C` |
| `--azul` | `#007e7a` | `#00807C` | ≈ 99% | Ajustar para `#00807C` |
| `--azul-claro` | `#df6b1d` | `#EEA722` | Divergente | Substituir por `#EEA722` (amarelo oficial) |
| `--cinza-bg` | `#f4f6fb` | Sem equiv. | Neutro | Manter ou usar `#F4F6F8` |
| `--cinza-borda` | `#e2e7f0` | Sem equiv. | Neutro | Manter |
| `--texto` | `#292929` | `#1A1A1A` | Próximo | Pode ajustar para `#1A1A1A` |
| `--texto-sec` | `#f6f6f6` | `#77787B` | Divergente | `#77787B` (cinza Vale) sobre fundos claros |
| `--verde` | `#16a34a` | — | Status | Manter para status "Ativo" |
| Tipografia | `Segoe UI` | `Arial` | Diferente | Substituir por `Arial, Helvetica, sans-serif` |

> **Observação**: Os nomes de variáveis como `--azul-*` são semanticamente incorretos para a marca Vale (que não usa azul). Na próxima refatoração de CSS, considerar renomear para `--vale-green-*`.

---

## 5. Tokens de Design Propostos

Bloco CSS pronto para substituir o bloco `:root` atual, alinhado à identidade Vale:

```css
:root {
  /* === CORES PRIMÁRIAS VALE === */
  --vale-green:        #00807C;   /* Verde Vale — cor primária da marca */
  --vale-green-dark:   #006661;   /* Verde escuro — sidebar, hover */
  --vale-green-light:  #E0F4F3;   /* Verde claro — fundos de destaque */

  --vale-yellow:       #EEA722;   /* Amarelo Vale — cor secundária/acento */
  --vale-yellow-light: #FDF3D9;   /* Amarelo claro — fundo de badge */

  --vale-gray:         #77787B;   /* Cinza Vale — suporte */
  --vale-gray-light:   #F4F6F8;   /* Cinza claro — fundo geral */
  --vale-gray-border:  #E2E7F0;   /* Cinza borda — divisórias */

  --vale-black:        #1A1A1A;   /* Texto principal */
  --vale-white:        #FFFFFF;   /* Fundo e texto invertido */

  /* === ALIASES SEMÂNTICOS (compatibilidade com CSS atual) === */
  --azul-escuro:  var(--vale-green-dark);
  --azul:         var(--vale-green);
  --azul-claro:   var(--vale-yellow);       /* era laranja; agora amarelo Vale */
  --cinza-bg:     var(--vale-gray-light);
  --cinza-borda:  var(--vale-gray-border);
  --texto:        var(--vale-black);
  --texto-sec:    var(--vale-gray);

  /* === STATUS (não alterados — convensão interna da equipe) === */
  --verde:        #16a34a;  --verde-bg:  #dcfce7;
  --amarelo:      #b45309;  --amarelo-bg: #fef3c7;
  --roxo:         #6d28d9;  --roxo-bg:   #ede9fe;
}
```

---

## 6. Exemplos de Aplicação no Dicionário AWP

### Sidebar

```css
.sidebar {
  background: var(--vale-green-dark);   /* #006661 */
  color: var(--vale-white);
}

.sidebar .nav-item.active {
  background: var(--vale-yellow);       /* #EEA722 */
  color: var(--vale-black);
}
```

### Botões Primários

```css
.btn-primary {
  background: var(--vale-green);        /* #00807C */
  color: var(--vale-white);
  font-family: Arial, sans-serif;
  font-weight: 700;
}

.btn-primary:hover {
  background: var(--vale-green-dark);   /* #006661 */
}
```

### Badge de Item Selecionado

```css
.item-selected {
  border-left: 3px solid var(--vale-yellow);  /* #EEA722 */
  background: var(--vale-yellow-light);        /* #FDF3D9 */
}
```

### Cabeçalho de Seção (Label)

```css
.section-label {
  font-family: Arial, sans-serif;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  color: var(--vale-gray);              /* #77787B */
}
```

---

## 7. Referências

| Fonte | URL |
|-------|-----|
| Guia Rápido da Marca Vale (PDF) | http://www.refinariadesign.com.br/manuais/VALE/brandbook-manual-de-identidade-vale.pdf |
| Vale S.A. Brand Color Codes | https://www.brandcolorcode.com/vale-s-a |
| Site oficial Vale | https://vale.com/pt |
| Manual da Marca Fundação Vale (PDF) | https://www.fundacaovale.org/wp-content/uploads/2021/03/Manual-da-Maraca-Fundacao-Vale.pdf |
| Biblioteca de Documentos Vale | https://vale.com/pt/biblioteca-de-documentos |

---

*Gerado em 2026-06-26 · Versão 1.0 · Squad S11D – Engenharia Digital*
