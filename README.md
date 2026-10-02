# imortalistas

Painel de saúde e longevidade do Sérgio F (página estática em GitHub Pages, `noindex`).

```
index.html                         página (HTML + CSS + JS, sem bibliotecas nem pedidos externos)
data/sangue.json                   análises ao sangue e à urina, por marcador e por data
data/exames.json                   valores numéricos dos outros exames, por exame/parâmetro e por data
ferramentas/adicionar_colheita.py  acrescenta uma data e verifica os ficheiros
.nojekyll
```

A página lê `data/*.json` ao abrir. Para a ver localmente: `python3 -m http.server` na raiz e abrir `http://localhost:8000/` (por `file://` o navegador bloqueia a leitura dos JSON).

## Formato dos dados

`data/sangue.json`
```json
{
 "colheitas": [ {"data": "2026-08-25", "rotulo": "ago 2026", "descricao": "AIWO e Thyrocare 25-08-2026 · Lipomic 27-08-2026 · Chennai"} ],
 "marcadores": [
  {"m": "Ferritina", "c": "Ferro", "alvo": "< 100", "otimo_min": null, "otimo_max": 100, "regras": ["acima_do_otimo_fora"],
   "resultados": [
    {"data": "2026-08-25", "lab": "AIWO", "v": "310", "u": "ng/mL", "ref": "30.00 - 300.00", "ref_min": 30, "ref_max": 300,
     "s": "fora_de_referencia", "nota": "Alvo do Sérgio < 100 ng/mL."}
   ]}
 ]
}
```
- `colheitas[].data` é a chave de cada coluna da tabela (AAAA-MM-DD). Cada resultado tem `data` igual a uma colheita; se o exame foi feito noutro dia da mesma bateria, acrescenta-se `data_real` (ex. Lipomic: `"data": "2026-08-25", "data_real": "2026-08-27"`).
- `v` é o valor tal como no exame (texto; ponto decimal). `s` é o estado: `otimo`, `aceitavel`, `fora_do_otimo`, `fora_de_referencia` ou `sem_alvo`. Se faltar, a página calcula-o com a mesma regra de `biomarcadores/scripts/comum.py`.
- `regras` (opcional): `sem_limite_inferior` (LDL, ApoB, estrôncio: quanto mais baixo, melhor), `acima_do_otimo_fora` (ferritina ≥ 100 = fora), `so_categoria` (NAFLD Fibrosis Score: só a categoria, nunca o número).
- `alvo` é só o texto mostrado; se faltar, é gerado a partir de `otimo_min`/`otimo_max`.
- O nome `m` tem de ser exatamente o mesmo entre datas (nomes normalizados de `historico.csv`).

`data/exames.json`: `colheitas` igual; `grupos[]` = `{ "g": nome do exame, "itens": [ {"m", "u", "ref", "otimo_min"?, "otimo_max"?, "melhor"? ("baixo"/"alto"), "resultados": [ {"data", "v" (número), "s", "data_real"?, "nota"?} ]} ] }`.

## Como adicionar uma nova data

1. **Análises ao sangue:** registar primeiro o exame em `/workspace/biomarcadores/historico.csv` com o procedimento habitual (`comum.gravar()`), e depois, na raiz deste repositório:
   ```
   python3 ferramentas/adicionar_colheita.py sangue --csv /workspace/biomarcadores/historico.csv \
     --data 2026-12-03 --rotulo "dez 2026" --descricao "AIWO 03-12-2026 · Lisboa" \
     [--datas-csv 2026-12-03,2026-12-05]
   ```
   `--data` é a coluna nova; `--datas-csv` junta na mesma coluna exames da mesma bateria feitos noutros dias. O script é idempotente (repetir substitui essa data), mantém os nomes dos marcadores, cria marcadores novos se for preciso e aplica as regras acima.
2. **Outros exames (DEXA, volumetria, sono, …):** um comando por valor numérico, por exemplo
   ```
   python3 ferramentas/adicionar_colheita.py exame --data 2027-02-10 --rotulo "fev 2027" \
     --grupo "DEXA: composição corporal" --item "Gordura corporal" --valor 28.4 --data-real 2027-02-11
   ```
   (usar o mesmo `--grupo` e `--item` de `data/exames.json`; `--estado` opcional). Também se pode editar o JSON à mão seguindo o formato acima. Os cartões de texto da secção Exames descrevem os relatórios de 25–26-08-2026; quando houver relatórios novos, atualizar esse texto em `index.html`.
3. Correr `python3 ferramentas/adicionar_colheita.py verificar` (datas coerentes e pesquisa de termos proibidos), abrir a página por `http.server` e confirmar que não há erros na consola.
4. Fazer commit de `data/*.json` (e de `index.html`, se mudou). A tabela passa a ter uma coluna por data, Δ face à data anterior, filtro de tendência e gráfico por marcador.

## Regras permanentes do painel

- Nome: só “Sérgio F”.
- Privacidade: nunca publicar a medida da balança, o índice de massa do corpo (nem pela sigla), índices por altura² (de massa gorda, de massa magra, ALMI…), massas totais de gordura/magra/osso nem a TMB estimada por fórmula — nada que permita deduzir aquela medida. Os percentuais da DEXA são permitidos.
- `meta robots noindex`; sugestões dos bots marcadas como “não aplicadas”; sem recomendações de NAD+.
- Não repor as secções retiradas (Dieta e exercício, Pele/corpo/cabelo, Investigação, Resumo antigo). A secção Prioridades fica logo a seguir às Análises.
