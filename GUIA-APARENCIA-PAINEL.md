# Guia de aparência — Painel Construneves (dark)

**Applyfy:** a implementação deste tema no repositório Applyfy está em `static/painel-theme.css` e `static/painel-shell.js` (HTML estático + sidebar, sem Tailwind no build).

Documento de referência visual para replicar o mesmo “look” em outro projeto (Next.js + Tailwind). Pode copiar o arquivo inteiro para o outro repositório.

---

## 1. Princípios

- **Tema:** escuro contínuo (fundo preto / zinc-950), sem modo claro.
- **Contraste:** texto principal claro (`zinc-50`–`zinc-100`), secundário `zinc-400`–`zinc-500`, bordas discretas `zinc-700`–`zinc-800`.
- **Acento:** ciano/azul para destaques e dados; vermelho/âmbar para alertas e KPIs semânticos.
- **Forma:** cantos arredondados (`rounded-lg` / `rounded-xl` / `rounded-2xl`), bordas finas com opacidade (`border-zinc-700/50`).
- **Dados:** números com `tabular-nums` quando fizer sentido; valores em **pt-BR** (moeda e separadores).

---

## 2. Stack de referência (este projeto)

- **Next.js** (App Router), **React**
- **Tailwind CSS v4** — `@import "tailwindcss"` no CSS global
- **Fontes:** **Geist Sans** e **Geist Mono** (Google Fonts via `next/font`)
- **Ícones:** `@tabler/icons-react`
- **Gráficos:** Recharts (tooltips e fundos alinhados ao dark)
- **Toasts:** Sonner (`richColors`, canto superior direito)

---

## 3. Variáveis CSS (`:root`)

Valores usados em `globals.css` (ajuste em um único lugar se portar):

| Token           | Valor     | Uso                          |
|-----------------|-----------|------------------------------|
| `--background`  | `#000000` | Fundo da aplicação           |
| `--foreground`  | `#ededed` | Texto base (fallback)        |
| `--muted`       | `#a1a1aa` | Texto secundário             |
| `--border`      | `#27272a` | Cor padrão de borda global   |
| `--accent`      | `#3b82f6` | Acento (blue-500)            |
| `--card`        | `#0a0a0a` | Superfície de cartão escura  |

**Body sugerido:** `bg-black text-zinc-100 antialiased min-h-screen`  
**HTML:** `lang="pt-BR"` e classe `dark` se precisar compatibilidade com libs.

---

## 4. Scrollbar (WebKit)

- Largura/altura **8px**, track transparente.
- Thumb: `#27272a`, hover `#3f3f46`, `border-radius: 4px`.

---

## 5. Paleta Tailwind (como usamos na prática)

### Neutros (Zinc)

- **Título de página:** `text-zinc-100`, `text-2xl font-semibold tracking-tight`
- **Subtítulo / descrição:** `text-sm text-zinc-400`
- **Labels de formulário:** `text-sm font-medium text-zinc-300`
- **Bordas:** `border-zinc-800`, `border-zinc-700/50`, `border-zinc-700/40`
- **Superfícies:** `bg-zinc-900/30`, `bg-zinc-950/50`, `bg-black`, `backdrop-blur-sm` em cartões

### Acento e ações

- **Eyebrow / seção (rótulo superior):** `text-[10px] font-semibold uppercase tracking-[0.22em] text-cyan-500/90` ou similar
- **Título de seção:** `text-lg font-semibold text-zinc-100 tracking-tight`
- **Botão primário:** `bg-blue-600 hover:bg-blue-500 text-white rounded-lg`
- **Botão secundário:** `bg-zinc-800 hover:bg-zinc-700 text-zinc-100 border-zinc-700`
- **Focus em input:** `focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500`

### Estados

- **Erro (banner):** `bg-red-500/10 border border-red-500/20 text-red-400 text-sm`
- **Sucesso / info:** via Sonner ou `text-emerald-400` se precisar inline

### KPIs semânticos (cartões)

Variantes usadas no painel (gradiente suave + borda):

- **default:** `border-zinc-700/40 bg-zinc-950/50 backdrop-blur-sm shadow-sm shadow-black/10`
- **accent (ciano):** `border-cyan-500/25 bg-gradient-to-br from-cyan-950/40 to-zinc-950/60 shadow-cyan-950/20`
- **warn (âmbar):** `border-amber-500/20 bg-gradient-to-br from-amber-950/25 to-zinc-950/60`
- **danger (rosa/vermelho):** `border-rose-500/20 bg-gradient-to-br from-rose-950/30 to-zinc-950/60`

**KPI selecionável (filtro):** anel `ring-2 ring-blue-500/70 border-blue-500/40` quando `selected`.

**Label do KPI:** `text-[11px] font-semibold uppercase tracking-[0.14em] text-zinc-500`  
**Valor:** `text-lg sm:text-xl font-semibold text-zinc-50 tabular-nums tracking-tight`

---

## 6. Layout com sidebar

- **Sidebar fixa:** `w-64`, fundo `bg-black`, borda direita `border-zinc-800`
- **Links inativos:** `text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200`
- **Link ativo:** `bg-zinc-800 text-white`
- **Área principal:** `lg:ml-64`, `main` com `p-4 sm:p-6 lg:p-8`, `overflow-x-auto`
- **Header superior (faixa):** `h-14 lg:h-16`, `border-b border-zinc-800/80`
- **Mobile:** menu hambúrguer + overlay escuro `bg-black/60`

---

## 7. Cartões e tabelas (dashboard)

### Container de cartão genérico

- `rounded-xl border border-zinc-700/50 bg-zinc-900/30 overflow-hidden`
- Cabeçalho do bloco: `px-4 py-3 border-b border-zinc-800`, título `text-sm font-medium text-zinc-300`

### Tabela

- **Cabeçalho sticky:** `sticky top-0 bg-zinc-950/95 backdrop-blur-sm z-10`
- **Th:** `text-left font-medium text-zinc-400 px-3 py-2.5 whitespace-nowrap`
- **Td:** `text-zinc-200 px-3 py-2`, linhas `border-b border-zinc-700/30`, hover `hover:bg-zinc-800/30`
- **Área rolável:** `overflow-auto max-h-[min(520px,70vh)]` (ajuste conforme densidade)

### Cabeçalho clicável (ordenação)

- `cursor-pointer hover:text-white hover:bg-zinc-800/50`
- Indicador ativo: `text-cyan-400` com ▲ / ▼

---

## 8. Gráficos (pizza / barras)

- **Tooltip:** fundo `#18181b`, borda `#3f3f46`, texto claro, `borderRadius: 8px`
- **Paleta sugerida (slices):**  
  `#3b82f6`, `#6366f1`, `#22c55e`, `#f97316`, `#ef4444`, `#eab308`, `#a855f7`, `#64748b`
- **Stroke entre fatias:** `#18181b` (zinc-950)

---

## 9. Formulários

- **Input:** `bg-zinc-900/50 border border-zinc-700 rounded-lg px-3 py-2 text-zinc-100 placeholder-zinc-500`
- **Erro no campo:** `border-red-500/50`, mensagem `text-sm text-red-400`
- **Select (filtros):** `bg-zinc-950 border border-zinc-700 rounded-lg px-2 py-1.5 text-sm text-zinc-200`

---

## 10. Tipografia — hierarquia de página

| Nível        | Classes típicas |
|-------------|------------------|
| Título H1   | `text-2xl font-semibold text-zinc-100 tracking-tight` |
| H2 seção    | `text-sm font-medium text-zinc-300 mb-3` (ou `text-lg` em `DashboardSection`) |
| Código inline | `text-zinc-500` dentro de `<code>` |
| Texto auxiliar | `text-xs text-zinc-500` |

---

## 11. Formatação de dados (locale)

- **Moeda BRL:** `toLocaleString("pt-BR", { style: "currency", currency: "BRL", minimumFractionDigits: 2 })`
- **Número:** `toLocaleString("pt-BR", { minimumFractionDigits, maximumFractionDigits })`
- **Inteiro:** `maximumFractionDigits: 0`
- Valores inválidos: exibir `—`

---

## 12. Espaçamento e ritmo

- Entre blocos grandes: `space-y-6` ou `space-y-8`
- Grades de KPI: `grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3`
- Em telas estreitas, priorizar uma coluna e scroll horizontal só onde necessário (`min-w-[640px]` em tabelas largas)

---

## 13. Checklist para colar em outro projeto

1. [ ] Tailwind configurado; fundo preto + texto zinc claro no `body`
2. [ ] Geist (ou fonte sans neutra) + `antialiased`
3. [ ] Variáveis `:root` ou equivalente no tema
4. [ ] Scrollbar custom (opcional, mas fecha o visual)
5. [ ] Componentes: botão primário azul, input zinc, erro vermelho suave
6. [ ] Cartões `rounded-xl` + borda zinc semitransparente
7. [ ] Tabelas com header sticky e zebra sutil via borda/hover
8. [ ] Gráficos com tooltip escuro e paleta acima
9. [ ] `pt-BR` em números e moeda

---

*Extraído do painel em `/painel` (Construneves). Última revisão alinhada a Next 16 + Tailwind 4.*
