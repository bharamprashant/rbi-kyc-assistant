(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
  function link(href, text) {
    var a = el("a", null, text); if (/^https:\/\/(www\.)?rbi\.org\.in\//i.test(href)) { a.href = href; a.rel = "noopener noreferrer"; a.target = "_blank"; } return a;
  }
  function show(tab) {
    $("ask").hidden = tab !== "ask"; $("changes").hidden = tab !== "changes";
    $("tab-ask").setAttribute("aria-selected", tab === "ask"); $("tab-changes").setAttribute("aria-selected", tab === "changes");
    if (tab === "changes") loadChanges();
  }
  $("tab-ask").onclick = function () { show("ask"); }; $("tab-changes").onclick = function () { show("changes"); };

  function card(r) {
    var c = el("div", "card");
    var h = el("div", "meta", r.doc_title + " · paragraph " + r.para_no + (r.section ? " · " + r.section : ""));
    c.appendChild(h);
    var meta = el("div", "meta", "Version: " + (r.version || "n/a") + " · Last amended: " + (r.last_amended || (r.change_dates && r.change_dates.length ? r.change_dates[r.change_dates.length - 1] : "no recorded amendment")) + " ");
    meta.appendChild(el("span", "tag" + (r.status === "historical" ? " hist" : ""), r.status === "historical" ? "historical (repealed)" : "current"));
    c.appendChild(meta); c.appendChild(el("pre", null, r.text));
    (r.amendments || []).forEach(function (a) { var d = el("div", "meta", a.kind + ": " + a.instrument + " "); if (a.url) d.appendChild(link(a.url, "[RBI circular]")); c.appendChild(d); });
    var src = el("div", "meta", "Source: "); src.appendChild(link(r.source_url, "RBI page")); c.appendChild(src);
    return c;
  }
  $("f").onsubmit = function (ev) {
    ev.preventDefault(); var out = $("out"); out.textContent = "Searching…";
    fetch("/api/ask", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: $("q").value, entity: $("entity").value || null, include_historical: $("hist").checked }) })
      .then(function (r) { return r.json().then(function (j) { return { s: r.status, j: j }; }); })
      .then(function (x) {
        out.textContent = "";
        if (x.s !== 200) { out.appendChild(el("p", null, x.j.error || "Something went wrong.")); return; }
        var j = x.j;
        if (j.status !== "answered") { out.appendChild(el("p", null, j.reason)); out.appendChild(el("p", "meta", j.disclaimer)); return; }
        if (j.summary) out.appendChild(el("p", null, "AI summary (check against the RBI text below): " + j.summary));
        out.appendChild(el("p", null, j.answer));
        out.appendChild(el("h2", null, "RBI text"));
        j.results.forEach(function (r) { out.appendChild(card(r)); });
        out.appendChild(el("p", "meta", j.disclaimer));
      }).catch(function () { out.textContent = "Network error. Please try again."; });
  };
  function loadChanges() {
    var box = $("chg"); box.textContent = "Loading…";
    fetch("/api/changes?include_historical=true").then(function (r) { return r.json(); }).then(function (j) {
      box.textContent = "";
      (j.changes || []).forEach(function (c) {
        var d = el("div", "card"); d.appendChild(el("strong", null, c.date + " · " + c.doc_title));
        d.appendChild(el("div", "meta", (c.status === "historical" ? "Historical (repealed 2016 Direction)" : "Current") + " · paragraphs: " + c.paragraphs.map(function (p) { return p.para_no + " (" + p.kind + ")"; }).join(", ")));
        c.instruments.forEach(function (i) { d.appendChild(el("div", "meta", i)); }); box.appendChild(d);
      });
    }).catch(function () { box.textContent = "Could not load changes."; });
  }
})();
