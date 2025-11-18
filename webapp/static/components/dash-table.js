class DashTable extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }

  connectedCallback() {
    this.api = this.getAttribute("data-api");
    this.guestId = this.getAttribute("data-guest");
    this.limit = parseInt(this.getAttribute("data-limit") || "10", 10);
    this.headers = JSON.parse(this.getAttribute("data-head") || "[]");
    this.color = this.getAttribute("data-theme") || "green";
    this.renderSkeleton();
    this.loadData();
  }

  renderSkeleton() {
    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          width: 100%;
          font-family: Arial, sans-serif;
        }
        .dash-table-wrapper {
          border-radius: 12px;
          box-shadow: 0 2px 12px 0 rgba(0,0,0,0.08);
          border: 2px solid var(--header-bg);
          background: #fff;
          overflow: hidden;
        }
        .table-container {
          max-height: 220px;
          overflow: auto;
          width: 100%;
        }
        table.dash-table {
          width: 100%;
          border-collapse: collapse;
          min-width: 600px;
          table-layout: fixed;
        }
        thead tr {
          color: #fff;
        }
        thead th {
          padding: 10px 12px;
          text-align: left;
          font-weight: bold;
          border-right: 1px solid #e0e0e0;
          font-size: 1rem;
          position: sticky;
          top: 0;
          z-index: 2;
          background: var(--header-bg);
        }
        tbody td {
          padding: 10px 12px;
          text-align: left;
          border-right: 1px solid #e0e0e0;
          color: #2a2a2a;
          font-size: 1rem;
          word-break: break-word;
        }
        tbody tr:nth-child(odd) {
          background: var(--row-normal);
        }
        tbody tr:nth-child(even) {
          background: var(--row-alt);
        }
        .icon {
          width: 18px;
          height: 18px;
          margin-right: 8px;
        }
        :host([data-theme="green"]) {
          --header-bg: #1b7a3a;
          --row-normal: #fff;
          --row-alt: #e8f6ee;
        }
        :host([data-theme="blue"]) {
          --header-bg: #1e4f91;
          --row-normal: #fff;
          --row-alt: #e7f0fb;
        }
        :host([data-theme="gray"]) {
          --header-bg: #585858;
          --row-normal: #fff;
          --row-alt: #f2f2f2;
        }
      </style>
      <div class="dash-table-wrapper">
        <div class="table-container">
          <table class="dash-table">
            <thead>
              <tr>
                ${this.headers.map(h => `<th>${h}</th>`).join("")}
              </tr>
            </thead>
            <tbody></tbody>
          </table>
        </div>
      </div>
    `;
  }
  async loadData() {
    const tbody = this.shadowRoot.querySelector('.dash-table tbody') || this.shadowRoot.querySelector('tbody');

    // show loading row
    tbody.innerHTML = '';
    const loadingTr = document.createElement('tr');
    const loadingTd = document.createElement('td');
    loadingTd.setAttribute('colspan', Math.max(1, this.headers.length));
    loadingTd.textContent = 'Loading...';
    loadingTr.className = 'loading-row';
    loadingTr.appendChild(loadingTd);
    tbody.appendChild(loadingTr);

    // Build endpoint: explicit data-api wins, otherwise use guest logs endpoint when data-guest is provided
    let endpoint = this.api;
    if (endpoint && this.guestId) {
      // Support placeholder {guest} -> replace with guestId
      if (endpoint.includes('{guest}')) {
        endpoint = endpoint.replace('{guest}', encodeURIComponent(this.guestId));
      } else if (endpoint.endsWith('/')) {
        // If api is provided as base like '/metadata/guest/', append guestId
        endpoint = endpoint + encodeURIComponent(this.guestId);
      }
    }
    if (!endpoint && this.guestId) {
      endpoint = `/attendance/guest_logs?guest_id=${encodeURIComponent(this.guestId)}&limit=${this.limit}`;
    }

    if (!endpoint) {
      tbody.innerHTML = `<tr class="empty-row"><td colspan="${Math.max(1, this.headers.length)}">No data source configured</td></tr>`;
      return;
    }

    try {
      const resp = await fetch(endpoint, { method: 'GET', headers: { 'Accept': 'application/json' }, credentials: 'include' });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${resp.statusText}`);

      const json = await resp.json();
      const rows = Array.isArray(json) ? json : (json.data || json.items || []);

      if (!Array.isArray(rows) || rows.length === 0) {
        tbody.innerHTML = '';
        const emptyTr = document.createElement('tr');
        const emptyTd = document.createElement('td');
        emptyTd.setAttribute('colspan', Math.max(1, this.headers.length));
        emptyTd.textContent = 'No data available';
        emptyTr.className = 'empty-row';
        emptyTr.appendChild(emptyTd);
        tbody.appendChild(emptyTr);
        return;
      }

      this.renderData(rows);
    } catch (err) {
      console.error('dash-table load error:', err);
      tbody.innerHTML = '';
      const errTr = document.createElement('tr');
      const errTd = document.createElement('td');
      errTd.setAttribute('colspan', Math.max(1, this.headers.length));
      errTd.textContent = 'Failed to load data';
      errTr.className = 'empty-row';
      errTr.appendChild(errTd);
      tbody.appendChild(errTr);
    }
  }

  getIconForCategory(cat) {
    switch (cat) {
      case "food":
        return "🍽️";
      case "alert":
        return "⚠️";
      case "cleaning":
        return "🧹";
      case "payment":
        return "💰";
      default:
        return "📌";
    }
  }

  getIconForDevice(device) {
    if (!device) return '📌';
    switch ((device || '').toUpperCase()) {
      case 'LIFT_CAM': return '🛗';
      case 'EXIT_CAM': return '🚪';
      default: return '📌';
    }
  }

  renderData(data) {
    const tbody = this.shadowRoot.querySelector('.dash-table tbody') || this.shadowRoot.querySelector('tbody');
    tbody.innerHTML = '';
    data.forEach((row) => {
      const tr = document.createElement('tr');
      this.headers.forEach((h) => {
        const td = document.createElement('td');
        const val = row[h];
        td.textContent = (val === null || val === undefined) ? '' : String(val);
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
  }
}

customElements.define("dash-table", DashTable);



//arish working side dont touch it

// class DashTable extends HTMLElement {
//     constructor() {
//         super();
//         this.attachShadow({ mode: 'open' });
//     }

//     connectedCallback() {
//         this.api = this.getAttribute("data-api");
//         this.headers = JSON.parse(this.getAttribute("data-head") || "[]");
//         this.color = this.getAttribute("data-theme") || "green"; // default theme

//         this.renderSkeleton();
//         this.loadData();
//     }

//     renderSkeleton() {
//         this.shadowRoot.innerHTML = `
//             <style>
//                 :host {
//                     display: block;
//                     width: 100%;
//                     max-height: 300px;
//                     overflow: auto;
//                     font-family: Arial, sans-serif;
//                 }

//                 table {
//                     width: 100%;
//                     border-collapse: collapse;
//                     min-width: 600px;
//                     color:  #333333;
//                     background: linear-gradient(135deg,#000 0%,#000 100%);
//                 }

//                 thead {
//                     position: sticky;
//                     top: 0;
//                     z-index: 1;
//                 }

//                 /* Theme Colors */
//                 thead tr {
//                     background: var(--header-bg);
//                     color: white;
//                 }
//                 tbody tr:nth-child(odd) {
//                     background: var(--row-normal);
//                 }

//                 tbody tr:nth-child(even) {
//                     background: var(--row-alt);
//                 }
//                 /* tr:nth-child(even) {
//                  background: var(--row-alt);
//                  }

//                  tr:nth-child(odd) {
//                      background: var(--row-normal);
//                  }*/

//                 td, th {
//                     padding: 8px 12px;
//                     text-align: left;
//                     border-bottom: 1px solid #e0e0e0;
//                 }

//                 .icon {
//                     width: 18px;
//                     height: 18px;
//                     margin-right: 8px;
//                 }

//                 /* Green Theme */
//                 :host([data-theme="green"]) {
//                     --header-bg: #1b7a3a;
//                     --row-normal: #ffffff;
//                     --row-alt: #e8f6ee;
//                 }

//                 /* Blue Theme */
//                 :host([data-theme="blue"]) {
//                     --header-bg: #1e4f91;
//                     --row-normal: #ffffff;
//                     --row-alt: #e7f0fb;
//                 }

//                 /* Gray Theme */
//                 :host([data-theme="gray"]) {
//                     --header-bg: #585858;
//                     --row-normal: #ffffff;
//                     --row-alt: #f2f2f2;
//                 }
//             </style>

//             <table>
//                 <thead><tr></tr></thead>
//                 <tbody></tbody>
//             </table>
//         `;

//         let headerRow = this.shadowRoot.querySelector("thead tr");
//         headerRow.innerHTML = `<th></th>` + this.headers.map(h => `<th>${h}</th>`).join("");
//     }

//     loadData() {
//         // Fake API data for demonstration
//         let sample = [
//             { category:"food", guest:"Sam", guest_id:"001", name:"Breakfast", description:"Bread & Eggs", timestamp:"2025-01-01" },
//             { category:"alert", guest:"Nisha", guest_id:"002", name:"Late Entry", description:"Returned at 11.30 PM", timestamp:"2025-01-03" },
//             { category:"cleaning", guest:"Ritu", guest_id:"003", name:"Room Check", description:"Clean & neat", timestamp:"2025-01-05" },
//             { category:"payment", guest:"Anu", guest_id:"004", name:"Rent Paid", description:"UPI Payment", timestamp:"2025-01-08" }
//         ];

//         this.renderData(sample);
//     }

//     getIconForCategory(cat) {
//         switch(cat) {
//             case "food": return "🍽️";
//             case "alert": return "⚠️";
//             case "cleaning": return "🧹";
//             case "payment": return "💰";
//             default: return "📌";
//         }
//     }

//     renderData(data) {
//         const tbody = this.shadowRoot.querySelector("tbody");
//         tbody.innerHTML = "";

//         data.forEach(row => {
//             let tr = document.createElement("tr");

//             let iconCol = `<td>${this.getIconForCategory(row.category)}</td>`;

//             let cols = this.headers.map(h => `<td>${row[h] ?? ""}</td>`).join("");

//             tr.innerHTML = iconCol + cols;
//             tbody.appendChild(tr);
//         });
//     }
// }

// customElements.define("dash-table", DashTable);
