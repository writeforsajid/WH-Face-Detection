$(document).ready(function () {
    // Load header dynamically

    $("#menu-container").load("header.html", function() {
        applyRoleMenu();
        setupUserMenu();

    });
});

function applyRoleMenu() {
    //const role = sessionStorage.getItem("role") || "guest";
    const role = JSON.parse(localStorage.getItem('wh_user') || '{}').role || '';
    // Hide all role-specific elements first
    
    $(".role-owner, .role-employee, .role-resident").hide();

    if (role === "owner") $(".role-owner").show();
    else if (role === "employee") $(".role-employee").show();
    else if (role === "resident") $(".role-resident").show();
}



// Set user name in header and handle logout
function setupUserMenu() {
  const user = JSON.parse(localStorage.getItem('wh_user') || '{}');
  const userNameElem = document.getElementById('userName');

  if (user && user.name) {
    userNameElem.textContent = user.name;
  } else {
    // No user — redirect to login
     window.location.href = 'login.html';
    
  }
}

document.addEventListener("click", function (e) {
  const dropdown = document.querySelector(".user-dropdown");
  const button = document.getElementById("userMenuBtn");

  if (button && button.contains(e.target)) {
    dropdown.classList.toggle("open");
  } else if (!dropdown.contains(e.target)) {
    dropdown.classList.remove("open");
  }
});

// function handleLogout() {
//   localStorage.removeItem('wh_token');
//   localStorage.removeItem('wh_user');
//   localStorage.removeItem('wh_api_base');
//   window.location.href = 'login.html';
// }


 // Handle logout
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