import logging
from fastapi import FastAPI, BackgroundTasks, HTTPException, Header, Depends
from pydantic import BaseModel
import os
import config
from lark_client import LarkClient
from assigner import assign_m0_lead_to_tvv, assign_t0_leads_to_tts

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Lark Bitable Lead Distributor", version="1.0.0")
lark_client = LarkClient()

# Security Token (optional, set in .env as WEBHOOK_TOKEN)
WEBHOOK_TOKEN = os.getenv("WEBHOOK_TOKEN", "")

class M0WebhookPayload(BaseModel):
    record_id: str

def verify_token(x_webhook_token: str = Header(default=None)):
    """Optional token verification for security."""
    if WEBHOOK_TOKEN and x_webhook_token != WEBHOOK_TOKEN:
        logger.warning(f"Unauthorized access attempt with token: {x_webhook_token}")
        raise HTTPException(status_code=401, detail="Unauthorized")

def process_m0_assignment(record_id: str):
    """Background task to process the assignment without blocking HTTP response."""
    try:
        config.validate_config()
        result = assign_m0_lead_to_tvv(lark_client, record_id)
        if result:
            logger.info(f"Background task: Lead {record_id} successfully assigned to TVV {result['name']}.")
        else:
            logger.warning(f"Background task: Lead {record_id} could not be assigned to any TVV.")
    except Exception as e:
        logger.error(f"Background task: Error assigning lead {record_id}: {e}")

@app.get("/")
def read_root():
    return {"status": "running", "service": "Lark Lead Distributor"}

@app.get("/health")
def health_check():
    try:
        # Check config validation
        config.validate_config()
        # Verify connection by fetching a token
        lark_client.get_token()
        return {"status": "healthy", "lark_connection": "ok"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

@app.post("/webhook/m0")
def webhook_m0(payload: M0WebhookPayload, background_tasks: BackgroundTasks, authorized: None = Depends(verify_token)):
    """
    Webhook endpoint triggered when a lead's status changes to M0.
    Expects JSON: {"record_id": "recXXXXXXXXX"}
    """
    record_id = payload.record_id
    if not record_id:
        raise HTTPException(status_code=400, detail="Missing record_id in payload")
        
    logger.info(f"Received webhook trigger for M0 Lead: {record_id}")
    
    # Process assignment in the background to avoid Lark webhook timeout (usually 5 seconds)
    background_tasks.add_task(process_m0_assignment, record_id)
    
    return {"status": "received", "record_id": record_id, "message": "Assignment task queued in background"}

@app.post("/cron/daily-t0")
def cron_daily_t0(background_tasks: BackgroundTasks, authorized: None = Depends(verify_token)):
    """
    Endpoint to trigger the daily 8:00 AM T0 data distribution to TTS.
    Can be called by an external scheduler (cron job).
    """
    logger.info("Received request to trigger daily T0 distribution.")
    
    def process_t0():
        try:
            config.validate_config()
            count = assign_t0_leads_to_tts(lark_client)
            logger.info(f"Daily distribution completed. Assigned {count} T0 leads.")
        except Exception as e:
            logger.error(f"Error in daily distribution task: {e}")
            
    background_tasks.add_task(process_t0)
    return {"status": "triggered", "message": "Daily T0 distribution queued in background"}

if __name__ == "__main__":
    import uvicorn
    # Run the server
    uvicorn.run("main:app", host="0.0.0.0", port=config.PORT, reload=True)
