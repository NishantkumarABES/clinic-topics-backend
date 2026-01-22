from rest_framework import serializers
from apps.IDI.models import IDI, IDIKeyInteraction, IDIPracticalPearl
from rest_framework.pagination import PageNumberPagination


class IDIKeyInteractionSerializer(serializers.ModelSerializer):
    class Meta:
        model = IDIKeyInteraction
        fields = [
            "id",
            "interaction_title",
            "clinical_impact",
            "what_to_do",
        ]

class IDIPracticalPearlSerializer(serializers.ModelSerializer):
    class Meta:
        model = IDIPracticalPearl
        fields = [
            "id",
            "pearl_title",
            "pearl_content",
        ]

class AdminIDIListPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = 'page_size'
    max_page_size = 100

class IDIReadSerializer(serializers.ModelSerializer):
    key_interactions = IDIKeyInteractionSerializer(many=True, read_only=True)
    practical_prescribing_pearls = IDIPracticalPearlSerializer(many=True, read_only=True)

    class Meta:
        model = IDI
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

class IDIWriteSerializer(serializers.ModelSerializer):
    key_interactions = IDIKeyInteractionSerializer(many=True, required=False)
    practical_prescribing_pearls = IDIPracticalPearlSerializer(many=True, required=False)

    class Meta:
        model = IDI
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

        idi = IDI.objects.create(**validated_data)

        IDIKeyInteraction.objects.bulk_create([
            IDIKeyInteraction(idi=idi, **item)
            for item in interactions
        ])

        IDIPracticalPearl.objects.bulk_create([
            IDIPracticalPearl(idi=idi, **item)
            for item in pearls
        ])

        return idi

    def update(self, instance, validated_data):
        interactions = validated_data.pop("key_interactions", None)
        pearls = validated_data.pop("practical_prescribing_pearls", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if interactions is not None:
            instance.key_interactions.all().delete()
            IDIKeyInteraction.objects.bulk_create([
                IDIKeyInteraction(idi=instance, **item)
                for item in interactions
            ])

        if pearls is not None:
            instance.practical_prescribing_pearls.all().delete()
            IDIPracticalPearl.objects.bulk_create([
                IDIPracticalPearl(idi=instance, **item)
                for item in pearls
            ])

        return instance
