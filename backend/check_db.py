import sys
sys.path.insert(0, '.')
from app.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    # Check pending leads count
    r1 = db.execute(text("SELECT COUNT(*) FROM leads WHERE qualification_status = 'pending'"))
    pending = r1.scalar()
    print(f'Pending leads: {pending}')

    # Check auto_campaign columns exist
    r2 = db.execute(text("SELECT COUNT(*) FROM auto_discovery_settings"))
    settings_count = r2.scalar()
    print(f'Auto discovery settings rows: {settings_count}')

    # Check active campaigns
    r3 = db.execute(text("SELECT COUNT(*) FROM campaigns WHERE status = 'active'"))
    active_campaigns = r3.scalar()
    print(f'Active campaigns: {active_campaigns}')

    # Check pending_ai campaign leads
    r4 = db.execute(text("SELECT COUNT(*) FROM campaign_leads WHERE status = 'pending_ai'"))
    pending_ai = r4.scalar()
    print(f'Campaign leads pending_ai: {pending_ai}')

    # Check auto discovery settings
    try:
        r5 = db.execute(text("SELECT user_id, enabled, auto_campaign_enabled, auto_campaign_email_account_ids FROM auto_discovery_settings LIMIT 5"))
        rows = r5.fetchall()
        print(f'Settings rows found: {len(rows)}')
        for row in rows:
            print(f'  User: {str(row[0])[:8]}... enabled={row[1]} auto_campaign={row[2]} accounts={row[3]}')
    except Exception as e:
        print(f'auto_campaign columns error: {e}')

except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
finally:
    db.close()
