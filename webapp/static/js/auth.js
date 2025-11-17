$("#loginBtn").click(function() {
    const username = $("#username").val();
    const password = $("#password").val();

    $.ajax({
        url: "/auth/login",
        type: "POST",
        data: { username, password },   // <== sends as form data
        success: function(res) {
            sessionStorage.setItem("role", res.role);
            sessionStorage.setItem("username", res.username);
            
            if (res.role === 'employee' || res.role === 'owner')
                window.location.href = 'admin_dashboard.html';
            else
                window.location.href = 'mydashboard.html';
            return;

        },
        error: function(err) {
            alert("Login failed!");
            console.error(err);
        }
    });
});
