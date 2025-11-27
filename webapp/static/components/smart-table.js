class SmartTable extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });

    // internal state
    this.page = 1;
    this.pageSize = 10;
    this.total = 0;
    this.data = [];
    this.extraParams = {};
    this.formatters = {};
    this.selectedSet = new Set(); // stores unique id values for current page selections
    this.idKey = this.getAttribute("data-id-key") || "id"; // unique id field in row objects
    this.columns = this.parseColumns();
    this.actions = this.parseActions();
    this.loading = false;
    this.render();
  }

  /* ============================
     ======= Attributes =========
     ============================ */

  get api() {
    return this.getAttribute("data-api") || "";
  }

  get title() {
    return this.getAttribute("data-title") || "";
  }

  parseColumns() {
    const raw = this.getAttribute("data-columns");
    if (!raw) return [];
    try {
      const parsed = JSON.parse(raw);
      // normalize to objects { key, label }
      return parsed.map(c => (typeof c === "string" ? { key: c, label: c } : { key: c.key, label: c.label ?? c.key }));
    } catch (err) {
      console.warn("smart-table: invalid data-columns JSON", err);
      return [];
    }
  }

  parseActions() {
    const raw = this.getAttribute("data-actions");
    if (!raw) return [];
    try {
      return JSON.parse(raw);
    } catch (err) {
      console.warn("smart-table: invalid data-actions JSON", err);
      return [];
    }
  }

  connectedCallback() {
    // allow attributes to inform idKey after construction
    this.idKey = this.getAttribute("data-id-key") || this.idKey;
    this.attachUIEvents();
    if (this.getAttribute("data-auto-load") !== "false") {
        this.load();
    }
  }

  /* ============================
     ======= Rendering ==========
     ============================ */

  render() {
    // main template
    this.shadowRoot.innerHTML = `
      <style>
        :host { display:block; font-family: system-ui, Arial, sans-serif; color: #222; }
        .card { border:1px solid #e0e0e0; border-radius:8px; padding:12px; background: #fff; box-shadow: 0 1px 2px rgba(0,0,0,0.03); }
        .top { display:flex; justify-content:space-between; align-items:center; gap:12px; margin-bottom:12px; flex-wrap:wrap; }
        .title { font-size:1.05rem; font-weight:600; }
        .actions { display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
        button { padding:6px 10px; border-radius:6px; border:1px solid #cfcfcf; background:#f7f7f7; cursor:pointer; }
        button.primary { background:#2b6cb0; color:#fff; border-color: #245e9a; }
        button:disabled { opacity:0.5; cursor:not-allowed; }
        .controls { display:flex; gap:8px; align-items:center; }
        .table-wrap { overflow:auto; border-radius:6px; border:1px solid #eee; }
        table { width:100%; border-collapse:collapse; min-width:600px; }
        th, td { padding:10px 12px; border-bottom:1px solid #f0f0f0; text-align:left; font-size:14px; }
        th { background:#fafafa; position:sticky; top:0; z-index:1; font-weight:600; }
        .loader { text-align:center; padding:18px 0; color:#666; }
        .empty { text-align:center; padding:18px 0; color:#777; }
        .pagination { display:flex; justify-content:center; gap:8px; align-items:center; padding-top:12px; }
        .page-info { font-size:13px; color:#444; }
        .select-all { margin-right:6px; }
        @media(max-width:700px){
          th, td { padding:8px 10px; font-size:13px; }
        }
      </style>

      <div class="card">
        <div class="top">
          <div class="title">${this.title}</div>
          <div class="controls">
            <div class="actions" id="topActions"></div>
            <div style="display:flex;align-items:center;gap:8px;">
              <label>Page size:
                <select id="pageSizeSelect">
                  <option value="10">10</option>
                  <option value="20">20</option>
                  <option value="50">50</option>
                </select>
              </label>
            </div>
          </div>
        </div>

        <div class="table-wrap" id="tableWrap">
          <table>
            <thead>
              <tr id="theadRow"></tr>
            </thead>
            <tbody id="tbody"></tbody>
          </table>
        </div>

        <div id="emptyBox" class="empty" style="display:none;">No records found</div>
        <div id="loader" class="loader" style="display:none;">Loading…</div>

        <div class="pagination">
          <button id="prevBtn">Prev</button>
          <div class="page-info" id="pageInfo"></div>
          <button id="nextBtn">Next</button>
        </div>
      </div>
    `;

    // populate header row, including checkbox column for selection
    this.renderHeader();
    this.renderTopActions();
    this.shadowRoot.getElementById("pageSizeSelect").value = String(this.pageSize);
  }

  renderHeader() {
    const theadRow = this.shadowRoot.getElementById("theadRow");
    theadRow.innerHTML = "";

    // select-all checkbox th
    const thSelect = document.createElement("th");
    thSelect.style.width = "48px";
    thSelect.innerHTML = `<label><input type="checkbox" id="selectAll" class="select-all" /></label>`;
    theadRow.appendChild(thSelect);

    // data columns
    this.columns.forEach(col => {
      const th = document.createElement("th");
      th.textContent = col.label || col.key;
      theadRow.appendChild(th);
    });
  }

  renderTopActions() {
    const container = this.shadowRoot.getElementById("topActions");
    container.innerHTML = "";
    if (!this.actions || this.actions.length === 0) return;

    this.actions.forEach(act => {
      const btn = document.createElement("button");
      btn.textContent = this.humanize(act);
      btn.dataset.action = act;
      btn.className = "primary";
      btn.disabled = true; // disabled until some rows selected
      btn.addEventListener("click", () => this.emitAction(act));
      container.appendChild(btn);
    });
  }

  humanize(s) {
    if (!s) return "";
    return s.replace(/[_-]/g, " ").replace(/\b\w/g, l => l.toUpperCase());
  }

  /* ============================
     ======= Events ============
     ============================ */

  attachUIEvents() {
    // pagination
    this.shadowRoot.getElementById("prevBtn").addEventListener("click", () => {
      if (this.page > 1) {
        this.page--;
        this.clearSelection(); // per-page selection reset
        this.load();
      }
    });
    this.shadowRoot.getElementById("nextBtn").addEventListener("click", () => {
      const totalPages = Math.max(1, Math.ceil(this.total / this.pageSize));
      if (this.page < totalPages) {
        this.page++;
        this.clearSelection();
        this.load();
      }
    });

    // page size change
    this.shadowRoot.getElementById("pageSizeSelect")
      .addEventListener("change", (e) => {
        this.pageSize = Number(e.target.value);
        this.page = 1;
        this.clearSelection();
        this.load();
      });

    // select all checkbox
    this.onSelectAllChange = (e) => {
      const checked = e.target.checked;
      const tbody = this.shadowRoot.getElementById("tbody");
      const inputs = tbody.querySelectorAll('input.row-select');
      inputs.forEach(inp => {
        inp.checked = checked;
        const idVal = inp.dataset.id;
        if (checked) this.selectedSet.add(idVal);
        else this.selectedSet.delete(idVal);
      });
      this.updateActionButtonsState();
    };

    // bubble selectAll event listener after DOM ready
    // (we attach/remove on each render/tbody refresh)
  }

  /* ============================
     ======= Data / Fetch =======
     ============================ */

  buildUrl() {
    if (!this.api) return "";
    const url = new URL(this.api, window.location.origin);
    // preserve guest role behavior like before if needed
    url.searchParams.set("page", this.page);
    url.searchParams.set("pageSize", this.pageSize);
    for (const k in this.extraParams) {
      if (this.extraParams[k] !== "") url.searchParams.set(k, this.extraParams[k]);
    }
    return url.toString();
  }

  async load() {
    // public method to trigger (auto-called on connected)
    if (!this.api) {
      console.warn("smart-table: data-api is not set");
      this.renderBody([], []);
      return;
    }
    try {
      this.setLoading(true);
      const url = this.buildUrl();
      const res = await fetch(url);
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const json = await res.json();

      // try to infer data / total fields (common patterns)
      let list = json.data ?? json.items ?? json.rows ?? json;
      let total = json.total ?? json.totalCount ?? json.count ?? (Array.isArray(list) ? list.length : 0);

      // if the API returns an object with metadata: handle that
      if (!Array.isArray(list) && typeof list === "object") {
        // attempt to extract array
        if (Array.isArray(json.data)) list = json.data;
        else list = [];
      }

      this.data = Array.isArray(list) ? list : [];
      this.total = Number(total) || this.data.length;

      // render
      this.renderBody(this.columns, this.data);
      this.updatePagination();
    } catch (err) {
      console.error("smart-table load error:", err);
      this.data = [];
      this.total = 0;
      this.renderBody(this.columns, []);
      this.updatePagination();
    } finally {
      this.setLoading(false);
    }
  }

  setParams(params = {}) {
    this.extraParams = params;
    this.page = 1;
    this.clearSelection();
    this.load();
  }

  setFormatters(formatterMap = {}) {
    this.formatters = formatterMap || {};
    // re-render current data with formatters applied
    this.renderBody(this.columns, this.data);
  }

  /* ============================
     ======= Render Body ========
     ============================ */

  renderBody(columns, rows) {
    const tbody = this.shadowRoot.getElementById("tbody");
    const emptyBox = this.shadowRoot.getElementById("emptyBox");
    const loader = this.shadowRoot.getElementById("loader");

    tbody.innerHTML = "";

    // detach previous selectAll listener to avoid duplicates
    const existingSelectAll = this.shadowRoot.getElementById("selectAll");
    if (existingSelectAll) {
      existingSelectAll.checked = false;
      existingSelectAll.removeEventListener("change", this.onSelectAllChange);
      existingSelectAll.addEventListener("change", this.onSelectAllChange);
    }

    if (this.loading) {
      loader.style.display = "block";
      emptyBox.style.display = "none";
      return;
    } else {
      loader.style.display = "none";
    }

    if (!rows || rows.length === 0) {
      emptyBox.style.display = "block";
      this.updateActionButtonsState();
      return;
    } else {
      emptyBox.style.display = "none";
    }

    // Build rows
    rows.forEach(row => {
      const tr = document.createElement("tr");

      const idVal = String(row[this.idKey] ?? JSON.stringify(row)); // fallback to stringify (not ideal)
      // checkbox cell
      const tdSelect = document.createElement("td");
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.className = "row-select";
      checkbox.dataset.id = idVal;
      checkbox.checked = this.selectedSet.has(idVal);
      checkbox.addEventListener("change", (e) => {
        if (e.target.checked) this.selectedSet.add(idVal);
        else this.selectedSet.delete(idVal);
        // if any unchecked, uncheck selectAll; if all checked, check selectAll
        this.syncSelectAllCheckbox();
        this.updateActionButtonsState();
      });
      tdSelect.appendChild(checkbox);
      tr.appendChild(tdSelect);

      // data cells
      columns.forEach(col => {
        const td = document.createElement("td");
        const rawVal = row[col.key];
        const formatted = this.applyFormatter(col.key, rawVal, row);
        td.textContent = (formatted === undefined || formatted === null) ? "" : formatted;
        td.dataset.label = col.label || col.key;
        tr.appendChild(td);
      });

      tbody.appendChild(tr);
    });

    this.updateActionButtonsState();
    this.syncSelectAllCheckbox();
  }

  applyFormatter(key, val, row) {
    try {
      const fn = this.formatters?.[key];
      if (typeof fn === "function") return fn(val, row);
      return val;
    } catch (err) {
      console.warn("formatter error for", key, err);
      return val;
    }
  }

  syncSelectAllCheckbox() {
    const selectAll = this.shadowRoot.getElementById("selectAll");
    const tbody = this.shadowRoot.getElementById("tbody");
    const inputs = tbody.querySelectorAll('input.row-select');
    if (!selectAll) return;
    const total = inputs.length;
    const checked = Array.from(inputs).filter(i => i.checked).length;
    selectAll.checked = (total > 0 && checked === total);
    // if none selected, ensure set is empty
    // (we keep set keyed by idVal so it persists per page)
  }

  updateActionButtonsState() {
    const container = this.shadowRoot.getElementById("topActions");
    const buttons = container.querySelectorAll("button");
    const hasSelection = this.selectedSet.size > 0;
    buttons.forEach(b => b.disabled = !hasSelection);
  }

  setLoading(flag) {
    this.loading = !!flag;
    const loader = this.shadowRoot.getElementById("loader");
    if (loader) loader.style.display = this.loading ? "block" : "none";
  }

  updatePagination() {
    const totalPages = Math.max(1, Math.ceil((this.total || 0) / this.pageSize));
    this.shadowRoot.getElementById("pageInfo").textContent = `${this.page} / ${totalPages}`;
    this.shadowRoot.getElementById("prevBtn").disabled = this.page <= 1;
    this.shadowRoot.getElementById("nextBtn").disabled = this.page >= totalPages;
  }

  /* ============================
     ======= Selection API ======
     ============================ */

  getSelectedRows() {
    // return row objects for currently-selected ids on the current page
    const ids = Array.from(this.selectedSet);
    return this.data.filter(r => ids.includes(String(r[this.idKey])));
  }

  clearSelection() {
    this.selectedSet.clear();
    // uncheck checkboxes in DOM
    const tbody = this.shadowRoot.getElementById("tbody");
    if (tbody) {
      const inputs = tbody.querySelectorAll('input.row-select');
      inputs.forEach(i => i.checked = false);
    }
    // uncheck selectAll
    const selectAll = this.shadowRoot.getElementById("selectAll");
    if (selectAll) selectAll.checked = false;
    this.updateActionButtonsState();
  }

  /* ============================
     ======= Actions ============
     ============================ */

  emitAction(actionName) {
    // build payload: selected rows
    const rows = this.getSelectedRows();
    // dispatch a CustomEvent from the element itself
    this.dispatchEvent(new CustomEvent(actionName, {
      detail: {
        rows,
        page: this.page,
        pageSize: this.pageSize,
        params: this.extraParams
      },
      bubbles: true,
      composed: true
    }));
  }

  /* ============================
     ======= Public Helpers =====
     ============================ */

  // convenience: reload current page
  reload() {
    this.clearSelection();
    this.load();
  }
}

/* define element */
customElements.define("smart-table", SmartTable);
