from rest_framework import serializers
from .models import UserProfile, JobProfile

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ('phone_number', 'qr_code')

class JobProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobProfile
        fields = ('external_id','phone_number')
