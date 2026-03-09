from django.db import models

class OrderStatus(models.TextChoices):
    PENDING_PAYMENT = 'pending_payment', 'Pending Payment'
    PAID = 'paid', 'Paid'
    CANCELLED = 'cancelled', 'Cancelled'
    REFUNDED = 'refunded', 'Refunded'

class PaymentMethod(models.TextChoices):
    CARD = "card", "Credit/Debit Card"
    UPI = "upi", "UPI"
    NETBANKING = "netbanking", "Net Banking"
    WALLET = "wallet", "Wallet"
    COD = "cod", "Cash on Delivery"

class Status(models.TextChoices):
    PENDING = "pending", "Pending Review"
    INREVIEW = "in_review", "Under Review"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"

class AccessLevel(models.TextChoices):
    PUBLIC = "public", "Public"
    INSTITUTIONAL = "institutional", "Institutional"
    PHYSICIANS = "physicians", "Verified Physicians"
    PRIVATE = "private", "Private"

class CopyrightStatus(models.TextChoices):
    OPEN = "open", "Open Access / Public Domain"
    AUTHOR = "author", "Author Owned"
    INSTITUTIONAL = "institutional", "Institutional License"
    PUBLISHER = "publisher", "Publisher Authorization"
    FAIR_USE = "fair_use", "Educational Fair Use"

class BookType(models.TextChoices):
    TEXTBOOK = "textbook", "Textbook"
    HANDBOOK = "handbook", "Handbook"
    GUIDELINE = "guideline", "Guideline"
    REVIEW = "review", "Review Article"

SPECIALTY_BOOK_CATEGORIES = {
    "General Medicine": "Internal Medicine & Clinical Practice",
    "General Surgery": "General Surgery",
    "Cardiology": "Cardiology & Heart Health",
    "Nephrology": "Kidney Diseases & Nephrology",
    "Neurology": "Neurology & Neuroscience",
    "Endocrinology": "Endocrinology & Metabolic Disorders",
    "Medical Oncology": "Medical Oncology & Cancer Therapy",
    "Pediatrics and Adolescent Medicine": "Pediatrics & Child Health",
    "Family Medicine and Geriatric Medicine": "Family Medicine & Primary Care",
    "Emergency Medicine": "Emergency & Trauma Medicine",
    "Anaesthesiology": "Anaesthesiology & Pain Management",
    "Intensive Care Medicine": "Critical Care Medicine",
    "Dermatology": "Dermatology & Skin Disorders",
    "Cosmetology": "Cosmetic Dermatology & Aesthetic Medicine",
    "Pulmonology": "Pulmonology & Respiratory Medicine",
    "Rheumatology": "Rheumatology & Autoimmune Diseases",
    "Diagnostic & Clinical Radiology": "Diagnostic Radiology & Imaging",
    "Interventional Radiology": "Interventional Radiology",
    "Forensic Medicine & Toxicology": "Forensic Medicine & Toxicology",
    "Microbiology & Hospital Infection Control": "Medical Microbiology & Infection Control",
    "Pathology & Oncopathology": "Pathology & Laboratory Medicine",
    "Haematology": "Hematology & Blood Disorders",
    "Biochemistry": "Medical Biochemistry",
    "Radiation Oncology": "Radiation Oncology",
    "Nuclear Medicine": "Nuclear Medicine & Molecular Imaging",
    "Psychiatry": "Psychiatry & Mental Health",
    "Clinical Psychology": "Clinical Psychology & Behavioral Science",
    "Clinical Pharmacology": "Clinical Pharmacology & Therapeutics",
    "Ophthalmology": "Ophthalmology & Vision Science",
    "Neurosurgery": "Neurosurgery",
    "Cardiothoracic Surgery": "Cardiothoracic Surgery",
    "Vascular Surgery": "Vascular Surgery",
    "Orthopaedic Surgery": "Orthopedics & Musculoskeletal Surgery",
    "ENT": "Otolaryngology (ENT)",
    "Head and Neck Surgery": "Head & Neck Surgery",
    "Plastic & Cosmetic Surgery": "Plastic & Reconstructive Surgery",
    "Urology & Transplant Surgery": "Urology & Renal Transplant Surgery",
    "Gastrointestinal Surgery & Transplant Surgery": "Gastrointestinal & Hepatobiliary Surgery",
    "Paediatric Surgery": "Pediatric Surgery",
    "Surgical Oncology": "Surgical Oncology",
    "Maxillofacial Surgery": "Oral & Maxillofacial Surgery",
    "Dentistry & Somatology": "Dentistry & Oral Health",
    "Obstetrics & Gynaecology": "Obstetrics & Gynecology",
    "Geriatric & Palliative Medicine": "Geriatric Medicine & Palliative Care",
    "Physiotherapy & Rehabilitation": "Physiotherapy & Rehabilitation Medicine",
    "Nutrition & Dietetics": "Nutrition, Dietetics & Lifestyle Medicine",
    "Sports Medicine": "Sports Medicine & Exercise Science",
    "Gastroenterology": "Gastroenterology & Digestive Diseases",
}