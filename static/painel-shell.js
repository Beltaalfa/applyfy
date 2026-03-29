/**
 * Sidebar única para todas as páginas do painel Applyfy.
 * body[data-active="/historico"] marca o link ativo (path exato).
 */
(function () {
  var NAV = [
    { href: "/", label: "Painel" },
    { href: "/historico", label: "Histórico" },
    { href: "/evolucao", label: "Evolução" },
    { href: "/vendas", label: "Vendas" },
    { href: "/log-vendas", label: "Log vendas" },
    { href: "/transacoes", label: "Transações" },
    { href: "/integracoes", label: "Integrações" },
    { href: "/meta", label: "Meta" },
    { href: "/produtores", label: "Produtores" },
    { href: "/financeiro", label: "Financeiro" },
    { href: "/log", label: "Log saldos" },
  ];

  function normalizePath(path) {
    if (!path) return "/";
    var p = path.split("?")[0];
    if (p === "/log-vendas.html" || p.endsWith("/log-vendas.html")) return "/log-vendas";
    return p;
  }

  function currentActive() {
    var body = document.body;
    var fromData = body.getAttribute("data-active");
    if (fromData) return normalizePath(fromData);
    return normalizePath(window.location.pathname);
  }

  function renderSidebar(host) {
    var active = currentActive();
    var links = NAV.map(function (item) {
      var href = item.href;
      var isActive = active === href || (active === "" && href === "/");
      var cls = "sidebar-link" + (isActive ? " is-active" : "");
      return '<a class="' + cls + '" href="' + href + '">' + item.label + "</a>";
    }).join("");
    host.innerHTML =
      '<div class="sidebar-brand">Apply<span>fy</span></div><nav class="sidebar-nav" aria-label="Principal">' +
      links +
      "</nav>";
  }

  function closeNav() {
    var shell = document.getElementById("app-shell");
    if (shell) shell.classList.remove("nav-open");
    var ov = document.getElementById("sidebar-overlay");
    if (ov) ov.hidden = true;
    document.body.style.overflow = "";
  }

  function openNav() {
    var shell = document.getElementById("app-shell");
    if (shell) shell.classList.add("nav-open");
    var ov = document.getElementById("sidebar-overlay");
    if (ov) ov.hidden = false;
    document.body.style.overflow = "hidden";
  }

  function init() {
    var host = document.getElementById("painel-sidebar");
    if (host) renderSidebar(host);

    var toggle = document.getElementById("sidebar-toggle");
    var overlay = document.getElementById("sidebar-overlay");
    if (toggle) {
      toggle.addEventListener("click", function () {
        var shell = document.getElementById("app-shell");
        if (shell && shell.classList.contains("nav-open")) closeNav();
        else openNav();
      });
    }
    if (overlay) {
      overlay.addEventListener("click", closeNav);
    }
    document.querySelectorAll(".sidebar-link").forEach(function (a) {
      a.addEventListener("click", function () {
        if (window.matchMedia("(max-width: 1023px)").matches) closeNav();
      });
    });
    window.addEventListener("resize", function () {
      if (window.matchMedia("(min-width: 1024px)").matches) closeNav();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
