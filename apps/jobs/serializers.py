from rest_framework import serializers
from apps.jobs.models import JobPost, JobApplication, JobTag
from apps.jobs.constants import JobPostStatus
from apps.accounts.models import User

class JobTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobTag
        fields = ("id", "name")

class JobListSerializer(serializers.ModelSerializer):
    created_by = serializers.StringRelatedField()
    tags = JobTagSerializer(many=True, read_only=True)

    class Meta:
        model = JobPost
        fields = (
            "id",
            "title",
            "company_name",
            "workplace_type",
            "employment_type",
            "job_location",
            "job_function",
            "specialty",
            "seniority_level",
            "salary_range",
            "application_deadline",
            "views",
            "applications_count",
            "created_at",
            "created_by",
            "tags",
        )

class JobDetailSerializer(JobListSerializer):

    class Meta(JobListSerializer.Meta):
        fields = JobListSerializer.Meta.fields + (
            "role_summary",
            "responsibilities",
            "qualifications",
            "must_have_skills",
            "nice_to_have_skills",
            "benefits",
            "required_degrees",
            # "required_registrations",
            "background_checks",
            "recruiter_name",
            "additional_notes",
            "status",
            "rejection_reason",
        )

class JobCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = JobPost
        exclude = (
            "created_by",
            "status",
            "rejection_reason",
            "views",
            "applications_count",
            "application_views_count",
            "is_deleted",
            "created_at",
            "updated_at",
        )

    def create(self, validated_data):
        request = self.context["request"]
        return JobPost.objects.create(
            created_by=request.user,
            status=JobPostStatus.DRAFT,
            **validated_data
        )

class JobUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = JobPost
        exclude = (
            "created_by",
            "status",
            "rejection_reason",
            "views",
            "applications_count",
            "application_views_count",
            "created_at",
            "updated_at",
        )

class JobReviewSerializer(serializers.ModelSerializer):

    class Meta:
        model = JobPost
        fields = ("status", "rejection_reason")

    def validate(self, attrs):
        status_value = attrs.get("status")
        reason = attrs.get("rejection_reason")

        if status_value == JobPostStatus.REJECTED and not reason:
            raise serializers.ValidationError(
                "Rejection reason is required."
            )

        if status_value == JobPostStatus.PUBLISHED:
            attrs["rejection_reason"] = None

        return attrs

class JobApplySerializer(serializers.ModelSerializer):

    class Meta:
        model = JobApplication
        exclude = ("job", "applicant", "created_at", "updated_at")

    def validate_resume(self, value):
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("Max file size is 10MB.")
        return value

    def validate_cover_letter(self, value):
        if not (50 <= len(value) <= 3000):
            raise serializers.ValidationError(
                "Cover letter must be 50–3000 characters."
            )
        return value

class MyAppliedJobListSerializer(serializers.ModelSerializer):
    job = JobListSerializer(read_only=True)

    class Meta:
        model = JobApplication
        fields = (
            "id",
            "job",
            "created_at",
        )

class MyAppliedJobDetailSerializer(serializers.ModelSerializer):
    job = JobDetailSerializer(read_only=True)

    class Meta:
        model = JobApplication
        fields = (
            "id",
            "job",
            "resume",
            "cover_letter",
            "years_of_experience",
            "current_position",
            "current_institution",
            "notice_period",
            "expected_salary",
            "additional_document",
            "created_at",
        )

class AdminApplicationListSerializer(serializers.ModelSerializer):
    applicant = serializers.StringRelatedField()
    job = JobListSerializer(read_only=True)

    class Meta:
        model = JobApplication
        fields = (
            "id",
            "applicant",
            "job",
            "created_at",
        )

class AdminJobCreateSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = JobPost
        exclude = (
            "created_by",
            "status",
            "views",
            "applications_count",
            "application_views_count",
            "is_deleted",
            "created_at",
            "updated_at",
        )

    def validate_user_id(self, value):
        try:
            user = User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found.")
        return user

    def create(self, validated_data):
        user = validated_data.pop("user_id")

        return JobPost.objects.create(
            created_by=user,
            status=JobPostStatus.PUBLISHED,
            **validated_data
        )



############################## Response Serializers ################################

class paginatedJobListSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = JobListSerializer(many=True)

class paginatedJobListResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    data = paginatedJobListSerializer()
    success = serializers.BooleanField()

class paginatedJobApplicationListSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = MyAppliedJobListSerializer(many=True)

class paginatedJobApplicationListResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    data = paginatedJobApplicationListSerializer()
    success = serializers.BooleanField()