$("#loginBtn").click(function() {
    const username = $("#username").val();
    const password = $("#password").val();

    $.ajax({
        url: "http://127.0.0.1:8000/auth/login",
        type: "POST",
        data: { username, password },   // <== sends as form data
        success: function(res) {
            sessionStorage.setItem("role", res.role);
            sessionStorage.setItem("username", res.username);
            window.location.href = "dashboard.html";
        },
        error: function(err) {
            alert("Login failed!");
            console.error(err);
        }
    });
});
