class GenTable extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this.extraParams = {};
    this.page = 1;
    this.pageSize = 10;
    this.total = 0;
  }

  connectedCallback() {
    this.render();
    //this.loadData();
    this.addEvents();
  }
  setParams(params) {
        this.extraParams = params;
        this.page = 1;  // reset to first page on filter apply
        this.loadData();
    }

    buildUrl() {
        const url = new URL(this.api, window.location.origin);

        url.searchParams.set("page", this.page);
        url.searchParams.set("pageSize", this.pageSize);

        // include filter params
        for (const key in this.extraParams) {
            if (this.extraParams[key] !== "") {
                url.searchParams.set(key, this.extraParams[key]);
            }
        }
        return url.toString();
    }
  get api() {
    return this.getAttribute("data-api");
  }

  get title() {
    return this.getAttribute("data-title") || "Table";
  }

  get headList() {
    try {
      return JSON.parse(this.getAttribute("data-head") || "[]");
    } catch {
      return [];
    }
  }

  render() {
    this.shadowRoot.innerHTML = `
<style>
:host { display:block; font-family:Arial; }
.card { border:1px solid #ddd; padding:1rem; border-radius:6px; background:#fff; margin:1rem 0; }
h3 { margin:0 0 .6rem 0; color: #000; }
table { width:100%; border-collapse: collapse; color: #000;border: 1px solid; }
th, td { padding:8px; border:1px solid #ddd; text-align:left; font-size:14px; }
.top-bar { display:flex; justify-content:space-between; margin-bottom:8px; }
.pagination { display:flex; justify-content:center; margin-top:8px; gap:8px; }
button { padding:6px 12px; border:1px solid #666; background:#f4f4f4; cursor:pointer; }
button:disabled { opacity:0.5; cursor:not-allowed; }
select { padding:4px; }
.empty { text-align:center; padding:20px; color:#666; }
@media(max-width:600px) { table, thead, tbody, th, td, tr { display:block; } tr { margin-bottom:10px; } td { border:none; padding-left:50%; position:relative; } td::before { content:attr(data-label); position:absolute; left:0; width:45%; font-weight:bold; } }
</style>

      <div class="card">
        <h3>${this.title}</h3>

        <div class="top-bar">
          <div></div>
          <div>
            Page size:
            <select id="pageSize">
              <option value="10">10</option>
              <option value="20">20</option>
              <option value="50">50</option>
            </select>
          </div>
        </div>

        <table>
          <thead>
            <tr id="tableHead"></tr>
          </thead>
          <tbody id="tableBody"></tbody>
        </table>

        <div id="emptyBox" class="empty" style="display:none;">No records found</div>

        <div class="pagination">
          <button id="prevBtn">Prev</button>
          <span id="pageInfo"></span>
          <button id="nextBtn">Next</button>
        </div>
      </div>
    `;
  }

  addEvents() {
    this.shadowRoot.getElementById("prevBtn")
      .addEventListener("click", () => {
        if (this.page > 1) {
          this.page--;
          this.loadData();
        }
      });

    this.shadowRoot.getElementById("nextBtn")
      .addEventListener("click", () => {
        const totalPages = Math.ceil(this.total / this.pageSize);
        if (this.page < totalPages) {
          this.page++;
          this.loadData();
        }
      });

    this.shadowRoot.getElementById("pageSize")
      .addEventListener("change", (e) => {
        this.pageSize = Number(e.target.value);
        this.page = 1;
        this.loadData();
      });
  }

  async loadData() {
    // let url = `${this.api}?page=${this.page}&pageSize=${this.pageSize}`;
    // for (const key in this.extraParams) {
    //     if (this.extraParams[key] !== "") {
    //     url += `&${encodeURIComponent(key)}=${encodeURIComponent(this.extraParams[key])}`;
    //     }
    // }
    try {
      const url = this.buildUrl();
      const res = await fetch(url);
      const json = await res.json();
      debugger;
      const columns = this.headList;

      this.total = json.total || 0;
      const rows = json.data || [];

      this.renderHead(columns);
      this.renderBody(columns, rows);
      this.updatePagination();

    } catch (err) {
      console.error("Table load error:", err);
    }
  }

  renderHead(columns) {
    const headRow = this.shadowRoot.getElementById("tableHead");
    headRow.innerHTML = "";

    columns.forEach(col => {
      const th = document.createElement("th");
      th.textContent = col;
      headRow.appendChild(th);
    });
  }

  renderBody(columns, rows) {
    const tbody = this.shadowRoot.getElementById("tableBody");
    const emptyBox = this.shadowRoot.getElementById("emptyBox");

    tbody.innerHTML = "";

    if (rows.length === 0) {
      emptyBox.style.display = "block";
      return;
    }

    emptyBox.style.display = "none";

    rows.forEach(item => {
      const tr = document.createElement("tr");

      columns.forEach(col => {
        const td = document.createElement("td");
        td.textContent = item[col] ?? "";
        td.setAttribute("data-label", col);
        tr.appendChild(td);
      });

      tbody.appendChild(tr);
    });
  }

  updatePagination() {
    const totalPages = Math.ceil(this.total / this.pageSize);

    this.shadowRoot.getElementById("pageInfo").textContent =
      `${this.page} / ${totalPages || 1}`;

    this.shadowRoot.getElementById("prevBtn").disabled = this.page <= 1;
    this.shadowRoot.getElementById("nextBtn").disabled = this.page >= totalPages;
  }
}

customElements.define("gen-table", GenTable);
