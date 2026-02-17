from django.db import models

class JobPostStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    IN_REVIEW = "in_review", "In Review"
    PUBLISHED = "published", "Published"
    REJECTED = "rejected", "Rejected"
    EXPIRED = "expired", "Expired"
    CLOSED = "closed", "Closed"

class JobApplicationStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    ACCEPTED = "accepted", "Accepted"
    REJECTED = "rejected", "Rejected"


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



