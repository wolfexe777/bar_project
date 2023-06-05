from rest_framework import generics
from .models import UserProfile, JobProfile
from .serializers import UserProfileSerializer, JobProfileSerializer

class UserProfileDetailView(generics.RetrieveAPIView):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer

class JobProfileDetailView(generics.RetrieveAPIView):
    queryset_1 = JobProfile.objects.all()
    serializer_class = JobProfileSerializer
