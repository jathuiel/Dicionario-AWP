# Guia de Utilização — Dicionário Visual AWP

Sistema de consulta visual de pacotes de trabalho (IWP) do projeto KS-N103101 — Usina,
com cadastro, gestão da hierarquia (projetos/CWAs/CWPs/status), upload de imagens
e importação em massa.

---

## 1. Iniciar o sistema

**Requisitos:** Python 3.10+ com as dependências instaladas (uma única vez), a
partir da pasta `deploy/` (é ela que roda em produção):

```
cd deploy
pip install -r requirements.txt
```

**Subir o servidor:**

```
python -m uvicorn app:app --port 8000
```

Abra no navegador: **http://127.0.0.1:8000**

As páginas carregam um pequeno script de animação via CDN (unpkg) — sem
internet elas ainda funcionam, só sem a animação de carregamento. As imagens
são servidas pelo próprio backend (WebP), não dependem de rede externa.

Se o banco (`awp.db`) ainda estiver no formato antigo (schema anterior à
hierarquia projeto→CWA→CWP→IWP), o **primeiro start migra automaticamente** —
ver seção 8.

Para verificar se está tudo funcionando: `python test_app.py` (dentro de
`deploy/`), deve terminar com `TODOS OS TESTES PASSARAM`.

---

## 2. Páginas

| Página | Para quê |
|---|---|
| `index.html` | Cartões dos squads cadastrados (via `GET /api/squads`) + atalhos para Cadastro e Upload |
| `{squad}/{squad}.html` | Dicionário visual do squad (ex.: `classificacao/classificacao.html`) |
| `cadastro.html` | Cadastro de IWP, importação em massa, consulta com filtros (máx. 200 registros) e **Gestão** da hierarquia |
| `upload.html` | Envio de imagens (vistas) para um IWP já cadastrado |

---

## 3. Consultar o dicionário (leitor)

1. Abra o dicionário do squad (pelo cartão na página inicial ou direto pela URL).
2. A página busca `GET /api/pacotes/{squad}` — o backend lista os arquivos
   `.webp` daquele squad, agrupa por código e devolve a descrição (do banco)
   e a URL de cada vista. As imagens carregam sob demanda (lazy), com cache
   HTTP normal do navegador — não há mais download de uma base inteira.
3. Use a **busca** (código IWP/CWP) e os **filtros** (CWA, CWP, Disciplina)
   para localizar o pacote; a lista é paginada.
4. Clique no pacote para abrir o **detalhe**: navegue entre as vistas com as
   setas ‹ ›, clique na imagem para abrir em **tela cheia** (lightbox — setas
   do teclado navegam, Esc fecha; no celular, deslize).
5. Aba **🖨️ Imprimir**: pré-visualização A4 do pacote selecionado com todas
   as vistas; escolha retrato ou paisagem e clique em Imprimir.

Se a lista aparecer vazia, confira se `imagens/{squad}/` tem arquivos `.webp`
e se o squad está cadastrado (`GET /api/squads`).

---

## 4. Cadastrar IWP

Em **http://127.0.0.1:8000/cadastro.html**, painel **Novo pacote**:

- Informe o **código completo** do pacote no formato:

  ```
  KS-N103101-{CWA}-{DISC}-MT-CWP-{nnn}-IWP-{nnn}
  Ex.: KS-N103101-294-S-MT-CWP-001-IWP-042
  ```

- A **descrição** é opcional. Clique em **Cadastrar** (ou Enter no campo código).

O sistema valida o formato e, por trás, cria (ou reaproveita, se já existirem)
o projeto, o CWA, a disciplina e o CWP correspondentes ao código — não é
preciso cadastrar essa cadeia antes. Erros comuns:

| Mensagem | Causa |
|---|---|
| Código inválido | Menos de 9 segmentos separados por `-`, ou contém ` - ` (espaço-hífen-espaço) |
| já cadastrado | O mesmo código já existe no banco |

### Consultar, alterar status e excluir

Na tabela **IWPs cadastrados**, acima dela há filtros por **CWA**, **CWP**,
**Disciplina** e um campo de **busca** (procura no código e na descrição,
enquanto digita); o botão **⇄** limpa todos os filtros.

**Nota:** a tabela renderiza no máximo 200 registros por consulta — se a busca
retornar mais, a página mostra "mostrando 200 de N registros — refine os filtros"
e você pode usar os filtros para reduzir o resultado.

Em cada linha:

- ✏️ ao lado da descrição abre um prompt para editá-la.
- O select de **Status** muda o status do IWP na hora (Planejado, Emitido,
  Em execução, Concluído, ou outros cadastrados em Gestão → Status).
- 🗑️ exclui o cadastro. **As imagens não são apagadas** — se o IWP for
  recadastrado depois, as vistas antigas em `imagens/{squad}/` voltam a
  aparecer.

---

## 5. Gestão (projetos, CWAs, CWPs, disciplinas, squads, status)

Mais abaixo na página de cadastro, o painel **Gestão** (e os painéis
**Disciplinas**/**Squads** logo acima dele) permitem administrar a hierarquia
usada pelos IWPs — `projeto → CWA → CWP → IWP`, com squads e disciplinas
ligados a essa cadeia:

| Seção | O que dá pra fazer |
|---|---|
| **Disciplinas** | Listar, criar/editar (salvar com código existente = edita o nome) e excluir |
| **Squads** | Criar (cria a pasta + página do dicionário), editar nome/ícone, excluir (não apaga a pasta/imagens) |
| **Projetos** | Listar, criar, editar nome, excluir |
| **CWAs** | Listar, criar (dentro de um projeto), atribuir/trocar o squad responsável, editar descrição, excluir |
| **CWPs** | Listar, editar descrição, excluir — CWPs **nascem automaticamente** do cadastro de IWP, não têm criação manual |
| **Status** | Listar (ordenados), criar, editar nome/ordem, excluir |

Exclusões respeitam a hierarquia: não é possível excluir um projeto com
squads/CWAs, um CWA com CWPs, um CWP com IWPs, nem uma disciplina referenciada
por algum CWP — a página mostra a mensagem de erro do backend (409) nesses casos.
Excluir um squad com CWA(s) atribuídos também é bloqueado — reatribua o(s)
CWA(s) a outro squad (ou a nenhum) antes. Excluir um status não bloqueia nada:
os IWPs que o usavam simplesmente ficam sem status.

---

## 6. Importar planilha (xlsx)

Na página de cadastro, painel **Importação em massa**:

1. Monte a planilha: **primeira aba**, cabeçalho na **linha 1** com as colunas:

   | codigo *(obrigatória)* | descricao *(opcional)* |
   |---|---|
   | KS-N103101-294-S-MT-CWP-001-IWP-050 | Plataforma norte |
   | KS-N103101-294-S-MT-CWP-001-IWP-051 | |

2. Selecione o arquivo `.xlsx` (até 5 MB) e clique em **Importar**.
3. Leia o resumo: `N importado(s), N duplicado(s), N inválido(s)` — duplicados e
   inválidos são listados **com o número da linha** e não impedem a importação
   das linhas válidas. Linhas em branco são ignoradas. Cada linha válida cria
   (ou reaproveita) a mesma cadeia projeto/CWA/disciplina/CWP do cadastro manual.

---

## 7. Enviar imagens (upload)

Em **http://127.0.0.1:8000/upload.html**:

1. Escolha o **squad** (define em qual dicionário a imagem aparece).
2. Informe o **código completo** do pacote e o **nome da vista**
   (ex.: `Top Front ISO`). O nome da vista não pode conter ` - `.
3. Selecione a imagem — **JPEG ou PNG, até 10 MB** — e clique em **Enviar**.
   O backend converte para WebP e grava em `imagens/{squad}/`.

Depois do envio, abra o dicionário do squad e busque o código: o pacote
aparece com a nova vista (pode ser preciso recarregar a página).

Regras importantes:

- Enviar de novo a **mesma vista do mesmo código substitui** o arquivo
  anterior (`substituida: true` na resposta) — o cadastro do IWP em si
  (descrição, status) não muda com o upload.
- O IWP **não precisa estar cadastrado** para receber upload — o envio só
  valida o formato do código, não se ele existe em `awp.db`. Se quiser que o
  pacote apareça com descrição/status, cadastre-o em Novo pacote.

---

## 8. Migração automática do schema (se você vem de uma versão anterior)

Bancos criados antes da normalização (`awp.db` com uma tabela `iwp` cujo
código era a chave primária, sem `cwp_id`) são migrados automaticamente no
primeiro start do backend, numa única passagem:

1. `awp.db` é copiado para `awp.db.bak-v1` antes de qualquer alteração (só se
   esse backup ainda não existir — é a cópia de segurança real da migração).
2. As tabelas antigas (`iwp_v1`, `disciplina_v1`) foram mantidas durante a validação
   e removidas com `VACUUM` na limpeza final.
3. O schema novo é criado; disciplinas são importadas; `squads.json`
   (se existir) vira o projeto `KS-N103101` + um squad por entrada.
4. Cada IWP antigo é reimportado, recriando a cadeia
   projeto→CWA→disciplina→CWP a partir do próprio código.

Não há passo manual — só suba o servidor normalmente. Se algo parecer
errado depois da migração, `awp.db.bak-v1` tem os dados originais intactos.

---

## 9. API (para integrações)

Documentação interativa (gerada pelo FastAPI): **http://127.0.0.1:8000/docs**

| Método e rota | Função |
|---|---|
| `GET /api/pacotes/{squad}` | Pacotes do squad com descrição e URL de cada vista (WebP) |
| `POST /api/iwp` | Cadastra IWP — `{"codigo": "...", "descricao": "..."}` |
| `GET /api/iwp?cwa=&cwp=&disc=&busca=` | Consulta cadastros; parâmetros opcionais e combináveis |
| `PATCH /api/iwp/{codigo}` | Edita `descricao` e/ou `status_id` (independentes) |
| `DELETE /api/iwp/{codigo}` | Exclui o cadastro (não apaga imagens) |
| `GET /api/iwp/filtros` | Valores distintos de CWA/CWP/Disciplina cadastrados |
| `GET/POST/PATCH/DELETE /api/disciplinas` | CRUD de disciplinas (por `codigo`) |
| `GET/POST/PATCH/DELETE /api/projetos` | CRUD de projetos |
| `GET/POST/PATCH/DELETE /api/cwas` | CRUD de CWAs (inclui atribuição de squad) |
| `GET/PATCH/DELETE /api/cwps` | CWPs — sem POST (nascem do cadastro de IWP) |
| `GET/POST/PATCH/DELETE /api/status` | CRUD de status do IWP |
| `GET/POST/PATCH/DELETE /api/squads` | CRUD de squads (POST cria pasta + página HTML) |
| `POST /api/importar` | Importa xlsx (multipart, campo `arquivo`) |
| `POST /api/upload` | Envia imagem (multipart: `squad`, `codigo`, `vista`, `arquivo`) |
| `GET /api/upload/{squad}` | Lista imagens enviadas do squad |

Exclusões que violam a hierarquia (projeto com squad/CWA, CWA com CWP, CWP com
IWP, disciplina em uso, squad com CWA atribuído) respondem **409** com uma
mensagem explicando o motivo.

---

## 10. Onde ficam os dados (e o que fazer backup)

| O quê | Onde |
|---|---|
| Cadastro (projetos, squads, CWAs, CWPs, IWPs, disciplinas, status) | `deploy/awp.db` (SQLite) |
| Backup pré-migração (v1→v2) | `awp.db.bak-v1` (na raiz, criado automaticamente) |
| Backup pós-padronização | `awp.db.bak-v2-padronizado` (na raiz) |
| Imagens (originais + enviadas por upload) | `deploy/imagens/{squad}/*.webp` |
| Controle de quais imagens vieram de upload | `deploy/imagens/{squad}/.uploads.json` |
| Template para importação em massa | `templates/template-importacao-iwp.xlsx` (na raiz) |

⚠️ Evite editar `awp.db` com o servidor rodando. A pasta do projeto é
sincronizada pelo OneDrive: para uso em produção, o recomendado é rodar o
serviço fora do OneDrive e usá-lo apenas como backup.

---

## 11. Solução de problemas

| Sintoma | Causa provável / solução |
|---|---|
| Página não abre | Servidor parado — rode o comando da seção 1. Porta ocupada? Troque `--port 8000` por outra |
| Dicionário sem imagens | `imagens/{squad}/` sem arquivos `.webp`, ou squad não cadastrado (`GET /api/squads`) |
| Imagem enviada não aparece no dicionário | Recarregue a página do squad; confira o código exato na busca |
| Exclusão recusada (409) | A entidade tem algo dependente dela (ex.: CWA com CWP, disciplina em uso) — remova/reatribua o dependente primeiro |
| Importação recusada (415/422) | Arquivo não é `.xlsx` ou falta a coluna `codigo` no cabeçalho da linha 1 |
| Erro ao gravar cadastro (banco travado) | Outra instância do servidor rodando? Feche duplicatas e tente de novo |
| Banco migrado mas algo parece perdido | Confira `awp.db.bak-v1` (cópia completa pré-migração) e `awp.db.bak-v2-padronizado` (após padronização); dados antigos podem estar em backups |
