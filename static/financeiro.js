(function () {
  "use strict";

  var API = {
    categorias: "/api/financeiro/categorias",
    lancamentos: "/api/financeiro/lancamentos",
    fluxo: "/api/financeiro/relatorios/fluxo-caixa",
    dre: "/api/financeiro/relatorios/dre",
    dfc: "/api/financeiro/relatorios/dfc"
  };

  function qs(sel, el) { return (el || document).querySelector(sel); }
  function qsAll(sel, el) { return (el || document).querySelectorAll(sel); }

  function showTab(name) {
    qsAll(".tab-panel").forEach(function (p) { p.classList.remove("active"); });
    qsAll(".tabs button").forEach(function (b) { b.classList.remove("active"); });
    var panel = qs("#panel-" + name);
    var btn = qs('.tabs button[data-tab="' + name + '"]');
    if (panel) panel.classList.add("active");
    if (btn) btn.classList.add("active");
    if (name === "categorias") loadCategorias();
    if (name === "lancamentos") { fillCategoriaSelects(); loadLancamentos(); }
    if (name === "relatorios") loadRelatorios();
  }

  function params(obj) {
    var parts = [];
    for (var k in obj) if (obj[k] !== "" && obj[k] != null) parts.push(encodeURIComponent(k) + "=" + encodeURIComponent(obj[k]));
    return parts.length ? "?" + parts.join("&") : "";
  }

  // --- Categorias ---
  function loadCategorias() {
    var tbody = qs("#tbodyCategorias");
    tbody.innerHTML = "<tr><td colspan=\"4\" class=\"empty\">Carregando…</td></tr>";
    fetch(API.categorias).then(function (r) { return r.json(); }).then(function (data) {
      var list = data.categorias || data || [];
      if (!list.length) {
        tbody.innerHTML = "<tr><td colspan=\"4\" class=\"empty\">Nenhuma categoria. Crie uma acima.</td></tr>";
        return;
      }
      tbody.innerHTML = list.map(function (c) {
        var nome = (c.nome || "").replace(/</g, "&lt;").replace(/"/g, "&quot;");
        var ativa = c.ativa === false ? "Nao" : "Sim";
        return "<tr><td>" + nome + "</td><td>" + (c.tipo || "") + "</td><td>" + ativa + "</td><td><button type=\"button\" class=\"btn btn-secondary btn-edit-cat\" data-id=\"" + c.id + "\">Editar</button> <button type=\"button\" class=\"btn btn-danger btn-del-cat\" data-id=\"" + c.id + "\">Excluir</button></td></tr>";
      }).join("");
      tbody.querySelectorAll(".btn-edit-cat").forEach(function (b) {
        b.addEventListener("click", function () { editCategoria(Number(this.getAttribute("data-id"))); });
      });
      tbody.querySelectorAll(".btn-del-cat").forEach(function (b) {
        b.addEventListener("click", function () { if (confirm("Excluir esta categoria?")) deleteCategoria(Number(this.getAttribute("data-id"))); });
      });
    }).catch(function (e) {
      tbody.innerHTML = "<tr><td colspan=\"4\" class=\"empty\">Erro: " + (e.message || "falha") + "</td></tr>";
    });
  }

  function editCategoria(id) {
    fetch(API.categorias + "/" + id).then(function (r) { return r.json(); }).then(function (c) {
      qs("#catId").value = c.id;
      qs("#catNome").value = c.nome || "";
      qs("#catTipo").value = (c.tipo || "receita") === "receita" ? "receita" : "despesa";
      qs("#btnCancelarCategoria").style.display = "inline-block";
    }).catch(function () {});
  }

  function deleteCategoria(id) {
    fetch(API.categorias + "/" + id, { method: "DELETE" }).then(function () { loadCategorias(); }).catch(function () {});
  }

  function fillCategoriaSelects() {
    fetch(API.categorias).then(function (r) { return r.json(); }).then(function (data) {
      var list = data.categorias || data || [];
      var opts = "<option value=\"\">— Categoria —</option>" + list.map(function (c) { return "<option value=\"" + c.id + "\">" + (c.nome || "") + " (" + (c.tipo || "") + ")</option>"; }).join("");
      ["lancCategoria", "lancCategoriaForm"].forEach(function (id) {
        var sel = qs("#" + id);
        if (sel) { sel.innerHTML = opts; }
      });
    }).catch(function () {});
  }

  qs(".tabs").addEventListener("click", function (e) {
    var t = e.target.getAttribute("data-tab");
    if (t) showTab(t);
  });

  qs("#btnSalvarCategoria").addEventListener("click", function () {
    var id = qs("#catId").value;
    var nome = (qs("#catNome").value || "").trim();
    var tipo = (qs("#catTipo").value || "receita").toLowerCase();
    if (!nome) return;
    if (id) {
      fetch(API.categorias + "/" + id, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nome: nome, tipo: tipo })
      }).then(function () { qs("#catId").value = ""; qs("#catNome").value = ""; qs("#btnCancelarCategoria").style.display = "none"; loadCategorias(); }).catch(function () {});
    } else {
      fetch(API.categorias, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nome: nome, tipo: tipo })
      }).then(function () { qs("#catNome").value = ""; loadCategorias(); }).catch(function () {});
    }
  });
  qs("#btnCancelarCategoria").addEventListener("click", function () {
    qs("#catId").value = ""; qs("#catNome").value = ""; this.style.display = "none";
  });

  // --- Lancamentos ---
  function getLancFiltros() {
    return {
      date_from: qs("#lancDateFrom").value || undefined,
      date_to: qs("#lancDateTo").value || undefined,
      mes: qs("#lancMes").value || undefined,
      ano: qs("#lancAno").value || undefined,
      tipo: qs("#lancTipo").value || undefined,
      categoria_id: qs("#lancCategoria").value || undefined
    };
  }

  function loadLancamentos() {
    var tbody = qs("#tbodyLancamentos");
    var q = params(getLancFiltros());
    tbody.innerHTML = "<tr><td colspan=\"6\" class=\"empty\">Carregando…</td></tr>";
    fetch(API.lancamentos + q).then(function (r) { return r.json(); }).then(function (data) {
      var list = data.lancamentos || [];
      if (!list.length) {
        tbody.innerHTML = "<tr><td colspan=\"6\" class=\"empty\">Nenhum lancamento no periodo. Use Novo lancamento ou altere os filtros.</td></tr>";
        return;
      }
      tbody.innerHTML = list.map(function (l) {
        var dataStr = l.data || "";
        var valor = Number(l.valor);
        var tipo = l.tipo || "";
        var cat = l.categoria_nome || "—";
        var desc = (l.descricao || "").replace(/</g, "&lt;").substring(0, 40);
        return "<tr><td>" + dataStr + "</td><td class=\"num\">" + valor.toFixed(2) + "</td><td>" + tipo + "</td><td>" + cat + "</td><td>" + desc + "</td><td><button type=\"button\" class=\"btn btn-secondary btn-edit-lanc\" data-id=\"" + l.id + "\">Editar</button> <button type=\"button\" class=\"btn btn-danger btn-del-lanc\" data-id=\"" + l.id + "\">Excluir</button></td></tr>";
      }).join("");
      tbody.querySelectorAll(".btn-edit-lanc").forEach(function (b) {
        b.addEventListener("click", function () { editLancamento(Number(this.getAttribute("data-id"))); });
      });
      tbody.querySelectorAll(".btn-del-lanc").forEach(function (b) {
        b.addEventListener("click", function () { if (confirm("Excluir este lancamento?")) deleteLancamento(Number(this.getAttribute("data-id"))); });
      });
    }).catch(function (e) {
      tbody.innerHTML = "<tr><td colspan=\"6\" class=\"empty\">Erro: " + (e.message || "falha") + "</td></tr>";
    });
  }

  function editLancamento(id) {
    fetch(API.lancamentos + "/" + id).then(function (r) { return r.json(); }).then(function (l) {
      qs("#lancId").value = l.id;
      qs("#lancData").value = l.data || "";
      qs("#lancValor").value = l.valor;
      qs("#lancTipoForm").value = (l.tipo || "receita") === "receita" ? "receita" : "despesa";
      qs("#lancCategoriaForm").value = l.categoria_id || "";
      qs("#lancDescricao").value = l.descricao || "";
      qs("#formLancamento").style.display = "flex";
    }).catch(function () {});
  }

  function deleteLancamento(id) {
    fetch(API.lancamentos + "/" + id, { method: "DELETE" }).then(function () { qs("#formLancamento").style.display = "none"; loadLancamentos(); }).catch(function () {});
  }

  qs("#btnFiltroLanc").addEventListener("click", loadLancamentos);
  qs("#btnNovoLanc").addEventListener("click", function () {
    qs("#lancId").value = "";
    qs("#lancData").value = new Date().toISOString().slice(0, 10);
    qs("#lancValor").value = "";
    qs("#lancTipoForm").value = "receita";
    qs("#lancCategoriaForm").value = "";
    qs("#lancDescricao").value = "";
    qs("#formLancamento").style.display = "flex";
  });
  qs("#btnCancelarLanc").addEventListener("click", function () { qs("#formLancamento").style.display = "none"; });
  qs("#btnSalvarLanc").addEventListener("click", function () {
    var id = qs("#lancId").value;
    var payload = {
      data: qs("#lancData").value,
      valor: parseFloat(qs("#lancValor").value),
      tipo: qs("#lancTipoForm").value,
      categoria_id: qs("#lancCategoriaForm").value || null,
      descricao: qs("#lancDescricao").value || ""
    };
    if (!payload.data || !payload.tipo) return;
    if (id) {
      fetch(API.lancamentos + "/" + id, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) })
        .then(function () { qs("#formLancamento").style.display = "none"; loadLancamentos(); }).catch(function () {});
    } else {
      fetch(API.lancamentos, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) })
        .then(function () { qs("#formLancamento").style.display = "none"; loadLancamentos(); }).catch(function () {});
    }
  });

  // --- Relatorios ---
  function getRelFiltros() {
    return {
      date_from: qs("#relDateFrom").value || undefined,
      date_to: qs("#relDateTo").value || undefined,
      mes: qs("#relMes").value || undefined,
      ano: qs("#relAno").value || undefined
    };
  }

  function loadRelatorios() {
    var q = params(getRelFiltros());
    if (!q) {
      qs("#tbodyFluxo").innerHTML = "<tr><td colspan=\"4\" class=\"empty\">Informe periodo (De/Ate ou Mes/Ano) e clique em Atualizar.</td></tr>";
      qs("#resumoFluxo").textContent = "";
      qs("#tbodyDreReceitas").innerHTML = ""; qs("#tbodyDreDespesas").innerHTML = ""; qs("#resumoDre").textContent = "";
      qs("#tbodyDfc").innerHTML = "<tr><td colspan=\"4\" class=\"empty\">Informe o periodo.</td></tr>";
      return;
    }
    qs("#tbodyFluxo").innerHTML = "<tr><td colspan=\"4\" class=\"empty\">Carregando…</td></tr>";
    fetch(API.fluxo + q).then(function (r) { return r.json(); }).then(function (data) {
      var dias = data.dias || [];
      if (!dias.length) {
        qs("#tbodyFluxo").innerHTML = "<tr><td colspan=\"4\" class=\"empty\">Nenhum dado no periodo.</td></tr>";
      } else {
        qs("#tbodyFluxo").innerHTML = dias.map(function (d) {
          return "<tr><td>" + d.data + "</td><td class=\"num\">" + (d.receitas || 0).toFixed(2) + "</td><td class=\"num\">" + (d.despesas || 0).toFixed(2) + "</td><td class=\"num\">" + (d.saldo || 0).toFixed(2) + "</td></tr>";
        }).join("");
      }
      qs("#resumoFluxo").textContent = "Total receitas: " + (data.total_receitas || 0).toFixed(2) + " | Total despesas: " + (data.total_despesas || 0).toFixed(2) + " | Saldo: " + (data.saldo || 0).toFixed(2);
    }).catch(function () { qs("#tbodyFluxo").innerHTML = "<tr><td colspan=\"4\" class=\"empty\">Erro ao carregar.</td></tr>"; });

    fetch(API.dre + q).then(function (r) { return r.json(); }).then(function (data) {
      var rec = data.receitas || [];
      var des = data.despesas || [];
      qs("#tbodyDreReceitas").innerHTML = rec.length ? rec.map(function (x) { return "<tr><td>" + (x.categoria || "") + "</td><td class=\"num\">" + (x.valor || 0).toFixed(2) + "</td></tr>"; }).join("") : "<tr><td colspan=\"2\" class=\"empty\">Nenhuma receita</td></tr>";
      qs("#tbodyDreDespesas").innerHTML = des.length ? des.map(function (x) { return "<tr><td>" + (x.categoria || "") + "</td><td class=\"num\">" + (x.valor || 0).toFixed(2) + "</td></tr>"; }).join("") : "<tr><td colspan=\"2\" class=\"empty\">Nenhuma despesa</td></tr>";
      qs("#resumoDre").textContent = "Total receitas: " + (data.total_receitas || 0).toFixed(2) + " | Total despesas: " + (data.total_despesas || 0).toFixed(2) + " | Resultado (DRE): " + (data.resultado || 0).toFixed(2);
    }).catch(function () {});

    fetch(API.dfc + q).then(function (r) { return r.json(); }).then(function (data) {
      var nat = ["operacional", "investimento", "financiamento"];
      var labels = { operacional: "Operacional", investimento: "Investimento", financiamento: "Financiamento" };
      qs("#tbodyDfc").innerHTML = nat.map(function (n) {
        var o = data[n] || {};
        return "<tr><td>" + (labels[n] || n) + "</td><td class=\"num\">" + (o.entradas || 0).toFixed(2) + "</td><td class=\"num\">" + (o.saidas || 0).toFixed(2) + "</td><td class=\"num\">" + (o.saldo || 0).toFixed(2) + "</td></tr>";
      }).join("");
    }).catch(function () { qs("#tbodyDfc").innerHTML = "<tr><td colspan=\"4\" class=\"empty\">Erro ao carregar DFC.</td></tr>"; });
  }

  qs("#btnRelatorio").addEventListener("click", loadRelatorios);

  // Inicializacao
  showTab("categorias");
})();
