from rest_framework import serializers
from apps.jobs.models import JobPost, JobApplication
from apps.jobs.constants import JobPostStatus
from apps.accounts.models import User

class JobListSerializer(serializers.ModelSerializer):
    created_by = serializers.StringRelatedField()

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
            "speciality",
            "seniority_level",
            "salary_range",
            "application_deadline",
            "views",
            "applications_count",
            "application_views_count",
            "created_at",
            "created_by",
            "tags",
            "status",
        )
    
class JobDetailSerializer(JobListSerializer):
    is_applied = serializers.SerializerMethodField()
    is_my_job = serializers.SerializerMethodField()

    class Meta(JobListSerializer.Meta):
        fields = JobListSerializer.Meta.fields + (
            "job_description",
            "must_have_skills",
            "required_degrees",
            "apply_method",
            "external_apply_link",
            "application_email",
            "recruiter_name",
            "status",
            "rejection_reason",
            "is_applied",
            "is_my_job"
        )
    
    def get_is_applied(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False

        return JobApplication.objects.filter(
            job=obj,
            applicant=request.user
        ).exists()
    
    def get_is_my_job(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False

        return obj.created_by == request.user
    
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
        status_value = attrs.get("status",)
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
        exclude = ("job", "applicant", "created_at", "updated_at", "status")

    def validate_resume(self, value):
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("Max file size is 10MB.")
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
            "additional_information",
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

class DoctorApplicationListSerializer(serializers.ModelSerializer):
    applicant = serializers.StringRelatedField()

    class Meta:
        model = JobApplication
        fields = (
            "id",
            "applicant",
            "status",
            "created_at",
        )

class DoctorApplicationDetailSerializer(serializers.ModelSerializer):
    applicant = serializers.StringRelatedField()

    class Meta:
        model = JobApplication
        fields = (
            "id",
            "applicant",
            "resume",
            "additional_information",
            "years_of_experience",
            "current_position",
            "current_institution",
            "notice_period",
            "expected_salary",
            "additional_document",
            "status",
            "created_at",
        )
        read_only_fields = ("status",)

class DoctorApplicationReviewSerializer(serializers.ModelSerializer):

    class Meta:
        model = JobApplication
        fields = ("status",)

class AdminJobListSerializer(serializers.ModelSerializer):
    created_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = JobPost
        fields = "__all__"

class AdminApplicationListSerializer(serializers.ModelSerializer):
    applicant = serializers.StringRelatedField(read_only=True)
    applicant_id = serializers.UUIDField(source="applicant.id", read_only=True)

    job_id = serializers.UUIDField(source="job.id", read_only=True)
    job_title = serializers.CharField(source="job.title", read_only=True)
    company_name = serializers.CharField(source="job.company_name", read_only=True)

    class Meta:
        model = JobApplication
        fields = (
            "id",

            # Applicant Info
            "applicant",
            "applicant_id",

            # Job Reference (minimal, not full job payload)
            "job_id",
            "job_title",
            "company_name",

            # Submitted Application Data
            "resume",
            "additional_information",
            "years_of_experience",
            "current_position",
            "current_institution",
            "notice_period",
            "expected_salary",
            "additional_document",

            # Admin Controls
            "status",
            # Meta
            "created_at",
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

class paginatedDoctorApplicationListSerializers(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = AdminApplicationListSerializer(many=True)

class paginatedDoctorApplicationListResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    data = paginatedDoctorApplicationListSerializers()
    success = serializers.BooleanField()