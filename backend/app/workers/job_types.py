from enum import StrEnum


class JobType(StrEnum):
    EMAIL_SEND = "email_send"
    FOLLOW_UP = "follow_up"
    REPLY_SYNC = "reply_sync"
    DELIVERY_SYNC = "delivery_sync"
    WEBSITE_SCAN = "website_scan"
    AI_ANALYSIS = "ai_analysis"