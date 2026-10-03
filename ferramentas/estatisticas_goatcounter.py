#!/usr/bin/env python3
"""Atualiza data/estatisticas.json com as estatísticas do GoatCounter (conta imortalistas), para a página escondida de estatísticas.

Corre de hora a hora no GitHub Actions (.github/workflows/goatcounter-stats.yml) com o token só de leitura no secret
GOATCOUNTER_TOKEN (variável de ambiente; nunca é escrito em lado nenhum). Só usa a biblioteca padrão do Python.

- API v0: /stats/total, /stats/hits (páginas e eventos), /stats/locations, /stats/browsers, /stats/systems, /stats/sizes, /stats/toprefs.
- Sem IPs nem dados pessoais: só contagens agregadas, nomes de páginas, ficheiros de relatórios, países, browsers, sistemas,
  tamanhos de ecrã e nomes de sites de origem (sem caminhos nem parâmetros).
- Tolerante: conta sem dados = JSON com zeros; erro na API ou token em falta = aviso e saída 0, sem tocar no JSON anterior;
  uma secção opcional que falhe fica com o valor anterior.
- Respeita o rate limit (4 pedidos/s): pausa entre pedidos e, num 429, espera o X-Rate-Limit-Reset.
- Só grava se os dados mudarem (o campo atualizado_em não conta), para o workflow só fazer commit quando há novidades.

Uso: GOATCOUNTER_TOKEN=... python3 ferramentas/estatisticas_goatcounter.py [--saida data/estatisticas.json] [--hoje AAAA-MM-DD]
"""
import argparse, datetime as dt, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request

API = os.environ.get('GOATCOUNTER_API', 'https://imortalistas.goatcounter.com/api/v0')  # GOATCOUNTER_API só para testes locais
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INICIO = dt.datetime(2026, 10, 1, tzinfo=dt.timezone.utc)  # a contagem começou em outubro de 2026
RE_PDF = re.compile(r'^/?(reports/[A-Za-z0-9._-]+\.pdf)$')
VAZIO = {'versao': 1, 'atualizado_em': None, 'desde': None,
         'total': {'visitas': 0, 'visitas_30d': 0, 'visitas_90d': 0, 'aberturas_pdf': 0},
         'dias': [], 'paginas': [], 'relatorios': [], 'paises': [], 'browsers': [], 'sistemas': [], 'tamanhos': [], 'origens': []}

def aviso(msg):
    print(f'::warning::{msg}' if os.environ.get('GITHUB_ACTIONS') else f'AVISO: {msg}')

class ErroAPI(Exception): pass

_ultimo = [0.0]
def pedido(caminho, token, **q):
    """GET à API com pausas (rate limit) e até 3 novas tentativas em 429/5xx/erros de rede."""
    url = API + caminho + ('?' + urllib.parse.urlencode({k: v for k, v in q.items() if v is not None}) if q else '')
    for tent in range(4):
        espera = 0.3 - (time.monotonic() - _ultimo[0])
        if espera > 0: time.sleep(espera)
        _ultimo[0] = time.monotonic()
        req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json', 'Accept': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                if r.headers.get('X-Rate-Limit-Remaining') == '0':
                    time.sleep(min(10.0, float(r.headers.get('X-Rate-Limit-Reset') or 1)))
                return json.loads(r.read().decode('utf-8') or '{}')
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500:
                try: pausa = float(e.headers.get('X-Rate-Limit-Reset') or 0)
                except ValueError: pausa = 0
                time.sleep(min(10.0, max(pausa, 1.5 * (tent + 1)))); continue
            raise ErroAPI(f'{caminho}: HTTP {e.code}')
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
            time.sleep(1.5 * (tent + 1)); continue
    raise ErroAPI(f'{caminho}: sem resposta válida depois de 4 tentativas')

def nome_limpo(s, origem=False):
    s = re.sub(r'[\x00-\x1f\x7f]', '', str(s or '')).strip()
    if origem:  # só o nome do site de origem: sem esquema, caminho, parâmetros nem e-mails
        s = re.sub(r'^[a-z][a-z0-9+.-]*://', '', s, flags=re.I).split('/')[0].split('?')[0].split('#')[0]
        if '@' in s: s = '(oculto)'
    return s[:100] or '(desconhecido)'

def inteiro(x):
    try: return max(0, int(x))
    except (TypeError, ValueError): return 0

def lista_stats(token, pagina, ini, fim, origem=False):
    d = pedido(f'/stats/{pagina}', token, start=ini, end=fim, limit=20)
    return [{'id': nome_limpo(s.get('id'))[:40], 'nome': nome_limpo(s.get('name'), origem), 'visitas': inteiro(s.get('count'))}
            for s in (d.get('stats') or []) if inteiro(s.get('count')) > 0]

def recolher(token, hoje):
    agora = dt.datetime.now(dt.timezone.utc).replace(minute=0, second=0, microsecond=0) + dt.timedelta(hours=1)
    ini_dt = max(INICIO, agora - dt.timedelta(days=366))
    ini, fim = ini_dt.strftime('%Y-%m-%dT%H:%M:%SZ'), agora.strftime('%Y-%m-%dT%H:%M:%SZ')
    # todos os caminhos (páginas e eventos), 100 de cada vez
    hits, vistos = [], []
    for _ in range(20):
        d = pedido('/stats/hits', token, start=ini, end=fim, limit=100, exclude_paths=','.join(map(str, vistos)) or None)
        novos = d.get('hits') or []
        hits += novos; vistos += [h.get('path_id') for h in novos if h.get('path_id') is not None]
        if not d.get('more') or not novos: break
    tot = pedido('/stats/total', token, start=ini, end=fim)
    # relatórios: ficheiro → id (data/reports.json do próprio repositório)
    fich = {}
    try:
        for r in json.load(open(os.path.join(RAIZ, 'data', 'reports.json'), encoding='utf-8')).get('relatorios', []):
            if r.get('ficheiro'): fich[r['ficheiro']] = (r.get('id'), 'pt')
            if r.get('ficheiro_en'): fich[r['ficheiro_en']] = (r.get('id'), 'en')
    except (OSError, ValueError): pass
    paginas, rel, por_dia = {}, {}, {}
    for h in hits:
        path, n = str(h.get('path') or ''), inteiro(h.get('count'))
        if h.get('event'):
            m = RE_PDF.match(path)
            if not m: continue
            f = m.group(1); rid, lng = fich.get(f, (None, 'en' if f.endswith('_en.pdf') else 'pt'))
            chave = rid or f
            e = rel.setdefault(chave, {'id': rid, 'ficheiro': None if rid else f, 'pt': 0, 'en': 0, 'total': 0})
            e[lng] += n; e['total'] += n
        else:
            p = nome_limpo(path.split('?')[0].split('#')[0])
            paginas[p] = paginas.get(p, 0) + n
            for s in h.get('stats') or []:
                dia = str(s.get('day') or '')[:10]
                if re.match(r'^\d{4}-\d{2}-\d{2}$', dia): por_dia[dia] = por_dia.get(dia, 0) + inteiro(s.get('daily'))
    dias = [(hoje - dt.timedelta(days=i)).isoformat() for i in range(89, -1, -1)]
    serie = [{'dia': d, 'visitas': por_dia.get(d, 0)} for d in dias if d >= INICIO.date().isoformat()]
    out = json.loads(json.dumps(VAZIO))
    out['desde'] = ini_dt.date().isoformat()
    out['dias'] = serie
    out['paginas'] = sorted(({'path': p, 'visitas': n} for p, n in paginas.items() if n > 0), key=lambda x: (-x['visitas'], x['path']))[:50]
    out['relatorios'] = sorted((v for v in rel.values() if v['total'] > 0), key=lambda x: (-x['total'], x['id'] or x['ficheiro']))
    out['total'] = {'visitas': sum(paginas.values()), 'visitas_30d': sum(x['visitas'] for x in serie[-30:]),
                    'visitas_90d': sum(x['visitas'] for x in serie), 'aberturas_pdf': sum(v['total'] for v in rel.values())}
    if inteiro(tot.get('total')) and not out['total']['visitas'] and not out['total']['aberturas_pdf']:
        out['total']['visitas'] = max(0, inteiro(tot.get('total')) - inteiro(tot.get('total_events')))
    return out, ini, fim

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--saida', default=os.path.join(RAIZ, 'data', 'estatisticas.json'))
    ap.add_argument('--hoje', default=None, help='data de hoje (UTC) para a série diária; por omissão, hoje')
    a = ap.parse_args()
    hoje = dt.date.fromisoformat(a.hoje) if a.hoje else dt.datetime.now(dt.timezone.utc).date()
    token = os.environ.get('GOATCOUNTER_TOKEN', '').strip()
    if not token:
        aviso('GOATCOUNTER_TOKEN em falta: data/estatisticas.json fica como estava.'); return 0
    try:
        anterior = json.load(open(a.saida, encoding='utf-8'))
        if not isinstance(anterior, dict): raise ValueError
    except (OSError, ValueError):
        anterior = json.loads(json.dumps(VAZIO))
    try:
        novo, ini, fim = recolher(token, hoje)
    except ErroAPI as e:
        aviso(f'API do GoatCounter: {e}. data/estatisticas.json fica como estava.'); return 0
    for chave, pagina, origem in (('paises', 'locations', False), ('browsers', 'browsers', False), ('sistemas', 'systems', False), ('tamanhos', 'sizes', False), ('origens', 'toprefs', True)):
        try: novo[chave] = lista_stats(token, pagina, ini, fim, origem)
        except ErroAPI as e:
            aviso(f'{pagina}: {e}; fica o valor anterior.'); novo[chave] = anterior.get(chave) if isinstance(anterior.get(chave), list) else []
    sem = lambda d: {k: v for k, v in d.items() if k != 'atualizado_em'}
    if sem(novo) == sem(anterior) and anterior.get('atualizado_em'):
        print('Sem mudanças nas estatísticas.'); return 0
    novo['atualizado_em'] = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).strftime('%Y-%m-%dT%H:%M:%SZ')
    tmp = a.saida + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f: json.dump(novo, f, ensure_ascii=False, indent=1); f.write('\n')
    os.replace(tmp, a.saida)
    print(f"Estatísticas atualizadas: {novo['total']['visitas']} visitas, {novo['total']['aberturas_pdf']} aberturas de PDFs, {len(novo['relatorios'])} relatórios.")
    return 0

if __name__ == '__main__':
    try: sys.exit(main())
    except Exception as e:  # nunca falhar de forma ruidosa nem apagar o JSON anterior
        aviso(f'erro inesperado ({type(e).__name__}); data/estatisticas.json fica como estava.'); sys.exit(0)
