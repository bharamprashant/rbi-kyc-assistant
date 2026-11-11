(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
  function link(href, text) {
    var a = el("a", null, text);
    if (/^https:\/\/(www\.)?rbi\.org\.in\//i.test(href)) { a.href = href; a.rel = "noopener noreferrer"; a.target = "_blank"; }
    return a;
  }
  function show(tab) {
    $("ask").hidden = tab !== "ask"; $("changes").hidden = tab !== "changes";
    $("tab-ask").setAttribute("aria-selected", String(tab === "ask")); $("tab-changes").setAttribute("aria-selected", String(tab === "changes"));
    if (tab === "changes") loadChanges();
  }
  $("tab-ask").onclick = function () { show("ask"); };
  $("tab-changes").onclick = function () { show("changes"); };
  function entity() { var r = document.querySelector('input[name="ent"]:checked'); return r ? r.value : ""; }

  function rbiCard(r) {
    var c = el("div", "card");
    var top = el("div", "meta");
    top.appendChild(el("span", "pill " + (r.status === "historical" ? "hist" : "cur"), r.status === "historical" ? "historical (repealed)" : "current"));
    top.appendChild(document.createTextNode(r.doc_title + " · paragraph " + r.para_no + (r.section ? " · " + r.section : "")));
    c.appendChild(top);
    c.appendChild(el("pre", "quote", r.text));
    var last = r.last_amended || (r.change_dates && r.change_dates.length ? r.change_dates[r.change_dates.length - 1] : "no recorded amendment");
    var m = el("div", "meta", "Version: " + (r.version || "n/a") + " · Last amended: " + last + " · ");
    m.appendChild(link(r.source_url, "RBI source"));
    c.appendChild(m);
    return c;
  }
  function keyPoint(p) {
    var c = el("div", "card");
    c.appendChild(el("div", "meta", p.reference));
    c.appendChild(el("pre", "quote", p.text));
    var m = el("div", "meta", "Version: " + (p.version || "n/a") + " · Last amended: " + (p.last_amended || "none recorded") + " · ");
    m.appendChild(link(p.source_url, "RBI source")); c.appendChild(m);
    return c;
  }
  function renderDetail(out, d) {
    out.appendChild(el("h2", null, "What RBI says"));
    d.key_points.forEach(function (p) { out.appendChild(keyPoint(p)); });
    var box = el("div", "changed" + (d.what_changed.length ? "" : " none"));
    box.appendChild(el("h3", null, "What changed"));
    if (d.what_changed.length) {
      var ul = el("ul");
      d.what_changed.forEach(function (a) {
        var li = el("li", null, a.date + " · " + a.kind + " (paragraph " + a.paragraph + "): " + a.instrument + " ");
        if (a.url) li.appendChild(link(a.url, "[RBI circular]")); ul.appendChild(li);
      });
      box.appendChild(ul);
    } else { box.appendChild(el("div", null, d.what_changed_note)); }
    out.appendChild(box);
    if (d.earlier_position) {
      var e = el("div", "earlier"); e.appendChild(el("h3", null, "Earlier position (history only)"));
      e.appendChild(el("div", "meta", d.earlier_position.note));
      e.appendChild(el("div", "meta", d.earlier_position.reference + (d.earlier_position.amended_on && d.earlier_position.amended_on.length ? " · amended on " + d.earlier_position.amended_on.join(", ") : "")));
      e.appendChild(el("pre", "quote", d.earlier_position.text));
      var l = el("div", "meta"); l.appendChild(link(d.earlier_position.source_url, "RBI source (2016 Direction)")); e.appendChild(l);
      out.appendChild(e);
    }
  }
  function sendFeedback(ctx, verdict, comment, done) {
    fetch("/api/feedback", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: ctx.question, entity: ctx.entity || null, verdict: verdict, comment: comment || "", shown: ctx.shown, status: ctx.status }) })
      .then(function (r) { return r.json().then(function (j) { done(r.status === 200, j); }); })
      .catch(function () { done(false, { error: "Network error. Please try again." }); });
  }
  function feedbackBox(ctx) {
    var box = el("div", "card feedback");
    box.appendChild(el("strong", null, "Was this answer right?"));
    var row = el("div", "chips");
    var up = el("button", "chip", "\uD83D\uDC4D Helpful"); up.type = "button";
    var down = el("button", "chip", "\uD83D\uDC4E Not correct / not what I expected"); down.type = "button";
    row.appendChild(up); row.appendChild(down); box.appendChild(row);
    var msg = el("p", "meta"); box.appendChild(msg);
    function finish(ok, j) { msg.textContent = ok ? "Thank you. Your feedback helps us improve the answers." : (j && j.error) || "Could not send feedback."; if (ok) { row.hidden = true; var f = box.querySelector("form"); if (f) f.hidden = true; } }
    up.onclick = function () { up.disabled = true; sendFeedback(ctx, "helpful", "", finish); };
    down.onclick = function () {
      if (box.querySelector("form")) return;
      var f = el("form"); var ta = el("textarea"); ta.maxLength = 500; ta.rows = 3; ta.setAttribute("aria-label", "What did you expect?");
      ta.placeholder = "What did you expect, or what is wrong? (optional, please don't include personal data)";
      f.appendChild(ta);
      f.appendChild(el("p", "meta", "This sends your question and this note to the site owner so the assistant can be improved. Nothing else about you is collected."));
      var b = el("button", "chip", "Send feedback"); b.type = "submit"; f.appendChild(b);
      f.onsubmit = function (ev) { ev.preventDefault(); b.disabled = true; sendFeedback(ctx, "incorrect", ta.value, function (ok, j) { if (!ok) b.disabled = false; finish(ok, j); }); };
      box.appendChild(f); ta.focus();
    };
    return box;
  }
  function ask(question, ent, hist) {
    var out = $("out"); out.textContent = "Searching…";
    fetch("/api/ask", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: question, entity: ent || null, include_historical: !!hist }) })
      .then(function (r) { return r.json().then(function (j) { return { s: r.status, j: j }; }); })
      .then(function (x) {
        out.textContent = "";
        if (x.s !== 200) { out.appendChild(el("p", null, x.j.error || "Something went wrong.")); return; }
        var j = x.j;
        if (j.status !== "answered") {
          var n = el("div", "card"); n.appendChild(el("p", null, j.reason));
          if (j.suggestions && j.suggestions.length) {
            n.appendChild(el("p", "meta", "Did you mean one of these?"));
            var sc = el("div", "chips"); j.suggestions.forEach(function (q) { sc.appendChild(chip(q, null, "", "")); }); n.appendChild(sc);
          }
          n.appendChild(el("p", "meta", j.disclaimer)); out.appendChild(n);
          out.appendChild(feedbackBox({ question: question, entity: ent, status: j.status, shown: [] })); return;
        }
        var a = el("div", "card answer");
        if (j.summary) a.appendChild(el("p", "meta", "AI summary (check against the RBI text below): " + j.summary));
        a.appendChild(el("p", null, j.answer)); out.appendChild(a);
        if (j.clarify) {
          var cb = el("div", "card"); cb.appendChild(el("p", null, j.clarify.prompt));
          var cc = el("div", "chips"); j.clarify.options.forEach(function (o) { cc.appendChild(chip(o.question, null, "", "")); }); cb.appendChild(cc); out.appendChild(cb);
        }
        if (j.detail) renderDetail(out, j.detail);
        var det = el("details"); det.appendChild(el("summary", null, "All matching RBI passages (" + j.results.length + ")"));
        j.results.forEach(function (r) { det.appendChild(rbiCard(r)); }); out.appendChild(det);
        out.appendChild(el("p", "meta", j.disclaimer));
        out.appendChild(feedbackBox({ question: question, entity: ent, status: j.status, shown: j.results.slice(0, 5).map(function (r) { return String(r.para_no); }) }));
        out.scrollIntoView({ behavior: "smooth", block: "start" });
      }).catch(function () { out.textContent = "Network error. Please try again."; });
  }
  $("f").onsubmit = function (ev) { ev.preventDefault(); ask($("q").value, entity(), $("hist").checked); };

  function chip(q, ent, cls, badge) {
    var b = el("button", "chip" + (cls ? " " + cls : ""), q); b.type = "button";
    if (badge) b.appendChild(el("span", "upd", badge));
    b.onclick = function () {
      $("q").value = q; if (ent) { var r = document.getElementById(ent === "nbfc" ? "e-nbfc" : "e-cb"); if (r) r.checked = true; }
      ask(q, ent || entity(), $("hist").checked);
    };
    return b;
  }
  function loadFaqs() {
    fetch("/api/faqs").then(function (r) { return r.json(); }).then(function (j) {
      var nw = j.whats_new || [];
      if (nw.length) { $("new-box").hidden = false; nw.forEach(function (w) { $("new").appendChild(chip(w.q, w.entity, "new", w.kind)); }); }
      var root = $("topics");
      (j.topics || []).forEach(function (t, i) {
        var d = el("details"); if (i === 0) d.open = true;
        d.appendChild(el("summary", null, t.title + " (" + t.items.length + ")"));
        var c = el("div", "chips");
        t.items.forEach(function (it) { c.appendChild(chip(it.q, null, "", it.amended ? "amended" : "")); });
        d.appendChild(c); root.appendChild(d);
      });
    }).catch(function () { $("topics").textContent = "Could not load suggested questions."; });
  }
  function loadChanges() {
    var box = $("chg"); box.textContent = "Loading…";
    fetch("/api/changes?include_historical=true").then(function (r) { return r.json(); }).then(function (j) {
      box.textContent = "";
      (j.changes || []).forEach(function (c) {
        var d = el("div", "card"); d.appendChild(el("strong", null, c.date + " · " + c.doc_title));
        var m = el("div", "meta");
        m.appendChild(el("span", "pill " + (c.status === "historical" ? "hist" : "cur"), c.status === "historical" ? "historical (repealed 2016 Direction)" : "current"));
        m.appendChild(document.createTextNode("paragraphs: " + c.paragraphs.map(function (p) { return p.para_no + " (" + p.kind + ")"; }).join(", ")));
        d.appendChild(m);
        c.instruments.forEach(function (i) { d.appendChild(el("div", "meta", i)); }); box.appendChild(d);
      });
    }).catch(function () { box.textContent = "Could not load changes."; });
  }
  loadFaqs();
})();
