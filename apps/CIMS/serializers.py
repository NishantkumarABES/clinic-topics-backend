from rest_framework import serializers
from apps.CIMS.models import CIMS, CIMSKeyInteraction, CIMSPracticalPearl
from rest_framework.pagination import PageNumberPagination


class CIMSKeyInteractionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CIMSKeyInteraction
        fields = [
            "id",
            "interaction_title",
            "clinical_impact",
            "what_to_do",
        ]

class CIMSPracticalPearlSerializer(serializers.ModelSerializer):
    class Meta:
        model = CIMSPracticalPearl
        fields = [
            "id",
            "pearl_title",
            "pearl_content",
        ]

class AdminCIMSListPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = 'page_size'
    max_page_size = 100

class CIMSReadSerializer(serializers.ModelSerializer):
    key_interactions = CIMSKeyInteractionSerializer(many=True, read_only=True)
    practical_prescribing_pearls = CIMSPracticalPearlSerializer(many=True, read_only=True)

    class Meta:
        model = CIMS
        fields = [
            "id",
            "drug_name_generic",
            "drug_class",
            "therapeutic_category",
            "brands_in_india",
            "strengths_available",
            "formulations_routes",
            "core_clinical_role",
            "preferred_clinical_scenarios",
            "where_benefit_limited",
            "usual_adult_dose",
            "timing_relative_to_meals",
            "review_duration_plan",
            "common_adverse_effects",
            "serious_but_uncommon_risks",
            "long_term_therapy_cautions",
            "guidelines",
            "landmark_trials",
            "status",
            "created_at",
            "updated_at",
            "key_interactions",
            "practical_prescribing_pearls",
        ]

class CIMSWriteSerializer(serializers.ModelSerializer):
    key_interactions = CIMSKeyInteractionSerializer(many=True, required=False)
    practical_prescribing_pearls = CIMSPracticalPearlSerializer(many=True, required=False)

    class Meta:
        model = CIMS
        fields = [
            "drug_name_generic",
            "drug_class",
            "therapeutic_category",
            "brands_in_india",
            "strengths_available",
            "formulations_routes",
            "core_clinical_role",
            "preferred_clinical_scenarios",
            "where_benefit_limited",
            "usual_adult_dose",
            "timing_relative_to_meals",
            "review_duration_plan",
            "common_adverse_effects",
            "serious_but_uncommon_risks",
            "long_term_therapy_cautions",
            "guidelines",
            "landmark_trials",
            "status",
            "key_interactions",
            "practical_prescribing_pearls",
        ]

    def create(self, validated_data):
        interactions = validated_data.pop("key_interactions", [])
        pearls = validated_data.pop("practical_prescribing_pearls", [])

        cims = CIMS.objects.create(**validated_data)

        CIMSKeyInteraction.objects.bulk_create([
            CIMSKeyInteraction(cims=cims, **item)
            for item in interactions
        ])

        CIMSPracticalPearl.objects.bulk_create([
            CIMSPracticalPearl(cims=cims, **item)
            for item in pearls
        ])

        return cims

    def update(self, instance, validated_data):
        interactions = validated_data.pop("key_interactions", None)
        pearls = validated_data.pop("practical_prescribing_pearls", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if interactions is not None:
            instance.key_interactions.all().delete()
            CIMSKeyInteraction.objects.bulk_create([
                CIMSKeyInteraction(cims=instance, **item)
                for item in interactions
            ])

        if pearls is not None:
            instance.practical_prescribing_pearls.all().delete()
            CIMSPracticalPearl.objects.bulk_create([
                CIMSPracticalPearl(cims=instance, **item)
                for item in pearls
            ])

        return instance
