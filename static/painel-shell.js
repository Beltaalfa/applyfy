/**
 * Sidebar única para todas as páginas do painel Applyfy.
 * body[data-active="/historico"] marca o link ativo (path exato).
 * Com APPLYFY_AUTH_ENABLED, filtra itens conforme /api/me (permissões do hub).
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
    { href: "/comercial", label: "Comercial" },
    { href: "/produtores", label: "Produtores" },
    { href: "/financeiro", label: "Financeiro" },
    { href: "/log", label: "Log saldos" },
  ];

  function normalizePath(path) {
    if (!path) return "/";
    var p = path.split("?")[0];
    if (p.length > 1 && p.endsWith("/")) p = p.slice(0, -1);
    if (p === "/log-vendas.html" || p.endsWith("/log-vendas.html")) return "/log-vendas";
    if (p === "/evolucao.html" || p.endsWith("/evolucao.html")) return "/evolucao";
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

  function navEqual(a, b) {
    if (a.length !== b.length) return false;
    for (var i = 0; i < a.length; i++) {
      if (a[i].href !== b[i].href) return false;
    }
    return true;
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
      return '<a class="' + cls + '" href="' + href + '">' + item.label + "</a>";
    }).join("");
    /**
     * GET directo para Hub `/logout` (mesma raiz DNS que applyfy.* → hub.*).
     * target=_top evita iframe; fallback Flask `/auth/logout` se não der para derivar URL.
     */
    var logout = "";
    if (me && me.auth_enabled && me.authenticated) {
      var la = resolveLogoutActionUrl(me);
      // #region agent log
      fetch("/api/_debug/client-log", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({
          sessionId: "422278",
          location: "painel-shell.js:renderSidebar",
          message: "logout_form_built",
          data: { logoutAction: la, auth_enabled: !!me.auth_enabled, authenticated: !!me.authenticated },
          timestamp: Date.now(),
          hypothesisId: "H1",
          runId: "pre-fix",
        }),
      }).catch(function () {});
      // #endregion
      logout =
        '<form class="sidebar-footer" method="get" action="' +
        escapeFormAction(la) +
        '" target="_top" aria-label="Terminar sessão">' +
        '<button type="submit" class="sidebar-link sidebar-link--logout">Sair</button></form>';
    }
    host.innerHTML =
      '<div class="sidebar-brand">Apply<span>fy</span></div><nav class="sidebar-nav" aria-label="Principal">' +
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
    // #region agent log
    document.addEventListener(
      "submit",
      function (ev) {
        var t = ev.target;
        if (t && t.classList && t.classList.contains("sidebar-footer")) {
          fetch("/api/_debug/client-log", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "same-origin",
            body: JSON.stringify({
              sessionId: "422278",
              location: "painel-shell.js:submit_capture",
              message: "sidebar_logout_submit",
              data: {
                action: t.action || "",
                method: (t.method || "").toLowerCase(),
                defaultPrevented: !!ev.defaultPrevented,
              },
              timestamp: Date.now(),
              hypothesisId: "H3",
              runId: "pre-fix",
            }),
          }).catch(function () {});
        }
      },
      true
    );
    // #endregion
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
        var ne = !navEqual(NAV, items);
        var authed = !!(me && me.auth_enabled && me.authenticated);
        var shouldRender = ne || authed;
        // #region agent log
        fetch("/api/_debug/client-log", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "same-origin",
          body: JSON.stringify({
            sessionId: "422278",
            location: "painel-shell.js:api_me_then",
            message: "me_loaded",
            data: {
              apiStatus: pack.status,
              shouldRender: shouldRender,
              navChanged: ne,
              authed: authed,
              auth_enabled: me && me.auth_enabled,
              authenticated: me && me.authenticated,
            },
            timestamp: Date.now(),
            hypothesisId: "H2",
            runId: "post-fix",
          }),
        }).catch(function () {});
        // #endregion
        /** Sempre aplicar `me` após /api/me (o primeiro paint usa me=null; evita deixar o menu desactualizado relativamente ao servidor). */
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
