# imortalistas · Cronologia de Exames de Sangue

Cronologia de Exames de Sangue do Sérgio F: resultados de análises ao sangue (e urina do mesmo painel), para registo e comparação entre datas, a secção Intolerâncias Alimentares e a secção Genética. Página estática em GitHub Pages, `noindex`.

```
index.html                         página (HTML + CSS + JS, sem bibliotecas nem pedidos externos); a secção Genética é texto fixo no HTML, em PT e EN
data/sangue.json                   resultados por marcador e por data (sangue/urina em "marcadores", intolerâncias alimentares em "intolerancias")
ferramentas/adicionar_colheita.py  acrescenta uma data e verifica o ficheiro
.nojekyll
```

A página lê `data/sangue.json` ao abrir. Para a ver localmente: `python3 -m http.server` na raiz e abrir `http://localhost:8000/` (por `file://` o navegador bloqueia a leitura do JSON).

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
4. Fazer commit de `data/sangue.json`. A tabela passa a ter uma coluna por data, Δ face à data de comparação, filtro de tendência e gráfico por marcador.

## Regras permanentes do painel

- Só análises + Intolerâncias Alimentares (secção própria) + Genética: nada de outros exames, medicação/stack, suplementos, prioridades, questões ou sugestões dos bots.
- Identificação: só “Sérgio F” e a idade; sem data de nascimento nem cidade.
- Privacidade: nunca publicar a medida da balança, o índice de massa do corpo (nem pela sigla), índices por altura² nem nada que permita deduzir aquela medida.
- Sem nomes de laboratórios ou fornecedores em lado nenhum, nas duas línguas: só datas.
- Título: “Cronologia de Exames de Sangue” / “Blood Test Timeline”; cabeçalho sem marca, com o seletor “Português | English” no canto superior direito (guardado em `localStorage`, chave `lang`; por omissão português).
- Tema: seletor “Escuro | Claro” / “Dark | Light” ao lado do idioma (guardado em `localStorage`, chave `theme`; sem escolha, segue o tema do sistema). Cores só por variáveis CSS, incluindo os gráficos.
- `meta robots noindex`.
