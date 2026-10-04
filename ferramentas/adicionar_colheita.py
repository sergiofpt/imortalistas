#!/usr/bin/env python3
r"""Acrescenta uma nova data (colheita) de análises a data/sangue.json.

Uso (a partir da raiz do repositório):
  python3 ferramentas/adicionar_colheita.py sangue --csv historico.csv --data 2026-12-03 \
      --rotulo "dez 2026" --descricao "03-12-2026" [--rotulo-en "Dec 2026" --descricao-en "03-12-2026"]
      [--nota "..." --nota-en "..."] [--datas-csv 2026-12-03,2026-12-05]
  python3 ferramentas/adicionar_colheita.py verificar
  python3 ferramentas/adicionar_colheita.py relatorio --pdf novo.pdf --id meu-relatorio --data 2026-12-03 \
      --titulo-pt "Título" --titulo-en "Title" --resumo-pt "Uma linha genérica" --resumo-en "One generic line" \
      --areas cerebro[,longevidade] [--palavras "sono,sleep"] [--genes "CLOCK,PER2"] [--publicado 2026-12-03]
      [--descricao-pt "..." --descricao-en "..."] [--paginas 12] [--lingua-pt português --lingua-en Portuguese] [--nome nome-no-site.pdf]
      (verifica a privacidade do PDF com pdftotext, copia-o para reports/ e junta a entrada em data/reports.json;
       resumo = uma linha, até 120 caracteres, sem resultados pessoais; areas = ids da lista "areas" de reports.json (1 ou 2);
       publicado = data de publicação, por omissão hoje (dá a etiqueta Novo nos 14 dias seguintes); palavras e genes só para a pesquisa)
  python3 ferramentas/adicionar_colheita.py relatorio-en --pdf report_EN.pdf --id meu-relatorio [--paginas 12]
      (versão inglesa: verifica, copia para reports/<nome>_en.pdf e grava ficheiro_en/paginas_en/tamanho_kb_en)

É idempotente: voltar a correr com a mesma data substitui os resultados dessa data.
Não grava o nome do laboratório (a página mostra só datas).
Marcadores de intolerância alimentar (IgG/IgE específicas para alimentos) vão automaticamente para a lista
"intolerancias" (secção própria da página) e são classificados 'intolerante' / 'nao_intolerante' pelo limite do
laboratório (ver classifica_intolerancia); os restantes vão para "marcadores".
"""
import argparse, csv, json, os, re, sys
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F_SANGUE = os.path.join(RAIZ, 'data', 'sangue.json')
# páginas de genética (JSON editados à mão; ver README): Genética Má e Genética Boa
F_GENETICA = {'genetica.html': os.path.join(RAIZ, 'data', 'genetica.json'), 'genetica-boa.html': os.path.join(RAIZ, 'data', 'genetica_boa.json')}
# protocolo genético consolidado (mostrado no topo das duas páginas de genética)
F_PROTOCOLO = os.path.join(RAIZ, 'data', 'genetica_protocolo.json')
# página Genética Reports: lista de relatórios em PDF (data/reports.json; PDFs em reports/)
F_REPORTS = os.path.join(RAIZ, 'data', 'reports.json')
D_REPORTS = os.path.join(RAIZ, 'reports')
# privacidade: nunca publicar a medida da balança nem nada que a permita deduzir
# (os termos são montados por partes para que o próprio ficheiro não os contenha literalmente)
_T = ['ger' + 'mano', 'sou' + 'sa', 'cu' + 'f', 'coim' + 'bra', 'pe' + 'so', 'i' + 'mc', 'b' + 'mi', 'f' + 'mi', 'l' + 'mi', '19' + '99', 'lis' + 'boa', 'lis' + 'bon', 'chen' + 'nai']
PROIBIDO = re.compile('|'.join(r'\b%s\b' % t for t in _T) + '|' + '|'.join([
    r'(?<![a-z])' + 'we' + r'ight(?!:|ed\b|ing\b| loss)', 'massa ' + 'corporal', 'frei' + 'tas', r'\d\s?' + r'kg\b', 'kg' + '/m', 'har' + 'ris',
    # nomes de laboratórios/fornecedores: a página mostra só datas
    'ai' + 'wo', 'thyro' + 'care', 'lipo' + 'mic', 'food' + 'print', 'self' + 'decode', 'omics' + 'edge']), re.I)
# nos PDFs também não pode aparecer o país nem a ascendência regional (texto extraído com pdftotext)
PDF_EXTRA = re.compile(r'\bportugal\b|ib[ée]ric|s[ée]rgio(?!\s+f\b)', re.I)
# nos PDFs (PT e EN) também não pode aparecer ascendência/população, nacionalidade de coortes nem dados pessoais (nascimento, idade, família;
# o ano, a cidade e o apelido já estão em PROIBIDO);
# antes da procura retiram-se as expressões permitidas de PDF_PERMITIDO (nomes de plantas, dietas, doenças, bases de dados, sociedades)
PDF_PERMITIDO = re.compile('|'.join([
    r'dieta[s]? mediterr[âa]nic[ao]s?|padr[ãa]o mediterr[âa]nico|ensaio mediterr[âa]nico|febre mediterr[âa]nica familiar|mediterranean[- ](?:diet|style|pattern|eating)\w*|(?:familial )?mediterranean fever',
    r'medicina tradicional chinesa|traditional chinese medicine|couve-chinesa|chinese (?:cabbage|kale|angelic\w*|mantle|pestiler)|angélica chinesa|escutelária chinesa|pilriteiro chinês|chinesas?/kampo|chinese/kampo',
    r'ginseng (?:vermelho )?(?:coreano|asiático)|korean red ginseng|asian ginseng|(?:plantas )?das américas e de áfrica|americas and africas?|pygeum africano|manga-africana|african mango|batata-africana',
    r'multi-?(?:[ée]tnic|ethnic)\w*', r'consenso EAS', r'UK Biobank|FinnGen|GWAS Catalog|PGS Catalog|gnomAD',
    r'\bHar' + r'rison(?=\s+(?:S\b|et al|20\d\d))',  # autor citado na bibliografia ("… S et al. (2021)", "… 2021"; Referência da Via: Força), não o termo proibido
]), re.I)
PDF_POP = re.compile('|'.join([
    r'\beurop(?:eu|eia|eus|eias|e|ean|eans)\b', r'\bafrican[oa]s?\b|\bafricans?\b|\b[áa]frica\b', r'\basi[áa]tic[oa]s?\b|\b[áa]sia\b|\basians?\b', r'ashkenaz|asquenaz',
    r'\bjud(?:eu|eus|ia|ias|aic[oa]s?)\b|\bjewish\b', r'\bn[óo]rdic[oa]s?\b', r'\bfinland[eê]s\w*|\bfinlandesa|\bfinn(?:ish|s)\b', r'\bjapon[eê]s\w*|\bjaponesa|\bjapanese\b',
    r'\bchines[ae]s?\b|\bchin[eê]s\b|\bchinese\b', r'\bcorean[oa]s?\b|\bkoreans?\b', r'\bitalian[oa]s\b|\bitalians\b', r'\bdinamarqu[eê]s\w*|\bdinamarquesa|\bdan(?:ish|es)\b',
    r'\bbrit[âa]nic[oa]s?\b|\bbritish\b', r'\bisland[eê]s\w*|\bicelandic\b', r'\bsardos\b|sardenh|\bsardinian', r'\bhisp[âa]nic\w*|\bhispanics?\b', r'latino-?american\w*|latin american',
    r'afro-?american\w*', r'\bcaucasian\w*', r'\bascend[eê]ncia|\bancestralidade|\bancestr(?:y|al|ies)\b', r'\betnia\b|\b[eé]tnic[oa]s?\b|\bethnic\w*', r'\bmediterr[âa]ne\w*|\bmediterranean\b',
    r'1000\s?genomes|\b1000G\b|\b1K(?:G)\b', r'(?-i:\b(?:EUR|CEU|NFE|AFR)\b)', r'\bportugu[eê]s\w*|\bportuguesa|\bportuguese\b',
    r'reino unido|united kingdom|estados unidos|united states|áfrica do sul|south africa',
]), re.I)
PDF_PESSOAL = re.compile('|'.join([
    r'\b05-06|06-05-|06/05/', r'\bnascid[oa]\b|\bnasceu\b|\bborn\b(?! (?:from|in the))', r'\b27\s*(?:anos|years?\b|-year)|\baged?\s+27\b',
    r'\bgrand(?:father|mother|parents?)\b|\bav[ôó]s?\b', r'\b(?:his|my|sérgio\'s|o seu|a sua) (?:father|mother|brother|sister|uncle|aunt|cousin|pai|mãe|irmão|irmã|tio|tia|primo|prima)\b',
    r'https?://|www\.|\.(?:com|org|gov|net)\b|/home/|/workspace|(?<![a-z])file:|fontes/|dados/|scripts/|\b[a-z0-9_]+\.(?:py|tsv|csv|vcf|json)\b|ficheiro privado|private source file',
]), re.I)
# idade e ano/data de nascimento nunca podem aparecer em nenhum ficheiro publicado (HTML, JSON, README, ferramentas, PDFs; pedido do Sérgio F, 03-10-2026).
# IDADE procura nos textos (e no texto dos PDFs); ANO_BYTES procura a sequência do ano (e o utilizador antigo do GitHub) nos bytes de todos os ficheiros,
# incluindo os PDFs; as sequências são montadas por partes para que este ficheiro não as contenha
ANO_BYTES = [b'19' + b'99', b'sergiofrei' + b'tas']
IDADE = re.compile('|'.join([
    r'\b27\s*(?:anos|years?\b|-year)|\baged?\s+27\b', r's[ée]rgio f[^<\n]{0,5}(?:<[^>]*>\s*)*\d{1,3}\s*(?:anos|years?)\b',
    r'\b\d{1,3}\s*(?:anos de idade|years? old\b|-years?-old\b)', r'\b(?:idade|age)\s*[:=]\s*\d', r'\b(?:data|ano) de nascimento\s*[:=]|\b(?:date|year) of birth\s*[:=]|\bbirth ?date\s*[:=]|\bd\.?o\.?b\.?\s*[:=]',
    r'\bnascid[oa] (?:em|a) \d|\bborn (?:in|on) \d', r'(?<![\d:])19' + r'99(?!\d)']), re.I)
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

TAGS_OK = re.compile(r'</?(b|i|em|strong|br|small|sub|sup)\s*/?>', re.I)
def verificar_genetica():
    ok = True
    for pag, f in F_GENETICA.items():
        if not os.path.exists(os.path.join(RAIZ, pag)): ok = False; print(f'ERRO: falta {pag}')
        if not os.path.exists(f): ok = False; print(f'ERRO: falta data/{os.path.basename(f)} ({pag} fica vazia)'); continue
        ok = verificar_genetica_json(f) and ok
    if not os.path.exists(F_PROTOCOLO): ok = False; print('ERRO: falta data/genetica_protocolo.json (o Protocolo genético fica vazio)')
    else: ok = verificar_protocolo_json(F_PROTOCOLO) and ok
    if not os.path.exists(os.path.join(RAIZ, 'genetica-reports.html')): ok = False; print('ERRO: falta genetica-reports.html')
    if not os.path.exists(F_REPORTS): ok = False; print('ERRO: falta data/reports.json (a Genética Reports fica vazia)')
    else: ok = verificar_reports_json(F_REPORTS) and ok
    return ok

def privacidade_pdf(caminho):
    """Extrai o texto do PDF com pdftotext e devolve a lista de termos proibidos encontrados (None se não houver pdftotext)."""
    import shutil, subprocess
    if not shutil.which('pdftotext'): return None
    t = subprocess.run(['pdftotext', '-q', caminho, '-'], capture_output=True, text=True).stdout
    t2 = PDF_PERMITIDO.sub(' ', re.sub(r'\s+', ' ', t))
    achados = [m.group(0) for rx in (PROIBIDO, PDF_EXTRA, PDF_POP, PDF_PESSOAL, IDADE) for m in rx.finditer(t2)]
    raw = open(caminho, 'rb').read(); achados += [f'bytes {b.decode()[:2]}…' for b in ANO_BYTES if b in raw]
    if shutil.which('pdfinfo'):
        info = subprocess.run(['pdfinfo', caminho], capture_output=True, text=True).stdout
        achados += [f'metadado {k}' for k in ('Title', 'Author', 'Subject', 'Keywords') if re.search(rf'^{k}:\s*\S', info, re.M)]
    return achados

# página escondida de estatísticas: data/estatisticas.json (placeholder vazio ou gerado por ferramentas/estatisticas_goatcounter.py)
F_ESTAT = os.path.join(RAIZ, 'data', 'estatisticas.json')
def verificar_estatisticas():
    if not os.path.exists(F_ESTAT): print('ERRO data/estatisticas.json em falta'); return False
    try: d = json.load(open(F_ESTAT, encoding='utf-8'))
    except ValueError as e: print(f'ERRO data/estatisticas.json: JSON inválido ({e})'); return False
    chaves = {'versao', 'atualizado_em', 'desde', 'total', 'dias', 'paginas', 'relatorios', 'paises', 'browsers', 'sistemas', 'tamanhos', 'origens'}
    ok = isinstance(d, dict) and set(d) == chaves and isinstance(d.get('total'), dict) and all(isinstance(d[k], list) for k in chaves - {'versao', 'atualizado_em', 'desde', 'total'})
    if not ok: print('ERRO data/estatisticas.json: estrutura inesperada'); return False
    print(f"estatisticas.json: {d['total'].get('visitas', 0)} visitas, {len(d['relatorios'])} relatórios com aberturas, atualizado_em {d['atualizado_em']}")
    return True

# resumo de uma linha (Genética Reports): genérico, nunca resultados pessoais (percentis, genótipos, rsIDs, scores com valores)
RESUMO_MAX = 120
RESUMO_PESSOAL = re.compile(r'percentil|percentile|\bp\d|\b[ACGT]/[ACGT]\b|\b(?:hetero|homo)zig|\brs\d+|\*\d|\d+[,.]\d+\s*%|s[ée]rgio', re.I)
RE_GENE = re.compile(r'[A-Z0-9][A-Z0-9-]{1,14}')
def verificar_areas_relatorio(d, r, rid, err):
    """Campos da pesquisa/filtros da Genética Reports: resumo {pt,en}, areas [1-2 ids], publicado AAAA-MM-DD, genes [..], palavras [..]."""
    ids = {a.get('id') for a in d.get('areas') or [] if isinstance(a, dict)}
    res = r.get('resumo')
    _bi_check(res, f'{rid}.resumo', err)
    for v in ([res['pt'], res['en']] if isinstance(res, dict) and res.get('pt') and res.get('en') else [res] if isinstance(res, str) else []):
        if len(v) > RESUMO_MAX: err(f'{rid}.resumo: {len(v)} caracteres (máximo {RESUMO_MAX}) em {v[:50]!r}…')
        if RESUMO_PESSOAL.search(v): err(f'{rid}.resumo: parece ter resultados ou dados pessoais ({RESUMO_PESSOAL.search(v).group(0)!r}); o resumo é genérico sobre o tema')
        if PROIBIDO.search(v) or IDADE.search(v): err(f'{rid}.resumo: termo proibido em {v[:60]!r}')
    ar = r.get('areas')
    if not (isinstance(ar, list) and 1 <= len(ar) <= 2 and len(set(ar)) == len(ar)): err(f'{rid}.areas: tem de ser uma lista com 1 ou 2 áreas diferentes ({ar!r})')
    else:
        for x in ar:
            if x not in ids: err(f'{rid}.areas: {x!r} não está na lista "areas" de reports.json')
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', str(r.get('publicado', ''))): err(f'{rid}: publicado {r.get("publicado")!r} (AAAA-MM-DD, data de publicação)')
    for c in ('genes', 'palavras'):
        v = r.get(c, [])
        if not (isinstance(v, list) and all(isinstance(x, str) and x.strip() for x in v)): err(f'{rid}.{c}: tem de ser uma lista de textos'); continue
        if c == 'genes':
            mau = [x for x in v if not RE_GENE.fullmatch(x)]
            if mau: err(f'{rid}.genes: símbolos inválidos {mau[:5]}')
        for x in v:
            if PROIBIDO.search(x) or IDADE.search(x): err(f'{rid}.{c}: termo proibido em {x!r}')

RE_FICH = re.compile(r'reports/[A-Za-z0-9._-]+\.pdf')
RE_FICH_EN = re.compile(r'reports/[A-Za-z0-9._-]+_en\.pdf')
def verificar_reports_json(F):
    """data/reports.json: relatorios[{id, titulo{pt,en}, data AAAA-MM-DD, ficheiro reports/<nome>.pdf}] + PDF existente e sem termos proibidos."""
    ok = True; d = ler(F); nome = os.path.basename(F); ids = set()
    def err(m):
        nonlocal ok; ok = False; print(f'ERRO {nome}: ' + m)
    _bi_check(d.get('intro'), 'intro', err, False)
    if not isinstance(d.get('relatorios'), list): err('falta a lista "relatorios"'); return ok
    # áreas da Genética Reports (botões de filtro): [{id, pt, en}], ids únicos
    A = d.get('areas')
    if not (isinstance(A, list) and A): err('falta a lista "areas" (botões de filtro da página)'); A = []
    aids = [a.get('id') if isinstance(a, dict) else None for a in A]
    for a in A:
        if not (isinstance(a, dict) and re.fullmatch(r'[a-z0-9][a-z0-9-]*', str(a.get('id', ''))) and a.get('pt') and a.get('en')): err(f'areas: entrada inválida {a!r} (precisa de id, pt e en)')
    if len(set(aids)) != len(aids): err('areas: ids repetidos')
    for k, r in enumerate(d['relatorios']):
        rid = r.get('id', '')
        if not re.fullmatch(r'[a-z0-9][a-z0-9-]*', rid or ''): err(f'relatorios[{k}]: id inválido {rid!r}')
        if rid in ids or rid in ('reports', 'nav', 'lang', 'theme'): err(f'relatorios[{k}]: id repetido ou reservado {rid!r}')
        ids.add(rid)
        _bi_check(r.get('titulo'), f'{rid}.titulo', err); _bi_check(r.get('descricao'), f'{rid}.descricao', err, False)
        verificar_areas_relatorio(d, r, rid, err)
        if r.get('lingua') is not None: _bi_check(r.get('lingua'), f'{rid}.lingua', err)
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', str(r.get('data', ''))): err(f'{rid}: data {r.get("data")!r} (AAAA-MM-DD)')
        fich = r.get('ficheiro', '')
        if not RE_FICH.fullmatch(fich or '') or '..' in fich: err(f'{rid}: ficheiro {fich!r} (tem de ser reports/<nome>.pdf)'); continue
        cam = os.path.join(RAIZ, fich)
        if not os.path.exists(cam): err(f'{rid}: falta o ficheiro {fich}'); continue
        if open(cam, 'rb').read(5) != b'%PDF-': err(f'{rid}: {fich} não é um PDF')
        achados = privacidade_pdf(cam)
        if achados is None: print(f'AVISO {nome}: sem pdftotext, não verifiquei a privacidade de {fich}')
        elif achados: err(f'{rid}: {fich} tem termos proibidos: {sorted(set(achados))}')
        # versão inglesa opcional (ficheiro_en = reports/<nome>_en.pdf; a página usa-a no modo EN)
        fen = r.get('ficheiro_en')
        if fen is None: continue
        if not RE_FICH_EN.fullmatch(fen or '') or '..' in fen: err(f'{rid}: ficheiro_en {fen!r} (tem de ser reports/<nome>_en.pdf)'); continue
        cam = os.path.join(RAIZ, fen)
        if not os.path.exists(cam): err(f'{rid}: falta o ficheiro {fen}'); continue
        if open(cam, 'rb').read(5) != b'%PDF-': err(f'{rid}: {fen} não é um PDF')
        for c in ('paginas_en', 'tamanho_kb_en'):
            if c in r and not (isinstance(r[c], int) and r[c] > 0): err(f'{rid}: {c} tem de ser um inteiro positivo')
        achados = privacidade_pdf(cam)
        if achados: err(f'{rid}: {fen} tem termos proibidos: {sorted(set(achados))}')
    if os.path.isdir(D_REPORTS):
        usados = {r.get('ficheiro') for r in d['relatorios']} | {r.get('ficheiro_en') for r in d['relatorios'] if r.get('ficheiro_en')}
        for f in sorted(os.listdir(D_REPORTS)):
            if 'reports/' + f not in usados: print(f'AVISO {nome}: reports/{f} não está em reports.json (não aparece na página)')
    if A:
        vazias = [a.get('id') for a in A if isinstance(a, dict) and not any(a.get('id') in (r.get('areas') or []) for r in d['relatorios'])]
        if vazias: print(f'AVISO {nome}: áreas sem nenhum relatório (o botão fica a 0): {vazias}')
    print(f'{nome}: {len(d["relatorios"])} relatórios, {sum(1 for r in d["relatorios"] if r.get("ficheiro_en"))} com versão inglesa, {len(A)} áreas')
    return ok

def cmd_relatorio(a):
    """Junta um relatório PDF: verifica a privacidade, copia para reports/ e acrescenta a entrada em data/reports.json."""
    import shutil
    if not os.path.exists(a.pdf): sys.exit(f'Não encontro {a.pdf}')
    nomef = a.nome or os.path.basename(a.pdf)
    if not re.fullmatch(r'[A-Za-z0-9._-]+\.pdf', nomef): sys.exit('Nome do ficheiro: só letras, números, ponto, hífen e _; tem de acabar em .pdf (use --nome)')
    achados = privacidade_pdf(a.pdf)
    if achados is None: sys.exit('É preciso o pdftotext (poppler-utils) para verificar a privacidade do PDF')
    if achados: sys.exit(f'PDF com termos proibidos {sorted(set(achados))}: gere uma versão limpa primeiro')
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', a.data): sys.exit('--data no formato AAAA-MM-DD')
    for t in (a.titulo_pt, a.titulo_en, a.descricao_pt or '', a.descricao_en or '', a.resumo_pt, a.resumo_en):
        if PROIBIDO.search(t): sys.exit(f'Texto com termo proibido: {t!r}')
    d = ler(F_REPORTS) if os.path.exists(F_REPORTS) else {'atualizado_em': a.hoje, 'areas': [], 'relatorios': []}
    if any(r.get('id') == a.id for r in d['relatorios']): sys.exit(f'Já existe um relatório com id {a.id!r}')
    lista = lambda s: [x.strip() for x in (s or '').split(',') if x.strip()]
    pub = a.publicado or a.hoje
    extra = {'resumo': {'pt': a.resumo_pt, 'en': a.resumo_en}, 'areas': lista(a.areas), 'publicado': pub, 'palavras': lista(a.palavras), 'genes': lista(a.genes)}
    erros = []; verificar_areas_relatorio(d, extra, a.id, erros.append)
    if erros: sys.exit('\n'.join(erros))
    os.makedirs(D_REPORTS, exist_ok=True); shutil.copyfile(a.pdf, os.path.join(D_REPORTS, nomef))
    r = {'id': a.id, 'titulo': {'pt': a.titulo_pt, 'en': a.titulo_en}, 'resumo': extra['resumo'], 'data': a.data, 'publicado': pub, 'ficheiro': 'reports/' + nomef}
    if a.descricao_pt and a.descricao_en: r['descricao'] = {'pt': a.descricao_pt, 'en': a.descricao_en}
    if a.paginas: r['paginas'] = a.paginas
    r['tamanho_kb'] = round(os.path.getsize(a.pdf) / 1024)
    if a.lingua_pt and a.lingua_en: r['lingua'] = {'pt': a.lingua_pt, 'en': a.lingua_en}
    r['areas'] = extra['areas']; r['palavras'] = extra['palavras']; r['genes'] = extra['genes']
    d['relatorios'].append(r); d['atualizado_em'] = a.hoje; gravar(F_REPORTS, d)
    print(f'relatório {a.id!r} acrescentado: reports/{nomef} ({len(d["relatorios"])} relatórios); corra "verificar" antes de publicar')

def cmd_relatorio_en(a):
    """Junta a versão inglesa (PDF) a um relatório já existente: verifica a privacidade, copia para reports/<nome>_en.pdf
    e grava ficheiro_en, paginas_en e tamanho_kb_en na entrada (a página mostra-a no modo EN)."""
    import shutil, subprocess
    if not os.path.exists(a.pdf): sys.exit(f'Não encontro {a.pdf}')
    achados = privacidade_pdf(a.pdf)
    if achados is None: sys.exit('É preciso o pdftotext (poppler-utils) para verificar a privacidade do PDF')
    if achados: sys.exit(f'PDF com termos proibidos {sorted(set(achados))}: gere uma versão limpa primeiro')
    d = ler(F_REPORTS); r = next((x for x in d['relatorios'] if x.get('id') == a.id), None)
    if r is None: sys.exit(f'Não existe nenhum relatório com id {a.id!r}')
    nomef = os.path.basename(r['ficheiro'])[:-4] + '_en.pdf'
    shutil.copyfile(a.pdf, os.path.join(D_REPORTS, nomef))
    pag = a.paginas
    if not pag and shutil.which('pdfinfo'):
        m = re.search(r'^Pages:\s+(\d+)', subprocess.run(['pdfinfo', a.pdf], capture_output=True, text=True).stdout, re.M); pag = int(m.group(1)) if m else None
    r['ficheiro_en'] = 'reports/' + nomef
    if pag: r['paginas_en'] = pag
    r['tamanho_kb_en'] = round(os.path.getsize(a.pdf) / 1024)
    d['atualizado_em'] = a.hoje; gravar(F_REPORTS, d)
    print(f'versão inglesa de {a.id!r}: reports/{nomef}')

def _bi_check(o, onde, err, obrig=True):
    if o is None or o == '':
        if obrig: err(f'{onde}: texto em falta')
        return
    if isinstance(o, str): vals = [o]
    elif isinstance(o, dict) and o.get('pt') and o.get('en'): vals = [o['pt'], o['en']]
    else: err(f'{onde}: precisa de "pt" e "en" (ou um texto igual nas duas línguas)'); return
    for v in vals:
        if re.search(r'<[a-z/!]', TAGS_OK.sub('', v), re.I): err(f'{onde}: HTML não permitido em {v[:60]!r} (só b, i, em, strong, br, small, sub, sup)')

def verificar_protocolo_json(F):
    """data/genetica_protocolo.json: titulo, intro opcional, blocos[{titulo, itens[]}] com PT+EN e só HTML simples."""
    ok = True; d = ler(F); nome = os.path.basename(F)
    def err(m):
        nonlocal ok; ok = False; print(f'ERRO {nome}: ' + m)
    _bi_check(d.get('titulo'), 'titulo', err); _bi_check(d.get('intro'), 'intro', err, False)
    if not d.get('blocos'): err('sem "blocos"')
    n = 0
    for k, b in enumerate(d.get('blocos', [])):
        _bi_check(b.get('titulo'), f'blocos[{k}].titulo', err)
        if not b.get('itens'): err(f'blocos[{k}]: sem "itens"')
        for j, x in enumerate(b.get('itens', [])): n += 1; _bi_check(x, f'blocos[{k}].itens[{j}]', err)
    print(f'{nome}: {len(d.get("blocos", []))} blocos, {n} itens')
    return ok

def verificar_genetica_json(F):
    """JSON de uma página de genética: estrutura, PT+EN em todos os textos, ids únicos, estados válidos, só HTML simples."""
    ok = True; d = ler(F); ids = set(); n = 0; nome = os.path.basename(F)
    def err(m):
        nonlocal ok; ok = False; print(f'ERRO {nome}: ' + m)
    def bi(o, onde, obrig=True):
        if o is None or o == '':
            if obrig: err(f'{onde}: texto em falta')
            return
        if isinstance(o, str): vals = [o]
        elif isinstance(o, dict) and o.get('pt') and o.get('en'): vals = [o['pt'], o['en']]
        else: err(f'{onde}: precisa de "pt" e "en" (ou um texto igual nas duas línguas)'); return
        for v in vals:
            resto = TAGS_OK.sub('', v)
            if re.search(r'<[a-z/!]', resto, re.I): err(f'{onde}: HTML não permitido em {v[:60]!r} (só b, i, em, strong, br, small, sub, sup)')
    bi(d.get('fonte'), 'fonte')
    for k, x in enumerate(d.get('notas', [])): bi(x, f'notas[{k}]')
    if not d.get('seccoes'): err('sem "seccoes"')
    for s in d.get('seccoes', []):
        sid = s.get('id', '')
        if not re.fullmatch(r'[a-z0-9][a-z0-9-]*', sid or ''): err(f'id inválido {sid!r} (minúsculas, números e hífens)')
        if sid in ids or sid in ('genetica', 'gen', 'lang', 'theme', 'nav'): err(f'id repetido ou reservado {sid!r}')
        ids.add(sid); bi(s.get('titulo'), f'{sid}.titulo'); bi(s.get('intro'), f'{sid}.intro', False)
        for k, r in enumerate(s.get('linhas', [])):
            n += 1; bi(r.get('item'), f'{sid}.linhas[{k}].item'); bi(r.get('texto'), f'{sid}.linhas[{k}].texto')
            if r.get('rotulo') is not None: bi(r.get('rotulo'), f'{sid}.linhas[{k}].rotulo')
            if r.get('estado', 'na') not in ('ok', 'warn', 'bad', 'na', 'info'): err(f'{sid}.linhas[{k}]: estado {r.get("estado")!r} (ok, warn, bad, na, info)')
        # blocos Evitar / Priorizar (listas de textos PT/EN; obrigatórios em todas as secções)
        for campo in ('evitar', 'priorizar'):
            if not s.get(campo): err(f'{sid}: falta "{campo}" (lista de textos PT/EN)')
            for k, x in enumerate(s.get(campo) or []): bi(x, f'{sid}.{campo}[{k}]')
        # blocos opcionais Ajustar a dose / Monitorizar (usados na Farmacogenómica)
        for campo in ('ajustar', 'monitorizar'):
            if campo in s and not isinstance(s[campo], list): err(f'{sid}: "{campo}" tem de ser uma lista')
            for k, x in enumerate(s.get(campo) or []): bi(x, f'{sid}.{campo}[{k}]')
    # tabela pesquisável opcional dos fármacos acionáveis (relatório PGx)
    F2 = d.get('farmacos')
    if F2 is not None:
        bi(F2.get('titulo'), 'farmacos.titulo'); bi(F2.get('intro'), 'farmacos.intro', False); bi(F2.get('fonte'), 'farmacos.fonte', False)
        if (F2.get('id') or 'farmacos') in ids: err('farmacos.id repete o id de uma secção')
        if not F2.get('linhas'): err('farmacos: sem "linhas"')
        for k, l in enumerate(F2.get('linhas') or []):
            bi(l.get('f'), f'farmacos.linhas[{k}].f'); bi(l.get('genes'), f'farmacos.linhas[{k}].genes'); bi(l.get('rec'), f'farmacos.linhas[{k}].rec')
            if l.get('acao') not in ('evitar', 'ajustar', 'monitorizar', 'indeterminado'): err(f'farmacos.linhas[{k}]: acao {l.get("acao")!r} (evitar, ajustar, monitorizar, indeterminado)')
        print(f'{nome}: tabela farmacos com {len(F2.get("linhas") or [])} fármacos')
    # lista ordenada opcional (achados por ordem de impacto; cada linha cita os relatórios de origem publicados em data/reports.json)
    Li = d.get('lista')
    if Li is not None:
        bi(Li.get('titulo'), 'lista.titulo'); bi(Li.get('intro'), 'lista.intro', False)
        if (Li.get('id') or 'lista') in ids: err('lista.id repete o id de uma secção')
        rel = {r.get('id') for r in (ler(F_REPORTS).get('relatorios') or [])} if os.path.exists(F_REPORTS) else set()
        if not Li.get('linhas'): err('lista: sem "linhas"')
        for k, r in enumerate(Li.get('linhas') or []):
            if r.get('n') != k + 1: err(f'lista.linhas[{k}]: n={r.get("n")!r} (tem de ser {k + 1})')
            bi(r.get('texto'), f'lista.linhas[{k}].texto'); bi(r.get('evidencia'), f'lista.linhas[{k}].evidencia'); bi(r.get('analise'), f'lista.linhas[{k}].analise', False)
            if r.get('estado', 'na') not in ('ok', 'warn', 'bad', 'na', 'info'): err(f'lista.linhas[{k}]: estado {r.get("estado")!r} (ok, warn, bad, na, info)')
            if not isinstance(r.get('fraca', False), bool): err(f'lista.linhas[{k}]: "fraca" tem de ser true/false')
            if not isinstance(r.get('origem', []), list): err(f'lista.linhas[{k}]: "origem" tem de ser uma lista de ids de data/reports.json')
            for x in r.get('origem') or []:
                if x not in rel: err(f'lista.linhas[{k}]: origem {x!r} não é um relatório publicado em data/reports.json')
        nl = Li.get('linhas') or []
        print(f'{nome}: lista ordenada com {len(nl)} linhas ({sum(1 for r in nl if r.get("fraca"))} com evidência fraca)')
    print(f'{nome}: {len(ids)} secções, {n} linhas')
    return ok

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
    ok = verificar_genetica() and ok
    ok = verificar_estatisticas() and ok
    # data/estatisticas.json é gerado de 15 em 15 minutos pelo workflow (só contagens agregadas): não entra nas procuras de texto/bytes
    AUTO = os.path.join(RAIZ, 'data', 'estatisticas.json')
    for base, _, fs in os.walk(RAIZ):
        if '.git' in base.split(os.sep): continue
        for f in fs:
            if not f.endswith(('.html', '.json', '.md', '.py', '.txt', '.yml')) or os.path.join(base, f) == AUTO: continue
            t = open(os.path.join(base, f), encoding='utf-8').read().replace('font-weight', '')
            for mt in PROIBIDO.finditer(t):
                ok = False; print(f'PROIBIDO em {f}: …{t[max(0, mt.start()-30):mt.end()+30]}…')
            for mt in IDADE.finditer(t):
                ok = False; print(f'IDADE/NASCIMENTO em {f}: …{t[max(0, mt.start()-30):mt.end()+30]}…')
    for base, _, fs in os.walk(RAIZ):
        if '.git' in base.split(os.sep): continue
        for f in fs:
            if os.path.join(base, f) == AUTO: continue
            raw = open(os.path.join(base, f), 'rb').read()
            for b in ANO_BYTES:
                if b in raw: ok = False; print(f'ANO/UTILIZADOR ANTIGO nos bytes de {os.path.relpath(os.path.join(base, f), RAIZ)} (sequência {b[:2].decode()}…)')
    print('OK' if ok else 'FALHOU'); sys.exit(0 if ok else 1)

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument('--hoje', default=__import__('datetime').date.today().isoformat())
sp = ap.add_subparsers(dest='cmd', required=True)
p = sp.add_parser('sangue'); p.add_argument('--csv', required=True); p.add_argument('--data', required=True)
p.add_argument('--datas-csv'); p.add_argument('--rotulo'); p.add_argument('--descricao'); p.add_argument('--nota')
p.add_argument('--rotulo-en'); p.add_argument('--descricao-en'); p.add_argument('--nota-en'); p.set_defaults(f=cmd_sangue)
p = sp.add_parser('verificar'); p.set_defaults(f=cmd_verificar)
p = sp.add_parser('relatorio', help='juntar um relatório PDF à página Genética Reports')
p.add_argument('--pdf', required=True); p.add_argument('--id', required=True); p.add_argument('--data', required=True)
p.add_argument('--titulo-pt', required=True); p.add_argument('--titulo-en', required=True)
p.add_argument('--descricao-pt'); p.add_argument('--descricao-en'); p.add_argument('--lingua-pt'); p.add_argument('--lingua-en')
p.add_argument('--resumo-pt', required=True, help='uma linha genérica (até 120 caracteres, sem resultados pessoais)'); p.add_argument('--resumo-en', required=True)
p.add_argument('--areas', required=True, help='1 ou 2 ids da lista "areas" de data/reports.json, separados por vírgula')
p.add_argument('--palavras', help='palavras-chave PT/EN para a pesquisa, separadas por vírgula'); p.add_argument('--genes', help='genes citados no PDF, separados por vírgula')
p.add_argument('--publicado', help='data de publicação AAAA-MM-DD (por omissão, hoje)')
p.add_argument('--paginas', type=int); p.add_argument('--nome', help='nome do ficheiro em reports/ (por omissão, o do PDF)'); p.set_defaults(f=cmd_relatorio)
p = sp.add_parser('relatorio-en', help='juntar a versão inglesa (PDF) a um relatório já existente')
p.add_argument('--pdf', required=True); p.add_argument('--id', required=True); p.add_argument('--paginas', type=int); p.set_defaults(f=cmd_relatorio_en)
a = ap.parse_args(); a.f(a)
