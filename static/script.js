$(function () {
    var $authView = $("#authView");
    var $todoView = $("#todoView");
    var $logoutBtn = $("#logoutBtn");
    var $status = $("#status");
    var $todoList = $("#todoList");
    var $currentUser = $("#currentUser");

    function setStatus(message, isError) {
        $status.text(message || "");
        $status.toggleClass("error", Boolean(isError));
    }

    function request(method, url, data, onSuccess) {
        $.ajax({
            method: method,
            url: url,
            data: data ? JSON.stringify(data) : undefined,
            contentType: "application/json",
            dataType: "json",
            xhrFields: {
                withCredentials: true
            },
            success: function (response) {
                if (onSuccess) {
                    onSuccess(response);
                }
            },
            error: function (xhr) {
                var response = xhr.responseJSON || {};
                setStatus(response.message || "Request failed.", true);
            }
        });
    }

    function showAuth() {
        $authView.removeClass("hidden");
        $todoView.addClass("hidden");
        $logoutBtn.addClass("hidden");
        $currentUser.text("");
    }

    function showTodos(uid) {
        $authView.addClass("hidden");
        $todoView.removeClass("hidden");
        $logoutBtn.removeClass("hidden");
        $currentUser.text("Logged in as " + uid);
        loadTodos();
    }

    function renderTodos(todos) {
        $todoList.empty();

        if (!todos.length) {
            $("<li>")
                .addClass("muted")
                .text("No todos yet.")
                .appendTo($todoList);
            return;
        }

        todos.forEach(function (todo) {
            var $item = $("<li>")
                .addClass("todo-item")
                .toggleClass("done", Boolean(todo.completed));

            $("<span>")
                .addClass("todo-title")
                .text(todo.title)
                .appendTo($item);

            $("<button>")
                .addClass("secondary")
                .attr("type", "button")
                .text(todo.completed ? "Undo" : "Done")
                .on("click", function () {
                    request(
                        "PUT",
                        "/todos/" + todo.id,
                        { completed: !todo.completed },
                        function () {
                            setStatus("Todo updated.");
                            loadTodos();
                        }
                    );
                })
                .appendTo($item);

            $("<button>")
                .addClass("danger")
                .attr("type", "button")
                .text("Delete")
                .on("click", function () {
                    request("DELETE", "/todos/" + todo.id, null, function () {
                        setStatus("Todo deleted.");
                        loadTodos();
                    });
                })
                .appendTo($item);

            $item.appendTo($todoList);
        });
    }

    function loadTodos() {
        request("GET", "/todos", null, function (response) {
            renderTodos(response.todos || []);
        });
    }

    function checkSession() {
        request("GET", "/me", null, function (response) {
            if (response.logged_in) {
                showTodos(response.uid);
            } else {
                showAuth();
            }
        });
    }

    $("#registerForm").on("submit", function (event) {
        event.preventDefault();
        var uid = $("#registerUid").val().trim();

        request(
            "POST",
            "/register",
            {
                uname: $("#registerName").val().trim(),
                uid: uid,
                upwd: $("#registerPwd").val()
            },
            function () {
                setStatus("Account created. You can log in now.");
                $("#loginUid").val(uid);
                $("#loginPwd").focus();
                $("#registerForm")[0].reset();
            }
        );
    });

    $("#loginForm").on("submit", function (event) {
        event.preventDefault();
        request(
            "POST",
            "/login",
            {
                uid: $("#loginUid").val().trim(),
                upwd: $("#loginPwd").val()
            },
            function (response) {
                setStatus("Logged in.");
                $("#loginForm")[0].reset();
                showTodos(response.uid);
            }
        );
    });

    $("#todoForm").on("submit", function (event) {
        event.preventDefault();
        request(
            "POST",
            "/todos",
            {
                title: $("#todoTitle").val().trim()
            },
            function () {
                setStatus("Todo added.");
                $("#todoForm")[0].reset();
                loadTodos();
            }
        );
    });

    $("#refreshBtn").on("click", function () {
        loadTodos();
    });

    $logoutBtn.on("click", function () {
        request("POST", "/logout", null, function () {
            setStatus("Logged out.");
            showAuth();
        });
    });

    checkSession();
});
