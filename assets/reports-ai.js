/*! Ask Sergio AI — responde só com base no texto extraído dos Genética Reports.
 * Carrega data/kb/index.json e, para os reports relevantes, data/kb/<id>.paras.json.
 */
(function () {
  "use strict";
  if (window.__ASK_SERGIO_AI__) return;
  window.__ASK_SERGIO_AI__ = true;

  var INDEX_URL = "data/kb/index.json";
  var OFF_PT =
    "Só respondo com base nos Genética Reports deste site. Pergunta sobre um tema, gene, medicamento, suplemento ou achado dos teus relatórios.";
  var OFF_EN =
    "I only answer from the Genetics Reports on this site. Ask about a topic, gene, medicine, supplement, or finding from your reports.";
  var HELLO_PT =
    "Olá — sou o Ask Sergio AI. Li os teus Genética Reports e respondo só com o que neles está. Pergunta o que quiseres sobre esses relatórios (não substituo o médico).";
  var HELLO_EN =
    "Hi — I’m Ask Sergio AI. I’ve read your Genetics Reports and I only answer from what’s in them. Ask about those reports (I’m not a doctor).";

  var STOP = {
    a: 1, o: 1, e: 1, de: 1, da: 1, do: 1, das: 1, dos: 1, um: 1, uma: 1,
    em: 1, no: 1, na: 1, nos: 1, nas: 1, por: 1, para: 1, com: 1, sem: 1,
    que: 1, se: 1, ou: 1, as: 1, os: 1, ao: 1, aos: 1, à: 1, the: 1, and: 1,
    of: 1, to: 1, in: 1, on: 1, for: 1, is: 1, are: 1, what: 1, which: 1,
    about: 1, me: 1, my: 1, meu: 1, minha: 1, over: 1, from: 1, with: 1,
    this: 1, that: 1, como: 1, qual: 1, quais: 1, sobre: 1, tem: 1, há: 1,
    ha: 1, ser: 1, ter: 1, foi: 1, são: 1, sao: 1, mais: 1, menos: 1,
  };

  var OFF = [
    /\b(bitcoin|crypto|forex|apostas?)\b/i,
    /\b(receita de bolo|futebol|politica|eleic)\b/i,
    /\b(escreve codigo|hacke|namoro|horoscopo)\b/i,
    /\b(capital de fran)/i,
  ];

  function norm(s) {
    return String(s || "")
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[^a-z0-9\s-]/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  function tokens(q) {
    return norm(q)
      .split(" ")
      .filter(function (t) {
        return t.length > 2 && !STOP[t];
      });
  }

  function lang() {
    return (document.documentElement.lang || "").toLowerCase().indexOf("en") === 0
      ? "en"
      : "pt";
  }

  function T(o) {
    if (o == null) return "";
    if (typeof o === "string") return o;
    var L = lang();
    return (L === "en" ? o.en || o.pt : o.pt || o.en) || "";
  }

  function both(o) {
    if (o == null) return "";
    if (typeof o === "string") return o;
    return [o.pt || "", o.en || ""].join(" ");
  }

  var indexData = null;
  var parasCache = {};
  var pending = false;

  function loadIndex() {
    if (indexData) return Promise.resolve(indexData);
    return fetch(INDEX_URL, { cache: "no-cache" }).then(function (r) {
      if (!r.ok) throw new Error("index " + r.status);
      return r.json();
    }).then(function (d) {
      indexData = d;
      return d;
    });
  }

  function loadParas(rep) {
    var id = rep.id;
    if (parasCache[id]) return Promise.resolve(parasCache[id]);
    var url = rep.paras_file || ("data/kb/" + id + ".paras.json");
    return fetch(url, { cache: "force-cache" }).then(function (r) {
      if (!r.ok) throw new Error(id + " " + r.status);
      return r.json();
    }).then(function (paras) {
      parasCache[id] = Array.isArray(paras) ? paras : [];
      return parasCache[id];
    });
  }

  function isGreeting(q) {
    return /^(ola|oi|hey|hello|bom dia|boa tarde|boa noite|hi|good (morning|afternoon|evening))\b/.test(
      norm(q),
    );
  }

  function inScope(q, d) {
    var n = norm(q);
    if (!n) return false;
    if (isGreeting(q)) return true;
    if (OFF.some(function (re) { return re.test(q); })) return false;
    var tk = tokens(q);
    if (!tk.length) return false;
    // Any overlap with catalogue text / genes / areas / preview counts as in-scope.
    return (d.reports || []).some(function (r) {
      var hay = norm(
        [
          both(r.titulo),
          both(r.resumo),
          both(r.descricao),
          (r.palavras || []).join(" "),
          (r.genes || []).join(" "),
          (r.areas || []).join(" "),
          r.preview || "",
          r.id || "",
        ].join(" "),
      );
      return tk.some(function (t) {
        return hay.indexOf(t) !== -1;
      });
    });
  }

  function scoreReport(tk, r) {
    if (!tk.length) return 0;
    var title = norm(both(r.titulo) + " " + (r.id || ""));
    var meta = norm(
      [both(r.resumo), both(r.descricao), (r.palavras || []).join(" "), (r.areas || []).join(" ")].join(" "),
    );
    var genes = norm((r.genes || []).join(" "));
    var preview = norm(r.preview || "");
    var s = 0;
    for (var i = 0; i < tk.length; i++) {
      var t = tk[i];
      if (title.indexOf(t) !== -1) s += 6;
      if ((" " + genes + " ").indexOf(" " + t + " ") !== -1) s += 5;
      else if (genes.indexOf(t) !== -1) s += 3;
      if (meta.indexOf(t) !== -1) s += 3;
      if (preview.indexOf(t) !== -1) s += 2;
    }
    if (r.destaque) s += 0.3;
    return s;
  }

  function scorePara(tk, para) {
    var h = norm(para);
    if (!h) return 0;
    var s = 0;
    var hits = 0;
    for (var i = 0; i < tk.length; i++) {
      var t = tk[i];
      var re = new RegExp("(?:^|\\s)" + t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "g");
      var m = h.match(re);
      if (m) {
        hits += 1;
        s += 2 + Math.min(3, m.length);
      } else if (h.indexOf(t) !== -1) {
        hits += 1;
        s += 1;
      }
    }
    if (!hits) return 0;
    // Prefer denser, mid-length evidence paragraphs.
    var lenBonus = para.length > 80 && para.length < 900 ? 1.2 : 1;
    return (s * (1 + hits / tk.length)) * lenBonus;
  }

  function clip(s, n) {
    s = String(s || "").replace(/\s+/g, " ").trim();
    if (s.length <= n) return s;
    return s.slice(0, n - 1).replace(/\s+\S*$/, "") + "…";
  }

  function compose(q, ranked, evidence) {
    var L = lang();
    if (!evidence.length) {
      var names = ranked
        .slice(0, 3)
        .map(function (r) { return T(r.titulo) || r.id; })
        .join("; ");
      return L === "en"
        ? "I found related reports (" + names + ") but no clear excerpt for that exact question. Try a more specific term (gene, trait, or medicine)."
        : "Encontrei relatórios relacionados (" + names + "), mas sem um excerto claro para essa pergunta exacta. Experimenta um termo mais específico (gene, traço ou medicamento).";
    }

    var byReport = {};
    evidence.forEach(function (e) {
      if (!byReport[e.id]) byReport[e.id] = { rep: e.rep, paras: [] };
      if (byReport[e.id].paras.length < 3) byReport[e.id].paras.push(e.para);
    });

    var ids = Object.keys(byReport);
    var head =
      L === "en"
        ? "From your Genetics Reports (Ask Sergio AI):"
        : "Com base nos teus Genética Reports (Ask Sergio AI):";
    var parts = [head];

    ids.forEach(function (id, idx) {
      var block = byReport[id];
      var title = T(block.rep.titulo) || id;
      parts.push((idx + 1) + ". **" + title + "**");
      block.paras.forEach(function (p) {
        parts.push("«" + clip(p, 420) + "»");
      });
      parts.push(L === "en" ? "Source on page: #" + id : "Fonte na página: #" + id);
    });

    parts.push(
      L === "en"
        ? "_Supporting excerpts only — not medical advice. Open the PDF for full context._"
        : "_Excertos de apoio — não substituem o médico. Abre o PDF para o contexto completo._",
    );
    return parts.join("\n\n");
  }

  function answerQuestion(q, d) {
    var L = lang();
    if (isGreeting(q)) return Promise.resolve(L === "en" ? HELLO_EN : HELLO_PT);
    if (!inScope(q, d)) return Promise.resolve(L === "en" ? OFF_EN : OFF_PT);

    var tk = tokens(q);
    var ranked = (d.reports || [])
      .map(function (r) { return { r: r, s: scoreReport(tk, r) }; })
      .filter(function (x) { return x.s > 0; })
      .sort(function (a, b) { return b.s - a.s; })
      .slice(0, 5)
      .map(function (x) { return x.r; });

    if (!ranked.length) {
      return Promise.resolve(
        L === "en"
          ? "I couldn’t match that to any of your reports. Try a topic, gene, or report title from this page."
          : "Não consegui associar isso a nenhum dos teus relatórios. Experimenta um tema, gene ou título desta página.",
      );
    }

    return Promise.all(
      ranked.slice(0, 3).map(function (r) {
        return loadParas(r).then(
          function (paras) { return { r: r, paras: paras }; },
          function () { return { r: r, paras: [] }; },
        );
      }),
    ).then(function (loaded) {
      var evidence = [];
      loaded.forEach(function (item) {
        item.paras.forEach(function (para) {
          var s = scorePara(tk, para);
          if (s > 0) evidence.push({ id: item.r.id, rep: item.r, para: para, s: s });
        });
      });
      evidence.sort(function (a, b) { return b.s - a.s; });
      // Diversify: take best paras, max 3 per report, max 6 overall
      var picked = [];
      var per = {};
      for (var i = 0; i < evidence.length && picked.length < 6; i++) {
        var e = evidence[i];
        per[e.id] = (per[e.id] || 0) + 1;
        if (per[e.id] <= 2) picked.push(e);
      }
      return compose(q, ranked, picked);
    });
  }

  function renderText(el, text) {
    el.textContent = "";
    String(text).split(/(\*\*[^*]+\*\*|_[^_]+_)/g).forEach(function (part) {
      if (!part) return;
      if (part.indexOf("**") === 0 && part.slice(-2) === "**") {
        var s = document.createElement("strong");
        s.textContent = part.slice(2, -2);
        el.appendChild(s);
      } else if (part.charAt(0) === "_" && part.slice(-1) === "_") {
        var em = document.createElement("em");
        em.textContent = part.slice(1, -1);
        el.appendChild(em);
      } else {
        el.appendChild(document.createTextNode(part));
      }
    });
  }

  function injectStyles() {
    if (document.getElementById("ask-sergio-style")) return;
    var s = document.createElement("style");
    s.id = "ask-sergio-style";
    s.textContent =
      "#ask-sergio-root{position:fixed;right:16px;bottom:16px;z-index:9999;font:14px/1.45 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif}" +
      "#ask-sergio-toggle{display:inline-flex;align-items:center;gap:8px;border:0;border-radius:999px;padding:12px 16px;background:#0f2747;color:#fff;font-weight:700;cursor:pointer;box-shadow:0 10px 28px rgba(15,30,50,.35)}" +
      "#ask-sergio-toggle:hover{filter:brightness(1.08)}" +
      "#ask-sergio-panel{display:none;flex-direction:column;width:min(400px,calc(100vw - 20px));height:min(580px,72vh);margin-bottom:10px;border:1px solid rgba(20,32,46,.18);border-radius:16px;background:var(--card,#fff);color:var(--ink,#14202e);overflow:hidden;box-shadow:0 18px 50px rgba(15,30,50,.35)}" +
      "#ask-sergio-root.open #ask-sergio-panel{display:flex}" +
      "#ask-sergio-head{display:flex;align-items:flex-start;justify-content:space-between;gap:10px;padding:14px;background:linear-gradient(135deg,#0f2747,#1f5eff);color:#fff}" +
      "#ask-sergio-head h2{margin:0;font-size:17px;letter-spacing:-.2px}" +
      "#ask-sergio-head p{margin:4px 0 0;font-size:12px;opacity:.9}" +
      "#ask-sergio-close{border:0;background:transparent;color:#fff;font-size:22px;line-height:1;cursor:pointer;padding:2px 8px;border-radius:8px}" +
      "#ask-sergio-msgs{flex:1;overflow:auto;padding:12px;display:flex;flex-direction:column;gap:8px;background:var(--bg,#f5f7fa)}" +
      ".ask-msg{max-width:94%;padding:9px 11px;border-radius:14px;white-space:pre-wrap;word-break:break-word}" +
      ".ask-msg.bot{align-self:flex-start;background:var(--card,#fff);border:1px solid rgba(20,32,46,.12);border-bottom-left-radius:5px}" +
      ".ask-msg.user{align-self:flex-end;background:#1f5eff;color:#fff;border-bottom-right-radius:5px}" +
      ".ask-msg.sys{align-self:center;background:#fff4dc;color:#9a5f00;border:1px solid rgba(20,32,46,.1);font-size:12.5px}" +
      "#ask-sergio-chips{display:flex;flex-wrap:wrap;gap:6px;padding:0 12px 8px;background:var(--bg,#f5f7fa)}" +
      "#ask-sergio-chips button{border:1px solid rgba(20,32,46,.14);background:var(--card,#fff);color:inherit;border-radius:999px;padding:5px 10px;font-size:11.5px;cursor:pointer}" +
      "#ask-sergio-form{display:flex;gap:8px;padding:10px;border-top:1px solid rgba(20,32,46,.12);background:var(--card,#fff)}" +
      "#ask-sergio-input{flex:1;min-width:0;border:1px solid rgba(20,32,46,.16);border-radius:10px;padding:9px 11px;font:inherit;background:var(--bg,#f5f7fa);color:inherit}" +
      "#ask-sergio-send{border:0;border-radius:10px;padding:0 14px;background:#1f5eff;color:#fff;font-weight:700;cursor:pointer}" +
      "#ask-sergio-send:disabled{opacity:.5;cursor:default}" +
      "@media(max-width:640px){#ask-sergio-root{right:10px;bottom:10px}}";
    document.head.appendChild(s);
  }

  function mount() {
    injectStyles();
    var root = document.createElement("div");
    root.id = "ask-sergio-root";
    root.innerHTML =
      '<div id="ask-sergio-panel" role="dialog" aria-label="Ask Sergio AI">' +
      '<div id="ask-sergio-head"><div>' +
      "<h2>Ask Sergio AI</h2>" +
      '<p data-pt="Respostas só a partir dos teus reports" data-en="Answers only from your reports">Respostas só a partir dos teus reports</p>' +
      "</div>" +
      '<button type="button" id="ask-sergio-close" aria-label="Close">×</button></div>' +
      '<div id="ask-sergio-msgs" aria-live="polite"></div>' +
      '<div id="ask-sergio-chips"></div>' +
      '<form id="ask-sergio-form">' +
      '<input id="ask-sergio-input" autocomplete="off" spellcheck="false" />' +
      '<button type="submit" id="ask-sergio-send">OK</button>' +
      "</form></div>" +
      '<button type="button" id="ask-sergio-toggle" aria-expanded="false">' +
      "<span>Ask Sergio AI</span></button>";
    document.body.appendChild(root);

    var msgs = root.querySelector("#ask-sergio-msgs");
    var chips = root.querySelector("#ask-sergio-chips");
    var form = root.querySelector("#ask-sergio-form");
    var input = root.querySelector("#ask-sergio-input");
    var sendBtn = root.querySelector("#ask-sergio-send");
    var toggle = root.querySelector("#ask-sergio-toggle");
    var close = root.querySelector("#ask-sergio-close");
    var sub = root.querySelector("#ask-sergio-head p");

    function applyUiLang() {
      var L = lang();
      sub.textContent = L === "en" ? sub.getAttribute("data-en") : sub.getAttribute("data-pt");
      input.placeholder =
        L === "en" ? "Ask about your reports…" : "Pergunta sobre os teus reports…";
      sendBtn.textContent = L === "en" ? "Send" : "Enviar";
      var sug =
        L === "en"
          ? [
              "What do my reports say about dopamine?",
              "Any findings on supplements?",
              "Cancer-related reports?",
              "Pharmacogenomics summary",
            ]
          : [
              "O que dizem os reports sobre dopamina?",
              "Há achados sobre suplementos?",
              "Relatórios ligados a cancro?",
              "Resumo de farmacogenómica",
            ];
      chips.innerHTML = "";
      sug.forEach(function (text) {
        var b = document.createElement("button");
        b.type = "button";
        b.textContent = text;
        b.addEventListener("click", function () { send(text); });
        chips.appendChild(b);
      });
    }

    function addMsg(role, text) {
      var div = document.createElement("div");
      div.className = "ask-msg " + role;
      if (role === "bot") renderText(div, text);
      else div.textContent = text;
      msgs.appendChild(div);
      // Deep-link report anchors
      if (role === "bot") {
        var hashes = String(text).match(/#[a-z0-9-]+/gi) || [];
        var seen = {};
        hashes.forEach(function (hash) {
          if (seen[hash]) return;
          seen[hash] = 1;
          var a = document.createElement("a");
          a.href = hash;
          a.textContent = lang() === "en" ? "Open " + hash : "Abrir " + hash;
          a.style.display = "inline-block";
          a.style.marginTop = "6px";
          a.style.marginRight = "8px";
          a.addEventListener("click", function (e) {
            var el = document.getElementById(hash.slice(1));
            if (el) {
              e.preventDefault();
              el.scrollIntoView({ behavior: "smooth", block: "start" });
            }
          });
          div.appendChild(document.createElement("br"));
          div.appendChild(a);
        });
      }
      msgs.scrollTop = msgs.scrollHeight;
    }

    function setOpen(on) {
      root.classList.toggle("open", !!on);
      toggle.setAttribute("aria-expanded", on ? "true" : "false");
      if (on) input.focus();
    }

    function send(text) {
      var q = String(text || "").trim();
      if (!q || pending) return;
      pending = true;
      sendBtn.disabled = true;
      chips.style.display = "none";
      addMsg("user", q);
      input.value = "";
      loadIndex()
        .then(function (d) { return answerQuestion(q, d); })
        .then(function (reply) { addMsg("bot", reply); })
        .catch(function () {
          addMsg(
            "sys",
            lang() === "en"
              ? "Could not load the report knowledge base."
              : "Não foi possível carregar a base dos relatórios.",
          );
        })
        .then(function () {
          pending = false;
          sendBtn.disabled = false;
          input.focus();
        });
    }

    toggle.addEventListener("click", function () {
      setOpen(!root.classList.contains("open"));
    });
    close.addEventListener("click", function () { setOpen(false); });
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      send(input.value);
    });
    document.querySelectorAll("#lang button").forEach(function (b) {
      b.addEventListener("click", function () { setTimeout(applyUiLang, 0); });
    });

    applyUiLang();
    addMsg("bot", lang() === "en" ? HELLO_EN : HELLO_PT);
    // Preload index so first answer is faster
    loadIndex().catch(function () {});
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }
})();
