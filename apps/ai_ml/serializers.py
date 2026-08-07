from rest_framework import serializers


class ClassifyRequestSerializer(serializers.Serializer):
    text = serializers.CharField(min_length=5, max_length=5000)
    language = serializers.CharField(max_length=5, default="en")


class ClassifyResponseSerializer(serializers.Serializer):
    category = serializers.CharField()
    confidence = serializers.FloatField()
    all_scores = serializers.DictField(child=serializers.FloatField())
    model_version = serializers.CharField()


class TranslateRequestSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=5000)
    source_language = serializers.CharField(max_length=5, default="hi")
    target_language = serializers.CharField(max_length=5, default="en")


class ProcessComplaintRequestSerializer(serializers.Serializer):
    text = serializers.CharField(min_length=3, max_length=5000)
    user_language = serializers.CharField(max_length=20, default="hi")
    complainant_name = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    mobile = serializers.CharField(max_length=15, required=False, allow_blank=True, default="")
    email = serializers.EmailField(required=False, allow_blank=True, default="")
    ward = serializers.CharField(max_length=80, required=False, allow_blank=True, default="")
    address = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")
    pincode = serializers.CharField(max_length=10, required=False, allow_blank=True, default="")
    title = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    district = serializers.CharField(max_length=80, required=False, allow_blank=True, default="")
    city = serializers.CharField(max_length=80, required=False, allow_blank=True, default="")
    location = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
