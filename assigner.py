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

def fetch_active_agents(client: LarkClient, role: str) -> List[Dict[str, Any]]:
    """
    Fetch active agents (TTS or TVV) from Bitable TVV Table.
    """
    try:
        records = client.list_records(config.TABLE_TVV_ID)
        active_agents = []
        
        for rec in records:
            fields = rec.get("fields", {})
            
            # Check role (TTS or TVV)
            agent_role = fields.get(config.FIELD_TVV_ROLE)
            if agent_role != role:
                continue
                
            # Check if active today (checkbox)
            is_active = fields.get(config.FIELD_TVV_ACTIVE, False)
            if not is_active:
                continue
                
            # Parse Personnel field
            person_info = parse_personnel_field(fields.get(config.FIELD_TVV_USER))
            if not person_info:
                logger.warning(f"TVV record {rec.get('record_id')} has no valid personnel account configured.")
                continue
                
            user_id, name = person_info
            region = fields.get(config.FIELD_TVV_REGION, "")
            
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
    """
    if target_callback_ms is None:
        return True # If no callback time, assume TVV is available
        
    cooldown_ms = config.COOLDOWN_MINUTES_BETWEEN_CALLS * 60 * 1000
    
    for ass in today_assignments:
        if ass["assigned_user_id"] == tvv_user_id:
            existing_cb = ass.get("callback_time")
            if existing_cb is not None:
                if abs(existing_cb - target_callback_ms) < cooldown_ms:
                    return False # Busy!
                    
    return True # Free!

def assign_t0_leads_to_tts(client: LarkClient) -> int:
    """
    Distribute T0 leads in TikTok table to active TTS (daily at 8 AM).
    """
    logger.info("Starting T0 distribution to TTS at 8:00 AM...")
    
    # 1. Fetch active TTS
    active_tts = fetch_active_agents(client, "TTS")
    if not active_tts:
        logger.warning("No active TTS found today. Aborting T0 distribution.")
        return 0
        
    # Sort TTS by user ID to make distribution deterministic
    active_tts.sort(key=lambda x: x["user_id"])
    
    # 2. Fetch T0 leads
    all_leads = client.list_records(config.TABLE_TIKTOK_ID)
    t0_leads = [rec for rec in all_leads if rec.get("fields", {}).get(config.FIELD_TIKTOK_STATUS) == "T0"]
    
    if not t0_leads:
        logger.info("No T0 leads found in the TikTok table to distribute.")
        return 0
        
    logger.info(f"Found {len(t0_leads)} T0 leads to distribute to {len(active_tts)} TTS.")
    
    # 3. Distribute leads using round-robin
    updates = []
    current_time_ms = int(time.time() * 1000)
    
    for i, lead in enumerate(t0_leads):
        assigned_tts = active_tts[i % len(active_tts)]
        updates.append({
            "record_id": lead["record_id"],
            "fields": {
                config.FIELD_TIKTOK_ASSIGNED_USER: [{"id": assigned_tts["user_id"]}],
                config.FIELD_TIKTOK_ASSIGNED_TIME: current_time_ms
                # Keep status as T0 or update as needed. User says "TTS nhận data vào mỗi ngày 8 giờ sáng sẽ được phân các data..."
            }
        })
        logger.info(f"Assigning Lead {lead['record_id']} to TTS {assigned_tts['name']} ({assigned_tts['user_id']})")
        
    # 4. Save to Lark
    if updates:
        client.batch_update_records(config.TABLE_TIKTOK_ID, updates)
        logger.info(f"Successfully distributed {len(updates)} T0 leads to TTS.")
        
    return len(updates)

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
        
    lead_region = fields.get(config.FIELD_TIKTOK_REGION, "")
    callback_time = fields.get(config.FIELD_TIKTOK_CALLBACK_TIME) # Millisecond timestamp or None
    
    logger.info(f"Lead Region: {lead_region}, Callback Time: {callback_time}")
    
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
        tvv["is_free"] = check_tvv_availability(tvv["user_id"], callback_time, today_assignments)
        
        logger.info(f"TVV {tvv['name']} ({tvv['region']}) today count: {tvv['count_today']}, free: {tvv['is_free']}, last assigned: {tvv['last_assigned_time']}")
        
    # 4. Match & Route
    selected_tvv = None
    
    # Split candidates into primary region and other region
    primary_tvvs = [t for t in active_tvvs if t["region"] == lead_region]
    other_tvvs = [t for t in active_tvvs if t["region"] != lead_region]
    
    # Tier 1: Try same region TVVs who are free and under the daily limit
    tier1_candidates = [t for t in primary_tvvs if t["is_free"] and t["count_today"] < config.MAX_ASSIGNMENTS_PER_DAY]
    
    if tier1_candidates:
        # Sort for Round-Robin: fewer assignments first, then oldest assignment time first
        tier1_candidates.sort(key=lambda x: (x["count_today"], x["last_assigned_time"]))
        selected_tvv = tier1_candidates[0]
        logger.info(f"Selected TVV {selected_tvv['name']} from same region ({lead_region}) under daily limit.")
    else:
        # Tier 2 (Overflow): Try other region TVVs who are free and under the daily limit
        logger.info(f"Same region ({lead_region}) TVVs are overloaded or busy. Attempting overflow to other region.")
        tier2_candidates = [t for t in other_tvvs if t["is_free"] and t["count_today"] < config.MAX_ASSIGNMENTS_PER_DAY]
        
        if tier2_candidates:
            tier2_candidates.sort(key=lambda x: (x["count_today"], x["last_assigned_time"]))
            selected_tvv = tier2_candidates[0]
            logger.info(f"Selected TVV {selected_tvv['name']} from opposite region due to overflow, under daily limit.")
        else:
            # Tier 3 (Fallback - Overload relaxed): If everyone is overloaded but someone is free, relax limit
            logger.warning("All TVVs under limit are busy or overloaded. Relaxing daily limit rule.")
            tier3_candidates = [t for t in active_tvvs if t["is_free"]]
            
            if tier3_candidates:
                tier3_candidates.sort(key=lambda x: (x["count_today"], x["last_assigned_time"]))
                selected_tvv = tier3_candidates[0]
                logger.info(f"Selected TVV {selected_tvv['name']} (limit relaxed, but free).")
            else:
                # Tier 4 (Extreme Fallback): Everyone is busy and overloaded. Pick any active TVV
                logger.warning("Everyone is busy! Picking any active TVV to avoid leaving lead unassigned.")
                active_tvvs.sort(key=lambda x: (x["count_today"], x["last_assigned_time"]))
                selected_tvv = active_tvvs[0]
                logger.info(f"Selected TVV {selected_tvv['name']} as fallback.")
                
    # 5. Perform the assignment
    if selected_tvv:
        current_time_ms = int(time.time() * 1000)
        update_fields = {
            config.FIELD_TIKTOK_ASSIGNED_USER: [{"id": selected_tvv["user_id"]}],
            config.FIELD_TIKTOK_ASSIGNED_TIME: current_time_ms
        }
        
        client.update_record(config.TABLE_TIKTOK_ID, lead_record_id, update_fields)
        logger.info(f"Successfully assigned lead {lead_record_id} to TVV {selected_tvv['name']} ({selected_tvv['user_id']})")
        return selected_tvv
        
    return None
