/*! Genetica Reports AI — assistente só sobre os relatórios desta página.
 * Usa data/reports.json (já carregado pela página quando possível).
 * Sem cookies, sem API paga: respostas locais a partir do catálogo.
 */
(function () {
  "use strict";
  if (window.__RAI_LOADED) return;
  window.__RAI_LOADED = true;

  const SRC = (document.body && document.body.dataset.json) || "data/reports.json";
  const OFF_PT =
    "Só consigo ajudar com perguntas sobre os Genética Reports deste site (títulos, temas, áreas, genes e como encontrar um PDF). Reformula a pergunta com um tema ou gene dos teus relatórios.";
  const OFF_EN =
    "I can only help with questions about the Genetics Reports on this site (titles, topics, areas, genes, and finding a PDF). Rephrase with a topic or gene from your reports.";
  const HELLO_PT =
    "Olá! Sou o assistente dos Genética Reports. Pergunta-me por um tema (ex.: dopamina, suplementos, cancro) ou por um gene — eu aponto o relatório certo. Não leio o conteúdo clínico dos PDFs nem substituo o médico.";
  const HELLO_EN =
    "Hi! I’m the Genetics Reports assistant. Ask about a topic (e.g. dopamine, supplements, cancer) or a gene — I’ll point you to the right report. I don’t read clinical PDF contents and I’m not a doctor.";

  const SCOPE = [
    "genetica",
    "genetics",
    "report",
    "relatorio",
    "pdf",
    "gene",
    "adn",
    "dna",
    "farmaco",
    "medicamento",
    "suplemento",
    "dopamina",
    "nutricao",
    "desporto",
    "cancro",
    "cancer",
    "metabolismo",
    "intestino",
    "longevidade",
    "musculo",
    "imunidade",
    "hormona",
    "vitamina",
    "intolerancia",
    "alzheimer",
    "avc",
    "coracao",
    "cerebro",
  ];

  const OFF = [
    /\b(bitcoin|crypto|forex|apostas?)\b/i,
    /\b(receita de bolo|futebol|politica|eleic)\b/i,
    /\b(escreve codigo|hacke|namoro|horoscopo)\b/i,
    /\b(capital de fran[cç]a|weather|tempo em)\b/i,
  ];

  const norm = (s) =>
    String(s || "")
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[^\p{L}\p{N}\s-]/gu, " ")
      .replace(/\s+/g, " ")
      .trim();

  const lang = () =>
    (document.documentElement.lang || "").toLowerCase().startsWith("en")
      ? "en"
      : "pt";

  const T = (o) => {
    if (o == null) return "";
    if (typeof o === "string") return o;
    const L = lang();
    return (L === "en" ? o.en || o.pt : o.pt || o.en) || "";
  };

  const both = (o) =>
    o == null
      ? ""
      : typeof o === "string"
        ? o
        : [o.pt || "", o.en || ""].join(" ");

  let catalog = null;
  let pending = false;

  function ensureCatalog() {
    if (catalog) return Promise.resolve(catalog);
    // A página principal guarda RD em scope local; tentamos re-fetch (cache HTTP).
    return fetch(SRC, { cache: "force-cache" })
      .then((r) => {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then((d) => {
        catalog = d;
        return d;
      });
  }

  function isGreeting(q) {
    return /^(ola|oi|hey|hello|bom dia|boa tarde|boa noite|hi|good (morning|afternoon|evening))\b/.test(
      norm(q),
    );
  }

  function areaNames(d) {
    return (d.areas || [])
      .map((a) => norm([a.id, a.pt, a.en].join(" ")))
      .join(" ");
  }

  function hay(r) {
    return norm(
      [
        both(r.titulo),
        both(r.resumo),
        both(r.descricao),
        (r.etiquetas || []).join(" "),
        (r.palavras || []).join(" "),
        (r.genes || []).join(" "),
        (r.areas || []).join(" "),
        r.id || "",
      ].join(" "),
    );
  }

  function inScope(q, d) {
    const n = norm(q);
    if (!n) return false;
    if (isGreeting(q)) return true;
    if (OFF.some((re) => re.test(q))) return false;
    if (SCOPE.some((k) => n.includes(norm(k)))) return true;
    const tokens = n.split(" ").filter((t) => t.length > 2);
    const areas = areaNames(d);
    if (tokens.some((t) => areas.includes(t))) return true;
    return (d.relatorios || []).some((r) => {
      const h = hay(r);
      return tokens.some((t) => h.includes(t));
    });
  }

  function score(q, r) {
    const tokens = norm(q)
      .split(" ")
      .filter((t) => t.length > 2);
    if (!tokens.length) return 0;
    const title = norm(both(r.titulo) + " " + (r.id || ""));
    const tags = norm(
      [(r.palavras || []).join(" "), (r.areas || []).join(" ")].join(" "),
    );
    const genes = norm((r.genes || []).join(" "));
    const body = hay(r);
    let s = 0;
    for (const t of tokens) {
      if (title.includes(t)) s += 5;
      if (genes.split(" ").some((g) => g === t || g.startsWith(t))) s += 4;
      if (tags.includes(t)) s += 3;
      if (body.includes(t)) s += 1;
    }
    if (r.destaque) s += 0.5;
    return s;
  }

  function retrieve(q, d, limit) {
    return (d.relatorios || [])
      .map((r) => ({ r, s: score(q, r) }))
      .filter((x) => x.s > 0)
      .sort((a, b) => b.s - a.s)
      .slice(0, limit || 4)
      .map((x) => x.r);
  }

  function answer(q, d) {
    const L = lang();
    if (isGreeting(q)) return L === "en" ? HELLO_EN : HELLO_PT;
    if (!inScope(q, d)) return L === "en" ? OFF_EN : OFF_PT;

    const hits = retrieve(q, d, 4);
    if (!hits.length) {
      return L === "en"
        ? "I didn’t find a matching report in the catalogue. Try another topic, area, or gene — or use the search box above."
        : "Não encontrei um relatório correspondente no catálogo. Experimenta outro tema, área ou gene — ou usa a pesquisa em cima.";
    }

    const lines = hits.map((r, i) => {
      const title = T(r.titulo) || r.id;
      const sum = T(r.resumo);
      const areas = (r.areas || [])
        .map((id) => {
          const a = (d.areas || []).find((x) => x.id === id);
          return a ? T(a) : id;
        })
        .filter(Boolean)
        .join(", ");
      const file = typeof r.ficheiro === "string" ? r.ficheiro : "";
      const anchor = r.id ? `#${r.id}` : "";
      let block = `${i + 1}. **${title}**`;
      if (sum) block += `\n${sum}`;
      if (areas)
        block +=
          L === "en" ? `\nAreas: ${areas}` : `\nÁreas: ${areas}`;
      if (anchor)
        block +=
          L === "en"
            ? `\nOpen on page: ${anchor}`
            : `\nAbrir na página: ${anchor}`;
      if (file) block += `\nPDF: ${file}`;
      return block;
    });

    const head =
      L === "en"
        ? "Based on your Genetics Reports catalogue:"
        : "Com base no catálogo dos teus Genética Reports:";
    const foot =
      L === "en"
        ? "\n\n_Supporting info only — not medical advice. Open the PDF for full detail._"
        : "\n\n_Documento de apoio — não substitui o médico. Abre o PDF para o detalhe completo._";

    return head + "\n\n" + lines.join("\n\n") + foot;
  }

  function renderText(el, text) {
    el.textContent = "";
    const parts = String(text).split(/(\*\*[^*]+\*\*|_[^_]+_)/g);
    for (const part of parts) {
      if (!part) continue;
      if (part.startsWith("**") && part.endsWith("**")) {
        const s = document.createElement("strong");
        s.textContent = part.slice(2, -2);
        el.appendChild(s);
      } else if (part.startsWith("_") && part.endsWith("_")) {
        const e = document.createElement("em");
        e.textContent = part.slice(1, -1);
        el.appendChild(e);
      } else {
        el.appendChild(document.createTextNode(part));
      }
    }
  }

  function injectStyles() {
    if (document.getElementById("rai-style")) return;
    const s = document.createElement("style");
    s.id = "rai-style";
    s.textContent = `
#rai-root{position:fixed;right:16px;bottom:16px;z-index:80;font:14px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
#rai-toggle{display:inline-flex;align-items:center;gap:8px;border:0;border-radius:999px;padding:12px 16px;background:var(--ink,#14202e);color:var(--actfg,#fff);font-weight:600;cursor:pointer;box-shadow:0 10px 28px rgba(15,30,50,.28)}
#rai-toggle:hover{filter:brightness(1.08)}
#rai-panel{display:none;flex-direction:column;width:min(380px,calc(100vw - 24px));height:min(560px,70vh);margin-bottom:10px;border:1px solid var(--line,#e3e8ef);border-radius:16px;background:var(--card,#fff);color:var(--ink,#14202e);overflow:hidden;box-shadow:0 18px 50px rgba(15,30,50,.28)}
#rai-root.open #rai-panel{display:flex}
#rai-head{display:flex;align-items:flex-start;justify-content:space-between;gap:10px;padding:14px 14px 12px;background:linear-gradient(135deg,var(--hero1,#0f2747),var(--hero2,#1f5eff));color:#fff}
#rai-head h2{margin:0;font-size:16px;letter-spacing:-.2px}
#rai-head p{margin:3px 0 0;font-size:12px;opacity:.88}
#rai-close{border:0;background:transparent;color:#fff;font-size:20px;line-height:1;cursor:pointer;padding:2px 6px;border-radius:8px}
#rai-close:hover{background:rgba(255,255,255,.14)}
#rai-msgs{flex:1;overflow:auto;padding:12px;display:flex;flex-direction:column;gap:8px;background:var(--bg,#f5f7fa)}
.rai-msg{max-width:92%;padding:9px 11px;border-radius:14px;white-space:pre-wrap;word-break:break-word}
.rai-msg.bot{align-self:flex-start;background:var(--card,#fff);border:1px solid var(--line,#e3e8ef);border-bottom-left-radius:5px}
.rai-msg.user{align-self:flex-end;background:var(--acc,#1f5eff);color:#fff;border-bottom-right-radius:5px}
.rai-msg.sys{align-self:center;background:var(--warnb,#fff4dc);color:var(--warnt,#9a5f00);border:1px solid var(--line,#e3e8ef);font-size:12.5px}
#rai-chips{display:flex;flex-wrap:wrap;gap:6px;padding:0 12px 8px;background:var(--bg,#f5f7fa)}
#rai-chips button{border:1px solid var(--line,#e3e8ef);background:var(--card,#fff);color:var(--ink,#14202e);border-radius:999px;padding:5px 10px;font-size:11.5px;cursor:pointer}
#rai-chips button:hover{border-color:var(--acc,#1f5eff)}
#rai-form{display:flex;gap:8px;padding:10px;border-top:1px solid var(--line,#e3e8ef);background:var(--card,#fff)}
#rai-input{flex:1;min-width:0;border:1px solid var(--line,#e3e8ef);border-radius:10px;padding:9px 11px;font:inherit;background:var(--bg,#f5f7fa);color:var(--ink,#14202e)}
#rai-send{border:0;border-radius:10px;padding:0 14px;background:var(--acc,#1f5eff);color:#fff;font-weight:600;cursor:pointer}
#rai-send:disabled{opacity:.5;cursor:default}
@media(max-width:640px){#rai-root{right:10px;bottom:10px}#rai-panel{width:min(100vw - 16px,380px)}}
`;
    document.head.appendChild(s);
  }

  function mount() {
    injectStyles();
    const root = document.createElement("div");
    root.id = "rai-root";
    root.innerHTML = `
      <div id="rai-panel" role="dialog" aria-label="Genética Reports AI">
        <div id="rai-head">
          <div>
            <h2 data-rai-pt="Genética Reports AI" data-rai-en="Genetics Reports AI">Genética Reports AI</h2>
            <p data-rai-pt="Só sobre os teus relatórios PDF" data-rai-en="Only about your PDF reports">Só sobre os teus relatórios PDF</p>
          </div>
          <button type="button" id="rai-close" aria-label="Fechar">×</button>
        </div>
        <div id="rai-msgs" aria-live="polite"></div>
        <div id="rai-chips"></div>
        <form id="rai-form">
          <input id="rai-input" autocomplete="off" spellcheck="false" placeholder="Pergunta sobre um report…" />
          <button type="submit" id="rai-send">OK</button>
        </form>
      </div>
      <button type="button" id="rai-toggle" aria-expanded="false">
        <span aria-hidden="true">💬</span>
        <span data-rai-pt="Reports AI" data-rai-en="Reports AI">Reports AI</span>
      </button>`;
    document.body.appendChild(root);

    const panel = root.querySelector("#rai-panel");
    const msgs = root.querySelector("#rai-msgs");
    const chips = root.querySelector("#rai-chips");
    const form = root.querySelector("#rai-form");
    const input = root.querySelector("#rai-input");
    const sendBtn = root.querySelector("#rai-send");
    const toggle = root.querySelector("#rai-toggle");
    const close = root.querySelector("#rai-close");

    function applyUiLang() {
      const L = lang();
      root.querySelectorAll("[data-rai-pt]").forEach((el) => {
        el.textContent = L === "en" ? el.dataset.raiEn : el.dataset.raiPt;
      });
      input.placeholder =
        L === "en" ? "Ask about a report…" : "Pergunta sobre um report…";
      sendBtn.textContent = L === "en" ? "Send" : "Enviar";
      const sug =
        L === "en"
          ? [
              "Which report covers dopamine?",
              "Reports about supplements",
              "Anything on cancer risk?",
              "Pharmacogenomics medicines",
            ]
          : [
              "Que relatório fala de dopamina?",
              "Reports sobre suplementos",
              "Há algo sobre risco de cancro?",
              "Farmacogenómica e medicamentos",
            ];
      chips.innerHTML = "";
      sug.forEach((text) => {
        const b = document.createElement("button");
        b.type = "button";
        b.textContent = text;
        b.addEventListener("click", () => send(text));
        chips.appendChild(b);
      });
    }

    function addMsg(role, text) {
      const div = document.createElement("div");
      div.className = "rai-msg " + role;
      if (role === "bot") renderText(div, text);
      else div.textContent = text;
      msgs.appendChild(div);
      msgs.scrollTop = msgs.scrollHeight;
      // Se a resposta apontar para #id, torna clicável o scroll
      if (role === "bot") {
        div.querySelectorAll("strong").forEach(() => {});
        const m = text.match(/#[a-z0-9-]+/gi) || [];
        m.forEach((hash) => {
          const a = document.createElement("a");
          a.href = hash;
          a.textContent =
            lang() === "en" ? ` → ${hash}` : ` → ir para ${hash}`;
          a.style.display = "inline-block";
          a.style.marginTop = "4px";
          a.addEventListener("click", (e) => {
            const el = document.getElementById(hash.slice(1));
            if (el) {
              e.preventDefault();
              el.scrollIntoView({ behavior: "smooth", block: "start" });
            }
          });
          div.appendChild(document.createElement("br"));
          div.appendChild(a);
        });
      }
    }

    function setOpen(on) {
      root.classList.toggle("open", on);
      toggle.setAttribute("aria-expanded", on ? "true" : "false");
      if (on) input.focus();
    }

    async function send(text) {
      const q = String(text || "").trim();
      if (!q || pending) return;
      pending = true;
      sendBtn.disabled = true;
      chips.style.display = "none";
      addMsg("user", q);
      input.value = "";
      try {
        const d = await ensureCatalog();
        addMsg("bot", answer(q, d));
      } catch (err) {
        addMsg(
          "sys",
          lang() === "en"
            ? "Could not load the reports catalogue."
            : "Não foi possível carregar o catálogo de relatórios.",
        );
      } finally {
        pending = false;
        sendBtn.disabled = false;
        input.focus();
      }
    }

    toggle.addEventListener("click", () =>
      setOpen(!root.classList.contains("open")),
    );
    close.addEventListener("click", () => setOpen(false));
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      send(input.value);
    });

    // Reagir a mudanças de idioma da página
    const mo = new MutationObserver(applyUiLang);
    mo.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["lang"],
    });
    document.querySelectorAll("#lang button").forEach((b) =>
      b.addEventListener("click", () => setTimeout(applyUiLang, 0)),
    );

    applyUiLang();
    addMsg("bot", lang() === "en" ? HELLO_EN : HELLO_PT);
    ensureCatalog().catch(() => {});
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }
})();
