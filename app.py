# --- LOGIC HELPER FUNCTIONS (UPDATED) ---
def get_pending_status(m_data, driver_ids):
    pending_list = {}
    for idx, row in enumerate(m_data[5:], start=6): 
        # Check column P (Index 15) for Status now, instead of O
        if len(row) > 15:
            d_id = str(row[1]).strip()
            status = str(row[15])  # Changed from 14 to 15
            if "Pending" in status:
                pending_list[d_id] = {
                    "row": idx,
                    "name": row[2],
                    "car": row[3],
                    "start": row[5]
                }
    return pending_list

def get_totals(m_data, driver_ids):
    stats = {d_id: 0 for d_id in driver_ids}
    for row in m_data[5:]: 
        if len(row) > 15:
            d_id = str(row[1]).strip()
            status = str(row[15]) # Changed from 14 to 15
            if d_id in stats and "Done" in status:
                try:
                    # Total is now in Column O (Index 14), previously N (13)
                    val = float(str(row[14]).replace(',', '')) 
                    stats[d_id] += int(val)
                except: pass
    return stats
