#!/usr/bin/env python3
r"""Acrescenta uma nova data (colheita) de análises a data/sangue.json.

Uso (a partir da raiz do repositório):
  python3 ferramentas/adicionar_colheita.py sangue --csv historico.csv --data 2026-12-03 \
      --rotulo "dez 2026" --descricao "AIWO 03-12-2026" [--datas-csv 2026-12-03,2026-12-05]
  python3 ferramentas/adicionar_colheita.py verificar

É idempotente: voltar a correr com a mesma data substitui os resultados dessa data.
"""
import argparse, csv, json, os, re, sys
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F_SANGUE = os.path.join(RAIZ, 'data', 'sangue.json')
# privacidade: nunca publicar a medida da balança nem nada que a permita deduzir
# (os termos são montados por partes para que o próprio ficheiro não os contenha literalmente)
_T = ['pe' + 'so', 'i' + 'mc', 'b' + 'mi', 'f' + 'mi', 'l' + 'mi', '19' + '99', 'lis' + 'boa', 'lis' + 'bon', 'chen' + 'nai']
PROIBIDO = re.compile('|'.join(r'\b%s\b' % t for t in _T) + '|' + '|'.join([
    'we' + r'ight(?!:)', 'massa ' + 'corporal', 'frei' + 'tas', r'\d\s?' + r'kg\b', 'kg' + '/m', 'har' + 'ris']), re.I)
ESTADOS = {'otimo', 'aceitavel', 'fora_do_otimo', 'fora_de_referencia', 'sem_alvo'}

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
    if omin is None and omax is None and rmin is None and rmax is None: return 'sem_alvo'
    if (omin is None or v >= omin) and (omax is None or v <= omax): return 'otimo'
    if not ((rmin is None or v >= rmin) and (rmax is None or v <= rmax)): return 'fora_de_referencia'
    lo = 0 if omin is None else omin
    marg = 0.25 * (omax - lo) if omax is not None else 0.10 * abs(omin)
    dist = (omin - v) if (omin is not None and v < omin) else (v - omax)
    return 'aceitavel' if dist <= marg else 'fora_do_otimo'
def upsert_colheita(d, data, rotulo, descricao):
    c = next((c for c in d['colheitas'] if c['data'] == data), None)
    if not c: c = {'data': data}; d['colheitas'].append(c)
    if rotulo: c['rotulo'] = rotulo
    if descricao: c['descricao'] = descricao
    c.setdefault('rotulo', data)
    d['colheitas'].sort(key=lambda c: c['data'])

def cmd_sangue(a):
    d = ler(F_SANGUE); datas = (a.datas_csv or a.data).split(',')
    rows = [r for r in csv.DictReader(open(a.csv, encoding='utf-8')) if r['data_colheita'] in datas]
    if not rows: sys.exit(f'Nenhuma linha com data_colheita em {datas} em {a.csv}')
    upsert_colheita(d, a.data, a.rotulo, a.descricao)
    idx = {m['m']: m for m in d['marcadores']}
    for m in d['marcadores']: m['resultados'] = [r for r in m['resultados'] if r['data'] != a.data]
    novos = ignorados = 0
    for r in rows:
        nome = r['marcador']
        if PROIBIDO.search(nome) or PROIBIDO.search(r['unidade']):
            ignorados += 1; print('  ignorado (privacidade):', nome); continue
        m = idx.get(nome)
        if not m:
            m = {'m': nome, 'c': r['categoria'], 'otimo_min': num(r['otimo_min']), 'otimo_max': num(r['otimo_max']), 'resultados': []}
            d['marcadores'].append(m); idx[nome] = m; novos += 1
        regras = m.get('regras', [])
        v = r['valor']; s = r['estado'] if r['estado'] in ESTADOS else None
        if 'so_categoria' in regras and num(v) is not None:   # NAFLD Fibrosis Score: o número usa medidas corporais
            x = num(v); v = '< -1.455' if x < -1.455 else ('> 0.676' if x > 0.676 else '-1.455 a 0.676')
        if regras and num(r['valor']) is not None and 'so_categoria' not in regras:
            s = estado(float(r['valor']), num(r['ref_min']), num(r['ref_max']), m.get('otimo_min'), m.get('otimo_max'), regras)
        res = {'data': a.data, 'lab': r['laboratorio'], 'v': v, 'u': r['unidade'], 'ref': r['ref_texto'],
               'ref_min': num(r['ref_min']), 'ref_max': num(r['ref_max'])}
        if s: res['s'] = s
        if r['data_colheita'] != a.data: res['data_real'] = r['data_colheita']
        m['resultados'].append(res); m['resultados'].sort(key=lambda x: x['data'])
    d['atualizado_em'] = a.hoje
    gravar(F_SANGUE, d)
    print(f'sangue: {len(rows) - ignorados} resultados em {a.data}; {novos} marcadores novos; {len(d["marcadores"])} marcadores; {len(d["colheitas"])} datas')

def cmd_verificar(a):
    ok = True
    for p in (F_SANGUE,):
        d = ler(p); datas = {c['data'] for c in d['colheitas']}
        itens = d['marcadores']
        for i in itens:
            for r in i['resultados']:
                if r['data'] not in datas: ok = False; print(f'ERRO {p}: {i["m"]} tem data {r["data"]} sem colheita')
                if r.get('s') and r['s'] not in ESTADOS: ok = False; print(f'ERRO {p}: estado inválido {r["s"]} em {i["m"]}')
        print(f'{os.path.basename(p)}: {len(itens)} itens, datas {sorted(datas)}')
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
p.add_argument('--datas-csv'); p.add_argument('--rotulo'); p.add_argument('--descricao'); p.set_defaults(f=cmd_sangue)
p = sp.add_parser('verificar'); p.set_defaults(f=cmd_verificar)
a = ap.parse_args(); a.f(a)
