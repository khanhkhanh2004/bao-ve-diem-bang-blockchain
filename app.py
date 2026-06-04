
from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import hashlib
from datetime import datetime
from web3 import Web3
import json
from pathlib import Path

app = Flask(__name__)
app.secret_key = "gradechain-real-secret"

DB_PATH = "gradechain.db"
CONFIG_PATH = Path("contract_config.json")


# =========================
# Hash điểm
# =========================
def make_grade_hash(student_id, student_name, subject, score, semester):
    raw = f"{student_id}|{student_name}|{subject}|{score}|{semester}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# =========================
# Database SQLite
# =========================
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS grades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            student_name TEXT NOT NULL,
            subject TEXT NOT NULL,
            score TEXT NOT NULL,
            semester TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS grade_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grade_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            old_score TEXT,
            new_score TEXT,
            reason TEXT,
            tx_hash TEXT NOT NULL,
            data_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


# =========================
# Kết nối Smart Contract
# =========================
def load_contract_config():
    if not CONFIG_PATH.exists():
        return None

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_contract():
    config = load_contract_config()

    if not config:
        return None, None, "Chưa có file contract_config.json"

    ganache_url = config["ganache_url"]
    contract_address = config["contract_address"]
    abi = config["abi"]

    w3 = Web3(Web3.HTTPProvider(ganache_url))

    if not w3.is_connected():
        return None, None, "Không kết nối được Ganache"

    contract = w3.eth.contract(
        address=Web3.to_checksum_address(contract_address),
        abi=abi
    )

    return w3, contract, None


# =========================
# Ghi hash lên blockchain
# =========================
def store_hash_on_blockchain(
    grade_id,
    action,
    data_hash
):
    w3, contract, error = get_contract()

    if error:
        raise Exception(error)

    account = w3.eth.accounts[0]

    tx_hash = contract.functions.storeHash(
        int(grade_id),
        action,
        data_hash
    ).transact({
        "from": account
    })

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    return receipt.transactionHash.hex()


# =========================
# Lấy hash mới nhất
# =========================
def get_hash_from_blockchain(grade_id):
    w3, contract, error = get_contract()

    if error:
        raise Exception(error)

    return contract.functions.getLatestHash(
        int(grade_id)
    ).call()


# =========================
# Lấy lịch sử blockchain
# =========================
def get_history_from_blockchain(grade_id):
    w3, contract, error = get_contract()

    if error:
        raise Exception(error)

    count = contract.functions.getHistoryCount(
        int(grade_id)
    ).call()

    history = []

    for i in range(count):

        record = contract.functions.getHistoryItem(
            int(grade_id),
            i
        ).call()

        history.append({
            "action": record[0],
            "data_hash": record[1],
            "timestamp": record[2],
            "sender": record[3]
        })

    return history


# =========================
# Trang chủ
# =========================
@app.route("/")
def index():

    conn = get_conn()

    grades = conn.execute("""
        SELECT * FROM grades
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    config_exists = CONFIG_PATH.exists()

    return render_template(
        "index.html",
        grades=grades,
        config_exists=config_exists
    )


# =========================
# Thêm điểm
# =========================
@app.route("/add", methods=["POST"])
def add_grade():

    student_id = request.form["student_id"].strip()
    student_name = request.form["student_name"].strip()
    subject = request.form["subject"].strip()
    score = request.form["score"].strip()
    semester = request.form["semester"].strip()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO grades
        (
            student_id,
            student_name,
            subject,
            score,
            semester,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        student_id,
        student_name,
        subject,
        score,
        semester,
        now,
        now
    ))

    grade_id = cur.lastrowid

    data_hash = make_grade_hash(
        student_id,
        student_name,
        subject,
        score,
        semester
    )

    try:

        tx_hash = store_hash_on_blockchain(
            grade_id,
            "CREATE",
            data_hash
        )

        cur.execute("""
            INSERT INTO grade_logs
            (
                grade_id,
                action,
                old_score,
                new_score,
                reason,
                tx_hash,
                data_hash,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            grade_id,
            "CREATE_GRADE",
            None,
            score,
            "Nhập điểm ban đầu",
            tx_hash,
            data_hash,
            now
        ))

        conn.commit()

        flash(
            "Đã nhập điểm và ghi blockchain thành công!",
            "success"
        )

    except Exception as e:

        conn.rollback()

        flash(
            f"Lỗi blockchain: {e}",
            "danger"
        )

    conn.close()

    return redirect(url_for("index"))


# =========================
# Chi tiết điểm
# =========================
@app.route("/detail/<int:grade_id>")
def detail(grade_id):

    conn = get_conn()

    grade = conn.execute("""
        SELECT * FROM grades
        WHERE id = ?
    """, (grade_id,)).fetchone()

    logs = conn.execute("""
        SELECT * FROM grade_logs
        WHERE grade_id = ?
        ORDER BY id ASC
    """, (grade_id,)).fetchall()

    conn.close()

    if not grade:
        return "Không tìm thấy điểm"

    current_hash = make_grade_hash(
        grade["student_id"],
        grade["student_name"],
        grade["subject"],
        grade["score"],
        grade["semester"]
    )

    latest_blockchain_hash = ""
    blockchain_history = []
    blockchain_error = None

    try:

        latest_blockchain_hash = get_hash_from_blockchain(
            grade_id
        )

        blockchain_history = get_history_from_blockchain(
            grade_id
        )

    except Exception as e:

        blockchain_error = str(e)

    is_valid = current_hash == latest_blockchain_hash

    return render_template(
        "detail.html",
        grade=grade,
        logs=logs,
        current_hash=current_hash,
        latest_blockchain_hash=latest_blockchain_hash,
        blockchain_history=blockchain_history,
        blockchain_error=blockchain_error,
        is_valid=is_valid
    )


# =========================
# Cập nhật điểm hợp lệ
# =========================
@app.route("/update/<int:grade_id>", methods=["POST"])
def update_grade(grade_id):

    new_score = request.form["new_score"].strip()

    reason = request.form["reason"].strip() or "Cập nhật điểm hợp lệ"

    conn = get_conn()
    cur = conn.cursor()

    grade = cur.execute("""
        SELECT * FROM grades
        WHERE id = ?
    """, (grade_id,)).fetchone()

    if not grade:
        conn.close()
        return "Không tìm thấy điểm"

    old_score = grade["score"]

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    new_hash = make_grade_hash(
        grade["student_id"],
        grade["student_name"],
        grade["subject"],
        new_score,
        grade["semester"]
    )

    try:

        tx_hash = store_hash_on_blockchain(
            grade_id,
            "UPDATE",
            new_hash
        )

        cur.execute("""
            UPDATE grades
            SET score = ?, updated_at = ?
            WHERE id = ?
        """, (
            new_score,
            now,
            grade_id
        ))

        cur.execute("""
            INSERT INTO grade_logs
            (
                grade_id,
                action,
                old_score,
                new_score,
                reason,
                tx_hash,
                data_hash,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            grade_id,
            "UPDATE_GRADE",
            old_score,
            new_score,
            reason,
            tx_hash,
            new_hash,
            now
        ))

        conn.commit()

        flash(
            "Đã cập nhật điểm và ghi blockchain!",
            "success"
        )

    except Exception as e:

        conn.rollback()

        flash(
            f"Lỗi blockchain: {e}",
            "danger"
        )

    conn.close()

    return redirect(url_for("detail", grade_id=grade_id))


# =========================
# Sửa lén database
# =========================
@app.route("/tamper/<int:grade_id>", methods=["POST"])
def tamper_grade(grade_id):

    fake_score = request.form["fake_score"].strip()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_conn()

    conn.execute("""
        UPDATE grades
        SET score = ?, updated_at = ?
        WHERE id = ?
    """, (
        fake_score,
        now,
        grade_id
    ))

    conn.commit()
    conn.close()

    flash(
        "Đã sửa database nhưng KHÔNG ghi blockchain",
        "warning"
    )

    return redirect(url_for("detail", grade_id=grade_id))


# =========================
# Reset database
# =========================
@app.route("/reset")
def reset():

    conn = get_conn()

    conn.execute("DROP TABLE IF EXISTS grades")
    conn.execute("DROP TABLE IF EXISTS grade_logs")

    conn.commit()
    conn.close()

    init_db()

    flash(
        "Đã reset database",
        "info"
    )

    return redirect(url_for("index"))


# =========================
# Main
# =========================
if __name__ == "__main__":

    init_db()

    app.run(debug=True)

