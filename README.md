# imortalistas · Cronologia de Exames de Sangue

Cronologia de Exames de Sangue do Sérgio F: resultados de análises ao sangue (e urina do mesmo painel), para registo e comparação entre datas, e a secção Intolerâncias Alimentares (`index.html`). A genética tem três páginas próprias: `genetica.html` (“Genética Má”: só resultados desfavoráveis), `genetica-boa.html` (“Genética Boa”: só resultados favoráveis) e `genetica-reports.html` (“Genética Reports”: relatórios completos em PDF). Site estático em GitHub Pages, `noindex` nas quatro páginas.

```
index.html                         análises ao sangue + Intolerâncias Alimentares (HTML + CSS + JS, sem bibliotecas; o único pedido externo é a contagem anónima pelo Worker, ver “Contagem de visitas e de PDFs”)
sf.js                              endereço do Worker de contagem e PDFs (uma só constante, SF_W), usado pelas quatro páginas
genetica.html                      Genética Má: só resultados desfavoráveis (mesmo cabeçalho, idioma e tema); conteúdo em data/genetica.json
genetica-boa.html                  Genética Boa: só resultados favoráveis; conteúdo em data/genetica_boa.json
data/sangue.json                   resultados por marcador e por data (sangue/urina em "marcadores", intolerâncias alimentares em "intolerancias")
data/genetica.json                 conteúdo de genetica.html (lista ordenada, secções, PT/EN)
data/genetica_boa.json             conteúdo de genetica-boa.html (mesmo formato)
data/genetica_protocolo.json       Protocolo genético consolidado, mostrado no topo das duas páginas de genética
genetica-reports.html              Genética Reports: lista de relatórios em PDF; conteúdo em data/reports.json
data/reports.json                  lista dos relatórios (título PT/EN, data, ficheiro em reports/)
reports/*.pdf                      os PDFs dos relatórios (já verificados quanto à privacidade)
ferramentas/adicionar_colheita.py  acrescenta uma data ou um relatório e verifica os ficheiros (sangue.json, genetica*.json, reports.json + PDFs e termos proibidos)
ferramentas/estatisticas_goatcounter.py  gera data/estatisticas.json a partir da API do GoatCounter (corre no GitHub Actions)
data/estatisticas.json             estatísticas agregadas para a página escondida (atualizado sozinho, de hora a hora)
.github/workflows/goatcounter-stats.yml  workflow de hora a hora que atualiza data/estatisticas.json
robots.txt                         regras para robôs (não lista nenhuma página)
.nojekyll
```

As páginas leem `data/sangue.json`, `data/genetica.json` ou `data/genetica_boa.json` (+ `data/genetica_protocolo.json` nas duas de genética; `data/reports.json` na Genética Reports) ao abrir. Para a ver localmente: `python3 -m http.server` na raiz e abrir `http://localhost:8000/` (por `file://` o navegador bloqueia a leitura do JSON).

## Formato dos dados

```json
{
 "colheitas": [ {"data": "2026-08-25", "rotulo": "ago 2026", "rotulo_en": "Aug 2026",
   "descricao": "25-08-2026 e 27-08-2026", "descricao_en": "25-08-2026 and 27-08-2026", "nota": "…", "nota_en": "…"} ],
 "marcadores": [
  {"m": "Ferritina", "m_en": "Ferritin", "c": "Ferro", "c_en": "Iron", "alvo": "< 100", "otimo_min": null, "otimo_max": 100, "regras": ["acima_do_otimo_fora"],
   "resultados": [
    {"data": "2026-08-25", "v": "310", "u": "ng/mL", "ref": "30.00 - 300.00", "ref_min": 30, "ref_max": 300,
     "s": "fora_de_referencia", "nota": "…", "nota_en": "…"}
   ]}
 ],
 "intolerancias": [
  {"m": "IgG Clara de ovo", "m_en": "IgG Egg white", "c": "IgG alimentar", "c_en": "Food IgG", "otimo_min": null, "otimo_max": null,
   "regras": ["intolerancia"], "melhor": "baixo",
   "resultados": [ {"data": "2026-08-25", "v": "32", "u": "U/ml", "ref": "normal ≤23; limítrofe 24-29; elevado ≥30", "ref_min": 0, "ref_max": 23, "s": "intolerante"} ]}
 ]
}
```
- `marcadores` = análises ao sangue e urina (tabela “Análises” e contagens do Resumo). `intolerancias` = intolerâncias alimentares (IgG/IgE específicas para alimentos): secção própria “Intolerâncias Alimentares” / “Food Intolerances”, com o mesmo formato, várias datas e comparação; não entram na tabela nem nas contagens das análises.
- Classificação das intolerâncias (`s` = `intolerante` ou `nao_intolerante`; regra `intolerancia`): compara-se o valor com o limite do próprio laboratório, `ref_max` (limite superior do intervalo normal/negativo; se faltar, lê-se do texto `ref`, ex. “normal ≤23”). **Acima do limite = Intolerante** (vermelho), incluindo a faixa limítrofe/duvidosa (ex. 24–29); **igual ou abaixo = Não intolerante** (verde). `<x` só conta como não intolerante se x ≤ limite; `>x` conta como intolerante se x ≥ limite; texto “negativo” = não intolerante, “positivo/elevado/limítrofe/duvidoso” = intolerante. Sem limite ou valor interpretável fica `sem_alvo` (“sem classificação”) e o `verificar` avisa. A mesma regra está em `ferramentas/adicionar_colheita.py` (`classifica_intolerancia`) e na página; no gráfico, a faixa verde vai até ao limite e a linha vermelha marca o limite. `melhor: "baixo"` faz o Δ ficar verde quando o valor desce.
- `colheitas[].data` é a chave de cada coluna da tabela (AAAA-MM-DD). Cada resultado tem `data` igual a uma colheita; se a análise foi feita noutro dia da mesma bateria, acrescenta-se `data_real` (ex. `"data": "2026-08-25", "data_real": "2026-08-27"`).
- Resultados anteriores citados noutro boletim (ex. 12-01-2024 e 21-02-2026, citados no de 21-03-2026) entram como colheita própria, com o intervalo de referência do boletim que os cita e uma `nota` a dizê-lo. Se a unidade de uma data for diferente da do marcador, converte-se o valor para a unidade do marcador e guarda-se o valor original na `nota` (ex. DHEA 19,20 ng/ml → 1920 ng/dL).
- Sem nomes de laboratórios: os dados não têm campo `lab` e `descricao` tem só datas; a página mostra só datas (o `verificar` falha se encontrar nomes de laboratórios ou um campo `lab`).
- `v` é o valor tal como no boletim (texto; ponto decimal). `s` é o estado: `otimo`, `aceitavel`, `fora_do_otimo`, `fora_de_referencia` ou `sem_alvo` (nas intolerâncias: `intolerante` / `nao_intolerante`). Se faltar, a página calcula-o com a mesma regra de `biomarcadores/scripts/comum.py`.
- `regras` (opcional): `sem_limite_inferior` (LDL, ApoB, estrôncio: quanto mais baixo, melhor; um valor abaixo do mínimo do laboratório não conta como fora do intervalo, na ferramenta e na página), `acima_do_otimo_fora` (ferritina ≥ 100 = fora), `so_categoria` (NAFLD Fibrosis Score: só a categoria, nunca o número), `sem_alvo` (estado sempre “Sem alvo”, sem cor), `intolerancia` (só em `intolerancias`: classificação acima). O script deteta marcadores alimentares (categoria/nome com “aliment”, “intoler” ou “food”, ou nome “IgG …”/“IgE …” que não seja “IgE total”), põe-nos em `intolerancias` e classifica-os automaticamente; o `verificar` falha se algum ficar em `marcadores` ou se a classificação gravada não bater com a regra.
- `alvo` é só o texto mostrado; se faltar, é gerado a partir de `otimo_min`/`otimo_max`.
- `nota` (opcional): só notas factuais sobre o próprio marcador ou a amostra (sem medicação, genética, suplementos nem recomendações).
- O nome `m` tem de ser exatamente o mesmo entre datas (nomes normalizados de `historico.csv`).
- Inglês (opcional): `m_en`, `c_en`, `alvo_en`, `ref_en`, `nota_en` nos marcadores/resultados e `rotulo_en`, `descricao_en`, `nota_en` nas colheitas. Se faltarem, a página em inglês mostra o texto em português.

## Como adicionar uma nova data

1. Registar primeiro as análises em `/workspace/biomarcadores/historico.csv` com o procedimento habitual (`comum.gravar()`).
2. Na raiz deste repositório:
   ```
   python3 ferramentas/adicionar_colheita.py sangue --csv /workspace/biomarcadores/historico.csv \
     --data 2026-12-03 --rotulo "dez 2026" --descricao "03-12-2026" \
     --rotulo-en "Dec 2026" --descricao-en "03-12-2026" \
     [--datas-csv 2026-12-03,2026-12-05]
   ```
   `--data` é a coluna nova; `--descricao` leva só datas (sem nome do laboratório); `--datas-csv` junta na mesma coluna análises da mesma bateria feitas noutros dias. O script é idempotente (repetir substitui essa data), mantém os nomes dos marcadores, cria marcadores novos se for preciso e aplica as regras acima.
3. Correr `python3 ferramentas/adicionar_colheita.py verificar` (datas coerentes e pesquisa de termos proibidos), abrir a página por `http.server` e confirmar que não há erros na consola.
4. Fazer commit de `data/sangue.json`. A página abre na data mais recente com “Não comparar” (sem coluna Δ nem filtro de tendência); ao escolher uma data em “comparar com” aparecem essa coluna, o Δ, o filtro de tendência e, no Resumo, as contagens de melhorias/pioras. “Mostrar todas as datas em colunas” mostra todas as datas. O gráfico de cada marcador tem os pontos igualmente espaçados por colheita (não proporcional ao tempo), eixo com valores redondos e rótulos sem sobreposição (verificado por `site_build/test_chart_overlap.py`, fora do repositório).

## Páginas de genética

| Página | Menu | Título | Conteúdo | O que entra |
|---|---|---|---|---|
| `genetica.html` | Genética Má / Bad Genetics | Genética - Apenas maus resultados / Genetics - Unfavourable results only | `data/genetica.json` | só desfavoráveis: alelos de risco, scores acima da média, estado de portador, metabolismo reduzido, necessidades aumentadas |
| `genetica-boa.html` | Genética Boa / Good Genetics | Genética - Apenas bons resultados / Genetics - Favourable results only | `data/genetica_boa.json` | só favoráveis: variantes protetoras, alelos de longevidade, scores abaixo da média, função normal com significado clínico tranquilizador |

Resultados neutros, médios ou não confirmados não entram em nenhuma das duas. Cada página só tem o cabeçalho, o título e um contentor; tudo o resto é gerado a partir do JSON respetivo, por isso **para acrescentar conteúdo basta editar o JSON** (não é preciso mexer no HTML). Os dois JSON têm o mesmo formato:

```json
{
 "atualizado_em": "2026-10-02",
 "fonte": {"pt": "Fonte principal: …", "en": "Primary source: …"},
 "notas": [ {"pt": "Caixa de nota (azul) no topo…", "en": "Note box at the top…"} ],
 "seccoes": [
  {"id": "farmacogenomica", "titulo": {"pt": "Farmacogenómica", "en": "Pharmacogenomics"},
   "intro": {"pt": "(opcional) frase por baixo do título", "en": "(optional) line under the title"},
   "linhas": [
    {"item": "CYP2C9", "texto": {"pt": "*1/*3 (metabolizador intermédio)…", "en": "*1/*3 (intermediate metaboliser)…"},
     "estado": "bad", "rotulo": {"pt": "Cautela", "en": "Caution"}}
   ],
   "evitar": [ {"pt": "Varfarina e acenocumarol (preferir DOAC)…", "en": "Warfarin and acenocoumarol (prefer a DOAC)…"} ],
   "priorizar": [ {"pt": "Cartão PGx no processo clínico…", "en": "PGx card in the medical record…"} ]}
 ]
}
```
- Cada entrada de `seccoes` é um cartão (2 por linha no computador, 1 no telemóvel), pela ordem do ficheiro, e aparece também nos atalhos por baixo da nota. Para uma secção nova, acrescentar um objeto com um `id` novo (minúsculas, números e hífens; dá o link `genetica.html#id` ou `genetica-boa.html#id`).
- `evitar` e `priorizar` (obrigatórios em todas as secções): listas de ações concretas ligadas aos genes dessa secção (fármacos, suplementos com doses, dieta, exercício, rastreio, análises de confirmação), mostradas por baixo da tabela nos blocos **Evitar** (vermelho) e **Priorizar** (verde) / **Avoid** e **Prioritize**. Na Genética Boa, “Priorizar” é para aproveitar ou manter a vantagem. Os valores das análises prevalecem sobre doses só genéticas (ex.: D3 10 000 UI, ómega-3 3,2–4 g/dia de EPA+DHA); tudo é sugestão e precisa de validação médica.
- `data/genetica_protocolo.json` (`titulo`, `intro`, `blocos[{titulo, itens[]}]`, textos PT/EN) é o **Protocolo genético**: um cartão destacado no topo das duas páginas (primeiro atalho, `#protocolo`) que junta o Evitar/Priorizar sem contradições, com o cartão PGx e as análises de confirmação. Ao mudar um Evitar/Priorizar, confirmar que o protocolo continua coerente.
- `ajustar` e `monitorizar` (opcionais, usados na Farmacogenómica da Genética Má): blocos **Ajustar a dose** (amarelo) e **Monitorizar** (azul) / **Adjust the dose** e **Monitor**, entre o Evitar e o Priorizar. `intro` (opcional) é um parágrafo por baixo do título do cartão.
- `farmacos` (opcional, só em `data/genetica.json`): tabela pesquisável **Fármacos acionáveis** (último cartão e último atalho, `#farmacos`) com `titulo`, `intro`, `fonte` e `linhas[{f, acao, genes, rec, atual}]`: `f` nome do fármaco PT/EN, `acao` = `evitar` | `ajustar` | `monitorizar` | `indeterminado`, `genes` e `rec` (recomendação resumida) PT/EN, `atual: true` para a medicação atual. Só entram os fármacos com ação; os normais e os sem interação PGx conhecida ficam de fora. Hoje é gerada a partir do CSV do relatório PGx de 632 fármacos (60 linhas; ivacaftor excluído, só se aplica a fibrose quística; somatropina em Evitar por coerência com o protocolo).
- `lista` (desde 03-10-2026, nas duas páginas): **lista ordenada** dos achados, do maior para o menor impacto provável (cartão logo a seguir ao Protocolo, atalho `#lista`), com `id`, `titulo`, `intro` e `linhas[{n, texto, evidencia, estado, fraca, origem, analise}]`: `n` = posição (1, 2, 3…), `texto` e `evidencia` (etiqueta: Forte, Moderada a forte, Moderada, Fraca a moderada, Fraca) PT/EN, `estado` = cor da etiqueta, `fraca: true` mostra “⚠ (evidência fraca)” / “⚠ (weak evidence)”, `origem` = lista de ids de `data/reports.json` (a página mostra “Fonte: …” com ligação ao PDF PT no modo Português e ao PDF EN no modo English; só relatórios publicados: um achado de um relatório não publicado fica sem `origem` e sem qualquer referência a esse relatório), `analise` (opcional) = valor medido nas análises ao sangue, que prevalece sobre a genética quando há conflito. Hoje: Genética Boa 67 linhas (7 fracas), Genética Má 66 (26 fracas), com os scores recalculados a 03-10-2026. As secções por categoria ficaram só com os blocos Evitar/Priorizar (sem `linhas`).
- Cada entrada de `linhas` (opcional nas secções; sem linhas, o cartão mostra só os blocos) é uma linha da tabela: `item` (gene/tema, a negrito), `texto`, e opcionalmente `estado` + `rotulo` (a etiqueta colorida): `ok` verde, `warn` amarelo, `bad` vermelho, `na` cinzento, `info` azul.
- Textos bilingues: `{"pt": "…", "en": "…"}`; se o texto for igual nas duas línguas (ex. nome do gene) pode ser só `"CYP2C9"`. Pode levar HTML simples: `<b>`, `<i>`, `<em>`, `<strong>`, `<br>`, `<small>`, `<sub>`, `<sup>` (o resto é mostrado como texto).
- As mesmas regras de privacidade e de nomes (abaixo) aplicam-se aqui: sem nomes de laboratórios ou empresas, sem dados pessoais.
- Depois de editar: `python3 ferramentas/adicionar_colheita.py verificar` (estrutura, PT+EN em todos os textos, ids únicos, estados válidos, `lista` com `origem` só de relatórios publicados, `evitar`/`priorizar` em todas as secções, `ajustar`/`monitorizar`/`farmacos`, protocolo, reports.json + privacidade dos PDFs, HTML permitido, termos proibidos), abrir `genetica.html` e `genetica-boa.html` por `http.server` e confirmar que não há erros na consola.

## Genética Reports (relatórios em PDF)

`genetica-reports.html` mostra a lista de `data/reports.json` (mais recente primeiro, com pesquisa); cada relatório tem o título, a data, uma descrição opcional e os botões **Descarregar PDF** / **Abrir no browser** (**Download PDF** / **Open in browser**).

Versão inglesa: cada relatório tem também um PDF em inglês (`ficheiro_en`, sempre `reports/<nome>_en.pdf`, com `paginas_en` e `tamanho_kb_en`). No modo **English** o cartão mostra o título EN, as páginas/tamanho do PDF inglês e “Language: English”, e os botões apontam para o PDF inglês; no modo **Português** fica tudo como antes (PDF em português). Por baixo dos botões, a ligação pequena **PDF: PT | EN** descarrega diretamente cada versão (a da língua da página fica marcada). O cartão em destaque (Imortalidade) funciona da mesma forma. Hoje: 116 relatórios, 116 com versão inglesa (os Haplogrupos Materno e Paterno nunca são publicados, nem em PT nem em EN).

```json
{"atualizado_em": "2026-10-02",
 "relatorios": [
  {"id": "farmacogenomica-632",
   "titulo": {"pt": "Farmacogenómica: resposta prevista a 632 medicamentos", "en": "Pharmacogenomics: predicted response to 632 drugs"},
   "data": "2026-10-02",
   "ficheiro": "reports/farmacogenomica-632-medicamentos.pdf",
   "descricao": {"pt": "…", "en": "…"}, "paginas": 49, "tamanho_kb": 272,
   "lingua": {"pt": "português", "en": "Portuguese"}, "etiquetas": ["PGx", "CPIC"],
   "ficheiro_en": "reports/farmacogenomica-632-medicamentos_en.pdf", "paginas_en": 48, "tamanho_kb_en": 275}
 ]}
```

Documento-mestre: uma entrada com `"destaque": true` (hoje, `imortalidade`, o relatório **Imortalidade** / **Immortality**) aparece num cartão em destaque por cima da pesquisa e da lista, com a etiqueta **Documento-mestre** / **Master document**; conta no total de relatórios, não se repete na grelha e fica sempre visível durante a pesquisa (o contador só o inclui se corresponder). A página não tem parágrafo de introdução.

Como acrescentar um relatório novo:
1. **Privacidade primeiro:** `pdftotext relatorio.pdf - | grep -i -E '…'` não pode encontrar o nome completo (só “Sérgio F”), a medida da balança, a data de nascimento, a idade, a família, a cidade, o país, nomes de laboratórios ou fornecedores, URLs, nomes de ficheiros/pastas privadas nem rótulos de ascendência ou população (PT e EN: “1000 Genomes”, europeu/European, africano/African, asiático/Asian, Ashkenazi, judeu/Jewish, nacionalidades de coortes como britânico, japonês, finlandês, dinamarquês, italiano…; países de estudos). Nomes de bases de dados (UK Biobank, FinnGen, GWAS Catalog, PGS Catalog, gnomAD), a dieta mediterrânica, a febre mediterrânica familiar, a medicina tradicional chinesa e nomes de plantas são permitidos. O metadado Title/Author do PDF tem de estar vazio. Se encontrar, gerar uma versão limpa a partir da fonte (HTML/MD) do relatório.
2. Mais simples: `python3 ferramentas/adicionar_colheita.py relatorio --pdf relatorio.pdf --id novo-relatorio --data 2026-12-03 --titulo-pt "…" --titulo-en "…" [--descricao-pt "…" --descricao-en "…" --paginas 12 --lingua-pt português --lingua-en Portuguese --nome nome-no-site.pdf]`. Faz a verificação de privacidade com `pdftotext` e `pdfinfo` (recusa o PDF se tiver termos proibidos ou Title/Author preenchidos), copia-o para `reports/` e junta a entrada em `data/reports.json`. A versão inglesa junta-se depois com `python3 ferramentas/adicionar_colheita.py relatorio-en --pdf relatorio_EN.pdf --id novo-relatorio` (mesma verificação; copia para `reports/<nome>_en.pdf` e grava `ficheiro_en`, `paginas_en`, `tamanho_kb_en`).
3. Ou à mão: copiar o PDF para `reports/` (nome só com letras, números, `.`, `-`, `_`) e acrescentar um objeto a `relatorios` (`id`, `titulo` PT/EN, `data` AAAA-MM-DD e `ficheiro` `reports/<nome>.pdf` são obrigatórios).
4. `python3 ferramentas/adicionar_colheita.py verificar` (confirma o JSON, que os PDFs PT e EN existem, que são PDF e que não têm termos proibidos; avisa de PDFs em `reports/` que não estão na lista) e abrir `genetica-reports.html` por `http.server`.

A página só aceita ficheiros `reports/<nome>.pdf` (e `reports/<nome>_en.pdf` para `ficheiro_en`); uma entrada inválida aparece marcada como “Ficheiro inválido”, sem link; um `ficheiro_en` inválido é ignorado (fica o PDF em português).

## Contagem de visitas e de PDFs (Worker próprio + GoatCounter)

- A contagem passa por um Cloudflare Worker próprio (`sf-site`), por isso funciona também com bloqueadores de anúncios (que costumam bloquear o script público do GoatCounter, já não usado). O endereço do Worker está numa só constante, em `sf.js` (`window.SF_W = 'https://sf-site.sergiofpt.workers.dev'`), carregado no `<head>` das quatro páginas. Com `SF_W = ''` o site volta às ligações diretas `reports/…` e não conta nada.
- **Visitas:** antes de `</body>`, um script pequeno (igual nas quatro páginas) envia uma vez por visita `{p: caminho da página (sem query), t: título, r: referrer, s: largura do ecrã}` para `SF_W + '/e'` (`navigator.sendBeacon`, ou `fetch` com `keepalive`). Não envia em `localhost`/rede local, em `file://`, dentro de iframes nem em browsers automatizados.
- **PDFs:** todas as ligações de PDF (botões Descarregar/Abrir dos cartões, documento-mestre Imortalidade, ligações “PDF: PT | EN” e ligações de fonte das páginas Genética Má/Boa) apontam para `SF_W + '/r/<ficheiro>.pdf'`; o Worker vai buscar o PDF a `reports/` deste site, entrega-o (Descarregar usa `?dl=1` → `Content-Disposition: attachment`, porque o atributo `download` não vale entre origens diferentes) e conta um evento com `path` = `reports/<ficheiro>.pdf` e `title` = título PT do relatório + língua (ex. “Esófago (EN)”), tirado de `data/reports.json`; um download (`?dl=1`) conta como evento distinto `download/<ficheiro>.pdf` (título “… · download”), desde 03-10-2026 (antes, os downloads contavam como aberturas). Assim conta o clique normal, Ctrl/Cmd + clique, o botão do meio e ligações copiadas. Não conta pedidos HEAD, pedidos parciais a meio do ficheiro nem robôs.
- O Worker envia as contagens à API do GoatCounter (conta `imortalistas`, `POST /api/v0/count`) com `no_sessions: true` (cada visita e cada abertura de PDF conta sempre, mesmo repetidas) e com o IP e o browser só para o GoatCounter tirar o país, o browser e o sistema; não guarda nada, sem cookies. As páginas continuam a enviar `no-referrer`.
- **Aparelhos:** com cada visita a página manda também o ecrã (largura, altura, densidade, toque) e, no Chrome/Edge, o modelo e a versão do sistema (Client Hints). O Worker tira daí só um rótulo (ex. “iPhone XR / 11”, “Galaxy S23 Ultra”, “Windows 11 · Chrome”, “Mac · Safari”) e envia-o ao GoatCounter como evento `aparelho/<tipo>/<rótulo>`, sem IP nem browser, no mesmo pedido da visita. Estes eventos não contam como visitas nem como aberturas de PDFs (aparecem na lista de eventos do painel do GoatCounter). O iPhone/iPad não diz o modelo: é estimado pelo tamanho do ecrã (grupo de modelos com o mesmo ecrã; com “Zoom do ecrã” pode falhar). Android só mostra o modelo quando o browser o indica (Chrome/Edge/Samsung Internet); nos computadores fica o sistema e o browser, sem versão do browser.
- O token do Worker (`GC_TOKEN`, permissão “Record pageviews”) é um secret do Worker no Cloudflare, nunca neste repositório; é diferente do token só de leitura das estatísticas.
- Se o Worker falhar, os PDFs deixam de abrir: pôr `SF_W = ''` em `sf.js` repõe as ligações diretas.
- Para não contar as próprias visitas, usar o endereço `#toggle-goatcounter` uma vez nesse browser (guarda `skipgc` em `localStorage`; repetir volta a contar as visitas). Os PDFs abertos contam sempre.
- Os testes usam um `sf.js` vazio ou um Worker local com um GoatCounter falso: nenhum teste contacta o GoatCounter nem conta visitas.

## Página escondida de estatísticas

- Uma página com nome difícil de adivinhar (o nome não está escrito em nenhum ficheiro do site), fora do menu, sem ligações a partir das outras páginas, com `noindex,nofollow` e **sem** a contagem (não carrega `sf.js`; as visitas a ela não contam). Mesmo visual do site (PT/EN, escuro por omissão, claro também; responsiva para telemóvel; sem bibliotecas nem pedidos externos, tudo no próprio ficheiro): cartões grandes com as visitas, as aberturas de PDFs, hoje e os últimos 7 dias; gráfico de barras por dia (visitas e aberturas de PDFs; 7/30/90 dias); proporção português vs inglês e abertos vs descarregados (gráficos circulares, com nota de que os downloads só se distinguem desde 03-10-2026); ranking dos PDFs mais abertos e descarregados com o título legível (de `data/reports.json`), os ficheiros, PT/EN com percentagem e abertos vs descarregados; países com bandeira (emoji a partir do código ISO, 🌐 se desconhecido; no Windows, que não tem emojis de bandeira, o código), páginas com nome legível, browsers, sistemas, aparelhos e origens com ícones e barras; “Atualizado em” na hora de Portugal. Sem dados, mostra um estado vazio.
- Os dados vêm de `data/estatisticas.json`, que o workflow `.github/workflows/goatcounter-stats.yml` atualiza de hora a hora (minuto 17, e também à mão em Actions → “Estatísticas GoatCounter” → Run workflow). O workflow corre `ferramentas/estatisticas_goatcounter.py` com o token só de leitura do secret `GOATCOUNTER_TOKEN` (API v0: `/stats/hits`, `/stats/total`, `/stats/locations`, `/stats/browsers`, `/stats/systems`, `/stats/sizes`, `/stats/toprefs`) e só faz commit (“estatísticas: atualização automática”, utilizador github-actions[bot]) quando o JSON muda.
- Cartão **Aparelhos**: modelos (telemóveis, tablets, computadores) com o número de visitas, % e “≈ estimativa” nos modelos de iPhone/iPad; conta a partir da publicação desta versão do Worker (os dados antigos não têm aparelhos). O cartão “Tamanho do ecrã” continua a mostrar as classes de ecrã do GoatCounter; países, browsers, sistemas e tamanhos somam só páginas e PDFs.
- Só contagens agregadas, sem IPs nem dados pessoais; das origens fica só o nome do site. Conta sem dados = zeros; erro da API ou token em falta = aviso no log, o JSON anterior fica igual. Os números são visitas e aberturas totais, não visitantes únicos: a API do GoatCounter só dá contagens de “visitantes”, mas como o Worker envia `no_sessions: true` cada pedido conta como novo (contagens anteriores a 03-10-2026 eram por sessão). Por relatório: `abertos_pt`, `abertos_en`, `descarregados_pt`, `descarregados_en`, `pt`, `en` e `total` (abertos + descarregados); totais `pdf_abertos`, `pdf_descarregados`, `pdf_pt`, `pdf_en` e `descarregados_desde`. Além dos totais, o JSON tem `visitas_hoje`, `visitas_7d`, `aberturas_hoje`, `aberturas_7d`, `aberturas_30d` e `dias[].aberturas` (o painel também lê o formato antigo, calculando hoje/7 dias a partir de `dias`).
- O `data/estatisticas.json` muda sozinho: fica fora das procuras do `verificar` (que só confirma a estrutura) e da verificação do site no ar. O JSON é público como o resto do site: a página escondida não é secreta, só não está à vista.

## Regras permanentes do painel

- Só análises + Intolerâncias Alimentares (secção própria) em `index.html` + Genética Má (`genetica.html`), Genética Boa (`genetica-boa.html`) e Genética Reports (`genetica-reports.html`, relatórios em PDF): nada de outros exames, medicação/stack, suplementos, prioridades, questões ou sugestões dos bots em `index.html`. Exceção (pedido do Sérgio F, 02-10-2026): nas páginas de genética, os blocos Evitar/Priorizar e o Protocolo genético podem ter fármacos, suplementos com doses, dieta, exercício e rastreio ligados aos genes, sempre como sugestão a validar pelo médico e sem valores de outros bots além dos usados nas regras de consistência.
- Identificação: só “Sérgio F” (cabeçalho “Sérgio F · M”); sem idade, ano ou data de nascimento, nem cidade, nos HTML, JSON, README e PDFs publicados (o `verificar` recusa).
- Privacidade: nunca publicar a medida da balança, o índice de massa do corpo (nem pela sigla), índices por altura² nem nada que permita deduzir aquela medida.
- Sem nomes de laboratórios ou fornecedores em lado nenhum, nas duas línguas: só datas.
- Títulos: “Cronologia de Exames de Sangue” / “Blood Test Timeline” (`index.html`) e os títulos acima nas páginas de genética. Cabeçalho sem marca, igual nas quatro páginas: Resumo · Análises · Intolerâncias Alimentares (âncoras de `index.html`) · Genética Má (`genetica.html`) · Genética Boa (`genetica-boa.html`) · Genética Reports (`genetica-reports.html`), com o seletor “Português | English” no canto superior direito (guardado em `localStorage`, chave `lang`, partilhada pelas quatro páginas; por omissão português). **Link para partilhar em inglês:** `?lang=en` na URL (ex. `https://sergiofpt.github.io/imortalistas/?lang=en`) abre a página em inglês e grava a escolha, por isso a navegação pelo menu continua em inglês; `?lang=pt` força o português; trocar de idioma numa página com `?lang=` atualiza a URL. A contagem usa só o caminho, sem `?lang`.
- Tema: seletor “Escuro | Claro” / “Dark | Light” ao lado do idioma (guardado em `localStorage`, chave `theme`, partilhada pelas quatro páginas; sem escolha, escuro: é o default para quem entra pela primeira vez, seja qual for o tema do sistema, e é aplicado por um script no `<head>` antes do primeiro desenho, para não piscar em branco; quem escolher Claro fica com o claro). Cores só por variáveis CSS, incluindo os gráficos.
- `meta robots noindex` nas quatro páginas.
