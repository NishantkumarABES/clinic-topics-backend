EVENT_TYPE_CHOICES = [
    ("webinar", "Webinar"),
    ("conference", "Conference"),
    ("cme", "CME"),
    ("patient_education", "Patient Education"),
    ("workshop", "Workshop"),
]

class EventType:
    WEBINAR = "webinar"
    CONFERENCE = "conference"
    CME = "cme"
    PATIENT_EDUCATION = "patient_education"
    WORKSHOP = "workshop"

    CHOICES = [
        (WEBINAR, "Webinar"),
        (CONFERENCE, "Conference"),
        (CME, "CME"),
        (PATIENT_EDUCATION, "Patient Education"),
        (WORKSHOP, "Workshop")
    ]

class EventFormat:
    LIVE = "live"
    RECORDED = "recorded"
    HYBRID = "hybrid"

    CHOICES = [
        (LIVE, "Live"),
        (RECORDED, "Recorded"),
        (HYBRID, "Hybrid")
    ]

class EventStatus:
    UPCOMING = "upcoming"
    ONGOING = "ongoing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

    CHOICES = [
        (UPCOMING, "Upcoming"),
        (ONGOING, "Ongoing"),
        (COMPLETED, "Completed"),
        (CANCELLED, "Cancelled")
    ]