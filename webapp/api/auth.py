from fastapi import APIRouter, HTTPException, Depends, Header, Request
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from db.database import get_connection
from utilities.passwords import hash_password, verify_password
from datetime import datetime, timedelta, timezone
import sqlite3
import uuid


router = APIRouter(prefix="/auth", tags=["Auth"])


class SignupRequest(BaseModel):
    guest_id: Optional[str] = Field(None, description="Existing guest_id. If omitted, a new guest will be created.")
    full_name: str = Field(..., min_length=2)
    email: EmailStr
    password: str = Field(..., min_length=6)
    phone_number: Optional[str] = Field(None, description="Phone number of the guest")
    role_name: Optional[str] = Field("residence", description="owner | residence | employee")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _get_guest_phone(cur: sqlite3.Cursor, guest_id: str) -> Optional[str]:
    """Return the guest's phone number from whichever column exists.

    Supports either `phone_number` or legacy `phone` column. Returns None if
    neither column exists or no value is set for the guest.
    """
    try:
        cur.execute("PRAGMA table_info(guests)")
        cols = [str(row[1]).lower() for row in cur.fetchall()]
        phone_col = None
        for c in ("phone_number", "phone"):
            if c in cols:
                phone_col = c
                break
        if not phone_col:
            return None

        # Safe because phone_col is derived from PRAGMA, not user input
        cur.execute(f"SELECT {phone_col} FROM guests WHERE guest_id = ?", (guest_id,))
        r = cur.fetchone()
        return r[0] if r and r[0] else None
    except sqlite3.Error:
        return None


@router.post("/signup")
def signup(payload: SignupRequest, request: Request):
    """Create guest (if needed), store credentials, and assign a role."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        # Ensure email unique in guest_auth
        cur.execute("SELECT guest_id FROM guest_auth WHERE email = ?", (str(payload.email),))
        row = cur.fetchone()
        if row:
            raise HTTPException(status_code=409, detail="Email already registered")

        gid = payload.guest_id

        # Create guest if not provided
        if not gid:
            # Generate a simple guest id if not provided
            gid = datetime.utcnow().strftime("%Y%m%d%H%M%S") + uuid.uuid4().hex[:4]
            
            # Determine guest_type (default to 'Resident')
            # Map from lowercase to capitalized values
            role_mapping = {
                'owner': 'Owner',
                'employee': 'Employee',
                'residence': 'Resident',
                'resident': 'Resident',
                'others': 'Others'
            }
            guest_type = role_mapping.get((payload.role_name or "resident").lower(), 'Resident')
            
            cur.execute(
                "INSERT INTO guests (guest_id, name, email, password, phone_number, guest_type, status) VALUES (?,?,?,?,?,?,'active')",
                (gid, payload.full_name, str(payload.email), payload.password, payload.phone_number, guest_type),
            )
        else:
            # Ensure guest exists; if exists, update email, password, and phone_number
            cur.execute("SELECT guest_id FROM guests WHERE guest_id = ?", (gid,))
            existing = cur.fetchone()
            
            # Determine guest_type (default to 'Resident')
            role_mapping = {
                'owner': 'Owner',
                'employee': 'Employee',
                'residence': 'Resident',
                'resident': 'Resident',
                'others': 'Others'
            }
            guest_type = role_mapping.get((payload.role_name or "resident").lower(), 'Resident')
            
            if not existing:
                # create guest row if provided gid not present
                cur.execute(
                    "INSERT INTO guests (guest_id, name, email, password, phone_number, guest_type, status) VALUES (?,?,?,?,?,?,'active')",
                    (gid, payload.full_name, str(payload.email), payload.password, payload.phone_number, guest_type),
                )
            else:
                # Update existing guest with email, password, phone_number and guest_type
                cur.execute(
                    "UPDATE guests SET name=?, email=?, password=?, phone_number=?, guest_type=? WHERE guest_id=?",
                    (payload.full_name, str(payload.email), payload.password, payload.phone_number, guest_type, gid),
                )

        # Insert auth credentials
        pwd_hash = hash_password(payload.password)
        cur.execute(
            "INSERT INTO guest_auth (guest_id, email, password_hash, is_active) VALUES (?,?,?,1)",
            (gid, str(payload.email), pwd_hash),
        )

        conn.commit()
        return {"status": "ok", "guest_id": gid, "email": str(payload.email), "role": guest_type}
    except sqlite3.IntegrityError as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Integrity error: {e}")
    finally:
        conn.close()


@router.post("/login")
def login(payload: LoginRequest, request: Request, user_agent: Optional[str] = Header(None)):
    
    conn = get_connection()

    cur = conn.cursor()
    try:
        # Verify credentials from guests table and check auth flags
        cur.execute(
            """
            SELECT 
                g.guest_id,
                g.name,
                g.email,
                g.password,
                g.guest_type,
                g.status,
                COALESCE(ga.is_active, 1) AS auth_active
            FROM guests g
            LEFT JOIN guest_auth ga ON ga.email = g.email
            WHERE g.email = ?
            """,
            (str(payload.email),),
        )
        row = cur.fetchone()
        
        if not row:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        guest_id = row[0]
        name = row[1]
        email = row[2]
        stored_password = row[3]  # Plain text password from guests table
        guest_type = row[4] if row[4] else 'Resident'
        status = (row[5] or '').lower()
        auth_active = int(row[6] or 1)

        # Check if account is enabled: block only if explicitly disabled in auth or status is 'closed'
        if auth_active != 1 or status == 'closed':
            raise HTTPException(status_code=403, detail="Account is disabled")
        
        # Verify password (plain text comparison)
        if stored_password != payload.password:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        
        # Create session
        token = uuid.uuid4().hex
        now = _now_utc()
        expires = now + timedelta(days=7)
        ip = request.client.host if request.client else None
        cur.execute(
            "INSERT INTO guest_sessions (session_id, guest_id, created_at, expires_at, user_agent, ip_address, revoked) VALUES (?,?,?,?,?,?,0)",
            (token, guest_id, _iso(now), _iso(expires), user_agent, ip),
        )
        
        # Map guest_type to lowercase role for frontend
        role_mapping = {
            'Owner': 'owner',
            'Employee': 'employee',
            'Resident': 'residence',
            'Others': 'others'
        }
        role = role_mapping.get(guest_type, 'residence')

        conn.commit()
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_at": _iso(expires),
            "guest": {"guest_id": guest_id, "name": name, "email": email, "role": role, "guest_type": guest_type},
        }
    finally:
        conn.close()


def _require_token(auth_header: Optional[str]) -> str:
    if not auth_header or not auth_header.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    return auth_header.split(" ", 1)[1].strip()


@router.get("/me")
def me(authorization: Optional[str] = Header(None)):
    token = _require_token(authorization)
    conn = get_connection()
    cur = conn.cursor()
    try:
        now_iso = _iso(_now_utc())
        cur.execute(
            """
            SELECT gs.guest_id, g.name, ga.email, g.guest_type, gs.expires_at, gs.revoked
            FROM guest_sessions gs
            JOIN guests g ON g.guest_id = gs.guest_id
            LEFT JOIN guest_auth ga ON ga.guest_id = gs.guest_id
            WHERE gs.session_id = ? AND gs.expires_at > ?
            """,
            (token, now_iso),
        )
        row = cur.fetchone()
        if not row or int(row[5] or 0) == 1:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
        # Map guest_type to lowercase role for frontend
        guest_type = row[3]
        role_mapping = {
            'Owner': 'owner',
            'Employee': 'employee',
            'Resident': 'residence',
            'Others': 'others'
        }
        role = role_mapping.get(guest_type, 'residence')
        
        return {
            "guest_id": row[0],
            "name": row[1],
            "email": row[2],
            "role": role,
            "expires_at": row[4],
        }
    finally:
        conn.close()


@router.post("/logout")
def logout(authorization: Optional[str] = Header(None)):
    token = _require_token(authorization)
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE guest_sessions SET revoked = 1 WHERE session_id = ?", (token,))
        conn.commit()
        return {"status": "ok"}
    finally:
        conn.close()
