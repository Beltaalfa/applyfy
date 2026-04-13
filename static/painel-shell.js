/**
 * Sidebar única para todas as páginas do painel Applyfy.
 * body[data-active="/historico"] marca o link ativo (path exato).
 * Com APPLYFY_AUTH_ENABLED, filtra itens conforme /api/me (permissões do hub).
 */
(function () {
  /** Ícones outline 24×24 (stroke), alinhados ao tema do painel */
  function navIconSvg(paths) {
    return (
      '<span class="sidebar-link__icon" aria-hidden="true">' +
      '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">' +
      paths +
      "</svg></span>"
    );
  }
  var ICON = {
    panel:
      '<path d="M3.75 6A2.25 2.25 0 0 1 6 3.75h2.25A2.25 2.25 0 0 1 10.5 6v2.25a2.25 2.25 0 0 1-2.25 2.25H6a2.25 2.25 0 0 1-2.25-2.25V6ZM3.75 15.75A2.25 2.25 0 0 1 6 13.5h2.25a2.25 2.25 0 0 1 2.25 2.25V18a2.25 2.25 0 0 1-2.25 2.25H6A2.25 2.25 0 0 1 3.75 18v-2.25ZM13.5 6a2.25 2.25 0 0 1 2.25-2.25H18A2.25 2.25 0 0 1 20.25 6v2.25A2.25 2.25 0 0 1 18 10.5h-2.25A2.25 2.25 0 0 1 13.5 8.25V6ZM13.5 15.75a2.25 2.25 0 0 1 2.25-2.25H18a2.25 2.25 0 0 1 2.25 2.25V18A2.25 2.25 0 0 1 18 20.25h-2.25A2.25 2.25 0 0 1 13.5 18v-2.25Z" />',
    clock: '<path d="M12 6v6h4.5m7.5.75a9.75 9.75 0 1 1-19.5 0 9.75 9.75 0 0 1 19.5 0Z" />',
    chart:
      '<path d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C19.996 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z" />',
    swap: '<path d="M7.5 21 3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />',
    link:
      '<path d="M13.19 8.688a4.5 4.5 0 0 1 6.364 6.364l-4.5 4.5a4.5 4.5 0 0 1-6.364-6.364l1.757-1.757m10.607 4.243 1.414-1.414m-11.364-5.657-1.414 1.414" />',
    flag: '<path d="M3 3v1.5M3 21v-6m0 0 2.77-.693a9 9 0 0 1 6.208.682l2.772 1.004a.75.75 0 0 0 1.073-.67V4.506a.75.75 0 0 0-1.076-.67l-2.772 1.004a9 9 0 0 1-6.208.682L3 4.5V21Z" />',
    briefcase:
      '<path d="M20.25 7.5h-.625a2.25 2.25 0 0 0-2.247-2.118H6.622a2.25 2.25 0 0 0-2.247 2.118L3.75 7.5M20.25 7.5v10.125a2.25 2.25 0 0 1-2.25 2.25H6.25a2.25 2.25 0 0 1-2.25-2.25V7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125Z" />',
    search:
      '<path d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />',
    wallet:
      '<path d="M21 12a2.25 2.25 0 0 0-2.25-2.25H15a3 3 0 1 1-6 0H5.25A2.25 2.25 0 0 0 3 12m18 0v6a2.25 2.25 0 0 1-2.25 2.25H5.25A2.25 2.25 0 0 1 3 18v-6m18 0V9M3 12V9m18 3V9m0 0h-1.5M3 12H4.5M3 9V6.75A2.25 2.25 0 0 1 5.25 4.5h13.5A2.25 2.25 0 0 1 21 6.75V9" />',
    percent:
      '<path d="M7.5 9a2.25 2.25 0 1 0 0-4.5 2.25 2.25 0 0 0 0 4.5Zm9 9a2.25 2.25 0 1 0 0-4.5 2.25 2.25 0 0 0 0 4.5ZM18 6 6 18" />',
    pie:
      '<path d="M10.5 6a7.5 7.5 0 1 0 7.5 7.5h-7.5v-7.5ZM13.5 10.5H21a7.5 7.5 0 0 0-7.5-7.5v7.5Z" />',
    doc:
      '<path d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />',
    lock:
      '<path d="M16.5 10.5V6.75a4.5 4.5 0 1 0-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 0 0 2.25-2.25v-6.75a2.25 2.25 0 0 0-2.25-2.25H6.75a2.25 2.25 0 0 0-2.25 2.25v6.75a2.25 2.25 0 0 0 2.25 2.25Z" />',
    logout:
      '<path d="M15.75 9V5.25A2.25 2.25 0 0 0 13.5 3h-6a2.25 2.25 0 0 0-2.25 2.25v13.5A2.25 2.25 0 0 0 7.5 21h6a2.25 2.25 0 0 0 2.25-2.25V15M12 9l3 3m0 0-3 3m3-3H2.25" />',
  };
  var ICON_BY_HREF = {
    "/": ICON.panel,
    "/dashboard": ICON.chart,
    "/historico": ICON.clock,
    "/evolucao": ICON.chart,
    "/transacoes": ICON.swap,
    "/meta": ICON.flag,
    "/comercial": ICON.briefcase,
    "/produtores": ICON.search,
    "/saldo": ICON.wallet,
    "/taxas": ICON.percent,
    "/financeiro": ICON.pie,
    "/log": ICON.doc,
    "/permissoes": ICON.lock,
  };
  function sidebarIconForHref(href) {
    var p = ICON_BY_HREF[href] || ICON.panel;
    return navIconSvg(p);
  }
  function logoutIcon() {
    return navIconSvg(ICON.logout);
  }

  var NAV = [
    { href: "/", label: "Painel" },
    { href: "/dashboard", label: "Dashboard" },
    { href: "/historico", label: "Histórico" },
    { href: "/evolucao", label: "Evolução" },
    { href: "/transacoes", label: "Transações" },
    { href: "/meta", label: "Meta" },
    { href: "/comercial", label: "Comercial" },
    { href: "/produtores", label: "Consultar produtores" },
    { href: "/saldo", label: "Saldo" },
    { href: "/taxas", label: "Taxas" },
    { href: "/financeiro", label: "Financeiro" },
    { href: "/log", label: "Log saldos" },
    { href: "/permissoes", label: "Permissões" },
  ];

  function normalizePath(path) {
    if (!path) return "/";
    var p = path.split("?")[0];
    if (p.length > 1 && p.endsWith("/")) p = p.slice(0, -1);
    if (p === "/vendas.html" || p.endsWith("/vendas.html")) return "/vendas";
    if (p === "/evolucao.html" || p.endsWith("/evolucao.html")) return "/evolucao";
    if (p === "/dashboard.html" || p.endsWith("/dashboard.html")) return "/dashboard";
    if (p === "/index.html" || p.endsWith("/index.html")) return "/";
    return p;
  }

  function currentActive() {
    var body = document.body;
    var fromData = body.getAttribute("data-active");
    if (fromData) return normalizePath(fromData);
    return normalizePath(window.location.pathname);
  }

  function filterNavForHub(me, items) {
    if (!me || !me.auth_enabled) return items.slice();
    var vis = me.nav || {};
    return items.filter(function (item) {
      return vis[item.href] !== false;
    });
  }

  /**
   * 1) Mesmo origin + `/auth/logout` — Flask limpa sessão e redirecciona ao Hub.
   * 2) Fallback: Hub `/logout` directo (JWT/NextAuth) se a rota Flask não for atingível.
   */
  function resolveLogoutActionUrl(me) {
    try {
      var same = new URL("/auth/logout", window.location.origin).href;
      if (same) return same;
    } catch (e) {}
    if (me && me.hub_logout_url && typeof me.hub_logout_url === "string") {
      var u = me.hub_logout_url.trim();
      if (/^https?:\/\//i.test(u)) return u;
    }
    try {
      var host = window.location.hostname;
      var parts = host.split(".");
      if (parts.length < 2) return "/auth/logout";
      var rest = parts.slice(1).join(".");
      return window.location.protocol + "//hub." + rest + "/logout";
    } catch (e2) {
      return "/auth/logout";
    }
  }

  function escapeFormAction(url) {
    return String(url).replace(/&/g, "&amp;").replace(/"/g, "&quot;");
  }

  function renderSidebar(host, items, me) {
    var active = currentActive();
    var links = items.map(function (item) {
      var href = item.href;
      var isActive = active === href || (active === "" && href === "/");
      var cls = "sidebar-link" + (isActive ? " is-active" : "");
      return (
        '<a class="' + cls + '" href="' + href + '">' + sidebarIconForHref(href) + '<span class="sidebar-link__text">' + item.label + "</span></a>"
      );
    }).join("");
    /**
     * GET directo para Hub `/logout` (mesma raiz DNS que applyfy.* → hub.*).
     * target=_top evita iframe; fallback Flask `/auth/logout` se não der para derivar URL.
     */
    var logout = "";
    if (me && me.auth_enabled && me.authenticated) {
      var la = resolveLogoutActionUrl(me);
      logout =
        '<form class="sidebar-footer" method="get" action="' +
        escapeFormAction(la) +
        '" target="_top" aria-label="Terminar sessão">' +
        '<button type="submit" class="sidebar-link sidebar-link--logout">' +
        logoutIcon() +
        '<span class="sidebar-link__text">Sair</span></button></form>';
    }
    host.innerHTML =
      '<div class="sidebar-brand"><a href="/" class="sidebar-brand__link" aria-label="Applyfy — início"><img src="/static/logo/app.applyfy.com.png?v=1" alt="Applyfy" class="sidebar-brand__img" decoding="async" /></a></div><nav class="sidebar-nav" aria-label="Principal">' +
      links +
      "</nav>" +
      logout;
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

  function bindNavHandlers() {
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

  function init() {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.getRegistrations().then(function (rs) {
        rs.forEach(function (r) {
          r.unregister();
        });
      });
    }
    var host = document.getElementById("painel-sidebar");
    if (!host) return;
    renderSidebar(host, NAV, null);
    fetch("/api/me", { credentials: "same-origin" })
      .then(function (r) {
        var st = r.status;
        return r.json().then(function (j) {
          return { status: st, me: j };
        });
      })
      .catch(function () {
        return { status: 0, me: { auth_enabled: false } };
      })
      .then(function (pack) {
        var me = pack.me;
        var items = filterNavForHub(me, NAV);
        /** Sempre aplicar `me` após /api/me (o primeiro paint usa me=null; evita deixar o menu desatualizado relativamente ao servidor). */
        renderSidebar(host, items, me);
        bindNavHandlers();
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
