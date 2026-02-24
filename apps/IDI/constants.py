from django.db import models

class IDIStatus:
    DRAFT = "draft"
    PUBLISHED = "published"
    STATUS_CHOICES = (
        (DRAFT, "Draft"),
        (PUBLISHED, "Published"),
    )


class DrugClass(models.TextChoices):
    BIGUANIDE = "Biguanide", "Biguanide"
    HMG_COA_REDUCTASE_INHIBITOR_STATIN = "HMG-CoA Reductase Inhibitor (Statin)", "HMG-CoA Reductase Inhibitor (Statin)"
    BETA_LACTAM_ANTIBIOTIC_AMINOPENICILLIN = "Beta-lactam antibiotic (Aminopenicillin)", "Beta-lactam antibiotic (Aminopenicillin)"
    ACE_INHIBITOR = "ACE Inhibitor", "ACE Inhibitor"
    ARB_ANGIOTENSIN_RECEPTOR_BLOCKER = "ARB (Angiotensin Receptor Blocker)", "ARB (Angiotensin Receptor Blocker)"
    BETA_BLOCKER = "Beta Blocker", "Beta Blocker"
    CALCIUM_CHANNEL_BLOCKER = "Calcium Channel Blocker", "Calcium Channel Blocker"
    DIURETIC = "Diuretic", "Diuretic"
    NSAID = "NSAID", "NSAID"
    PROTON_PUMP_INHIBITOR = "Proton Pump Inhibitor", "Proton Pump Inhibitor"
    SSRI = "SSRI", "SSRI"
    BENZODIAZEPINE = "Benzodiazepine", "Benzodiazepine"
    ANTIHISTAMINE = "Antihistamine", "Antihistamine"
    CORTICOSTEROID = "Corticosteroid", "Corticosteroid"
    BRONCHODILATOR = "Bronchodilator", "Bronchodilator"


class TherapeuticCategory(models.TextChoices):
    ANTIDIABETIC = "Antidiabetic", "Antidiabetic"
    ANTILIPEMIC = "Antilipemic", "Antilipemic"
    ANTIBACTERIAL = "Antibacterial", "Antibacterial"
    ANTIHYPERTENSIVE = "Antihypertensive", "Antihypertensive"
    ANALGESIC = "Analgesic", "Analgesic"
    ANTIULCER = "Antiulcer", "Antiulcer"
    ANTIDEPRESSANT = "Antidepressant", "Antidepressant"
    ANXIOLYTIC = "Anxiolytic", "Anxiolytic"
    ANTIALLERGIC = "Antiallergic", "Antiallergic"
    ANTI_INFLAMMATORY = "Anti-inflammatory", "Anti-inflammatory"
    BRONCHODILATOR = "Bronchodilator", "Bronchodilator"
    CARDIOVASCULAR = "Cardiovascular", "Cardiovascular"