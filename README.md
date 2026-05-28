# Todo Manager

Flask, SQLite, MySQL, and jQuery based todo CRUD project.

## Features

- Session based register, login, logout
- Todo CRUD API with JSON requests and responses
- SQLite auto initialization with `member` and `todolist` tables
- MySQL query logging with `type`, `sql`, and `datetime` fields
- jQuery AJAX web UI with success and error handlers

## Project Structure

```text
app.py
requirements.txt
templates/index.html
static/script.js
README.md
```

`todo.db` is created automatically when `python app.py` runs.

## SQLite Tables

```sql
CREATE TABLE IF NOT EXISTS member (
    idx INTEGER PRIMARY KEY AUTOINCREMENT,
    uname TEXT NOT NULL,
    uid TEXT NOT NULL UNIQUE,
    upwd TEXT NOT NULL,
    datetime TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS todolist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    uid TEXT NOT NULL,
    completed INTEGER DEFAULT 0,
    datetime TEXT DEFAULT (datetime('now', 'localtime'))
);
```

## MySQL Setup

Create the logging database and user on the MySQL server.

```sql
CREATE DATABASE IF NOT EXISTS query_logger
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'hancom5'@'%' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON query_logger.* TO 'hancom5'@'%';
FLUSH PRIVILEGES;
```

The app creates this MySQL table automatically:

```sql
CREATE TABLE IF NOT EXISTS query_log (
    `type` VARCHAR(20) NOT NULL,
    `sql` TEXT NOT NULL,
    `datetime` DATETIME NOT NULL
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

## Environment Variables

Copy `.env.example` to `.env` and edit the values for your server.

```text
SECRET_KEY=change-this-secret
MYSQL_HOST=192.168.45.50
MYSQL_USER=hancom5
MYSQL_PASSWORD=your_password
MYSQL_DB=query_logger
```

If MySQL variables are not set, the Flask app still runs and SQLite works, but MySQL query logging is disabled.

## Run

```bash
git clone <repository-url>
cd <project-name>
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open:

```text
http://localhost:5000
```

For Windows PowerShell virtualenv activation:

```powershell
.\venv\Scripts\Activate.ps1
```

## API Test Examples

Register:

```bash
curl -c cookies.txt -H "Content-Type: application/json" \
  -d '{"uname":"Test User","uid":"test1","upwd":"1234"}' \
  http://localhost:5000/register
```

Login:

```bash
curl -b cookies.txt -c cookies.txt -H "Content-Type: application/json" \
  -d '{"uid":"test1","upwd":"1234"}' \
  http://localhost:5000/login
```

Create todo:

```bash
curl -b cookies.txt -H "Content-Type: application/json" \
  -d '{"title":"Write README"}' \
  http://localhost:5000/todos
```

Read todos:

```bash
curl -b cookies.txt http://localhost:5000/todos
```

Complete todo:

```bash
curl -b cookies.txt -X PUT -H "Content-Type: application/json" \
  -d '{"completed":true}' \
  http://localhost:5000/todos/1
```

Delete todo:

```bash
curl -b cookies.txt -X DELETE http://localhost:5000/todos/1
```

Check MySQL logs:

```sql
SELECT `type`, `sql`, `datetime`
FROM query_log
ORDER BY `datetime` DESC
LIMIT 10;
```

## Required Endpoints

- `GET /todos`
- `POST /todos`
- `PUT /todos/<id>`
- `DELETE /todos/<id>`

Additional auth endpoints:

- `POST /register`
- `POST /login`
- `POST /logout`
- `GET /me`
