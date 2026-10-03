# imortalistas · Cronologia de Exames de Sangue

Cronologia de Exames de Sangue do Sérgio F: resultados de análises ao sangue (e urina do mesmo painel), para registo e comparação entre datas, e a secção Intolerâncias Alimentares (`index.html`). A genética tem três páginas próprias: `genetica.html` (“Genética Má”: só resultados desfavoráveis), `genetica-boa.html` (“Genética Boa”: só resultados favoráveis) e `genetica-reports.html` (“Genética Reports”: relatórios completos em PDF). Site estático em GitHub Pages, `noindex` nas quatro páginas.

```
index.html                         análises ao sangue + Intolerâncias Alimentares (HTML + CSS + JS, sem bibliotecas nem pedidos externos)
genetica.html                      Genética Má: só resultados desfavoráveis (mesmo cabeçalho, idioma e tema); conteúdo em data/genetica.json
genetica-boa.html                  Genética Boa: só resultados favoráveis; conteúdo em data/genetica_boa.json
data/sangue.json                   resultados por marcador e por data (sangue/urina em "marcadores", intolerâncias alimentares em "intolerancias")
data/genetica.json                 conteúdo de genetica.html (secções, linhas, PT/EN)
data/genetica_boa.json             conteúdo de genetica-boa.html (mesmo formato)
data/genetica_protocolo.json       Protocolo genético consolidado, mostrado no topo das duas páginas de genética
genetica-reports.html              Genética Reports: lista de relatórios em PDF; conteúdo em data/reports.json
data/reports.json                  lista dos relatórios (título PT/EN, data, ficheiro em reports/)
reports/*.pdf                      os PDFs dos relatórios (já verificados quanto à privacidade)
ferramentas/adicionar_colheita.py  acrescenta uma data ou um relatório e verifica os ficheiros (sangue.json, genetica*.json, reports.json + PDFs e termos proibidos)
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
- Cada entrada de `linhas` é uma linha da tabela: `item` (gene/tema, a negrito), `texto`, e opcionalmente `estado` + `rotulo` (a etiqueta colorida): `ok` verde, `warn` amarelo, `bad` vermelho, `na` cinzento, `info` azul.
- Textos bilingues: `{"pt": "…", "en": "…"}`; se o texto for igual nas duas línguas (ex. nome do gene) pode ser só `"CYP2C9"`. Pode levar HTML simples: `<b>`, `<i>`, `<em>`, `<strong>`, `<br>`, `<small>`, `<sub>`, `<sup>` (o resto é mostrado como texto).
- As mesmas regras de privacidade e de nomes (abaixo) aplicam-se aqui: sem nomes de laboratórios ou empresas, sem dados pessoais.
- Depois de editar: `python3 ferramentas/adicionar_colheita.py verificar` (estrutura, PT+EN em todos os textos, ids únicos, estados válidos, `evitar`/`priorizar` em todas as secções, `ajustar`/`monitorizar`/`farmacos`, protocolo, reports.json + privacidade dos PDFs, HTML permitido, termos proibidos), abrir `genetica.html` e `genetica-boa.html` por `http.server` e confirmar que não há erros na consola.

## Genética Reports (relatórios em PDF)

`genetica-reports.html` mostra a lista de `data/reports.json` (mais recente primeiro, com pesquisa); cada relatório tem o título, a data, uma descrição opcional e os botões **Descarregar PDF** / **Abrir no browser** (**Download PDF** / **Open in browser**).

```json
{"atualizado_em": "2026-10-02",
 "relatorios": [
  {"id": "farmacogenomica-632",
   "titulo": {"pt": "Farmacogenómica: resposta prevista a 632 medicamentos", "en": "Pharmacogenomics: predicted response to 632 drugs"},
   "data": "2026-10-02",
   "ficheiro": "reports/farmacogenomica-632-medicamentos.pdf",
   "descricao": {"pt": "…", "en": "…"}, "paginas": 49, "tamanho_kb": 272,
   "lingua": {"pt": "português", "en": "Portuguese"}, "etiquetas": ["PGx", "CPIC"]}
 ]}
```

Documento-mestre: uma entrada com `"destaque": true` (hoje, `imortalidade`, o relatório **Imortalidade** / **Immortality**) aparece num cartão em destaque por cima da pesquisa e da lista, com a etiqueta **Documento-mestre** / **Master document**; conta no total de relatórios, não se repete na grelha e fica sempre visível durante a pesquisa (o contador só o inclui se corresponder). A página não tem parágrafo de introdução.

Como acrescentar um relatório novo:
1. **Privacidade primeiro:** `pdftotext relatorio.pdf - | grep -i -E '…'` não pode encontrar o nome completo (só “Sérgio F”), a medida da balança, a data de nascimento, a cidade, o país nem nomes de laboratórios ou fornecedores. Se encontrar, gerar uma versão limpa a partir da fonte (HTML/MD) do relatório.
2. Mais simples: `python3 ferramentas/adicionar_colheita.py relatorio --pdf relatorio.pdf --id novo-relatorio --data 2026-12-03 --titulo-pt "…" --titulo-en "…" [--descricao-pt "…" --descricao-en "…" --paginas 12 --lingua-pt português --lingua-en Portuguese --nome nome-no-site.pdf]`. Faz a verificação de privacidade com `pdftotext` (recusa o PDF se tiver termos proibidos), copia-o para `reports/` e junta a entrada em `data/reports.json`.
3. Ou à mão: copiar o PDF para `reports/` (nome só com letras, números, `.`, `-`, `_`) e acrescentar um objeto a `relatorios` (`id`, `titulo` PT/EN, `data` AAAA-MM-DD e `ficheiro` `reports/<nome>.pdf` são obrigatórios).
4. `python3 ferramentas/adicionar_colheita.py verificar` (confirma o JSON, que o PDF existe, que é PDF e que não tem termos proibidos; avisa de PDFs em `reports/` que não estão na lista) e abrir `genetica-reports.html` por `http.server`.

A página só aceita ficheiros `reports/<nome>.pdf`; uma entrada inválida aparece marcada como “Ficheiro inválido”, sem link.

## Regras permanentes do painel

- Só análises + Intolerâncias Alimentares (secção própria) em `index.html` + Genética Má (`genetica.html`), Genética Boa (`genetica-boa.html`) e Genética Reports (`genetica-reports.html`, relatórios em PDF): nada de outros exames, medicação/stack, suplementos, prioridades, questões ou sugestões dos bots em `index.html`. Exceção (pedido do Sérgio F, 02-10-2026): nas páginas de genética, os blocos Evitar/Priorizar e o Protocolo genético podem ter fármacos, suplementos com doses, dieta, exercício e rastreio ligados aos genes, sempre como sugestão a validar pelo médico e sem valores de outros bots além dos usados nas regras de consistência.
- Identificação: só “Sérgio F” e a idade; sem data de nascimento nem cidade.
- Privacidade: nunca publicar a medida da balança, o índice de massa do corpo (nem pela sigla), índices por altura² nem nada que permita deduzir aquela medida.
- Sem nomes de laboratórios ou fornecedores em lado nenhum, nas duas línguas: só datas.
- Títulos: “Cronologia de Exames de Sangue” / “Blood Test Timeline” (`index.html`) e os títulos acima nas páginas de genética. Cabeçalho sem marca, igual nas quatro páginas: Resumo · Análises · Intolerâncias Alimentares (âncoras de `index.html`) · Genética Má (`genetica.html`) · Genética Boa (`genetica-boa.html`) · Genética Reports (`genetica-reports.html`), com o seletor “Português | English” no canto superior direito (guardado em `localStorage`, chave `lang`, partilhada pelas quatro páginas; por omissão português).
- Tema: seletor “Escuro | Claro” / “Dark | Light” ao lado do idioma (guardado em `localStorage`, chave `theme`, partilhada pelas quatro páginas; sem escolha, segue o tema do sistema). Cores só por variáveis CSS, incluindo os gráficos.
- `meta robots noindex` nas quatro páginas.
