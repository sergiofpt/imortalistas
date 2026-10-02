# imortalistas · Cronologia de Exames de Sangue

Cronologia de Exames de Sangue do Sérgio F: resultados de análises ao sangue (e urina do mesmo painel), para registo e comparação entre datas, e a secção Genética. Página estática em GitHub Pages, `noindex`.

```
index.html                         página (HTML + CSS + JS, sem bibliotecas nem pedidos externos); a secção Genética é texto fixo no HTML
data/sangue.json                   resultados por marcador e por data
ferramentas/adicionar_colheita.py  acrescenta uma data e verifica o ficheiro
.nojekyll
```

A página lê `data/sangue.json` ao abrir. Para a ver localmente: `python3 -m http.server` na raiz e abrir `http://localhost:8000/` (por `file://` o navegador bloqueia a leitura do JSON).

## Formato dos dados

```json
{
 "colheitas": [ {"data": "2026-08-25", "rotulo": "ago 2026", "descricao": "AIWO e Thyrocare 25-08-2026 · Lipomic 27-08-2026"} ],
 "marcadores": [
  {"m": "Ferritina", "c": "Ferro", "alvo": "< 100", "otimo_min": null, "otimo_max": 100, "regras": ["acima_do_otimo_fora"],
   "resultados": [
    {"data": "2026-08-25", "lab": "AIWO", "v": "310", "u": "ng/mL", "ref": "30.00 - 300.00", "ref_min": 30, "ref_max": 300,
     "s": "fora_de_referencia", "nota": "Alvo do Sérgio < 100 ng/mL."}
   ]}
 ]
}
```
- `colheitas[].data` é a chave de cada coluna da tabela (AAAA-MM-DD). Cada resultado tem `data` igual a uma colheita; se a análise foi feita noutro dia da mesma bateria, acrescenta-se `data_real` (ex. Lipomic: `"data": "2026-08-25", "data_real": "2026-08-27"`).
- `v` é o valor tal como no boletim (texto; ponto decimal). `s` é o estado: `otimo`, `aceitavel`, `fora_do_otimo`, `fora_de_referencia` ou `sem_alvo`. Se faltar, a página calcula-o com a mesma regra de `biomarcadores/scripts/comum.py`.
- `regras` (opcional): `sem_limite_inferior` (LDL, ApoB, estrôncio: quanto mais baixo, melhor), `acima_do_otimo_fora` (ferritina ≥ 100 = fora), `so_categoria` (NAFLD Fibrosis Score: só a categoria, nunca o número).
- `alvo` é só o texto mostrado; se faltar, é gerado a partir de `otimo_min`/`otimo_max`.
- `nota` (opcional): só notas factuais sobre o próprio marcador ou a amostra (sem medicação, genética, suplementos nem recomendações).
- O nome `m` tem de ser exatamente o mesmo entre datas (nomes normalizados de `historico.csv`).

## Como adicionar uma nova data

1. Registar primeiro as análises em `/workspace/biomarcadores/historico.csv` com o procedimento habitual (`comum.gravar()`).
2. Na raiz deste repositório:
   ```
   python3 ferramentas/adicionar_colheita.py sangue --csv /workspace/biomarcadores/historico.csv \
     --data 2026-12-03 --rotulo "dez 2026" --descricao "AIWO 03-12-2026" \
     [--datas-csv 2026-12-03,2026-12-05]
   ```
   `--data` é a coluna nova; `--datas-csv` junta na mesma coluna análises da mesma bateria feitas noutros dias. O script é idempotente (repetir substitui essa data), mantém os nomes dos marcadores, cria marcadores novos se for preciso e aplica as regras acima.
3. Correr `python3 ferramentas/adicionar_colheita.py verificar` (datas coerentes e pesquisa de termos proibidos), abrir a página por `http.server` e confirmar que não há erros na consola.
4. Fazer commit de `data/sangue.json`. A tabela passa a ter uma coluna por data, Δ face à data de comparação, filtro de tendência e gráfico por marcador.

## Regras permanentes do painel

- Só análises + Genética: nada de outros exames, medicação/stack, suplementos, prioridades, questões ou sugestões dos bots.
- Identificação: só “Sérgio F” e a idade; sem data de nascimento nem cidade.
- Privacidade: nunca publicar a medida da balança, o índice de massa do corpo (nem pela sigla), índices por altura² nem nada que permita deduzir aquela medida.
- `meta robots noindex`.
