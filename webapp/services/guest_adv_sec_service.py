from db.database import get_connection
from services.face_worker import process_guest_video_async
import random,datetime,os
from utilities.environment_variables import load_environment
import json
from typing import List, Dict
from fastapi import HTTPException
import re
import os, shutil, json, zipfile
from datetime import datetime
from utilities.crypto_manager import crypto
from utilities.email_service import send_email
#from passlib.context import CryptContext
#import ffmpeg

#VIDEOS_PATH = "./data/videos"
load_environment("./../data/.env.webapp")
VIDEOS_PATH=os.getenv("VIDEOS_PATH","./../data/Videos")
STATIC_TEMP_PATH=os.getenv("STATIC_TEMP_PATH","./static/temp")
#pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
#VIDEOS_PATH = "./data/videos"



def get_wallet_statement(guest_id):
    """
    Returns:
        {
            "advance_balance": float,
            "rows": [
                {
                    "amount": float,
                    "date": str,
                    "remarks": str
                },
                ...
            ]
        }
    """
    conn = get_connection()
    cur = conn.cursor()
    # 1️⃣ Fetch wallet account
    cur.execute("""
        SELECT id
        FROM wallet_accounts
        WHERE guest_id = ?
    """, (guest_id,))

    row = cur.fetchone()
    if not row:
        return {
            "advance_balance": 0,
            "rows": []
        }

    wallet_id = row["id"]

    # 2️⃣ Fetch transactions
    cur.execute("""
        SELECT
            amount,
            created_at AS date,
            remarks
        FROM wallet_transactions
        WHERE wallet_id = ?
        ORDER BY created_at ASC
    """, (wallet_id,))

    rows = [
        {
            "amount": float(r["amount"]),
            "date": r["date"],
            "remarks": r["remarks"]
        }
        for r in cur.fetchall()
    ]

    # 3️⃣ Total balance
    cur.execute("""
        SELECT COALESCE(SUM(amount), 0) AS balance
        FROM wallet_transactions
        WHERE wallet_id = ?
    """, (wallet_id,))

    total_balance = float(cur.fetchone()["balance"])
    conn.close()
    return {
        "advance_balance": total_balance,
        "rows": rows
    }




def get_security_statement(guest_id):
    """
    Returns:
        {
            "security_balance": float,
            "rows": [
                {
                    "amount": float,
                    "date": str,
                    "remarks": str,
                    "txn_type": str
                }
            ]
        }
    """
    conn = get_connection()
    cur = conn.cursor()
    # 1️⃣ Fetch security account
    cur.execute("""
        SELECT id
        FROM security_accounts
        WHERE guest_id = ?
    """, (guest_id,))

    row = cur.fetchone()
    if not row:
        return {
            "security_balance": 0,
            "rows": []
        }

    security_id = row["id"]

    # 2️⃣ Fetch transactions
    cur.execute("""
        SELECT
            amount,
            txn_type,
            created_at AS date,
            remarks
        FROM security_transactions
        WHERE security_id = ?
        ORDER BY created_at ASC
    """, (security_id,))

    rows = [
        {
            "amount": float(r["amount"]),
            "txn_type": r["txn_type"],
            "date": r["date"],
            "remarks": r["remarks"]
        }
        for r in cur.fetchall()
    ]

    # 3️⃣ Compute net security balance
    cur.execute("""
        SELECT COALESCE(SUM(
            CASE
                WHEN txn_type = 'received' THEN amount
                WHEN txn_type IN ('adjusted','refunded') THEN -amount
                ELSE 0
            END
        ), 0) AS balance
        FROM security_transactions
        WHERE security_id = ?
    """, (security_id,))

    security_balance = float(cur.fetchone()["balance"])
    conn.close()
    return {
        "security_balance": security_balance,
        "rows": rows
    }
