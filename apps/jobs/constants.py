from django.db import models

class JobStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PENDING_REVIEW = "pending_review", "Pending Review"
    PUBLISHED = "published", "Published"
    ARCHIVED = "archived", "Archived"


class WorkplaceType(models.TextChoices):
    ON_SITE = "on_site", "On-site"
    HYBRID = "hybrid", "Hybrid"
    REMOTE = "remote", "Remote"


class EmploymentType(models.TextChoices):
    FULL_TIME = "full_time", "Full-time"
    PART_TIME = "part_time", "Part-time"
    CONTRACT = "contract", "Contract"
    TEMPORARY = "temporary", "Temporary"
    INTERNSHIP = "internship", "Internship"
    FELLOWSHIP = "fellowship", "Fellowship"


class JobFunction(models.TextChoices):
    CLINICAL = "clinical", "Clinical"
    ACADEMIC = "academic", "Academic"
    RESEARCH = "research", "Research"
    INDUSTRY = "industry", "Industry"
    PUBLIC_HEALTH = "public_health", "Public Health"
    ADMINISTRATION = "administration", "Administration"


class SeniorityLevel(models.TextChoices):
    INTERN = "intern", "Intern"
    JUNIOR = "junior", "Junior"
    MID = "mid", "Mid"
    SENIOR = "senior", "Senior"
    LEAD = "lead", "Lead"
    DIRECTOR = "director", "Director"
    CONSULTANT = "consultant", "Consultant"


class ApplyMethod(models.TextChoices):
    PLATFORM = "platform", "Apply via Platform"
    EXTERNAL_LINK = "external_link", "External Link"
    EMAIL = "email", "Email Application"


class Visibility(models.TextChoices):
    PUBLIC = "public", "Public"
    MEMBERS_ONLY = "members_only", "Members Only"
    VERIFIED_ONLY = "verified_only", "Verified Doctors Only"


class WorkAuthorization(models.TextChoices):
    CITIZEN_ONLY = "citizen_only", "Citizen/Resident only"
    VISA_AVAILABLE = "visa_available", "Visa sponsorship available"
    OPEN = "open", "Open to all (case-by-case)"

