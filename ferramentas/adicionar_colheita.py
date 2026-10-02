#!/usr/bin/env python3
r"""Acrescenta uma nova data (colheita) de análises a data/sangue.json.

Uso (a partir da raiz do repositório):
  python3 ferramentas/adicionar_colheita.py sangue --csv historico.csv --data 2026-12-03 \
      --rotulo "dez 2026" --descricao "03-12-2026" [--rotulo-en "Dec 2026" --descricao-en "03-12-2026"]
      [--nota "..." --nota-en "..."] [--datas-csv 2026-12-03,2026-12-05]
  python3 ferramentas/adicionar_colheita.py verificar

É idempotente: voltar a correr com a mesma data substitui os resultados dessa data.
Não grava o nome do laboratório (a página mostra só datas).
Marcadores de intolerância alimentar (IgG/IgE específicas para alimentos) vão automaticamente para a lista
"intolerancias" (secção própria da página) e são classificados 'intolerante' / 'nao_intolerante' pelo limite do
laboratório (ver classifica_intolerancia); os restantes vão para "marcadores".
"""
import argparse, csv, json, os, re, sys
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F_SANGUE = os.path.join(RAIZ, 'data', 'sangue.json')
# privacidade: nunca publicar a medida da balança nem nada que a permita deduzir
# (os termos são montados por partes para que o próprio ficheiro não os contenha literalmente)
_T = ['ger' + 'mano', 'sou' + 'sa', 'cu' + 'f', 'coim' + 'bra', 'pe' + 'so', 'i' + 'mc', 'b' + 'mi', 'f' + 'mi', 'l' + 'mi', '19' + '99', 'lis' + 'boa', 'lis' + 'bon', 'chen' + 'nai']
PROIBIDO = re.compile('|'.join(r'\b%s\b' % t for t in _T) + '|' + '|'.join([
    'we' + r'ight(?!:)', 'massa ' + 'corporal', 'frei' + 'tas', r'\d\s?' + r'kg\b', 'kg' + '/m', 'har' + 'ris',
    # nomes de laboratórios/fornecedores: a página mostra só datas
    'ai' + 'wo', 'thyro' + 'care', 'lipo' + 'mic', 'food' + 'print', 'self' + 'decode']), re.I)
# painéis de intolerância/sensibilidade alimentar (IgG/IgE específicas para alimentos): lista 'intolerancias'
INTOL = re.compile(r'aliment|intoler|food', re.I)
def e_intolerancia(nome, cat, lab):
    return bool(INTOL.search(cat or '') or INTOL.search(nome or '') or INTOL.search(lab or '') or re.match(r'Ig[GE]4? (?!total)', nome or '', re.I))
ESTADOS = {'otimo', 'aceitavel', 'fora_do_otimo', 'fora_de_referencia', 'sem_alvo', 'intolerante', 'nao_intolerante'}
# ---- classificação das intolerâncias (a página usa a mesma regra) ----
# Limite = ref_max (limite superior do intervalo normal/negativo do laboratório); se faltar, lê-se do texto
# da referência ("normal ≤23", "negativo <24"...). Valor acima do limite = 'intolerante' (inclui a faixa
# limítrofe/duvidosa); igual ou abaixo = 'nao_intolerante'. "<x" só é 'nao_intolerante' se x ≤ limite; ">x" é
# 'intolerante' se x ≥ limite. Texto: "negativo" = nao_intolerante; "positivo/elevado/limítrofe/duvidoso" = intolerante.
# Sem limite ou sem valor interpretável: None (fica 'sem_alvo' e o verificar avisa).
def classifica_intolerancia(v, ref_max, ref_txt):
    t = str(v if v is not None else '').strip()
    if re.search(r'neg|n[ãa]o detet|not detect', t, re.I): return 'nao_intolerante'
    if re.search(r'pos|elev|lim[ií]tr|border|equ[ií]v|duvid|d[uú]bi', t, re.I): return 'intolerante'
    cut = ref_max
    if cut is None and ref_txt:
        mm = re.search(r'(?:normal|negativ\w*)\s*(≤|<=|<)\s*(\d+(?:[.,]\d+)?)', ref_txt, re.I)
        if mm: cut = float(mm.group(2).replace(',', '.')) - (1e-9 if mm.group(1) == '<' else 0)
    mm = re.fullmatch(r'([<>≤≥]=?)?\s*(-?\d+(?:[.,]\d+)?)', t)
    if cut is None or not mm: return None
    x, op = float(mm.group(2).replace(',', '.')), mm.group(1) or ''
    if op[:1] in ('<', '≤'): return 'nao_intolerante' if x <= cut else None
    if op[:1] in ('>', '≥'): return 'intolerante' if x >= cut else None
    return 'intolerante' if x > cut else 'nao_intolerante'
# ---- fim classificação

def ler(p): return json.load(open(p, encoding='utf-8'))
def gravar(p, d):
    with open(p, 'w', encoding='utf-8') as f: json.dump(d, f, ensure_ascii=False, indent=1); f.write('\n')
def num(x):
    x = (x or '').strip()
    if not x: return None
    try: f = float(x)
    except ValueError: return None
    return int(f) if re.fullmatch(r'-?\d+', x) else f
def estado(v, rmin, rmax, omin, omax, regras=()):
    """Igual a biomarcadores/scripts/comum.py + regras do painel."""
    if 'acima_do_otimo_fora' in regras and omax is not None and v >= omax: return 'fora_de_referencia'
    if 'sem_limite_inferior' in regras: rmin = None   # LDL, ApoB, estrôncio: abaixo do mínimo do laboratório não conta como fora
    if omin is None and omax is None and rmin is None and rmax is None: return 'sem_alvo'
    if (omin is None or v >= omin) and (omax is None or v <= omax): return 'otimo'
    if not ((rmin is None or v >= rmin) and (rmax is None or v <= rmax)): return 'fora_de_referencia'
    lo = 0 if omin is None else omin
    marg = 0.25 * (omax - lo) if omax is not None else 0.10 * abs(omin)
    dist = (omin - v) if (omin is not None and v < omin) else (v - omax)
    return 'aceitavel' if dist <= marg else 'fora_do_otimo'
def upsert_colheita(d, data, rotulo, descricao, extra=None):
    c = next((c for c in d['colheitas'] if c['data'] == data), None)
    if not c: c = {'data': data}; d['colheitas'].append(c)
    if rotulo: c['rotulo'] = rotulo
    if descricao: c['descricao'] = descricao
    for k, v in (extra or {}).items():
        if v: c[k] = v
    c.setdefault('rotulo', data)
    d['colheitas'].sort(key=lambda c: c['data'])

def cmd_sangue(a):
    d = ler(F_SANGUE); datas = (a.datas_csv or a.data).split(',')
    rows = [r for r in csv.DictReader(open(a.csv, encoding='utf-8')) if r['data_colheita'] in datas]
    if not rows: sys.exit(f'Nenhuma linha com data_colheita em {datas} em {a.csv}')
    for t in (a.rotulo, a.descricao, a.nota, a.rotulo_en, a.descricao_en, a.nota_en):
        if t and PROIBIDO.search(t): sys.exit(f'Texto com termo proibido (ex. nome do laboratório): {t!r}')
    upsert_colheita(d, a.data, a.rotulo, a.descricao, {'rotulo_en': a.rotulo_en, 'descricao_en': a.descricao_en, 'nota': a.nota, 'nota_en': a.nota_en})
    d.setdefault('intolerancias', [])
    # marcadores alimentares que tenham ficado na lista do sangue passam para a secção própria
    for m in [m for m in d['marcadores'] if e_intolerancia(m['m'], m.get('c'), '')]:
        d['marcadores'].remove(m); d['intolerancias'].append(m); print('  movido para intolerancias:', m['m'])
    idx = {m['m']: m for m in d['marcadores'] + d['intolerancias']}
    for m in d['marcadores'] + d['intolerancias']: m['resultados'] = [r for r in m['resultados'] if r['data'] != a.data]
    novos = ignorados = 0
    for r in rows:
        nome = r['marcador']
        if PROIBIDO.search(nome) or PROIBIDO.search(r['unidade']):
            ignorados += 1; print('  ignorado (privacidade):', nome); continue
        m = idx.get(nome); alim = e_intolerancia(nome, r['categoria'], r['laboratorio'])
        if not m:
            m = {'m': nome, 'c': r['categoria'], 'otimo_min': num(r['otimo_min']), 'otimo_max': num(r['otimo_max']), 'resultados': []}
            d['intolerancias' if alim else 'marcadores'].append(m); idx[nome] = m; novos += 1
        elif alim and m in d['marcadores']:
            d['marcadores'].remove(m); d['intolerancias'].append(m)
        if alim:
            m['regras'] = ['intolerancia']; m['melhor'] = 'baixo'; m['otimo_min'] = None; m['otimo_max'] = None; m.pop('alvo', None)
        regras = m.get('regras', [])
        v = r['valor']; s = r['estado'] if r['estado'] in ESTADOS else None
        if 'so_categoria' in regras and num(v) is not None:   # NAFLD Fibrosis Score: o número usa medidas corporais
            x = num(v); v = '< -1.455' if x < -1.455 else ('> 0.676' if x > 0.676 else '-1.455 a 0.676')
        if regras and num(r['valor']) is not None and 'so_categoria' not in regras:
            s = estado(float(r['valor']), num(r['ref_min']), num(r['ref_max']), m.get('otimo_min'), m.get('otimo_max'), regras)
        if 'sem_alvo' in regras: s = 'sem_alvo'
        if 'intolerancia' in regras:
            s = classifica_intolerancia(v, num(r['ref_max']), r['ref_texto'])
            if not s: s = 'sem_alvo'; print(f'  AVISO: {nome} = {v!r} sem limite interpretável em {r["ref_texto"]!r}: fica sem classificação')
        res = {'data': a.data, 'v': v, 'u': r['unidade'], 'ref': r['ref_texto'],
               'ref_min': num(r['ref_min']), 'ref_max': num(r['ref_max'])}
        if s: res['s'] = s
        if r['data_colheita'] != a.data: res['data_real'] = r['data_colheita']
        m['resultados'].append(res); m['resultados'].sort(key=lambda x: x['data'])
    d['atualizado_em'] = a.hoje
    gravar(F_SANGUE, d)
    print(f'sangue: {len(rows) - ignorados} resultados em {a.data}; {novos} marcadores novos; {len(d["marcadores"])} marcadores; {len(d["intolerancias"])} intolerâncias alimentares; {len(d["colheitas"])} datas')

def cmd_verificar(a):
    ok = True
    for p in (F_SANGUE,):
        d = ler(p); datas = {c['data'] for c in d['colheitas']}
        itens = d['marcadores'] + d.get('intolerancias', [])
        for i in d['marcadores']:
            if e_intolerancia(i['m'], i.get('c'), ''): ok = False; print(f'ERRO {p}: {i["m"]} é intolerância alimentar mas está em "marcadores"')
        for i in d.get('intolerancias', []):
            if 'intolerancia' not in i.get('regras', []): ok = False; print(f'ERRO {p}: {i["m"]} (intolerancias) sem a regra "intolerancia"')
            for r in i['resultados']:
                esp = classifica_intolerancia(r.get('v'), r.get('ref_max'), r.get('ref'))
                if esp and r.get('s') != esp: ok = False; print(f'ERRO {p}: {i["m"]} {r["data"]} = {r.get("v")} deve ser {esp} (está {r.get("s")})')
                if not esp: print(f'AVISO {p}: {i["m"]} {r["data"]} = {r.get("v")!r} sem classificação (limite em falta)')
        for i in d['marcadores']:
            if any(r.get('s') in ('intolerante', 'nao_intolerante') for r in i['resultados']): ok = False; print(f'ERRO {p}: {i["m"]} tem estado de intolerância fora da secção')
        for i in itens:
            for r in i['resultados']:
                if r['data'] not in datas: ok = False; print(f'ERRO {p}: {i["m"]} tem data {r["data"]} sem colheita')
                if 'lab' in r: ok = False; print(f'ERRO {p}: {i["m"]} tem campo lab (a página mostra só datas)')
                if r.get('s') and r['s'] not in ESTADOS: ok = False; print(f'ERRO {p}: estado inválido {r["s"]} em {i["m"]}')
        print(f'{os.path.basename(p)}: {len(d["marcadores"])} marcadores + {len(d.get("intolerancias", []))} intolerâncias alimentares, datas {sorted(datas)}')
    for base, _, fs in os.walk(RAIZ):
        if '.git' in base: continue
        for f in fs:
            if not f.endswith(('.html', '.json', '.md', '.py', '.txt')) : continue
            t = open(os.path.join(base, f), encoding='utf-8').read().replace('font-weight', '')
            for mt in PROIBIDO.finditer(t):
                ok = False; print(f'PROIBIDO em {f}: …{t[max(0, mt.start()-30):mt.end()+30]}…')
    print('OK' if ok else 'FALHOU'); sys.exit(0 if ok else 1)

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument('--hoje', default=__import__('datetime').date.today().isoformat())
sp = ap.add_subparsers(dest='cmd', required=True)
p = sp.add_parser('sangue'); p.add_argument('--csv', required=True); p.add_argument('--data', required=True)
p.add_argument('--datas-csv'); p.add_argument('--rotulo'); p.add_argument('--descricao'); p.add_argument('--nota')
p.add_argument('--rotulo-en'); p.add_argument('--descricao-en'); p.add_argument('--nota-en'); p.set_defaults(f=cmd_sangue)
p = sp.add_parser('verificar'); p.set_defaults(f=cmd_verificar)
a = ap.parse_args(); a.f(a)
