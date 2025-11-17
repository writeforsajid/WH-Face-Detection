
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
                    min-width: 600px;
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
                    padding: 8px 12px;
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
                <thead><tr></tr></thead>
                <tbody></tbody>
            </table>
        `;

        let headerRow = this.shadowRoot.querySelector("thead tr");
        headerRow.innerHTML = `<th></th>` + this.headers.map(h => `<th>${h}</th>`).join("");
    }

    loadData() {
        // Fake API data for demonstration
        let sample = [
            { category:"food", guest:"Sam", guest_id:"001", name:"Breakfast", description:"Bread & Eggs", timestamp:"2025-01-01" },
            { category:"alert", guest:"Nisha", guest_id:"002", name:"Late Entry", description:"Returned at 11.30 PM", timestamp:"2025-01-03" },
            { category:"cleaning", guest:"Ritu", guest_id:"003", name:"Room Check", description:"Clean & neat", timestamp:"2025-01-05" },
            { category:"payment", guest:"Anu", guest_id:"004", name:"Rent Paid", description:"UPI Payment", timestamp:"2025-01-08" }
        ];

        this.renderData(sample);
    }

    getIconForCategory(cat) {
        switch(cat) {
            case "food": return "🍽️";
            case "alert": return "⚠️";
            case "cleaning": return "🧹";
            case "payment": return "💰";
            default: return "📌";
        }
    }

    renderData(data) {
        const tbody = this.shadowRoot.querySelector("tbody");
        tbody.innerHTML = "";

        data.forEach(row => {
            let tr = document.createElement("tr");

            let iconCol = `<td>${this.getIconForCategory(row.category)}</td>`;

            let cols = this.headers.map(h => `<td>${row[h] ?? ""}</td>`).join("");

            tr.innerHTML = iconCol + cols;
            tbody.appendChild(tr);
        });
    }
}

customElements.define("dash-table", DashTable);

