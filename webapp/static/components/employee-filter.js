// assets/js/components/employee-filter.js
class EmployeeFilter extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }

  connectedCallback() {
    this.render();
    this.setupDefaults();
    this.loadEmployeeList();
    this.addEventListeners();
  }

  get dateDiff() {
    // Number of days to subtract from end date (default 0)
    return parseInt(this.getAttribute("date-diff")) || 0;
  }

  get dataApi() {
    // API endpoint to fetch employee list
    return this.getAttribute("data-api") || "/data/sample.json";
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
        <div class="filter-field role-owner role-employee">
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
    console.log("EmployeeFilter component rendered.");
  }

  setupDefaults() {
    const today = new Date();
    const endDateEl = this.shadowRoot.getElementById("endDate");
    const startDateEl = this.shadowRoot.getElementById("startDate");

    // Set end date to today
    const todayStr = today.toISOString().split("T")[0];
    endDateEl.value = todayStr;

    // Subtract dateDiff days from end date to get start date
    const startDate = new Date(today);
    startDate.setDate(startDate.getDate() - this.dateDiff);
    const startStr = startDate.toISOString().split("T")[0];
    startDateEl.value = startStr;
  }

  async loadEmployeeList() {
    try {
      debugger;
      const response = await fetch(this.dataApi);
      const employees = await response.json();
      const select = this.shadowRoot.getElementById("employeeSelect");

      const user = JSON.parse(localStorage.getItem('wh_user') || '{}');
      const guestId = user.guest_id || '';
      const role = user.role || '';
      // Clear old options except "All Employees"
      select.innerHTML = `<option value="all">All Employees</option>`;

      if (Array.isArray(employees)) {
        employees.forEach(emp => {
          const option = document.createElement("option");
          option.value = emp.id;
          option.textContent = emp.name;
          if (role === "employee" && emp.id == guestId) {
            option.selected = true;
            select.disabled = true;
          }


          select.appendChild(option);
        });
      }
    } catch (error) {
      console.error("Failed to load employee list:", error);
    }
  }

  addEventListeners() {
    const endDateEl = this.shadowRoot.getElementById("endDate");
    const fetchBtn = this.shadowRoot.getElementById("fetchBtn");

    // When end date changes → auto-update start date based on dateDiff
    endDateEl.addEventListener("change", () => this.updateStartFromEnd());

    // Fetch button click
    fetchBtn.addEventListener("click", () => this.handleFetch());
  }

  updateStartFromEnd() {
    const endDateEl = this.shadowRoot.getElementById("endDate");
    const startDateEl = this.shadowRoot.getElementById("startDate");
    const endDate = new Date(endDateEl.value);
    endDate.setDate(endDate.getDate() - this.dateDiff);
    const newStart = endDate.toISOString().split("T")[0];
    startDateEl.value = newStart;
  }

  handleFetch() {
    const startDate = this.shadowRoot.getElementById("startDate").value;
    const endDate = this.shadowRoot.getElementById("endDate").value;
    const employeeId = this.shadowRoot.getElementById("employeeSelect").value;

    if (!startDate || !endDate) {
      alert("Please select both start and end dates.");
      return;
    }
    if (new Date(startDate) > new Date(endDate)) {
      alert("Start date cannot be greater than end date!");
      return;
    }

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
