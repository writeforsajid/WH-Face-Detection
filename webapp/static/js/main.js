$(document).ready(function () {
    // Load header dynamically

    $("#menu-container").load("header.html", function() {
        applyRoleMenu();
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

function handleLogout() {
    sessionStorage.clear();
    window.location.href = "login.html";
}
