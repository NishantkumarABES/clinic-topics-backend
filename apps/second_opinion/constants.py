class SecondOpinionStatus:
    """Status of an individual doctor's second opinion request."""
    SUBMITTED = "submitted"      # Request sent to doctor
    IN_REVIEW = "in_review"      # Doctor is reviewing
    COMPLETED = "completed"      # Doctor has responded
    CANCELLED = "cancelled"      # Request cancelled

    CHOICES = [
        (SUBMITTED, "Submitted"),
        (IN_REVIEW, "In Review"),
        (COMPLETED, "Completed"),
        (CANCELLED, "Cancelled"),
    ]


class SecondOpinionPaymentStatus:
    """Payment status for second opinion requests."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"

    CHOICES = [
        (PENDING, "Pending"),
        (COMPLETED, "Completed"),
        (FAILED, "Failed"),
        (REFUNDED, "Refunded"),
    ]


class DocumentType:
    """Types of documents that can be uploaded for second opinion."""
    REPORT = "report"
    LAB_RESULT = "lab_result"
    IMAGING = "imaging"
    PRESCRIPTION = "prescription"
    OTHER = "other"

    CHOICES = [
        (REPORT, "Medical Report"),
        (LAB_RESULT, "Lab Result"),
        (IMAGING, "Imaging/Scan"),
        (PRESCRIPTION, "Prescription"),
        (OTHER, "Other"),
    ]
