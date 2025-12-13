class DashTable extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
    }

    connectedCallback() {
        this.api = this.getAttribute("data-api");
        this.headers = JSON.parse(this.getAttribute("data-head") || "[]");
        this.color = this.getAttribute("data-theme") || "green"; // default theme

        this.renderSkeleton();
        this.loadData();
    }
    buildUrl() {
        const url = new URL(this.api, window.location.origin);
        // include filter params
        const guestid = JSON.parse(localStorage.getItem('wh_user') || '{}').guest_id || '';
        url.searchParams.set('guest_id', guestid);
        for (const key in this.extraParams) {
            if (this.extraParams[key] !== "") {
                url.searchParams.set(key, this.extraParams[key]);
            }

        }
        return url.toString();
    }
    renderSkeleton() {
        this.shadowRoot.innerHTML = `
            <style>
                :host {
                    display: block;
                    width: 100%;
                    max-height: 300px;
                    overflow: auto;
                    font-family: Arial, sans-serif;
                }

                table {
                    width: 100%;
                    border-collapse: collapse;
                    color:  #333333;
                    background: linear-gradient(135deg,#000 0%,#000 100%);
                }

                thead {
                    position: sticky;
                    top: 0;
                    z-index: 1;
                }

                /* Theme Colors */
                thead tr {
                    background: var(--header-bg);
                    color: white;
                }
                tbody tr:nth-child(odd) {
                    background: var(--row-normal);
                }

                tbody tr:nth-child(even) {
                    background: var(--row-alt);
                }
                /* tr:nth-child(even) {
                 background: var(--row-alt);
                 }

                 tr:nth-child(odd) {
                     background: var(--row-normal);
                 }*/

                td, th {
                    padding: 2px 6px;
                    text-align: left;
                    border-bottom: 1px solid #e0e0e0;
                }

                .icon {
                    width: 18px;
                    height: 18px;
                    margin-right: 8px;
                }

                /* Green Theme */
                :host([data-theme="green"]) {
                    --header-bg: #1b7a3a;
                    --row-normal: #ffffff;
                    --row-alt: #e8f6ee;
                }

                /* Blue Theme */
                :host([data-theme="blue"]) {
                    --header-bg: #1e4f91;
                    --row-normal: #ffffff;
                    --row-alt: #e7f0fb;
                }

                /* Gray Theme */
                :host([data-theme="gray"]) {
                    --header-bg: #585858;
                    --row-normal: #ffffff;
                    --row-alt: #f2f2f2;
                }
            </style>
            <table>
              <thead>
                <tr id="tableHead"></tr>
              </thead>
              <tbody id="tableBody"></tbody>
            </table>

        `;

        let headerRow = this.shadowRoot.querySelector("thead tr");
        headerRow.innerHTML = `<th></th>` + this.headers.map(h => `<th>${h}</th>`).join("");
    }

    async loadData() {
      const url = this.buildUrl();
      const res = await fetch(url);
      const json = await res.json();
      const columns = this.headList;
      const rows = json.data || [];
      this.renderHead(columns);
      this.renderBody(columns, rows);

    }

    get headList() {
      try {
        return JSON.parse(this.getAttribute("data-head") || "[]");
      } catch {
        return [];
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
    //const emptyBox = this.shadowRoot.getElementById("emptyBox");
    tbody.innerHTML = "";

    if (rows.length === 0) {
     // emptyBox.style.display = "block";
      return;
    }

   // emptyBox.style.display = "none";

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


}

customElements.define("dash-table", DashTable);
