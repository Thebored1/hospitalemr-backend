from django.urls import path
from . import views

app_name = 'portal'

urlpatterns = [
    # Dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),
    
    # Agent Management
    path('agents/', views.AgentListView.as_view(), name='agent_list'),
    path('agents/create/', views.AgentCreateView.as_view(), name='agent_create'),
    path('agents/<int:pk>/edit/', views.AgentUpdateView.as_view(), name='agent_edit'),
    path('agents/<int:pk>/password/', views.AgentPasswordChangeView.as_view(), name='agent_password'),
    path('agents/<int:pk>/delete/', views.AgentDeleteView.as_view(), name='agent_delete'),
    path('agents/assignments/', views.AgentAssignmentListView.as_view(), name='agent_assignment_list'),
    path('agents/assignments/create/', views.AgentAssignmentCreateView.as_view(), name='agent_assignment_create'),
    path('agents/assignments/<int:pk>/', views.AgentAssignmentDetailView.as_view(), name='agent_assignment_detail'),
    path('agents/assignments/<int:pk>/delete/', views.AgentAssignmentDeleteView.as_view(), name='agent_assignment_delete'),
    
    # Trip Management (view-only - agents create trips via mobile app)
    path('trips/', views.TripListView.as_view(), name='trip_list'),
    path('trips/<int:pk>/', views.TripDetailView.as_view(), name='trip_detail'),
    
    # Doctor Master Table
    path('doctors/', views.DoctorListView.as_view(), name='doctor_list'),
    path('doctors/create/', views.DoctorCreateView.as_view(), name='doctor_create'),
    path('doctors/<int:pk>/', views.DoctorDetailView.as_view(), name='doctor_detail'),
    path('doctors/<int:pk>/edit/', views.DoctorUpdateView.as_view(), name='doctor_edit'),
    path('doctors/<int:pk>/commission/', views.DoctorCommissionUpdateView.as_view(), name='doctor_commission'),
    
    # Admission & Billing
    path('admissions/', views.AdmissionListView.as_view(), name='admission_list'),
    path('admissions/create/', views.AdmissionCreateView.as_view(), name='admission_create'),
    path('admissions/<int:pk>/', views.AdmissionDetailView.as_view(), name='admission_detail'),
    path('admissions/<int:pk>/edit/', views.AdmissionUpdateView.as_view(), name='admission_edit'),
    path('admissions/<int:pk>/discharge/', views.AdmissionDischargeView.as_view(), name='admission_discharge'),
    
    # Area Management
    path('areas/', views.AreaListView.as_view(), name='area_list'),
    
    # Area Management
    path('areas/', views.AreaListView.as_view(), name='area_list'),
    path('areas/create/', views.AreaCreateView.as_view(), name='area_create'),
    path('areas/<int:pk>/edit/', views.AreaUpdateView.as_view(), name='area_edit'),
    
    # Patient Referrals
    path('patients/', views.PatientReferralListView.as_view(), name='patient_list'),
    path('patients/<int:pk>/status/', views.PatientReferralStatusUpdateView.as_view(), name='patient_status_update'),
    
    # API
    path('api/commission-rates/', views.get_commission_rates, name='get_commission_rates'),
    
    # Doctor Toggle for Agent Assignments
    path('assignments/<int:assignment_id>/doctors/<int:doctor_id>/toggle/', views.toggle_doctor_assignment_status, name='toggle_doctor_assignment_status'),
    
    # Payment Category Management
    path('payment-categories/create/', views.PaymentCategoryCreateView.as_view(), name='payment_category_create'),
    
    # Reports
    path('reports/', views.ReportsDashboardView.as_view(), name='reports_dashboard'),
]
