from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TaskViewSet, DoctorReferralViewSet, PatientReferralViewSet, TripViewSet, OvernightStayViewSet, CustomAuthToken, SpecializationViewSet, QualificationViewSet, AreaViewSet

router = DefaultRouter()
router.register(r'areas', AreaViewSet, basename='area')
router.register(r'tasks', TaskViewSet)
router.register(r'doctor-referrals', DoctorReferralViewSet)
router.register(r'trips', TripViewSet)
router.register(r'overnight-stays', OvernightStayViewSet)
router.register(r'patient-referrals', PatientReferralViewSet)
router.register(r'specializations', SpecializationViewSet)
router.register(r'qualifications', QualificationViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('api-token-auth/', CustomAuthToken.as_view()),
]

