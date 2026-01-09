from django.db import models
from django.conf import settings
from core.models import TimeStampedUUIDModel
from apps.CIMS.constants import CIMSStatus


class CIMS(TimeStampedUUIDModel):
    # Basic Drug Information
    drug_name_generic = models.CharField(max_length=255)
    drug_class = models.CharField(max_length=255)
    therapeutic_category = models.CharField(max_length=255)
    brands_in_india = models.TextField()
    strengths_available = models.TextField()
    formulations_routes = models.TextField()

    # Clinical Information
    core_clinical_role = models.TextField()
    preferred_clinical_scenarios = models.TextField()
    where_benefit_limited = models.TextField()

    # Dosing Information
    usual_adult_dose = models.TextField()
    timing_relative_to_meals = models.TextField()
    review_duration_plan = models.TextField()

    # Safety Information
    common_adverse_effects = models.TextField()
    serious_but_uncommon_risks = models.TextField()
    long_term_therapy_cautions = models.TextField()

    # Evidence Base
    guidelines = models.TextField(blank=True)
    landmark_trials = models.TextField(blank=True)

    # Metadata
    status = models.CharField(
        max_length=20,
        choices=CIMSStatus.STATUS_CHOICES,
        default="draft"
    )

    class Meta(TimeStampedUUIDModel.Meta):
        db_table = "cims"
        indexes = [
            models.Index(fields=["drug_name_generic"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return self.drug_name_generic


class CIMSKeyInteraction(TimeStampedUUIDModel):
    cims = models.ForeignKey(
        CIMS,
        on_delete=models.CASCADE,
        related_name="key_interactions"
    )

    interaction_title = models.CharField(max_length=255)
    clinical_impact = models.TextField()
    what_to_do = models.TextField()

    class Meta:
        db_table = "cims_key_interactions"
        ordering = ["created_at"]

    def __str__(self):
        return self.interaction_title


class CIMSPracticalPearl(TimeStampedUUIDModel):
    cims = models.ForeignKey(
        CIMS,
        on_delete=models.CASCADE,
        related_name="practical_prescribing_pearls"
    )

    pearl_title = models.CharField(max_length=255)
    pearl_content = models.TextField()

    class Meta:
        db_table = "cims_practical_pearls"
        ordering = ["created_at"]

    def __str__(self):
        return self.pearl_title
