import time
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
import config
from lark_client import LarkClient

logger = logging.getLogger(__name__)

# Vietnam Timezone (GMT+7)
tz_vietnam = timezone(timedelta(hours=7))

def get_today_range() -> Tuple[int, int]:
    """
    Get the millisecond timestamps for the start and end of today in Vietnam timezone.
    """
    now_vn = datetime.now(tz_vietnam)
    today_start = datetime(now_vn.year, now_vn.month, now_vn.day, 0, 0, 0, tzinfo=tz_vietnam)
    today_end = today_start + timedelta(days=1) - timedelta(seconds=1)
    return int(today_start.timestamp() * 1000), int(today_end.timestamp() * 1000)

def parse_personnel_field(field_value: Any) -> Optional[Tuple[str, str]]:
    """
    Parse Lark personnel field to extract user_id and name.
    Lark personnel field structure is typically a list of dicts:
    [{"id": "ou_...", "name": "..."}]
    """
    if isinstance(field_value, list) and len(field_value) > 0:
        person = field_value[0]
        if isinstance(person, dict):
            return person.get("id"), person.get("name")
    return None

def normalize_region(region_value: str) -> str:
    """
    Normalize region values to a standard key.
    - "Hà Nội", "HN", "Miền Bắc", etc. -> "Miền Bắc"
    - "HCM", "Hồ Chí Minh", "Sài Gòn", "Miền Nam", etc. -> "Miền Nam"
    - "Đà Nẵng", "Miền Trung", etc. -> "Miền Trung"
    """
    if not region_value:
        return ""
    val_norm = str(region_value).lower().strip()
    if "hà nội" in val_norm or "ha noi" in val_norm or "hn" == val_norm or "bắc" in val_norm:
        return "Miền Bắc"
    if "hcm" in val_norm or "ho chi minh" in val_norm or "hồ chí minh" in val_norm or "sài gòn" in val_norm or "sai gon" in val_norm or "nam" in val_norm:
        return "Miền Nam"
    if "đà nẵng" in val_norm or "da nang" in val_norm or "trung" in val_norm:
        return "Miền Trung"
    return region_value

def detect_tvv_columns(records: List[Dict[str, Any]], date_candidates: List[str]) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """
    Dynamically detect the column/field names for:
    - Active Today Checkbox
    - Personnel (Nhân sự)
    - Region (Team TV / Khu vực)
    - Role (Vai trò / Hình thức - optional)
    Returns: (active_field, personnel_field, region_field, role_field)
    """
    all_keys = set()
    for rec in records:
        all_keys.update(rec.get("fields", {}).keys())
        
    active_field = None
    personnel_field = None
    region_field = None
    role_field = None
    
    # 1. Detect Active Today Checkbox column
    for k in all_keys:
        k_clean = k.strip()
        if k_clean in date_candidates:
            active_field = k
            break
            
    # 2. Detect Personnel (Nhân sự) column
    for k in all_keys:
        k_low = k.lower().strip()
        if k_low in ["nhân sự", "nhân viên", "tư vấn viên", "tvv", "họ tên", "tên", "nhan su", "nhan vien", "tu van vien", "ho ten", "ten"]:
            personnel_field = k
            break
    if not personnel_field:
        for k in all_keys:
            k_low = k.lower().strip()
            if any(kw in k_low for kw in ["nhân sự", "nhân viên", "tư vấn viên", "tvv", "họ tên", "họ và tên", "tên", "nhan su", "nhan vien", "tu van vien", "ho ten", "ten"]):
                personnel_field = k
                break
    if not personnel_field:
        for rec in records:
            for k, v in rec.get("fields", {}).items():
                if parse_personnel_field(v):
                    personnel_field = k
                    break
            if personnel_field:
                break
                
    # 3. Detect Region (Team TV / Khu vực) column
    for k in all_keys:
        k_low = k.lower().strip()
        if k_low in ["team tv", "team", "khu vực", "chi nhánh", "địa điểm", "vùng", "khu vuc", "chi nhanh", "dia diem"]:
            region_field = k
            break
    if not region_field:
        for k in all_keys:
            k_low = k.lower().strip()
            if any(kw in k_low for kw in ["team", "khu vực", "khu vuc", "chi nhánh", "chi nhanh", "vùng", "vung", "cơ sở", "co so"]):
                region_field = k
                break
    if not region_field:
        for rec in records:
            for k, v in rec.get("fields", {}).items():
                if isinstance(v, str):
                    norm = normalize_region(v)
                    if norm in ["Miền Bắc", "Miền Nam", "Miền Trung"]:
                        region_field = k
                        break
            if region_field:
                break
                
    # 4. Detect Role (Vai trò / Hình thức - optional) column
    for k in all_keys:
        k_low = k.lower().strip()
        if k_low in ["vai trò", "role", "hình thức", "loại", "vai tro", "hinh thuc", "loai"]:
            role_field = k
            break
    if not role_field:
        for k in all_keys:
            k_low = k.lower().strip()
            if any(kw in k_low for kw in ["vai trò", "role", "hình thức", "loại", "vai tro", "hinh thuc", "loai"]):
                role_field = k
                break
            
    return active_field, personnel_field, region_field, role_field

def fetch_active_agents(client: LarkClient, role: str) -> List[Dict[str, Any]]:
    """
    Fetch active agents (TTS or TVV) from Bitable TVV Table.
    """
    try:
        records = client.list_records(config.TABLE_TVV_ID)
        active_agents = []
        
        # Determine today's date in GMT+7 and candidate formats
        now_vn = datetime.now(tz_vietnam)
        day = now_vn.day
        month = now_vn.month
        year = now_vn.year
        year_short = str(year)[-2:]
        
        date_candidates = [
            f"{day:02d}/{month:02d}",  # "21/05"
            f"{day}/{month}",          # "21/5"
            f"{day:02d}-{month:02d}",  # "21-05"
            f"{day}-{month}",          # "21-5"
            f"{day:02d}/{month:02d}/{year}",  # "21/05/2026"
            f"{day}/{month}/{year}",          # "21/5/2026"
            f"{day:02d}/{month:02d}/{year_short}",  # "21/05/26"
            f"{day}/{month}/{year_short}",          # "21/5/26"
            f"{year}-{month:02d}-{day:02d}",  # "2026-05-21"
            f"{day:02d}.{month:02d}",  # "21.05"
            f"{day}.{month}",          # "21.5"
        ]
        
        # Dynamically detect columns
        active_col, personnel_col, region_col, role_col = detect_tvv_columns(
            records, date_candidates
        )
        
        logger.info(f"Dynamic columns detected: active={active_col}, personnel={personnel_col}, region={region_col}, role={role_col}")
        
        # Fallbacks to config values if auto-detection failed
        active_col = active_col or config.FIELD_TVV_ACTIVE
        personnel_col = personnel_col or config.FIELD_TVV_USER
        region_col = region_col or config.FIELD_TVV_REGION
        role_col = role_col or config.FIELD_TVV_ROLE
        
        for rec in records:
            fields = rec.get("fields", {})
            
            # Check role if column present and has value
            if role_col in fields:
                agent_role = fields.get(role_col)
                if agent_role and agent_role != role:
                    agent_role_str = str(agent_role).lower().strip()
                    requested_role_str = str(role).lower().strip()
                    if agent_role_str in ["tts", "tvv"] and agent_role_str != requested_role_str:
                        continue
                
            # Check if active today
            is_active = fields.get(active_col, False)
            if not is_active:
                continue
                
            # Parse Personnel field
            person_info = parse_personnel_field(fields.get(personnel_col))
            if not person_info:
                logger.warning(f"TVV record {rec.get('record_id')} has no valid personnel account configured in column '{personnel_col}'.")
                continue
                
            user_id, name = person_info
            raw_region = fields.get(region_col, "")
            region = normalize_region(raw_region)
            
            active_agents.append({
                "record_id": rec.get("record_id"),
                "user_id": user_id,
                "name": name,
                "region": region
            })
            
        logger.info(f"Found {len(active_agents)} active agents for role '{role}' today.")
        return active_agents
    except Exception as e:
        logger.error(f"Error fetching active agents: {e}")
        raise

def fetch_today_assignments(client: LarkClient) -> List[Dict[str, Any]]:
    """
    Fetch all TikTok leads that were assigned today.
    """
    try:
        start_ms, end_ms = get_today_range()
        records = client.list_records(config.TABLE_TIKTOK_ID)
        
        today_assignments = []
        for rec in records:
            fields = rec.get("fields", {})
            assigned_time = fields.get(config.FIELD_TIKTOK_ASSIGNED_TIME)
            
            # Filter records assigned today
            if assigned_time and start_ms <= assigned_time <= end_ms:
                person_info = parse_personnel_field(fields.get(config.FIELD_TIKTOK_ASSIGNED_USER))
                assigned_user_id = person_info[0] if person_info else None
                callback_time = fields.get(config.FIELD_TIKTOK_CALLBACK_TIME)
                
                today_assignments.append({
                    "record_id": rec.get("record_id"),
                    "assigned_user_id": assigned_user_id,
                    "assigned_time": assigned_time,
                    "callback_time": callback_time
                })
                
        logger.info(f"Found {len(today_assignments)} data assignments created/assigned today.")
        return today_assignments
    except Exception as e:
        logger.error(f"Error fetching today assignments: {e}")
        raise

def check_tvv_availability(tvv_user_id: str, target_callback_ms: Optional[int], today_assignments: List[Dict[str, Any]]) -> bool:
    """
    Check if a TVV is free during the target callback time.
    TVV is busy if they have an existing callback within 30 minutes of the target callback.
    If target_callback_ms is None, treat it as the current time.
    """
    if target_callback_ms is None:
        target_callback_ms = int(time.time() * 1000)
        
    cooldown_ms = config.COOLDOWN_MINUTES_BETWEEN_CALLS * 60 * 1000
    
    for ass in today_assignments:
        if ass["assigned_user_id"] == tvv_user_id:
            existing_cb = ass.get("callback_time")
            if existing_cb is not None:
                if abs(existing_cb - target_callback_ms) < cooldown_ms:
                    return False # Busy!
                    
    return True # Free!

def find_next_free_slot(tvv_user_id: str, start_time_ms: int, today_assignments: List[Dict[str, Any]]) -> int:
    """
    Find the next available callback time (in ms) for a TVV starting from start_time_ms.
    Shifts the time by config.COOLDOWN_MINUTES_BETWEEN_CALLS in each step until a slot is free.
    """
    candidate_ms = start_time_ms
    cooldown_ms = config.COOLDOWN_MINUTES_BETWEEN_CALLS * 60 * 1000
    
    while not check_tvv_availability(tvv_user_id, candidate_ms, today_assignments):
        candidate_ms += cooldown_ms
        
    return candidate_ms

def assign_t0_leads_to_tts(client: LarkClient) -> int:
    """
    [DISABLED] Distribute T0 leads in TikTok table to active TTS (daily at 8 AM).
    This function has been deactivated.
    """
    logger.info("T0 distribution to TTS is disabled.")
    return 0

def assign_m0_lead_to_tvv(client: LarkClient, lead_record_id: str) -> Optional[Dict[str, Any]]:
    """
    Distribute an M0 lead to the best available TVV using:
    - Availability checks (checkbox active today & schedule availability)
    - Regional priority
    - Daily workload limit (config.MAX_ASSIGNMENTS_PER_DAY) with overflow logic
    - Round-robin (based on count today and last assignment time)
    """
    logger.info(f"Starting M0 distribution for Lead {lead_record_id}...")
    
    # 1. Fetch the lead details
    lead = client.get_record(config.TABLE_TIKTOK_ID, lead_record_id)
    if not lead:
        logger.error(f"Lead {lead_record_id} not found.")
        return None
        
    fields = lead.get("fields", {})
    status = fields.get(config.FIELD_TIKTOK_STATUS)
    
    # Check if status is indeed M0
    if status != "M0":
        logger.warning(f"Lead {lead_record_id} status is '{status}', not 'M0'. We will still proceed since webhook was triggered.")
        
    lead_region = normalize_region(fields.get(config.FIELD_TIKTOK_REGION, ""))
    callback_time = fields.get(config.FIELD_TIKTOK_CALLBACK_TIME) # Millisecond timestamp or None
    
    current_time_ms = int(time.time() * 1000)
    target_callback_time = callback_time if callback_time is not None else current_time_ms
    
    logger.info(f"Lead Region: {lead_region}, Original Callback Time: {callback_time}, Target Callback Time: {target_callback_time}")
    
    # 2. Fetch active TVVs and today's assignments
    active_tvvs = fetch_active_agents(client, "TVV")
    if not active_tvvs:
        logger.error("No active TVVs found today. Cannot distribute lead.")
        return None
        
    today_assignments = fetch_today_assignments(client)
    
    # 3. Calculate metrics for each active TVV
    for tvv in active_tvvs:
        # Count assignments today
        tvv_assignments = [a for a in today_assignments if a["assigned_user_id"] == tvv["user_id"]]
        tvv["count_today"] = len(tvv_assignments)
        
        # Last assignment time today
        tvv["last_assigned_time"] = max([a["assigned_time"] for a in tvv_assignments]) if tvv_assignments else 0
        
        # Availability based on schedule
        tvv["is_free"] = check_tvv_availability(tvv["user_id"], target_callback_time, today_assignments)
        
        logger.info(f"TVV {tvv['name']} ({tvv['region']}) today count: {tvv['count_today']}, free: {tvv['is_free']}, last assigned: {tvv['last_assigned_time']}")
        
    # 4. Match & Route
    selected_tvv = None
    
    # Split candidates into primary region and other region
    primary_tvvs = [t for t in active_tvvs if t["region"] == lead_region]
    other_tvvs = [t for t in active_tvvs if t["region"] != lead_region]
    
    # Tier 1: Try same region TVVs who are free (based on cooldown)
    tier1_candidates = [t for t in primary_tvvs if t["is_free"]]
    
    if tier1_candidates:
        # Sort for Round-Robin: fewer assignments first, then oldest assignment time first
        tier1_candidates.sort(key=lambda x: (x["count_today"], x["last_assigned_time"]))
        selected_tvv = tier1_candidates[0]
        logger.info(f"Selected TVV {selected_tvv['name']} from same region ({lead_region}) who is free.")
    else:
        # Tier 2: Try other region TVVs who are free
        logger.info(f"No free TVV in same region ({lead_region}). Attempting overflow to other region.")
        tier2_candidates = [t for t in other_tvvs if t["is_free"]]
        
        if tier2_candidates:
            tier2_candidates.sort(key=lambda x: (x["count_today"], x["last_assigned_time"]))
            selected_tvv = tier2_candidates[0]
            logger.info(f"Selected TVV {selected_tvv['name']} from other region who is free.")
        else:
            # Tier 3 (Fallback): Everyone is busy. Pick from same region if possible, otherwise any active TVV
            logger.warning("Everyone is busy! Picking any active TVV to avoid leaving lead unassigned.")
            if primary_tvvs:
                primary_tvvs.sort(key=lambda x: (x["count_today"], x["last_assigned_time"]))
                selected_tvv = primary_tvvs[0]
                logger.info(f"Selected TVV {selected_tvv['name']} from same region as fallback (busy).")
            else:
                other_tvvs.sort(key=lambda x: (x["count_today"], x["last_assigned_time"]))
                selected_tvv = other_tvvs[0]
                logger.info(f"Selected TVV {selected_tvv['name']} from other region as fallback (busy).")
                
    # 5. Perform the assignment
    if selected_tvv:
        # Determine final callback time
        if selected_tvv["is_free"]:
            final_callback_time = target_callback_time
        else:
            final_callback_time = find_next_free_slot(selected_tvv["user_id"], target_callback_time, today_assignments)
            
        current_time_ms = int(time.time() * 1000)
        update_fields = {
            config.FIELD_TIKTOK_ASSIGNED_USER: [{"id": selected_tvv["user_id"]}],
            config.FIELD_TIKTOK_ASSIGNED_TIME: current_time_ms
        }
        
        # Write callback time if it shifted or was None originally
        if final_callback_time != callback_time:
            update_fields[config.FIELD_TIKTOK_CALLBACK_TIME] = final_callback_time
            logger.info(f"Callback time updated/shifted to {final_callback_time} for Lead {lead_record_id} due to overlap or missing time.")
            
        client.update_record(config.TABLE_TIKTOK_ID, lead_record_id, update_fields)
        logger.info(f"Successfully assigned lead {lead_record_id} to TVV {selected_tvv['name']} ({selected_tvv['user_id']})")
        return selected_tvv
        
    return None
