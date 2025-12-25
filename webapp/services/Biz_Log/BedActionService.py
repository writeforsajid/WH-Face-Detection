# class PaymentAllocator:

#     @staticmethod
#     def allocate(cur, rent_payment_id, guest_id, amount):
#         remaining = amount

#         dues = cur.execute("""
#             SELECT id, due_amount, amount_paid
#             FROM dues
#             WHERE guest_id = ?
#               AND status IN ('open','partial')
#             ORDER BY year, month, id
#         """, (guest_id,)).fetchall()

#         for d in dues:
#             if remaining <= 0:
#                 break

#             balance = d["due_amount"] - d["amount_paid"]
#             alloc = min(balance, remaining)

#             cur.execute("""
#                 INSERT INTO rent_payment_allocations
#                 (rent_payment_id, due_id, allocated_amount)
#                 VALUES (?,?,?)
#             """, (rent_payment_id, d["id"], alloc))

#             new_paid = d["amount_paid"] + alloc
#             status = "paid" if new_paid >= d["due_amount"] else "partial"

#             cur.execute("""
#                 UPDATE dues
#                 SET amount_paid=?, status=?
#                 WHERE id=?
#             """, (new_paid, status, d["id"]))

#             remaining -= alloc

#         return remaining

# class PaymentActionService:

#     @staticmethod
#     def approve(cur, rent_payment_id, approver, comment=None):
#         payment = cur.execute("""
#             SELECT guest_id, amount, status
#             FROM rent_payments
#             WHERE rent_payment_id=?
#         """, (rent_payment_id,)).fetchone()

#         if not payment:
#             return

#         if payment["status"] not in ("submitted", "forwarded"):
#             return

#         PaymentAllocator.allocate(
#             cur,
#             rent_payment_id,
#             payment["guest_id"],
#             payment["amount"]
#         )

#         cur.execute("""
#             UPDATE rent_payments
#             SET status='approved_final',
#                 approved_at=datetime('now'),
#                 approved_by=?
#             WHERE rent_payment_id=?
#         """, (approver, rent_payment_id))

#         PaymentActionService._history(
#             cur, rent_payment_id, approver, "approved", comment
#         )

#     @staticmethod
#     def reject(cur, rent_payment_id, actor, comment=None):
#         cur.execute("""
#             UPDATE rent_payments
#             SET status='rejected'
#             WHERE rent_payment_id=?
#         """, (rent_payment_id,))

#         PaymentActionService._history(
#             cur, rent_payment_id, actor, "rejected", comment
#         )

#     @staticmethod
#     def cancel(cur, rent_payment_id, actor, comment=None):
#         # future-safe placeholder
#         cur.execute("""
#             UPDATE rent_payments
#             SET status='cancelled'
#             WHERE rent_payment_id=?
#         """, (rent_payment_id,))

#         PaymentActionService._history(
#             cur, rent_payment_id, actor, "cancelled", comment
#         )

#     @staticmethod
#     def _history(cur, payment_id, actor, action, comment):
#         cur.execute("""
#             INSERT INTO rent_approval_history
#             (rent_payment_id, acted_by, action, comment)
#             VALUES (?,?,?,?)
#         """, (payment_id, actor, action, comment))
