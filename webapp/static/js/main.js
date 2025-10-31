$(document).ready(function () {
  // ✅ Load header first
  $("#menu-container").load("header.html", function () {
    console.log("Header loaded successfully");

    const user = JSON.parse(localStorage.getItem('wh_user') || '{}');
    if (!user.name) {
      window.location.href = "login.html";
      return;
    }

    $("#userName").text(user.name);

    applyRoleMenu();
    setupUserMenu();

    // Get elements
    const hamburger = document.getElementById("hamburger-btn");
    const navMenu = document.getElementById("nav-menu");
    //const userMenuBtn = document.getElementById("userMenuBtn");
    const userDropdown = document.querySelector(".user-dropdown");

    // ✅ Handle all clicks cleanly
    document.addEventListener("click", function (e) {
      // --- Hamburger toggle ---
      if (hamburger && hamburger.contains(e.target)) {
        e.stopPropagation();
        navMenu.classList.toggle("show");
        // userDropdown.classList.remove("open"); // close user dropdown
        return;
      }

      // --- User dropdown toggle ---
      // if (userMenuBtn && userMenuBtn.contains(e.target)) {
      //   e.stopPropagation();
      //   userDropdown.classList.toggle("open");
      //   navMenu.classList.remove("show"); // close hamburger menu
      //   return;
      // }

      // --- Clicked outside both ---
      if (!navMenu.contains(e.target) && !hamburger.contains(e.target)) {
        navMenu.classList.remove("show");
      }
      // if (!userDropdown.contains(e.target) && !userMenuBtn.contains(e.target)) {
      //   userDropdown.classList.remove("open");
      // }
    });
  });
});

// --- Role visibility ---
function applyRoleMenu() {
  const role = JSON.parse(localStorage.getItem('wh_user') || '{}').role || '';
  $(".role-owner, .role-employee, .role-resident").hide();

  if (role === "owner") $(".role-owner").show();
  else if (role === "employee") $(".role-employee").show();
  else if (role === "resident") $(".role-resident").show();
}

// --- Set username ---
function setupUserMenu() {
  const user = JSON.parse(localStorage.getItem('wh_user') || '{}');
  const userNameElem = document.getElementById('userName');
  if (user && user.name) {
    userNameElem.textContent = user.name;
  } else {
    window.location.href = 'login.html';
  }
}

// --- Handle logout ---
async function handleLogout() {
  if (confirm('Are you sure you want to logout?')) {
    const token = localStorage.getItem('wh_token');
    const apiBase = localStorage.getItem('wh_api_base') || 'http://localhost:8000';
    try {
      if (token) {
        await fetch(`${apiBase}/auth/logout`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        });
      }
    } catch (error) {
      console.error('Logout error:', error);
    }
    localStorage.removeItem('wh_token');
    localStorage.removeItem('wh_user');
    window.location.href = 'login.html';
  }
}





