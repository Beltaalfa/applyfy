/**
 * Exportação CSV/XLSX (vista atual) e helpers compartilhados.
 * XLSX: carrega SheetJS do CDN à primeira utilização.
 */
(function (g) {
  function csvCell(v) {
    if (v == null || v === undefined) return "";
    var s = String(v);
    if (/[\r\n;"]/.test(s)) return '"' + s.replace(/"/g, '""') + '"';
    return s;
  }

  g.ApplyfyTable = {
    /**
     * Primeiro clique numa coluna: números e datas → maior / mais recente primeiro (desc).
     * Texto → A→Z (asc).
     */
    firstSortAsc: function (dataType) {
      var t = String(dataType || "").toLowerCase();
      if (t === "num" || t === "data") return false;
      return true;
    },
    exportCSV: function (headers, rows, filename) {
      var lines = [headers.map(csvCell).join(";")].concat(
        rows.map(function (r) {
          return r.map(csvCell).join(";");
        })
      );
      var blob = new Blob(["\ufeff" + lines.join("\r\n")], { type: "text/csv;charset=utf-8;" });
      var a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = /\.csv$/i.test(filename) ? filename : filename + ".csv";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(a.href);
    },
    exportXLSX: function (headers, rows, filename, sheetName) {
      function write() {
        var XLSX = g.XLSX;
        var aoa = [headers].concat(rows);
        var ws = XLSX.utils.aoa_to_sheet(aoa);
        var wb = XLSX.utils.book_new();
        var sn = (sheetName || "Dados").replace(/[:\\/?*[\]]/g, "_").slice(0, 31) || "Dados";
        XLSX.utils.book_append_sheet(wb, ws, sn);
        var fn = /\.xlsx$/i.test(filename) ? filename : filename + ".xlsx";
        XLSX.writeFile(wb, fn);
      }
      if (g.XLSX) return write();
      var s = document.createElement("script");
      s.src = "https://cdn.sheetjs.com/xlsx-0.20.3/package/dist/xlsx.full.min.js";
      s.async = true;
      s.onload = function () {
        write();
      };
      s.onerror = function () {
        alert("Não foi possível carregar a biblioteca XLSX.");
      };
      document.head.appendChild(s);
    },
  };
})(typeof window !== "undefined" ? window : this);
