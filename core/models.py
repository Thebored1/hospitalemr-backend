from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES = (
        ('advisor', 'Advisor (Executive)'),
        ('maintenance', 'Maintenance (Staff)'),
        ('admin', 'Admin'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='advisor')
    
    @property
    def full_name_or_username(self):
        full_name = self.get_full_name()
        return full_name if full_name else self.username

class Task(models.Model):
    STATUS_CHOICES = (
        ('Open', 'Open'),
        ('In Progress', 'In Progress'),
        ('Resolved', 'Resolved'),
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    raised_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='raised_tasks', limit_choices_to={'role': 'maintenance'})
    raised_on = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Open')
    allotted_budget = models.CharField(max_length=50)
    fix_by = models.DateTimeField()
    location = models.CharField(max_length=100)
    issue_category = models.CharField(max_length=50)

    def __str__(self):
        return self.title

class Trip(models.Model):
    STATUS_CHOICES = (
        ('ONGOING', 'Ongoing'),
        ('COMPLETED', 'Completed'),
    )
    agent = models.ForeignKey(User, on_delete=models.CASCADE, related_name='trips', limit_choices_to={'role': 'advisor'})
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ONGOING')
    
    # Expense / Travel Details
    odometer_start_image = models.ImageField(upload_to='trip_odometers/', null=True, blank=True)
    odometer_end_image = models.ImageField(upload_to='trip_odometers/', null=True, blank=True)
    total_kilometers = models.FloatField(default=0.0)
    additional_expenses = models.TextField(null=True, blank=True)
    
    # Location Tracking
    start_lat = models.DecimalField(max_digits=20, decimal_places=15, null=True, blank=True)
    start_long = models.DecimalField(max_digits=20, decimal_places=15, null=True, blank=True)
    end_lat = models.DecimalField(max_digits=20, decimal_places=15, null=True, blank=True)
    end_long = models.DecimalField(max_digits=20, decimal_places=15, null=True, blank=True)

    class Meta:
        ordering = ['-start_time']

    def __str__(self):
        return f"Trip by {self.agent.username} on {self.start_time.date()}"

class Specialization(models.Model):
    """Master list of doctor specializations"""
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Qualification(models.Model):
    """Master list of doctor qualifications"""
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class PaymentCategory(models.Model):
    """Master list of payment categories (Cash, Insurance, Ayushman, etc.)."""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=50, unique=True, help_text="Short code e.g. CASH, INSURANCE")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Payment Categories'

    def __str__(self):
        return self.name


class Area(models.Model):
    """Geographic area master table."""
    name = models.CharField(max_length=100, unique=True, help_text="e.g. Downtown, North Zone")
    street = models.CharField(max_length=200, blank=True, null=True)
    landmark = models.CharField(max_length=200, blank=True, null=True)
    city = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10, default='')
    state = models.CharField(max_length=100, default='Maharashtra')
    region = models.CharField(max_length=100, blank=True, null=True, help_text="e.g. Vidarbha, West")
    description = models.TextField(blank=True, null=True)
    
    # Executive is assigned by Admin, not during creation usually
    agent = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                            related_name='assigned_areas', limit_choices_to={'role': 'advisor'})
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['city', 'name']

    def __str__(self):
        return f"{self.name}, {self.city}"

class AgentAssignment(models.Model):
    """Log of executive assignments to areas (History/Transaction)."""
    agent = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assignments', limit_choices_to={'role': 'advisor'})
    area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name='assignment_history')
    assigned_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-assigned_at']

    def __str__(self):
        return f"{self.agent.username} -> {self.area.name} ({self.assigned_at.date()})"


class AgentAssignmentDoctorStatus(models.Model):
    """Track doctor status and visit progress per executive assignment.
    Each assignment gets its own set of doctor statuses, so reassignments start fresh."""
    assignment = models.ForeignKey(AgentAssignment, on_delete=models.CASCADE, related_name='doctor_statuses')
    doctor = models.ForeignKey('DoctorReferral', on_delete=models.CASCADE, related_name='assignment_statuses')
    is_active = models.BooleanField(default=True)
    
    # Per-assignment visit tracking
    is_visited = models.BooleanField(default=False)
    visit_trip = models.ForeignKey('Trip', on_delete=models.SET_NULL, null=True, blank=True, related_name='assignment_visits')
    visited_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('assignment', 'doctor')
        verbose_name_plural = 'Executive Assignment Doctor Statuses'

    def __str__(self):
        active = "Active" if self.is_active else "Disabled"
        visited = "Visited" if self.is_visited else "Pending"
        return f"{self.doctor.name} in {self.assignment.area.name} - {active}/{visited}"



class Address(models.Model):
    """Physical address details linked to an Area"""
    area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name='addresses')
    street = models.CharField(max_length=200, blank=True, null=True)
    landmark = models.CharField(max_length=200, blank=True, null=True)
    pincode = models.CharField(max_length=10, blank=True, null=True)
    
    def __str__(self):
        return f"{self.street or ''}, {self.area.name}"


class DoctorReferral(models.Model):
    # New Address Link
    address_details = models.OneToOneField(Address, on_delete=models.SET_NULL, null=True, blank=True, related_name='doctor')
    
    # Trip is optional - assigned when executive actually visits the doctor
    trip = models.ForeignKey(Trip, on_delete=models.SET_NULL, null=True, blank=True, related_name='doctor_referrals')
    
    # Legacy Executive (Deprecating in favor of Area.agent)
    agent = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='doctor_referrals_legacy', limit_choices_to={'role': 'advisor'})
    
    name = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=20, blank=True, null=True)
    
    specialization = models.CharField(max_length=100, blank=True, null=True)
    degree_qualification = models.CharField(max_length=100, default='MBBS', blank=True)
    email = models.EmailField(max_length=100, blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    additional_details = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_internal = models.BooleanField(default=False, help_text="Internal doctors do not need addresses and cannot be assigned to executives.")
    
    DOCTOR_STATUS_CHOICES = (
        ('Assigned', 'Assigned'),
        ('Referred', 'Referred'),
        ('Internal', 'Internal'),
    )
    status = models.CharField(max_length=50, choices=DOCTOR_STATUS_CHOICES, default='Assigned')
    visit_image = models.ImageField(upload_to='doctor_visits/', null=True, blank=True)
    visit_lat = models.DecimalField(max_digits=20, decimal_places=15, null=True, blank=True)
    visit_long = models.DecimalField(max_digits=20, decimal_places=15, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class DoctorVisit(models.Model):
    """Per-trip visit record for a doctor."""

    doctor = models.ForeignKey(
        DoctorReferral,
        on_delete=models.CASCADE,
        related_name='visits',
    )
    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name='doctor_visits',
    )
    remarks = models.TextField(blank=True, null=True)
    additional_details = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=50,
        choices=DoctorReferral.DOCTOR_STATUS_CHOICES,
        default='Referred',
    )
    visit_image = models.ImageField(upload_to='doctor_visits/', null=True, blank=True)
    visit_lat = models.DecimalField(max_digits=20, decimal_places=15, null=True, blank=True)
    visit_long = models.DecimalField(max_digits=20, decimal_places=15, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('doctor', 'trip')

    def __str__(self):
        return f"{self.doctor.name} visit on trip {self.trip_id}"

class DoctorCommissionProfile(models.Model):
    """Referral rates for a doctor based on payment category."""
    
    doctor = models.ForeignKey(DoctorReferral, on_delete=models.CASCADE, related_name='commission_profiles')
    payment_category = models.ForeignKey(PaymentCategory, on_delete=models.CASCADE, related_name='commission_profiles')
    
    # Referral Rates (Percentages)
    bed_charges_rate = models.FloatField(default=0.0, help_text="Referral % for Bed Charges")
    nursing_charges_rate = models.FloatField(default=0.0, help_text="Referral % for Nursing Charges")
    doctor_consultation_charges_rate = models.FloatField(default=0.0, help_text="Referral % for Doctor Consultation")
    investigation_charges_rate = models.FloatField(default=0.0, help_text="Referral % for Investigation Charges")
    procedural_surgical_charges_rate = models.FloatField(default=0.0, help_text="Referral % for Procedural/Surgical")
    anaesthesia_charges_rate = models.FloatField(default=0.0, help_text="Referral % for Anaesthesia")
    surgeon_charges_rate = models.FloatField(default=0.0, help_text="Referral % for Surgeon Charges")
    other_charges_rate = models.FloatField(default=0.0, help_text="Referral % for Other Charges")
    
    # Referral Configuration
    discount_percentage = models.FloatField(default=0.0, help_text="Standard Referral % for this category")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('doctor', 'payment_category')

    def __str__(self):
        return f"{self.doctor.name} - {self.payment_category.name}"


class ClientLog(models.Model):
    LEVEL_CHOICES = (
        ('DEBUG', 'Debug'),
        ('INFO', 'Info'),
        ('WARN', 'Warn'),
        ('ERROR', 'Error'),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='client_logs',
    )
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default='INFO')
    message = models.TextField()
    logger = models.CharField(max_length=100, blank=True, null=True)
    context = models.JSONField(default=dict, blank=True)
    device_id = models.CharField(max_length=64, blank=True, null=True)
    app_version = models.CharField(max_length=32, blank=True, null=True)
    platform = models.CharField(max_length=32, blank=True, null=True)
    build_mode = models.CharField(max_length=16, blank=True, null=True)
    client_time = models.DateTimeField(null=True, blank=True)
    ip_address = models.CharField(max_length=45, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        who = self.user.username if self.user else "anonymous"
        return f"[{self.level}] {who}: {self.message[:60]}"

class OvernightStay(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='overnight_stays')
    hotel_name = models.CharField(max_length=100)
    hotel_address = models.TextField()
    bill_image = models.ImageField(upload_to='hotel_bills/', null=True, blank=True)
    latitude = models.DecimalField(max_digits=20, decimal_places=15, null=True, blank=True)
    longitude = models.DecimalField(max_digits=20, decimal_places=15, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Stay at {self.hotel_name}"

class PatientReferral(models.Model):
    agent = models.ForeignKey(User, on_delete=models.CASCADE, related_name='patient_referrals', limit_choices_to={'role': 'advisor'})
    patient_name = models.CharField(max_length=100)
    age = models.IntegerField()
    gender = models.CharField(max_length=20)
    phone = models.CharField(max_length=20)
    illness = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    reported_on = models.DateTimeField(auto_now_add=True)
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Admitted', 'Admitted'),
        ('Dismissed', 'Dismissed'),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    is_urgent = models.BooleanField(default=False)
    
    referred_by_doctor = models.ForeignKey('DoctorReferral', on_delete=models.SET_NULL, null=True, blank=True, related_name='patients_referred_out')
    referred_to_doctor = models.ForeignKey('DoctorReferral', on_delete=models.SET_NULL, null=True, blank=True, related_name='patients_referred_in')

    class Meta:
        ordering = ['-reported_on']

    def __str__(self):
        return self.patient_name


class Admission(models.Model):
    """Hospital admission record with detailed billing breakdown."""
    
    ADMISSION_TYPE_CHOICES = (
        ('OPD', 'Out-Patient Department (OPD)'),
        ('IPD', 'In-Patient Department (IPD)'),
    )
    
    STATUS_CHOICES = (
        ('ADMITTED', 'Admitted'),
        ('DISCHARGED', 'Discharged'),
        ('CANCELLED', 'Cancelled'),
    )

    
    # Patient Information
    patient_name = models.CharField(max_length=100)
    patient_phone = models.CharField(max_length=20, blank=True, null=True)
    patient_age = models.IntegerField(blank=True, null=True)
    patient_gender = models.CharField(max_length=20, blank=True, null=True)
    patient_address = models.TextField(blank=True, null=True)

    # Link to patient referral (optional)
    patient_referral = models.ForeignKey(
        'PatientReferral',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='admissions',
        help_text='Linked patient referral for auto status updates'
    )
    
    # Referral Information (links to doctor referred by executive)
    referred_by_doctor = models.ForeignKey(
        'DoctorReferral', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='admissions',
        help_text='Doctor who referred this patient (linked to executive for referral tracking)'
    )
    referred_to_doctor = models.ForeignKey(
        'DoctorReferral', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='admissions_received',
        help_text='Internal doctor handling the admission'
    )
    
    # Admission Details
    admission_type = models.CharField(max_length=10, choices=ADMISSION_TYPE_CHOICES, default='OPD')
    payment_category = models.ForeignKey(PaymentCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='admissions')
    admission_date = models.DateTimeField(auto_now_add=True)
    discharge_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ADMITTED')
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Calculated total referral")
    
    # Charge Breakdown
    bed_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    nursing_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    doctor_consultation_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    investigation_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    investigation_type = models.CharField(
        max_length=20, 
        choices=(('IN_HOUSE', 'In-House'), ('OUTSIDE', 'Outside')),
        default='IN_HOUSE',
        blank=True
    )
    procedural_surgical_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    anaesthesia_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    surgeon_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Additional charges and notes
    other_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    other_charges_description = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-admission_date']
    
    @property
    def total_charges(self):
        """Calculate total of all charges."""
        return (
            self.bed_charges +
            self.nursing_charges +
            self.doctor_consultation_charges +
            self.investigation_charges +
            self.procedural_surgical_charges +
            self.anaesthesia_charges +
            self.surgeon_charges +
            self.other_charges
        )
    
    @property
    def final_amount(self):
        """Calculate final amount after referral deduction."""
        return max(self.total_charges - self.commission_amount, 0)
    
    def __str__(self):
        return f"{self.patient_name} - {self.admission_type} ({self.admission_date.date()})"

