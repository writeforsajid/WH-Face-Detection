// /static/components/log-filter.js
class LogFilter extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }

  connectedCallback() {
    this.render();
    this.setupDefaults();
    this.loadComboList();
    this.addEventListeners();
    this.applyVisibilityRules();
  }

  get dataApi() {
    return this.getAttribute("data-api") || "/data/sample.json";
  }

  render() {
    this.shadowRoot.innerHTML = `
      <link rel="stylesheet" href="/static/css/components/employee-filter.css">
      <style>
        :host { display:block; }
        .hidden { display: none !important; }
        .quick-buttons button.active { background:#4c3a97; color:#fff; }
        .filter-field { margin-bottom:0.5rem; }
        .filter-row { display:flex; gap:0.5rem; flex-wrap:wrap; align-items:end; }
        select, input[type="date"], input[type="text"] { padding:0.35rem; font-size:0.95rem; }
      </style>

      <div class="log-filter">
        <div class="quick-buttons">
          <button id="btnToday">Today</button>
          <button id="btnYesterday">Yesterday</button>
          <button id="btnThisWeek">This Week</button>
          <button id="btnThisMonth">This Month</button>
          <button id="btnLastMonth">Last Month</button>
          <button id="btnTillDate">Till Date</button>
        </div>

        <div class="employee-filter-content">
          <div class="filter-row">

            <div class="filter-field">
              <label for="startDate">Start Date:</label><br/>
              <input type="date" id="startDate" required>
            </div>

            <div class="filter-field">
              <label for="endDate">End Date:</label><br/>
              <input type="date" id="endDate" required>
            </div>

            <!-- NEW HEADS COMBO -->
            <div class="filter-field">
              
              <select id="headsSelect">
                <option value="">-- Select Head --</option>
              </select>
              <input type="text" id="headsText" placeholder="Type head..." />
            </div>

            <!-- NEW HEADS TEXT
            <div class="filter-field">
              <label for="headsText">Heads (text overrides select)</label><br/>
              <input type="text" id="headsText" placeholder="Type head..." />
            </div> -->


            <div class="filter-field">
              <label for="meta-desc">Description</label><br/>
              <input type="text" id="meta-desc" placeholder="Description (optional)" />
            </div>


            <div class="filter-field">
              <label>&nbsp;</label><br/>
              <button id="fetchBtn" type="button">Fetch</button>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  setupDefaults() {
    const today = new Date().toISOString().split('T')[0];
    this.shadowRoot.querySelector("#startDate").value = today;
    this.shadowRoot.querySelector("#endDate").value = today;
  }

  async loadComboList() {
    try {
        const apiBase = localStorage.getItem('wh_api_base') || window.location.origin;
        const token = localStorage.getItem('wh_token');
        
        const headers = {
            'Content-Type': 'application/json'
        };
        
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
      
			try {
					const response = await fetch(`${apiBase}/system/appconfig?name=LOG_ITEMS`, { headers });
					if (!response.ok) throw new Error("Failed to fetch app config");
					const data = await response.json();
					// Example response: { name: "LOG_ITEMS", description: { options: [...] } }
					//const options = data.description?.options || [];
					let desc = data.description;
					// Replace single quotes with double quotes safely
					if (typeof desc === "string") {
						try {
							desc = desc.replace(/'/g, '"');
							desc = JSON.parse(desc);
						} catch (e) {
							console.error("Parsing failed:", e);
							desc = {};
						}
					}


					// Cache in memory for later use
					window.LOG_ITEMS = desc.options;
					//const comboBox =  shadow.getElementById("headsSelect");
          const comboBox = this.shadowRoot.getElementById("headsSelect");          
					// Clear existing except first
					comboBox.length = 1;
					// Populate dynamically
					window.LOG_ITEMS.forEach(item => {
					const opt =  document.createElement("option");
					opt.value = item.value;
					opt.textContent = item.label;
					comboBox.appendChild(opt);
					});

					console.log("✅ LOG_ITEMS loaded:", desc);
            } catch (error) {
                console.error('Error fetching dashboard data:', error);
                // Set default values on error
                //setDefaultValues();
            }
      
      
      
      
    //   const response = await fetch(this.dataApi);
    //   const employees = await response.json();
    //   const select = this.shadowRoot.getElementById("employeeSelect");

    //   const user = JSON.parse(localStorage.getItem('wh_user') || '{}');
    //   const guestId = user.guest_id || '';
    //   const role = user.role || '';
    //   // Clear old options except "All Employees"
    //   select.innerHTML = `<option value="all">All Users</option>`;

    //   if (Array.isArray(employees)) {
    //     employees.forEach(emp => {
    //       const option = document.createElement("option");
    //       option.value = emp.id;
    //       option.textContent = emp.name;
    //       if (role === "employee" && emp.id == guestId) {
    //         option.selected = true;
    //         select.disabled = true;
    //       }


    //       select.appendChild(option);
    //     });
    //   }
     } catch (error) {
       console.error("Failed to load employee list:", error);
     }
  }

  

  addEventListeners() {
    const shadow = this.shadowRoot;
    const fetchBtn = shadow.getElementById("fetchBtn");
    const startDate = this.shadowRoot.getElementById("startDate");
    const endDate = this.shadowRoot.getElementById("endDate");
    //const select = shadow.getElementById("employeeSelect");
    // const metaName = shadow.getElementById("meta-name");

    // heads fields
    const headsSelect = shadow.getElementById("headsSelect");
    const headsText = shadow.getElementById("headsText");

    
    // HEADS: text overrides combo
    headsText.addEventListener("input", () => {
      if (headsText.value) {
        headsSelect.value = "";
      }
    });

    // HEADS: combo → sets textbox
    headsSelect.addEventListener("change", () => {
      const t = headsSelect.selectedOptions[0]?.textContent?.trim() || "";
      headsText.value = t;
    });

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
    //console.log(btns.today, "Button ready?");
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

  applyVisibilityRules() {
    const parse = (attr) => {
      try { return attr ? JSON.parse(attr) : []; }
      catch { return []; }
    };

    const disableIds = parse(this.getAttribute("data-disable"));
    const hiddenIds = parse(this.getAttribute("data-hidden"));

    disableIds.forEach(id => {
      const el = this.shadowRoot.getElementById(id);
      if (el) el.disabled = true;
    });

    hiddenIds.forEach(id => {
      const el = this.shadowRoot.getElementById(id);
      if (el) el.classList.add("hidden");
    });
  }

  handleFetch() {
    const shadow = this.shadowRoot;

    const startDate = shadow.getElementById("startDate").value;
    const endDate = shadow.getElementById("endDate").value;

    const metaDesc = shadow.getElementById("meta-desc").value.trim();

    const headsSelectEl = shadow.getElementById("headsSelect");
    const headsTextEl = shadow.getElementById("headsText");

    const headsSelect = headsSelectEl.value.trim();
    const headsText = headsTextEl.value.trim();

    // Priority: combo → text → empty
    let heads = "";
    if (headsSelect) {
      heads = headsSelectEl.selectedOptions[0]?.textContent?.trim() || "";
    } else if (headsText) {
      heads = headsText;
    }

    const data = {
      startDate,
      endDate,
      heads,      // final resolved value
      metaDesc,
    };

    this.dispatchEvent(
      new CustomEvent("filter-data", {
        detail: data,
        bubbles: true,
        composed: true
      })
    );
  }
}

customElements.define("log-filter", LogFilter);
