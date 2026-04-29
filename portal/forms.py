from django import forms
from django.contrib.auth.forms import UserCreationForm, SetPasswordForm
from decimal import Decimal
from core.models import User, Trip, DoctorReferral, Admission, Specialization, Qualification, Area, Address, AgentAssignment, PatientReferral, DoctorCommissionProfile


class AgentCreationForm(UserCreationForm):
    """Form for creating new executive accounts."""
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from portal.models import CustomRole
        # Add Bootstrap classes
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
        
        # Repurpose username as Phone Number
        self.fields['username'].label = 'Phone Number (Login ID)'
        self.fields['username'].help_text = 'Required. Enter the 10-digit phone number.'
        self.fields['username'].widget.attrs['placeholder'] = 'e.g. 9876543210'
        self.fields['username'].widget.attrs['type'] = 'text'
        self.fields['username'].widget.attrs['maxlength'] = '10'
        self.fields['username'].widget.attrs['oninput'] = "this.value = this.value.replace(/[^0-9]/g, '')"

        # Add Custom Role selection
        self.fields['custom_role'] = forms.ModelChoiceField(
            queryset=CustomRole.objects.all(),
            required=True,
            label="Role",
            help_text="Select a predefined role to define portal access and permissions.",
            widget=forms.Select(attrs={'class': 'form-select'})
        )

    def clean_username(self):
        # We must call super() for UserCreationForm's uniqueness check
        username = super().clean_username() 
        if not username.isdigit():
            raise forms.ValidationError('Phone number must contain only digits (0-9).')
        if len(username) != 10:
            raise forms.ValidationError('Phone number must be exactly 10 digits.')
        return username

    def save(self, commit=True):
        user = super().save(commit=False)
        custom_role = self.cleaned_data.get('custom_role')
        
        # Set a default system role if not set
        if not user.role or user.role == 'advisor':
            role_name = custom_role.name.lower()
            if 'admin' in role_name:
                user.role = 'admin'
            elif 'maintenance' in role_name or 'staff' in role_name:
                user.role = 'maintenance'
            else:
                user.role = 'advisor'

        if commit:
            user.is_staff = True
            user.save()
            if custom_role:
                from portal.models import UserRoleAssignment
                UserRoleAssignment.objects.update_or_create(
                    user=user,
                    defaults={'role': custom_role}
                )
        return user


class AgentUpdateForm(forms.ModelForm):
    """Form for updating executive details (without password)."""
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'is_active']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from portal.models import CustomRole, UserRoleAssignment
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            else:
                field.widget.attrs['class'] = 'form-control'

        # Repurpose username as Phone Number
        self.fields['username'].label = 'Phone Number (Login ID)'
        self.fields['username'].help_text = 'Required. Enter the 10-digit phone number.'
        self.fields['username'].widget.attrs['placeholder'] = 'e.g. 9876543210'
        self.fields['username'].widget.attrs['type'] = 'text'
        self.fields['username'].widget.attrs['maxlength'] = '10'
        self.fields['username'].widget.attrs['oninput'] = "this.value = this.value.replace(/[^0-9]/g, '')"

        # Add Custom Role selection (MANDATORY)
        initial_role = None
        if self.instance.pk:
            assignment = UserRoleAssignment.objects.filter(user=self.instance).first()
            if assignment:
                initial_role = assignment.role

        self.fields['custom_role'] = forms.ModelChoiceField(
            queryset=CustomRole.objects.all(),
            required=True,
            initial=initial_role,
            label="Role",
            help_text="Select a predefined role to define portal access and permissions.",
            widget=forms.Select(attrs={'class': 'form-select'})
        )

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if not username.isdigit():
            raise forms.ValidationError('Phone number must contain only digits (0-9).')
        if len(username) != 10:
            raise forms.ValidationError('Phone number must be exactly 10 digits.')
            
        # Check uniqueness manually
        from core.models import User
        qs = User.objects.filter(username=username)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('A user with that phone number already exists.')
            
        return username

    def save(self, commit=True):
        user = super().save(commit=False)
        custom_role = self.cleaned_data.get('custom_role')
        if commit:
            user.is_staff = True
            user.save()
            from portal.models import UserRoleAssignment
            if custom_role:
                UserRoleAssignment.objects.update_or_create(
                    user=user,
                    defaults={'role': custom_role}
                )
            else:
                UserRoleAssignment.objects.filter(user=user).delete()
        return user



class UserPortalCreationForm(UserCreationForm):
    """Form for creating any user account with role selection."""
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from portal.models import CustomRole
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
        
        self.fields['username'].label = 'Phone Number (Login ID)'
        self.fields['username'].widget.attrs['maxlength'] = '10'
        self.fields['username'].widget.attrs['oninput'] = "this.value = this.value.replace(/[^0-9]/g, '')"

        self.fields['custom_role'] = forms.ModelChoiceField(
            queryset=CustomRole.objects.all(),
            required=True,
            label="Role",
            help_text="Select a predefined role to define portal access and permissions.",
            widget=forms.Select(attrs={'class': 'form-select'})
        )

    def clean_username(self):
        username = super().clean_username()
        if not username.isdigit() or len(username) != 10:
            raise forms.ValidationError('Enter a valid 10-digit phone number.')
        return username

    def save(self, commit=True):
        user = super().save(commit=False)
        custom_role = self.cleaned_data.get('custom_role')
        
        # Mapping system role best effort
        role_name = custom_role.name.lower()
        if 'admin' in role_name:
            user.role = 'admin'
        elif 'maintenance' in role_name or 'staff' in role_name:
            user.role = 'maintenance'
        else:
            user.role = 'advisor'

        if commit:
            user.is_staff = True
            user.save()
            from portal.models import UserRoleAssignment
            UserRoleAssignment.objects.update_or_create(
                user=user,
                defaults={'role': custom_role}
            )
        return user

class UserPortalUpdateForm(forms.ModelForm):
    """Form for updating any user account with role selection."""
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'is_active']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from portal.models import CustomRole, UserRoleAssignment
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            else:
                field.widget.attrs['class'] = 'form-control'
        
        self.fields['username'].label = 'Phone Number (Login ID)'
        self.fields['username'].widget.attrs['maxlength'] = '10'

        initial_role = None
        if self.instance.pk:
            assignment = UserRoleAssignment.objects.filter(user=self.instance).first()
            if assignment:
                initial_role = assignment.role

        self.fields['custom_role'] = forms.ModelChoiceField(
            queryset=CustomRole.objects.all(),
            required=True,
            initial=initial_role,
            label="Role",
            help_text="Select a predefined role to define portal access and permissions.",
            widget=forms.Select(attrs={'class': 'form-select'})
        )

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if not username.isdigit() or len(username) != 10:
            raise forms.ValidationError('Enter a valid 10-digit phone number.')
        qs = User.objects.filter(username=username)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('A user with that phone number already exists.')
        return username

    def save(self, commit=True):
        user = super().save(commit=False)
        custom_role = self.cleaned_data.get('custom_role')
        if commit:
            user.is_staff = True
            user.save()
            from portal.models import UserRoleAssignment
            UserRoleAssignment.objects.update_or_create(
                user=user,
                defaults={'role': custom_role}
            )
        return user


class AgentPasswordForm(SetPasswordForm):
    """Form for admin to set/reset executive password."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'


class TripCreateForm(forms.ModelForm):
    """Form for creating trips and assigning to executives."""
    
    agent = forms.ModelChoiceField(
        queryset=User.objects.filter(custom_role_assignment__role__name='Mobile App User', is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Assign to Executive'
    )
    
    class Meta:
        model = Trip
        fields = ['agent']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class DoctorAssignmentForm(forms.Form):
    """Form for assigning doctors to a trip."""
    
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Doctor Name'})
    )
    specialization = forms.ModelChoiceField(
        queryset=Specialization.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False,
        empty_label='Select Specialization'
    )
    contact_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contact Number'})
    )
    area = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Area *'})
    )
    street = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Street'})
    )
    city = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'})
    )
    pin = forms.CharField(
        max_length=10,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'PIN *'})
    )
    is_internal = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Internal Hospital Doctor'
    )


class AreaForm(forms.ModelForm):
    """Form for creating/editing Areas."""
    class Meta:
        model = Area
        fields = ['name', 'street', 'landmark', 'city', 'pincode', 'region', 'state', 'description', 'agent']
        labels = {
            'region': 'District',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Area Name'}),
            'street': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Street Address'}),
            'landmark': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Landmark'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'pincode': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Pincode'}),
            'region': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'District (e.g. Bilaspur)'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Description'}),
            'agent': forms.Select(attrs={'class': 'form-select'}),
        }

class AddressForm(forms.ModelForm):
    """Child form for Address details."""
    area = forms.ModelChoiceField(
        queryset=Area.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label="Select Area"
    )

    class Meta:
        model = Address
        fields = ['area']


class DoctorForm(forms.ModelForm):
    """Form for manually creating/editing doctors - assigned to executives later via trips."""
    
    # Specialization dropdown (Select2)
    specialization_select = forms.ModelChoiceField(
        queryset=Specialization.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select', 'data-placeholder': 'Select Specialization'}),
        required=False,
        empty_label=None, # For Select2 placeholder
        label='Specialization'
    )
    
    # Qualification dropdown (Select2)
    degree_qualification_select = forms.ModelChoiceField(
        queryset=Qualification.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select', 'data-placeholder': 'Select Qualification'}),
        required=False,
        empty_label=None,
        label='Qualification'
    )

    class Meta:
        model = DoctorReferral
        fields = [
            'name', 
            'contact_number', 'email', 
            'is_internal',
            # Address fields removed - handled by AddressForm
            'remarks', 'additional_details'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Doctor Name'}),
            'contact_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contact Number'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address'}),
            'is_internal': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'additional_details': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Pre-populate dropdowns if editing existing doctor
        if self.instance.pk:
            if self.instance.specialization:
                try:
                    spec = Specialization.objects.get(name=self.instance.specialization)
                    self.initial['specialization_select'] = spec
                except Specialization.DoesNotExist:
                    pass
            
            if self.instance.degree_qualification:
                try:
                    qual = Qualification.objects.get(name=self.instance.degree_qualification)
                    self.initial['degree_qualification_select'] = qual
                except Qualification.DoesNotExist:
                    pass

        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = 'form-select'
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs['class'] = 'form-control'
            elif isinstance(field.widget, forms.CheckboxInput):
                 field.widget.attrs['class'] = 'form-check-input'
            else:
                field.widget.attrs['class'] = 'form-control'

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Handle specialization
        spec_select = self.cleaned_data.get('specialization_select')
        if spec_select:
            instance.specialization = spec_select.name
        else:
            instance.specialization = ''

        # Handle qualification
        qual_select = self.cleaned_data.get('degree_qualification_select')
        if qual_select:
            instance.degree_qualification = qual_select.name
        else:
            instance.degree_qualification = ''
        
        # Always set default for portal entry
        if not instance.pk:
            instance.agent = None
            if instance.is_internal:
                instance.status = 'Internal'
            else:
                instance.status = 'Assigned'
            
        if commit:
            instance.save()
        return instance


class AdmissionForm(forms.ModelForm):
    """Form for creating/editing admission records with billing."""

    patient_referral = forms.ModelChoiceField(
        queryset=PatientReferral.objects.all(),
        required=False,
        widget=forms.HiddenInput()
    )
    
    referred_by_doctor = forms.ModelChoiceField(
        queryset=DoctorReferral.objects.filter(is_internal=False).select_related('agent').all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Referred by (External Doctor)',
        help_text='Select the external doctor who referred this patient'
    )

    referred_to_doctor = forms.ModelChoiceField(
        queryset=DoctorReferral.objects.filter(is_internal=True).all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Referred to (Internal Doctor)',
        help_text='Select the internal hospital doctor managing this admission'
    )
    
    class Meta:
        model = Admission
        fields = [
            # Patient Info
            'patient_name', 'patient_phone', 'patient_age', 'patient_gender', 'patient_address', 'patient_referral',
            # Referral
            'referred_by_doctor', 'referred_to_doctor',
            # Admission
            'admission_type', 'payment_category', 'commission_amount',
            # Charges
            'bed_charges', 'nursing_charges', 'doctor_consultation_charges',
            'investigation_charges', 'investigation_type',
            'procedural_surgical_charges', 'anaesthesia_charges', 'surgeon_charges',
            'other_charges', 'other_charges_description',
            # Notes
            'notes',
        ]
        widgets = {
            'patient_address': forms.Textarea(attrs={'rows': 2}),
            'other_charges_description': forms.Textarea(attrs={'rows': 2}),
            'notes': forms.Textarea(attrs={'rows': 3}),
            'commission_amount': forms.HiddenInput(),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = 'form-select'
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs['class'] = 'form-control'
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            else:
                field.widget.attrs['class'] = 'form-control'

        # Enable datalist autocomplete on patient name input
        self.fields['patient_name'].widget.attrs['list'] = 'patient-referral-list'
        
        # Format doctor choices to show executive info
        self.fields['referred_by_doctor'].label_from_instance = lambda obj: f"{obj.name} (Executive: {obj.agent.username})" if obj.agent else obj.name
        self.fields['referred_to_doctor'].label_from_instance = lambda obj: obj.name

    def _calculate_total_commission(self, profile):
        charge_rate_map = (
            ('bed_charges', 'bed_charges_rate'),
            ('nursing_charges', 'nursing_charges_rate'),
            ('doctor_consultation_charges', 'doctor_consultation_charges_rate'),
            ('investigation_charges', 'investigation_charges_rate'),
            ('procedural_surgical_charges', 'procedural_surgical_charges_rate'),
            ('anaesthesia_charges', 'anaesthesia_charges_rate'),
            ('surgeon_charges', 'surgeon_charges_rate'),
            ('other_charges', 'other_charges_rate'),
        )

        total_charges = Decimal('0')
        charge_wise_commission = Decimal('0')

        for charge_field, rate_field in charge_rate_map:
            amount = Decimal(self.cleaned_data.get(charge_field) or 0)
            total_charges += amount
            rate = Decimal(str(getattr(profile, rate_field, 0.0) or 0.0))
            charge_wise_commission += (amount * rate) / Decimal('100')

        standard_referral_rate = Decimal(str(profile.discount_percentage or 0.0))
        standard_referral_amount = (total_charges * standard_referral_rate) / Decimal('100')

        # Standard referral is always added on top of charge-wise commission.
        return (charge_wise_commission + standard_referral_amount).quantize(Decimal('0.01'))

    def clean(self):
        cleaned_data = super().clean()

        referred_by_doctor = cleaned_data.get('referred_by_doctor')
        patient_referral = cleaned_data.get('patient_referral')
        payment_category = cleaned_data.get('payment_category')

        # If doctor is omitted in the form, derive it from linked referral when available.
        if not referred_by_doctor and patient_referral and patient_referral.referred_by_doctor:
            referred_by_doctor = patient_referral.referred_by_doctor
            cleaned_data['referred_by_doctor'] = referred_by_doctor

        if referred_by_doctor and payment_category:
            try:
                profile = DoctorCommissionProfile.objects.get(
                    doctor=referred_by_doctor,
                    payment_category=payment_category,
                )
            except DoctorCommissionProfile.DoesNotExist:
                cleaned_data['commission_amount'] = Decimal('0.00')
            else:
                cleaned_data['commission_amount'] = self._calculate_total_commission(profile)
        else:
            cleaned_data['commission_amount'] = Decimal('0.00')

        return cleaned_data


class DoctorCommissionForm(forms.ModelForm):
    """Form for editing referral rates and referral percentage."""
    class Meta:
        model = DoctorCommissionProfile
        fields = [
            'bed_charges_rate', 'nursing_charges_rate', 'doctor_consultation_charges_rate',
            'investigation_charges_rate', 'procedural_surgical_charges_rate',
            'anaesthesia_charges_rate', 'surgeon_charges_rate', 'other_charges_rate',
            'discount_percentage'
        ]
        widgets = {
            'bed_charges_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'nursing_charges_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'doctor_consultation_charges_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'investigation_charges_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'procedural_surgical_charges_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'anaesthesia_charges_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'surgeon_charges_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'other_charges_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'discount_percentage': forms.NumberInput(attrs={'class': 'form-control bg-warning bg-opacity-10', 'step': '0.01'}),
        }


class AgentSelectionForm(forms.Form):
    agent = forms.ModelChoiceField(
        queryset=User.objects.filter(custom_role_assignment__role__name='Mobile App User'),
        empty_label="Select Executive",
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Assign to Executive"
    )


class AgentAssignmentForm(forms.ModelForm):
    """Form for creating a new executive assignment to an area."""
    
    agent = forms.ModelChoiceField(
        queryset=User.objects.filter(custom_role_assignment__role__name='Mobile App User', is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Select Executive'
    )
    
    area = forms.ModelChoiceField(
        queryset=Area.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Select Area'
    )

    class Meta:
        model = AgentAssignment
        fields = ['area', 'agent', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional notes for this assignment'}),
        }

