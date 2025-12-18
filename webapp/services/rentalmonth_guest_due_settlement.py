class GuestDueSettlement:
    """
    Handles all due adjustments during guest move-out.
    Uses ADVANCE + SECURITY to clear outstanding dues.
    """

    CREDIT_TYPES = (2, 3)  # ADVANCE, SECURITY

    def __init__(self, conn):
        self.conn = conn

    # --------------------------------------------------
    # Internal helpers
    # --------------------------------------------------

    def _get_cursor(self):
        return self.conn.cursor()

    def _get_available_credit(self, cur, guest_id):
        """
        Returns usable credit from ADVANCE + SECURITY
        as a positive number
        """
        cur.execute("""
            SELECT COALESCE(SUM(due_amount - amount_paid), 0)
            FROM dues
            WHERE guest_id = ?
              AND due_type_id IN (2, 3)
        """, (guest_id,))
        value = cur.fetchone()[0]
        return abs(value) if value < 0 else 0

    def _get_open_dues(self, cur, guest_id):
        """
        Fetch dues that need to be cleared (excluding credits)
        """
        cur.execute("""
            SELECT id, due_amount, amount_paid
            FROM dues
            WHERE guest_id = ?
              AND (due_amount - amount_paid) > 0
              AND due_type_id NOT IN (2, 3)
            ORDER BY due_type_id, id
        """, (guest_id,))
        return cur.fetchall()

    def _get_credit_rows(self, cur, guest_id):
        """
        Fetch ADVANCE / SECURITY rows for reduction
        """
        cur.execute("""
            SELECT id, due_amount, amount_paid
            FROM dues
            WHERE guest_id = ?
              AND due_type_id IN (2, 3)
              AND (due_amount - amount_paid) < 0
            ORDER BY due_type_id, id
        """, (guest_id,))
        return cur.fetchall()

    # --------------------------------------------------
    # Core settlement logic
    # --------------------------------------------------

    def settle_all_dues(self, guest_id):
        """
        Clears all outstanding dues using available credits.
        Returns final balance after settlement.
        """
        cur = self._get_cursor()

        try:
            credit = self._get_available_credit(cur, guest_id)
            if credit <= 0:
                return self._get_final_balance(cur, guest_id)

            open_dues = self._get_open_dues(cur, guest_id)
            used_credit = 0

            # 1️⃣ Clear dues
            for due_id, due_amount, paid in open_dues:
                if credit <= 0:
                    break

                balance = due_amount - paid
                adjust = min(balance, credit)

                cur.execute("""
                    UPDATE dues
                    SET amount_paid = amount_paid + ?,
                        status = CASE
                            WHEN amount_paid + ? >= due_amount THEN 'paid'
                            ELSE 'partial'
                        END
                    WHERE id = ?
                """, (adjust, adjust, due_id))

                credit -= adjust
                used_credit += adjust

            # 2️⃣ Reduce ADVANCE / SECURITY
            if used_credit > 0:
                self._consume_credit(cur, guest_id, used_credit)

            self.conn.commit()

            return self._get_final_balance(cur, guest_id)

        except Exception:
            self.conn.rollback()
            raise

    # --------------------------------------------------
    # Credit consumption
    # --------------------------------------------------

    def _consume_credit(self, cur, guest_id, amount):
        """
        Reduces ADVANCE / SECURITY based on usage
        """
        credit_rows = self._get_credit_rows(cur, guest_id)

        for due_id, due_amount, paid in credit_rows:
            if amount <= 0:
                break

            available = abs(due_amount - paid)
            consume = min(available, amount)

            cur.execute("""
                UPDATE dues
                SET amount_paid = amount_paid + ?
                WHERE id = ?
            """, (consume, due_id))

            amount -= consume

    # --------------------------------------------------
    # Final balance
    # --------------------------------------------------

    def _get_final_balance(self, cur, guest_id):
        cur.execute("""
            SELECT COALESCE(SUM(due_amount - amount_paid), 0)
            FROM dues
            WHERE guest_id = ?
        """, (guest_id,))
        return cur.fetchone()[0]
