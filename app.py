from datetime import datetime
import os
import sqlite3

from flask import Flask, jsonify, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash

try:
    from flask_cors import CORS
except ImportError:
    def CORS(flask_app, *args, **kwargs):
        return flask_app

try:
    import pymysql
except ImportError:
    pymysql = None

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv():
        return False


load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
CORS(app, supports_credentials=True)

DB_PATH = os.getenv("SQLITE_DB_PATH", "todo.db")

MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_HOST"),
    "user": os.getenv("MYSQL_USER"),
    "password": os.getenv("MYSQL_PASSWORD"),
    "database": os.getenv("MYSQL_DB", "query_logger"),
    "charset": "utf8mb4",
}


def mysql_configured():
    if pymysql is None:
        return False

    return all(
        [
            MYSQL_CONFIG.get("host"),
            MYSQL_CONFIG.get("user"),
            MYSQL_CONFIG.get("password"),
            MYSQL_CONFIG.get("database"),
        ]
    )


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def sql_literal(value):
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(value)
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


def build_logged_sql(sql_text, params=()):
    logged_sql = " ".join(sql_text.strip().split())
    for value in params:
        logged_sql = logged_sql.replace("?", sql_literal(value), 1)
    return logged_sql


def init_mysql_log_table():
    if not mysql_configured():
        print("MySQL logging is disabled. Set MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, and MYSQL_DB.")
        return

    try:
        conn = pymysql.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS query_log (
                `type` VARCHAR(20) NOT NULL,
                `sql` TEXT NOT NULL,
                `datetime` DATETIME NOT NULL
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
            """
        )
        conn.commit()
        conn.close()
        print("MySQL query_log table is ready.")
    except Exception as exc:
        print(f"MySQL log table initialization failed: {exc}")


def log_query(logged_sql):
    if not mysql_configured():
        return

    try:
        query_type = logged_sql.strip().split()[0].lower()
        logged_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = pymysql.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO query_log (`type`, `sql`, `datetime`) VALUES (%s, %s, %s)",
            (query_type, logged_sql, logged_at),
        )
        conn.commit()
        conn.close()
    except Exception as exc:
        print(f"Query logging failed: {exc}")


def execute_query(sql_text, params=(), fetch=False):
    logged_sql = build_logged_sql(sql_text, params)
    log_query(logged_sql)

    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(sql_text, params)
        rows = cursor.fetchall() if fetch else None
        last_id = cursor.lastrowid
        conn.commit()
        return rows, last_id
    finally:
        conn.close()


def init_db():
    execute_query(
        """
        CREATE TABLE IF NOT EXISTS member (
            idx INTEGER PRIMARY KEY AUTOINCREMENT,
            uname TEXT NOT NULL,
            uid TEXT NOT NULL UNIQUE,
            upwd TEXT NOT NULL,
            datetime TEXT DEFAULT (datetime('now', 'localtime'))
        )
        """
    )
    execute_query(
        """
        CREATE TABLE IF NOT EXISTS todolist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            uid TEXT NOT NULL,
            completed INTEGER DEFAULT 0,
            datetime TEXT DEFAULT (datetime('now', 'localtime'))
        )
        """
    )


def current_uid():
    return session.get("uid")


def require_login():
    uid = current_uid()
    if not uid:
        return None, (jsonify({"success": False, "message": "Login is required."}), 401)
    return uid, None


def request_json():
    return request.get_json(silent=True) or {}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "mysql_logging": mysql_configured()})


@app.route("/me", methods=["GET"])
def me():
    uid = current_uid()
    return jsonify({"logged_in": bool(uid), "uid": uid})


@app.route("/register", methods=["POST"])
def register():
    data = request_json()
    uname = str(data.get("uname", "")).strip()
    uid = str(data.get("uid", "")).strip()
    upwd = str(data.get("upwd", "")).strip()

    if not uname or not uid or not upwd:
        return jsonify({"success": False, "message": "uname, uid, and upwd are required."}), 400

    rows, _ = execute_query("SELECT uid FROM member WHERE uid = ?", (uid,), fetch=True)
    if rows:
        return jsonify({"success": False, "message": "uid already exists."}), 409

    hashed_password = generate_password_hash(upwd)
    execute_query(
        "INSERT INTO member (uname, uid, upwd) VALUES (?, ?, ?)",
        (uname, uid, hashed_password),
    )
    return jsonify({"success": True, "message": "Registered successfully."}), 201


@app.route("/login", methods=["POST"])
def login():
    data = request_json()
    uid = str(data.get("uid", "")).strip()
    upwd = str(data.get("upwd", "")).strip()

    if not uid or not upwd:
        return jsonify({"success": False, "message": "uid and upwd are required."}), 400

    rows, _ = execute_query("SELECT uid, upwd FROM member WHERE uid = ?", (uid,), fetch=True)
    if not rows:
        return jsonify({"success": False, "message": "Invalid uid or password."}), 401

    member = rows[0]
    if not check_password_hash(member["upwd"], upwd):
        return jsonify({"success": False, "message": "Invalid uid or password."}), 401

    session["uid"] = uid
    return jsonify({"success": True, "message": "Logged in successfully.", "uid": uid})


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True, "message": "Logged out successfully."})


@app.route("/todos", methods=["GET"])
def get_todos():
    uid, error = require_login()
    if error:
        return error

    rows, _ = execute_query(
        """
        SELECT id, title, uid, completed, datetime
        FROM todolist
        WHERE uid = ?
        ORDER BY id DESC
        """,
        (uid,),
        fetch=True,
    )
    todos = []
    for row in rows:
        todo = dict(row)
        todo["completed"] = bool(todo["completed"])
        todos.append(todo)

    return jsonify({"success": True, "todos": todos})


@app.route("/todos", methods=["POST"])
def add_todo():
    uid, error = require_login()
    if error:
        return error

    data = request_json()
    title = str(data.get("title", "")).strip()
    if not title:
        return jsonify({"success": False, "message": "title is required."}), 400

    _, new_id = execute_query(
        "INSERT INTO todolist (title, uid, completed) VALUES (?, ?, 0)",
        (title, uid),
    )
    return jsonify({"success": True, "id": new_id, "message": "Todo created."}), 201


@app.route("/todos/<int:todo_id>", methods=["PUT"])
def update_todo(todo_id):
    uid, error = require_login()
    if error:
        return error

    rows, _ = execute_query(
        "SELECT id, completed FROM todolist WHERE id = ? AND uid = ?",
        (todo_id, uid),
        fetch=True,
    )
    if not rows:
        return jsonify({"success": False, "message": "Todo not found."}), 404

    data = request_json()
    completed = data.get("completed")
    if completed is None:
        completed_value = 1
    else:
        completed_value = 1 if bool(completed) else 0

    execute_query(
        "UPDATE todolist SET completed = ? WHERE id = ? AND uid = ?",
        (completed_value, todo_id, uid),
    )
    return jsonify(
        {
            "success": True,
            "completed": bool(completed_value),
            "message": "Todo updated.",
        }
    )


@app.route("/todos/<int:todo_id>", methods=["DELETE"])
def delete_todo(todo_id):
    uid, error = require_login()
    if error:
        return error

    rows, _ = execute_query(
        "SELECT id FROM todolist WHERE id = ? AND uid = ?",
        (todo_id, uid),
        fetch=True,
    )
    if not rows:
        return jsonify({"success": False, "message": "Todo not found."}), 404

    execute_query("DELETE FROM todolist WHERE id = ? AND uid = ?", (todo_id, uid))
    return jsonify({"success": True, "message": "Todo deleted."})


if __name__ == "__main__":
    init_mysql_log_table()
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
