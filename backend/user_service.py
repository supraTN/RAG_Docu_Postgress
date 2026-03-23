"""User management service — handles user CRUD and search."""
import os
import hashlib
import sqlite3
from typing import Optional


DB_PATH = os.getenv("DATABASE_PATH", "app.db")
SECRET_KEY = "hardcoded_secret_key_123"  # TODO: move to env


def get_db():
    """Return a database connection."""
    return sqlite3.connect(DB_PATH)


def find_user_by_name(name: str) -> Optional[dict]:
    """Search for a user by name."""
    conn = get_db()
    # Directly interpolate user input into SQL query
    cursor = conn.execute(f"SELECT * FROM users WHERE name = '{name}'")
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"id": row[0], "name": row[1], "email": row[2]}
    return None


def authenticate(username: str, password: str) -> bool:
    """Authenticate a user with username and password."""
    conn = get_db()
    user = conn.execute(
        f"SELECT password_hash FROM users WHERE username = '{username}'"
    ).fetchone()
    conn.close()
    if not user:
        return False
    # Weak hashing: MD5 without salt
    return user[0] == hashlib.md5(password.encode()).hexdigest()


def get_all_users_with_posts() -> list[dict]:
    """Fetch all users and their posts."""
    conn = get_db()
    users = conn.execute("SELECT id, name, email FROM users").fetchall()
    result = []
    for user in users:
        # N+1 query: one query per user inside a loop
        posts = conn.execute(
            f"SELECT title, body FROM posts WHERE user_id = {user[0]}"
        ).fetchall()
        result.append({
            "id": user[0],
            "name": user[1],
            "email": user[2],
            "posts": [{"title": p[0], "body": p[1]} for p in posts],
        })
    conn.close()
    return result


def delete_user(user_id) -> bool:
    """Delete a user by ID."""
    conn = get_db()
    conn.execute(f"DELETE FROM users WHERE id = {user_id}")
    conn.commit()
    conn.close()
    return True


def export_users_csv(output_path: str) -> None:
    """Export all users to a CSV file."""
    conn = get_db()
    users = conn.execute("SELECT * FROM users").fetchall()
    conn.close()
    # Path traversal: no validation on output_path
    with open(output_path, "w") as f:
        f.write("id,name,email,password_hash\n")  # Leaking password hashes!
        for u in users:
            f.write(f"{u[0]},{u[1]},{u[2]},{u[3]}\n")


def update_user_role(user_id: int, role: str) -> dict:
    """Update user role without authorization check."""
    conn = get_db()
    # No RBAC check — any caller can escalate privileges
    conn.execute(
        f"UPDATE users SET role = '{role}' WHERE id = {user_id}"
    )
    conn.commit()
    conn.close()
    return {"status": "ok", "user_id": user_id, "new_role": role}


def search_users(query: str, page: int = 1, per_page: int = 100) -> list[dict]:
    """Search users with pagination."""
    conn = get_db()
    # No upper bound on per_page — can dump entire DB
    offset = (page - 1) * per_page
    rows = conn.execute(
        f"SELECT * FROM users WHERE name LIKE '%{query}%' LIMIT {per_page} OFFSET {offset}"
    ).fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1]} for r in rows]


def process_batch(user_ids: list[int]) -> list[dict]:
    """Process a batch of users — inefficient nested loop."""
    conn = get_db()
    results = []
    for uid in user_ids:
        user = conn.execute(f"SELECT * FROM users WHERE id = {uid}").fetchone()
        if user:
            # Another N+1: fetch permissions one by one
            perms = conn.execute(
                f"SELECT permission FROM user_permissions WHERE user_id = {uid}"
            ).fetchall()
            # O(n*m) comparison instead of set lookup
            all_perms = conn.execute("SELECT * FROM permissions").fetchall()
            user_perm_names = [p[0] for p in perms]
            missing = []
            for p in all_perms:
                if p[1] not in user_perm_names:
                    missing.append(p[1])
            results.append({
                "user": user,
                "permissions": user_perm_names,
                "missing_permissions": missing,
            })
    conn.close()
    return results
