"""
Database layer for the employee tracking app.

- Employees table: weekly salary + 5 daily missing-hour columns (Pzt–Cum)
- payment_history table: weekly payout archive (saved on global reset)

All stored in shop_data.db (sqlite3).
"""
import datetime
import sqlite3

DB_PATH = "shop_data.db"

DAY_COLS = ["miss_pzt", "miss_sal", "miss_car", "miss_per", "miss_cum"]
DAY_KEYS = ["pzt", "sal", "car", "per", "cum"]


def get_connection():
    return sqlite3.connect(DB_PATH)


def _ensure_day_columns(cur):
    cur.execute("PRAGMA table_info(employees)")
    columns = [row[1] for row in cur.fetchall()]
    for col in DAY_COLS:
        if col not in columns:
            cur.execute(f"ALTER TABLE employees ADD COLUMN {col} REAL DEFAULT 0")
    # One-time migration: move old missing_hours into miss_pzt if present
    if "missing_hours" in columns:
        cur.execute(
            "UPDATE employees SET miss_pzt = COALESCE(missing_hours, 0) "
            "WHERE COALESCE(miss_pzt, 0) = 0 AND COALESCE(missing_hours, 0) > 0"
        )
    # Add is_paid column if it doesn't exist yet
    if "is_paid" not in columns:
        cur.execute("ALTER TABLE employees ADD COLUMN is_paid INTEGER DEFAULT 0")
    # Add actual_paid column if it doesn't exist yet
    if "actual_paid" not in columns:
        cur.execute("ALTER TABLE employees ADD COLUMN actual_paid REAL DEFAULT NULL")


def _ensure_payment_history(cur):
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS payment_history (
            id INTEGER PRIMARY KEY,
            emp_name TEXT,
            payment_date TEXT,
            base_salary REAL,
            net_paid REAL,
            missing_summary TEXT,
            actual_paid REAL
        )
        """
    )
    # Migration: add actual_paid column to existing payment_history if missing
    cur.execute("PRAGMA table_info(payment_history)")
    ph_cols = [r[1] for r in cur.fetchall()]
    if "actual_paid" not in ph_cols:
        cur.execute("ALTER TABLE payment_history ADD COLUMN actual_paid REAL")


def init_database():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY,
            name TEXT,
            phone TEXT,
            weekly_salary REAL,
            is_active INTEGER DEFAULT 1,
            miss_pzt REAL DEFAULT 0,
            miss_sal REAL DEFAULT 0,
            miss_car REAL DEFAULT 0,
            miss_per REAL DEFAULT 0,
            miss_cum REAL DEFAULT 0,
            is_paid INTEGER DEFAULT 0,
            actual_paid REAL DEFAULT NULL
        )
        """
    )
    conn.commit()
    _ensure_day_columns(cur)
    _ensure_payment_history(cur)
    conn.commit()

    # Mock data for first run
   
    conn.close()


def mark_as_paid(emp_id, status=1):
    """Mark employee as paid (status=1) or unpaid (status=0). Clears actual_paid when undone."""
    init_database()
    conn = get_connection()
    cur = conn.cursor()
    if status == 0:
        cur.execute("UPDATE employees SET is_paid = 0, actual_paid = NULL WHERE id = ?", (emp_id,))
    else:
        cur.execute("UPDATE employees SET is_paid = 1 WHERE id = ?", (emp_id,))
    conn.commit()
    conn.close()


def set_actual_paid(emp_id, amount):
    """Save the manually entered actual paid amount. Pass None to clear."""
    init_database()
    conn = get_connection()
    cur = conn.cursor()
    value = float(amount) if amount is not None else None
    cur.execute("UPDATE employees SET actual_paid = ? WHERE id = ?", (value, emp_id))
    conn.commit()
    conn.close()


def fetch_active_employees():
    """
    Each row:
      (id, name, phone, weekly_salary, is_active, miss_pzt, miss_sal, miss_car, miss_per, miss_cum, is_paid, actual_paid)
    """
    init_database()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, name, phone, weekly_salary, is_active,
               COALESCE(miss_pzt,0), COALESCE(miss_sal,0), COALESCE(miss_car,0),
               COALESCE(miss_per,0), COALESCE(miss_cum,0), COALESCE(is_paid,0),
               actual_paid
        FROM employees
        WHERE is_active = 1
        ORDER BY name
        """
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_employee(employee_id):
    """
    Row:
      (id, name, phone, weekly_salary, is_active, miss_pzt, miss_sal, miss_car, miss_per, miss_cum, is_paid, actual_paid)
    """
    init_database()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, name, phone, weekly_salary, is_active,
               COALESCE(miss_pzt,0), COALESCE(miss_sal,0), COALESCE(miss_car,0),
               COALESCE(miss_per,0), COALESCE(miss_cum,0), COALESCE(is_paid,0),
               actual_paid
        FROM employees
        WHERE id = ?
        """,
        (employee_id,),
    )
    row = cur.fetchone()
    conn.close()
    return row


def add_employee(name, phone, weekly_salary):
    init_database()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO employees (name, phone, weekly_salary, is_active, miss_pzt, miss_sal, miss_car, miss_per, miss_cum)
        VALUES (?, ?, ?, 1, 0, 0, 0, 0, 0)
        """,
        (
            (name or "").strip(),
            (phone or "").strip(),
            float(weekly_salary) if weekly_salary not in (None, "") else 0.0,
        ),
    )
    conn.commit()
    conn.close()


def update_employee(emp_id, name, phone, weekly_salary):
    init_database()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE employees SET name = ?, phone = ?, weekly_salary = ? WHERE id = ?",
        (
            (name or "").strip(),
            (phone or "").strip(),
            float(weekly_salary) if weekly_salary not in (None, "") else 0.0,
            emp_id,
        ),
    )
    conn.commit()
    conn.close()


def remove_employee(emp_id):
    """Soft delete: mark employee inactive (history remains)."""
    init_database()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE employees SET is_active = 0 WHERE id = ?", (emp_id,))
    conn.commit()
    conn.close()


def add_missing_for_day(employee_id, day_key, hours):
    """day_key in ('pzt','sal','car','per','cum'). Adds hours to that day."""
    if day_key not in DAY_KEYS:
        return
    col = DAY_COLS[DAY_KEYS.index(day_key)]
    init_database()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        f"UPDATE employees SET {col} = COALESCE({col}, 0) + ? WHERE id = ?",
        (float(hours), employee_id),
    )
    conn.commit()
    conn.close()


def set_day_missing(employee_id, day_key, value):
    """Set that day's missing hours to value (clamped 0–10)."""
    if day_key not in DAY_KEYS:
        return
    col = DAY_COLS[DAY_KEYS.index(day_key)]
    init_database()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        f"UPDATE employees SET {col} = ? WHERE id = ?",
        (float(max(0, min(10, value))), employee_id),
    )
    conn.commit()
    conn.close()


def reset_missing_hours(employee_id):
    """Set all 5 day columns to 0 for this employee."""
    init_database()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE employees SET miss_pzt=0, miss_sal=0, miss_car=0, miss_per=0, miss_cum=0 WHERE id = ?",
        (employee_id,),
    )
    conn.commit()
    conn.close()


def reset_all_missing_hours():
    """Set all 5 day columns, is_paid, and actual_paid to 0/NULL for all employees."""
    init_database()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE employees SET miss_pzt=0, miss_sal=0, miss_car=0, miss_per=0, miss_cum=0, is_paid=0, actual_paid=NULL")
    conn.commit()
    conn.close()


def insert_payment(emp_name, payment_date, base_salary, net_paid, missing_summary, actual_paid=None):
    init_database()
    if not payment_date:
        payment_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO payment_history (emp_name, payment_date, base_salary, net_paid, missing_summary, actual_paid)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (emp_name, payment_date, base_salary, net_paid, missing_summary or "", actual_paid),
    )
    conn.commit()
    conn.close()


def fetch_payment_history():
    """Rows: (id, emp_name, payment_date, base_salary, net_paid, missing_summary, actual_paid) newest first."""
    init_database()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, emp_name, payment_date, base_salary, net_paid, missing_summary, actual_paid FROM payment_history ORDER BY id DESC"
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def clear_payment_history():
    """Delete all records from payment_history (employees are not touched)."""
    init_database()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM payment_history")
    conn.commit()
    conn.close()