// assets/js/components/employee-filter.js
class EmployeeFilter extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }

  connectedCallback() {
    this.render();
    this.loadEmployeeList();
    this.setDefaultDates();
    this.addEventListeners();
  }

  render() {
    this.shadowRoot.innerHTML = `
      <link rel="stylesheet" href="/static/css/components/employee-filter.css">
      <div class="employee-filter">
        <div class="filter-field">
          <label for="startDate">Start Date:</label>
          <input type="date" id="startDate" name="startDate" required>
        </div>
        <div class="filter-field">
          <label for="endDate">End Date:</label>
          <input type="date" id="endDate" name="endDate" required>
        </div>
        <div class="filter-field">
          <label for="employeeSelect">Employee:</label>
          <select id="employeeSelect">
            <option value="all">All Employees</option>
          </select>
        </div>
        <div class="filter-field">
          <button id="fetchBtn" class="fetch-btn">Fetch</button>
        </div>
      </div>
    `;
  }

  setDefaultDates() {
    const today = new Date().toISOString().split("T")[0];
    this.shadowRoot.getElementById("startDate").value = today;
    this.shadowRoot.getElementById("endDate").value = today;
  }

  async loadEmployeeList() {
    try {
      const response = await fetch("/static/temp/sample.json");
      const employees = await response.json();
      const select = this.shadowRoot.getElementById("employeeSelect");
      employees.forEach(emp => {
        const option = document.createElement("option");
        option.value = emp.id;
        option.textContent = emp.name;
        select.appendChild(option);
      });
    } catch (error) {
      console.error("Failed to load employee list:", error);
    }
  }

  addEventListeners() {
    const fetchBtn = this.shadowRoot.getElementById("fetchBtn");
    fetchBtn.addEventListener("click", () => this.handleFetch());
  }

  handleFetch() {
    const startDate = this.shadowRoot.getElementById("startDate").value;
    const endDate = this.shadowRoot.getElementById("endDate").value;
    const employeeId = this.shadowRoot.getElementById("employeeSelect").value;

    // ✅ Client-side validation
    if (!startDate || !endDate) {
      alert("Please select both start and end dates.");
      return;
    }
    if (new Date(startDate) > new Date(endDate)) {
      alert("Start date cannot be greater than end date!");
      return;
    }

    // ✅ Emit JSON event to parent
    const data = { startDate, endDate, employeeId };
    this.dispatchEvent(
      new CustomEvent("filter-data", {
        detail: data,
        bubbles: true,
        composed: true,
      })
    );
  }
}

customElements.define("employee-filter", EmployeeFilter);
