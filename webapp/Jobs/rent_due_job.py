from datetime import date
from db.database import get_connection


class RentDueJob:

    @staticmethod
    async def run():
        print("[JOB] Rent due insertion started")
        conn = get_connection()
        cur = conn.cursor()

        try:
            cur.execute("""
                Select g.guest_id,b.sharing_type,b.bed_id,brp.monthly_rent,status from guests as a
                JOIN guest_roles AS g ON a.guest_id = g.guest_id
                Left join roles as r ON r.role_id = g.role_id
                Left join guest_beds as gb ON gb.guest_id = g.guest_id
                Left join beds as b ON b.bed_id= gb.bed_id
                Left join bed_rent_plan as brp ON brp.sharing_type = b.sharing_type
                where status <>'closed' and r.role_name ='resident'     
            """)

            rows = cur.fetchall()
            today = date.today()
            # Extract the year and month
            current_year = today.year
            current_month = today.month

            for r in rows:
                guest_id      = r[0]
                # sharing_type  = r[1]
                # bed_id        = r[2]
                # monthly_rent  = r[3]    # <-- IMPORTANT FIX
                # status        = r[4]
                calculated_rent = r[3] or 0
                guest_id = r[0]
                if calculated_rent < 0:
                    calculated_rent = 6000  # Default rent if not found
                # Insert due record
                cur.execute(f"""
                    INSERT INTO dues (guest_id, year, month, due_type_id, due_amount)
                    SELECT '{guest_id}', {current_year}, {current_month}, 1, {calculated_rent}
                    WHERE NOT EXISTS (
                        SELECT 1 FROM dues m
                        WHERE m.guest_id = '{guest_id}'
                        AND m.year = {current_year}
                        AND m.month = {current_month}
                    );
                """)
            conn.commit()

        finally:
            conn.close()



        print("[JOB] Rent due insertion completed")


# async def insert_midnight_data():
#     print("Running midnight job...")
#     conn = get_connection()
#     cur = conn.cursor()

#     try:
#         cur.execute("""
#             Select g.guest_id,b.sharing_type,b.bed_id,brp.monthly_rent,status from guests as a
#             JOIN guest_roles AS g ON a.guest_id = g.guest_id
#             Left join roles as r ON r.role_id = g.role_id
#             Left join guest_beds as gb ON gb.guest_id = g.guest_id
#             Left join beds as b ON b.bed_id= gb.bed_id
#             Left join bed_rent_plan as brp ON brp.sharing_type = b.sharing_type
#             where status <>'closed' and r.role_name ='resident'     
#         """)

#         rows = cur.fetchall()
#         today = date.today()
#         # Extract the year and month
#         current_year = today.year
#         current_month = today.month

#         for r in rows:
#             guest_id      = r[0]
#             # sharing_type  = r[1]
#             # bed_id        = r[2]
#             # monthly_rent  = r[3]    # <-- IMPORTANT FIX
#             # status        = r[4]
#             calculated_rent = r[3] or 0
#             guest_id = r[0]
#             if calculated_rent < 0:
#                 calculated_rent = 6000  # Default rent if not found
#             # Insert due record
#             cur.execute(f"""
#                 INSERT INTO dues (guest_id, year, month, due_type_id, due_amount)
#                 SELECT '{guest_id}', {current_year}, {current_month}, 1, {calculated_rent}
#                 WHERE NOT EXISTS (
#                     SELECT 1 FROM dues m
#                     WHERE m.guest_id = '{guest_id}'
#                     AND m.year = {current_year}
#                     AND m.month = {current_month}
#                 );
#             """)
#         conn.commit()
#         return {"status": "ok"}
#     finally:
#         conn.close()
