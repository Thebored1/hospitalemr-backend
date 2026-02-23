from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Task, Trip, Specialization, Qualification, DoctorReferral, OvernightStay, PatientReferral, Admission, DoctorCommissionProfile

# Register your models here.
@admin.register(DoctorCommissionProfile)
class DoctorCommissionProfileAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'payment_category', 'updated_at')
    list_filter = ('payment_category', 'doctor')
    search_fields = ('doctor__name',)
admin.site.register(User, UserAdmin)
admin.site.register(Task)
@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ('id', 'agent', 'start_time', 'end_time', 'status', 'total_kilometers', 'start_lat', 'start_long', 'end_lat', 'end_long')
    list_filter = ('status', 'start_time', 'agent')
    search_fields = ('agent__username', 'status')
    readonly_fields = ('start_lat', 'start_long', 'end_lat', 'end_long')

admin.site.register(Specialization)
admin.site.register(Qualification)

@admin.register(DoctorReferral)
class DoctorReferralAdmin(admin.ModelAdmin):
    list_display = ('name', 'trip', 'specialization', 'contact_number', 'status', 'visit_lat', 'visit_long', 'created_at')
    list_filter = ('status', 'specialization', 'created_at', 'trip')
    search_fields = ('name', 'contact_number', 'trip__agent__username')
    readonly_fields = ('visit_lat', 'visit_long')
admin.site.register(OvernightStay)
@admin.register(PatientReferral)
class PatientReferralAdmin(admin.ModelAdmin):
    list_display = ('patient_name', 'agent', 'phone', 'illness', 'status', 'is_urgent', 'reported_on')
    list_filter = ('status', 'is_urgent', 'agent', 'reported_on')
    search_fields = ('patient_name', 'phone', 'illness', 'agent__username')

# Missing registrations
from .models import Area, Address, AgentAssignment, AgentAssignmentDoctorStatus, PaymentCategory

class AddressInline(admin.StackedInline):
    model = Address
    extra = 1

@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'pincode', 'state', 'agent', 'created_at')
    list_filter = ('city', 'state', 'agent', 'created_at')
    search_fields = ('name', 'city', 'pincode', 'agent__username')
    inlines = [AddressInline]

class AgentAssignmentDoctorStatusInline(admin.TabularInline):
    model = AgentAssignmentDoctorStatus
    extra = 0
    raw_id_fields = ('doctor',)

@admin.register(AgentAssignment)
class AgentAssignmentAdmin(admin.ModelAdmin):
    list_display = ('agent', 'area', 'assigned_at', 'current_assignment_status')
    list_filter = ('assigned_at', 'agent', 'area')
    search_fields = ('agent__username', 'area__name')
    inlines = [AgentAssignmentDoctorStatusInline]
    
    def current_assignment_status(self, obj):
        # Count active/inactive doctors for this assignment
        total = obj.doctor_statuses.count()
        active = obj.doctor_statuses.filter(is_active=True).count()
        inactive = total - active
        return f"{total} Docs ({active} Active, {inactive} Disabled)"
    current_assignment_status.short_description = "Status"
    
@admin.register(AgentAssignmentDoctorStatus)
class AgentAssignmentDoctorStatusAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'assignment', 'is_active', 'updated_at')
    list_filter = ('is_active', 'updated_at', 'assignment__agent', 'assignment__area')
    search_fields = ('doctor__name', 'assignment__agent__username', 'assignment__area__name')

@admin.register(PaymentCategory)
class PaymentCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'created_at')
    search_fields = ('name', 'code')

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('street', 'area', 'pincode')
    search_fields = ('street', 'pincode', 'area__name')

class DoctorCommissionProfileInline(admin.TabularInline):
    model = DoctorCommissionProfile
    extra = 0

# Unregister if already registered to avoid conflict/double registration errors during potential re-runs
try:
    admin.site.unregister(DoctorReferral)
except admin.sites.NotRegistered:
    pass

@admin.register(DoctorReferral)
class DoctorReferralAdmin(admin.ModelAdmin):
    list_display = ('name', 'specialization', 'address_summary', 'status', 'created_at')
    list_filter = ('status', 'specialization', 'created_at', 'address_details__area')
    search_fields = ('name', 'contact_number', 'address_details__area__name')
    inlines = [DoctorCommissionProfileInline]
    
    def address_summary(self, obj):
        if obj.address_details and obj.address_details.area:
            return f"{obj.address_details.area.name}, {obj.address_details.area.city}"
        return "-"
    address_summary.short_description = "Area"

@admin.register(Admission)
class AdmissionAdmin(admin.ModelAdmin):
    list_display = ('patient_name', 'admission_type', 'status', 'admission_date', 'total_charges_display', 'commission_amount')
    list_filter = ('status', 'admission_type', 'admission_date', 'payment_category')
    search_fields = ('patient_name', 'patient_phone', 'referred_by_doctor__name')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Patient Info', {
            'fields': ('patient_name', 'patient_phone', 'patient_age', 'patient_gender', 'patient_address', 'patient_referral')
        }),
        ('Admission Details', {
            'fields': ('admission_type', 'status', 'admission_date', 'discharge_date', 'referred_by_doctor', 'payment_category')
        }),
        ('Billing Breakdown', {
            'fields': (
                ('bed_charges', 'nursing_charges'),
                ('doctor_consultation_charges', 'investigation_charges'),
                ('procedural_surgical_charges', 'anaesthesia_charges'),
                ('surgeon_charges', 'other_charges'),
                'other_charges_description'
            )
        }),
        ('Financials', {
            'fields': ('commission_amount', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def total_charges_display(self, obj):
        return obj.total_charges
    total_charges_display.short_description = "Total Charges"
