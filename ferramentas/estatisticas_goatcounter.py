#!/usr/bin/env python3
"""Atualiza data/estatisticas.json com as estatísticas do GoatCounter (conta imortalistas), para a página escondida de estatísticas.

Corre de 15 em 15 minutos no GitHub Actions (.github/workflows/goatcounter-stats.yml) com o token só de leitura no secret
GOATCOUNTER_TOKEN (variável de ambiente; nunca é escrito em lado nenhum). Só usa a biblioteca padrão do Python.

- API v0: /stats/total, /stats/hits (páginas e eventos), /stats/locations, /stats/browsers, /stats/systems, /stats/sizes, /stats/toprefs.
- Portugal vs outros países: o Worker manda, de cada hit, uma cópia origem/<pt|fora>/<caminho> (país do Cloudflare; sem IP nem UA). Ficam em
  "por_origem": {"pt": {...}, "fora": {...}} com total, dias, paginas, relatorios, aparelhos e paises (PT / os outros), e "origem_desde"
  (03-10-2026 23:00 PT; antes disso as visitas não têm origem e só contam no geral). Os totais gerais não mudam (origem/… é ignorado).
- Sem cortes: todos os caminhos (hits, paginação com exclude_paths até more=false) e listas completas de países / browsers / sistemas /
  tamanhos / origens (offset até more=false); páginas e aparelhos ficam todos no JSON, desde 01-10-2026 (sem janela de 366 dias).
- Sem IPs nem dados pessoais: só contagens agregadas, nomes de páginas, ficheiros de relatórios, países, browsers, sistemas,
  tamanhos de ecrã e nomes de sites de origem (sem caminhos nem parâmetros).
- Tolerante: conta sem dados = JSON com zeros (a API responde 404 a /stats/* enquanto o site não tem dados: conta como "sem dados"); erro na API ou token em falta = aviso e saída 0, sem tocar no JSON anterior;
  uma secção opcional que falhe fica com o valor anterior.
- Respeita o rate limit (4 pedidos/s): pausa entre pedidos e, num 429, espera o X-Rate-Limit-Reset.
- Só grava se os dados mudarem (o campo atualizado_em não conta), para o workflow só fazer commit quando há novidades.
- Contagens = todas as visitas e aberturas: a API só expõe "count" (visitantes), mas o Worker do site envia uma sessão aleatória nova
  (UUID) em cada pedido, por isso cada pedido conta como um novo visitante (= cada visita, abertura de PDF, aparelho e cópia de origem).
  O no_sessions:true sozinho não chegava (o GoatCounter conta cada caminho 1 vez por sessão de 8 h): até 04-10-2026 os aparelhos e as
  origens/* (sem IP nem user-agent = uma só sessão partilhada) ficavam presos a 1 por caminho, e visitas repetidas do mesmo IP+browser não contavam.
- Além dos totais, grava hoje / 7 dias / 30 dias (visitas e aberturas) e as aberturas de PDFs por dia (dias[].aberturas).
- Aparelhos: com cada visita o Worker envia o evento aparelho/<tipo>/<slug> (título = rótulo, ex. "iPhone XR / 11"; sem IP nem user-agent).
  Ficam em "aparelhos" (+ "aparelhos_desde", o 1.º dia com eventos) (contagem por rótulo; iPhone/iPad = estimativa pelo ecrã), não contam como visitas nem aberturas, e os países /
  browsers / sistemas / tamanhos / origens são pedidos só para as páginas e PDFs (include_paths), para os eventos de aparelho não os somarem.
- PDFs abertos vs descarregados: o Worker conta a abertura como o evento reports/<f>.pdf (formato de sempre) e o botão Descarregar
  (?dl=1) como download/<f>.pdf (desde DL_DESDE; antes, os downloads contavam como aberturas). Por relatório: abertos_pt/en,
  descarregados_pt/en, pt, en e total (pt/en/total = abertos + descarregados); totais pdf_abertos, pdf_descarregados, pdf_pt, pdf_en.

- Ao vivo: o Worker sf-site (cf_worker/src/stats.js, GET /s/<chave>) calcula o MESMO JSON na hora (mesma lógica; testes de paridade); o painel lê
  primeiro o Worker e este ficheiro/workflow fica como reserva. Qualquer mudança aqui tem de ir também para o stats.js do Worker.

Uso: GOATCOUNTER_TOKEN=... python3 ferramentas/estatisticas_goatcounter.py [--saida data/estatisticas.json] [--hoje AAAA-MM-DD]
"""
import argparse, datetime as dt, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request

API = os.environ.get('GOATCOUNTER_API', 'https://imortalistas.goatcounter.com/api/v0')  # GOATCOUNTER_API só para testes locais
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INICIO = dt.datetime(2026, 10, 1, tzinfo=dt.timezone.utc)  # a contagem começou em outubro de 2026
RE_PDF = re.compile(r'^/?(reports/[A-Za-z0-9._-]+\.pdf)$')      # abertura (formato de sempre)
RE_DL = re.compile(r'^/?download/([A-Za-z0-9._-]+\.pdf)$')      # download (botão Descarregar, ?dl=1 no Worker)
RE_AP = re.compile(r'^/?aparelho/(iphone|ipad|android|android-tablet|computador|outro)/([a-z0-9-]{1,60})$')  # evento do aparelho (Worker)
RE_OR = re.compile(r'^/?origem/(pt|fora)/(.{1,1000})$')  # cópia do Worker com o grupo de origem (Portugal / outros países)
ORIGEM_DESDE = '2026-10-03T22:00:00Z'  # 03-10-2026 23:00 (PT): a partir daqui as visitas têm origem
DL_DESDE = '2026-10-03'  # a partir deste dia os downloads contam à parte; antes contavam como aberturas
VAZIO = {'versao': 1, 'atualizado_em': None, 'desde': None, 'descarregados_desde': DL_DESDE,
         'total': {'visitas': 0, 'visitas_30d': 0, 'visitas_90d': 0, 'aberturas_pdf': 0,
                   'visitas_hoje': 0, 'visitas_7d': 0, 'aberturas_hoje': 0, 'aberturas_7d': 0, 'aberturas_30d': 0,
                   'pdf_abertos': 0, 'pdf_descarregados': 0, 'pdf_pt': 0, 'pdf_en': 0},
         'dias': [], 'paginas': [], 'relatorios': [], 'aparelhos': [], 'paises': [], 'browsers': [], 'sistemas': [], 'tamanhos': [], 'origens': []}

def aviso(msg):
    print(f'::warning::{msg}' if os.environ.get('GITHUB_ACTIONS') else f'AVISO: {msg}')

class ErroAPI(Exception):
    def __init__(self, msg, codigo=None): super().__init__(msg); self.codigo = codigo
class SemDados(Exception): pass  # 404 em /stats/*: o site ainda não tem dados (não é erro)

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
            if e.code == 404: raise SemDados(caminho)
            raise ErroAPI(f'{caminho}: HTTP {e.code}', e.code)
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

def lista_stats(token, pagina, ini, fim, origem=False, incluir=None):
    """Lista completa (sem corte): 100 de cada vez, com offset, até a API dizer more=false."""
    todos, off = [], 0
    while True:
        d = pedido(f'/stats/{pagina}', token, start=ini, end=fim, limit=100, offset=off or None, include_paths=','.join(map(str, incluir)) if incluir else None)
        st = d.get('stats') or []
        todos += st; off += len(st)
        if not d.get('more') or not st: break
    return [{'id': nome_limpo(s.get('id'))[:40], 'nome': nome_limpo(s.get('name') or ('' if origem else s.get('id')), origem), 'visitas': inteiro(s.get('count'))}
            for s in todos if inteiro(s.get('count')) > 0]

def periodo(agora=None):
    """(início, fins): início = 01-10-2026 (início da contagem: tudo o que já passou, sem janela); fins = [hora atual arredondada para baixo + 1 h (nunca mais
    de 1 h no futuro), hora atual arredondada para baixo] — o segundo só é usado se a API rejeitar o primeiro."""
    base = (agora or dt.datetime.now(dt.timezone.utc)).replace(minute=0, second=0, microsecond=0)
    ini_dt = INICIO
    f = lambda x: x.strftime('%Y-%m-%dT%H:%M:%SZ')
    return ini_dt, f(ini_dt), [f(base + dt.timedelta(hours=1)), f(base)]

def recolher(token, hoje):
    ini_dt, ini, fins = periodo()
    for n, fim in enumerate(fins):
        try: return _recolher(token, hoje, ini_dt, ini, fim)
        except (ErroAPI, SemDados) as e:
            # fim no futuro rejeitado (400/422) ou 404: repetir uma vez com a hora atual arredondada para baixo
            if n == 0 and (isinstance(e, SemDados) or e.codigo in (400, 422)): continue
            if isinstance(e, SemDados): return _vazio(hoje, ini_dt), ini, fim
            raise

def _vazio(hoje, ini_dt):
    out = json.loads(json.dumps(VAZIO)); out['desde'] = ini_dt.date().isoformat()
    out['dias'] = [{'dia': d, 'visitas': 0, 'aberturas': 0} for d in ((hoje - dt.timedelta(days=i)).isoformat() for i in range(89, -1, -1)) if d >= INICIO.date().isoformat()]
    return out

def _recolher(token, hoje, ini_dt, ini, fim):
    # todos os caminhos (páginas e eventos), 100 de cada vez, até more=false (sem limite de páginas)
    hits, vistos, k = [], [], -1
    while True:
        k += 1
        try: d = pedido('/stats/hits', token, start=ini, end=fim, limit=100, exclude_paths=','.join(map(str, vistos)) or None)
        except SemDados:
            if k == 0: raise  # site sem dados
            break  # página seguinte sem dados: fica o que já veio
        ja = set(vistos); novos = [h for h in (d.get('hits') or []) if h.get('path_id') is None or h.get('path_id') not in ja]
        ids = [h.get('path_id') for h in novos if h.get('path_id') is not None]
        hits += novos; vistos += ids
        if not d.get('more') or not ids: break  # fim, ou sem caminhos novos (evita ciclo infinito)
    try: tot = pedido('/stats/total', token, start=ini, end=fim)
    except SemDados: tot = {}
    # relatórios: ficheiro → id (data/reports.json do próprio repositório)
    fich = {}
    try:
        for r in json.load(open(os.path.join(RAIZ, 'data', 'reports.json'), encoding='utf-8')).get('relatorios', []):
            if r.get('ficheiro'): fich[r['ficheiro']] = (r.get('id'), 'pt')
            if r.get('ficheiro_en'): fich[r['ficheiro_en']] = (r.get('id'), 'en')
    except (OSError, ValueError): pass
    extra = any(RE_AP.match(str(h.get('path') or '')) or RE_OR.match(str(h.get('path') or '')) for h in hits if h.get('event'))
    incluir = [h.get('path_id') for h in hits if h.get('path_id') is not None and not (h.get('event') and (RE_AP.match(str(h.get('path') or '')) or RE_OR.match(str(h.get('path') or ''))))]
    out = json.loads(json.dumps(VAZIO))
    out['desde'] = ini_dt.date().isoformat()
    out.update(agregar([h for h in hits if not (h.get('event') and RE_OR.match(str(h.get('path') or '')))], fich, hoje))
    # Portugal vs outros países: as cópias origem/<pt|fora>/<caminho> do Worker, com o caminho original
    grupos, or_dias = {'pt': [], 'fora': []}, set()
    for h in hits:
        mo = RE_OR.match(str(h.get('path') or '')) if h.get('event') else None
        if not mo: continue
        resto = mo.group(2); pag = resto.startswith('imortalistas/')
        grupos[mo.group(1)].append(dict(h, path=('/' + resto) if pag else resto, event=not pag))
        for x in h.get('stats') or []:
            dia = str(x.get('day') or '')[:10]
            if re.match(r'^\d{4}-\d{2}-\d{2}$', dia) and inteiro(x.get('daily')) > 0: or_dias.add(dia)
    if grupos['pt'] or grupos['fora']:
        out['por_origem'] = {g: agregar(grupos[g], fich, hoje) for g in ('pt', 'fora')}
        out['origem_desde'] = ORIGEM_DESDE
    if inteiro(tot.get('total')) and not out['total']['visitas'] and not out['total']['aberturas_pdf']:
        out['total']['visitas'] = max(0, inteiro(tot.get('total')) - inteiro(tot.get('total_events')))
    out['_incluir'] = incluir if extra and incluir else None  # só se houver eventos de aparelho/origem (sem IP nem UA)
    return out, ini, fim

def agregar(hits, fich, hoje):
    """Páginas, relatórios (abertos/descarregados, PT/EN), aparelhos, série diária e totais de uma lista de hits."""
    paginas, rel, por_dia, pdf_dia, aps, ap_dias = {}, {}, {}, {}, {}, set()
    for h in hits:
        path, n = str(h.get('path') or ''), inteiro(h.get('count'))
        ma = RE_AP.match(path) if h.get('event') else None
        if ma:
            k = ma.group(1) + '/' + ma.group(2)
            nome = nome_limpo(h.get('title') or ma.group(2))[:60]
            a = aps.setdefault(k, {'id': k, 'tipo': ma.group(1), 'nome': nome, 'estimativa': ma.group(1) in ('iphone', 'ipad') and nome not in ('iPhone', 'iPad'), 'visitas': 0})
            a['visitas'] += n
            for s in h.get('stats') or []:
                dia = str(s.get('day') or '')[:10]
                if re.match(r'^\d{4}-\d{2}-\d{2}$', dia) and inteiro(s.get('daily')) > 0: ap_dias.add(dia)
            continue
        if h.get('event'):
            m, tipo = RE_PDF.match(path), 'abertos'
            if m: f = m.group(1)
            else:
                m, tipo = RE_DL.match(path), 'descarregados'
                if not m: continue
                f = 'reports/' + m.group(1)
            rid, lng = fich.get(f, (None, 'en' if f.endswith('_en.pdf') else 'pt'))
            chave = rid or f
            e = rel.setdefault(chave, {'id': rid, 'ficheiro': None if rid else f, 'pt': 0, 'en': 0, 'total': 0,
                                       'abertos_pt': 0, 'abertos_en': 0, 'descarregados_pt': 0, 'descarregados_en': 0})
            e[lng] += n; e['total'] += n; e[f'{tipo}_{lng}'] += n
            for s in h.get('stats') or []:
                dia = str(s.get('day') or '')[:10]
                if re.match(r'^\d{4}-\d{2}-\d{2}$', dia): pdf_dia[dia] = pdf_dia.get(dia, 0) + inteiro(s.get('daily'))
        else:
            p = nome_limpo(path.split('?')[0].split('#')[0])
            paginas[p] = paginas.get(p, 0) + n
            for s in h.get('stats') or []:
                dia = str(s.get('day') or '')[:10]
                if re.match(r'^\d{4}-\d{2}-\d{2}$', dia): por_dia[dia] = por_dia.get(dia, 0) + inteiro(s.get('daily'))
    dias = [(hoje - dt.timedelta(days=i)).isoformat() for i in range(89, -1, -1)]
    serie = [{'dia': d, 'visitas': por_dia.get(d, 0), 'aberturas': pdf_dia.get(d, 0)} for d in dias if d >= INICIO.date().isoformat()]
    out = {'dias': serie}
    out['paginas'] = sorted(({'path': p, 'visitas': n} for p, n in paginas.items() if n > 0), key=lambda x: (-x['visitas'], x['path']))  # todas
    out['relatorios'] = sorted((v for v in rel.values() if v['total'] > 0), key=lambda x: (-x['total'], x['id'] or x['ficheiro']))
    out['aparelhos'] = sorted((v for v in aps.values() if v['visitas'] > 0), key=lambda x: (-x['visitas'], x['nome']))  # todos
    if out['aparelhos'] and ap_dias: out['aparelhos_desde'] = min(ap_dias)  # 1.º dia com eventos de aparelho
    out['total'] = {'visitas': sum(paginas.values()), 'visitas_30d': sum(x['visitas'] for x in serie[-30:]),
                    'visitas_90d': sum(x['visitas'] for x in serie), 'aberturas_pdf': sum(v['total'] for v in rel.values()),
                    'visitas_hoje': sum(x['visitas'] for x in serie[-1:]), 'visitas_7d': sum(x['visitas'] for x in serie[-7:]),
                    'aberturas_hoje': sum(x['aberturas'] for x in serie[-1:]), 'aberturas_7d': sum(x['aberturas'] for x in serie[-7:]),
                    'aberturas_30d': sum(x['aberturas'] for x in serie[-30:]),
                    'pdf_abertos': sum(v['abertos_pt'] + v['abertos_en'] for v in rel.values()), 'pdf_descarregados': sum(v['descarregados_pt'] + v['descarregados_en'] for v in rel.values()),
                    'pdf_pt': sum(v['pt'] for v in rel.values()), 'pdf_en': sum(v['en'] for v in rel.values())}
    return out

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
    incluir = novo.pop('_incluir', None)
    for chave, pagina, origem in (('paises', 'locations', False), ('browsers', 'browsers', False), ('sistemas', 'systems', False), ('tamanhos', 'sizes', False), ('origens', 'toprefs', True)):
        try: novo[chave] = lista_stats(token, pagina, ini, fim, origem, incluir)
        except SemDados: novo[chave] = []
        except ErroAPI as e:
            aviso(f'{pagina}: {e}; fica o valor anterior.'); novo[chave] = anterior.get(chave) if isinstance(anterior.get(chave), list) else []
    if isinstance(novo.get('por_origem'), dict):  # países: Portugal / todos os outros (da lista de países do GoatCounter)
        novo['por_origem']['pt']['paises'] = [p for p in novo.get('paises', []) if str(p.get('id', '')).upper() == 'PT']
        novo['por_origem']['fora']['paises'] = [p for p in novo.get('paises', []) if str(p.get('id', '')).upper() != 'PT']
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
