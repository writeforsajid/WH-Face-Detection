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
    this.applyVisibilityRules();

  }


  get dataApi() {
    // API endpoint to fetch employee list
    return this.getAttribute("data-api") || "/data/sample.json";
  }

  render() {
    this.shadowRoot.innerHTML = `
      <link rel="stylesheet" href="/static/css/components/employee-filter.css">
      <style>
        .hidden { display: none !important; }
      </style>
      <div class="employee-filter">

        <div class="quick-buttons">
          <button id="btnToday">Today</button>
          <button id="btnYesterday">Yesterday</button>
          <button id="btnThisWeek">This Week</button>
          <button id="btnThisMonth">This Month</button>
          <button id="btnLastMonth">Last Month</button>
          <button id="btnTillDate">Till Date</button>
        </div>

        <div class="employee-filter-content">
            <div class="filter-field">
              <label for="startDate">Start Date:</label>
              <input type="date" id="startDate" name="startDate" required>
            </div>
            <div class="filter-field">
              <label for="endDate">End Date:</label>
              <input type="date" id="endDate" name="endDate" required>
            </div>
            <div class="filter-field role-owner role-employee">
              <label for="employeeSelect">Users:</label>
              <select id="employeeSelect">
                <option value="all">All Users</option>
              </select>
            </div>
            <div class="filter-field">
              <label for="fetchBtn">Fatch:</label>
              <button id="fetchBtn" class="fetch-btn">Fetch</button>
            </div>
        </div>
      </div>
    `;
    console.log("EmployeeFilter component rendered.");
  }

  setupDefaults() {

    const now = new Date();
    const today = now.toISOString().split('T')[0];

    const startDate = this.shadowRoot.querySelector("#startDate");
    const endDate = this.shadowRoot.querySelector("#endDate");
    startDate.value = today;
    endDate.value = today;



  }

  async loadEmployeeList() {
    try {
      const response = await fetch(this.dataApi);
      const employees = await response.json();
      const select = this.shadowRoot.getElementById("employeeSelect");

      const user = JSON.parse(localStorage.getItem('wh_user') || '{}');
      const guestId = user.guest_id || '';
      const role = user.role || '';
      // Clear old options except "All Employees"
      select.innerHTML = `<option value="all">All Users</option>`;

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
    // const endDateEl = this.shadowRoot.getElementById("endDate");
    const fetchBtn = this.shadowRoot.getElementById("fetchBtn");

    // When end date changes → auto-update start date based on dateDiff
    // endDateEl.addEventListener("change", () => this.updateStartFromEnd());
    const startDate = this.shadowRoot.getElementById("startDate");
    const endDate = this.shadowRoot.getElementById("endDate");
    // Fetch button click
    fetchBtn.addEventListener("click", () => this.handleFetch());
    const now = new Date();
    // Button references
    const btns = {
      today: this.shadowRoot.querySelector("#btnToday"),
      yesterday: this.shadowRoot.querySelector("#btnYesterday"),
      thisWeek: this.shadowRoot.querySelector("#btnThisWeek"),
      thisMonth: this.shadowRoot.querySelector("#btnThisMonth"),
      lastMonth: this.shadowRoot.querySelector("#btnLastMonth"),
      tillDate: this.shadowRoot.querySelector("#btnTillDate")

    };
    console.log(btns.today, "Button ready?");
    // Utility to activate selected button
    const setActive = (id) => {
      this.shadowRoot.querySelectorAll(".quick-buttons button").forEach(btn =>
        btn.classList.remove("active")
      );
      btns[id].classList.add("active");
    };




    // Button handlers
    btns.today.addEventListener("click", () => {
      const y = new Date(now);
      y.setDate(y.getDate() - 0);
      const yStr = y.toISOString().split('T')[0];
      startDate.value = yStr;
      endDate.value = yStr;
      setActive("today");
    });
    
    btns.yesterday.addEventListener("click", () => {
      const y = new Date(now);
      y.setDate(y.getDate() - 1);
      const yStr = y.toISOString().split('T')[0];
      startDate.value = yStr;
      endDate.value = yStr;
      setActive("yesterday");
    });

    btns.thisWeek.addEventListener("click", () => {
      const firstDayOfWeek = new Date(now);
      const day = now.getDay();
      const diff = now.getDate() - day + (day === 0 ? -6 : 1);
      firstDayOfWeek.setDate(diff);
      const first = firstDayOfWeek.toISOString().split('T')[0];
      startDate.value = first;

      const y = new Date(now);
      y.setDate(y.getDate() - 0);
      const yStr = y.toISOString().split('T')[0];
      endDate.value = yStr;
      setActive("thisWeek");
    });

    btns.thisMonth.addEventListener("click", () => {
      const first = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().split('T')[0];
      startDate.value = first;
      

      const y = new Date(now);
      y.setDate(y.getDate() - 0);
      const yStr = y.toISOString().split('T')[0];
      endDate.value = yStr;
      setActive("thisMonth");
    });

    btns.lastMonth.addEventListener("click", () => {
      const first = new Date(now.getFullYear(), now.getMonth() - 1, 1).toISOString().split('T')[0];
      const last = new Date(now.getFullYear(), now.getMonth(), 0).toISOString().split('T')[0];
      startDate.value = first;
      endDate.value = last;
      setActive("lastMonth");
    });

    btns.tillDate.addEventListener("click", () => {
      startDate.value = "2024-01-01";

      const y = new Date(now);
      y.setDate(y.getDate() - 0);
      const yStr = y.toISOString().split('T')[0];
      endDate.value = yStr;
      setActive("tillDate");
    });




  }

  // updateStartFromEnd() {
  //   const endDateEl = this.shadowRoot.getElementById("endDate");
  //   const startDateEl = this.shadowRoot.getElementById("startDate");
  //   const endDate = new Date(endDateEl.value);
  //   endDate.setDate(endDate.getDate() - this.dateDiff);
  //   const newStart = endDate.toISOString().split("T")[0];
  //   startDateEl.value = newStart;
  // }

  applyVisibilityRules() {
    debugger;
    const disableList = this.getAttribute("data-disable");
    const hiddenList = this.getAttribute("data-hidden");

    const parseList = (attr) => {
      try {
        return attr ? JSON.parse(attr) : [];
      } catch (e) {
        console.error("Invalid JSON in attribute:", attr);
        return [];
      }
    };

    const disableIds = parseList(disableList);
    const hiddenIds = parseList(hiddenList);

    // 🔹 Disable controls
    disableIds.forEach((id) => {
      const el = this.shadowRoot.getElementById(id);
      if (el) el.disabled = true;
    });

    // 🔹 Hide controls
    hiddenIds.forEach((id) => {
      const el = this.shadowRoot.getElementById(id);
      if (el) el.classList.add("hidden");
  
     });
    }
  
    handleFetch() {
    debugger;
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
//Samples parmeters
// data-api="http://localhost:8000/employees/active" 
// data-disable='["endDate1","employeeSelect","fetchBtn"]' 
// data-hidden='["fetchBtn",""]'