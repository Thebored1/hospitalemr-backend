from django import forms
from django.contrib.auth.forms import UserCreationForm, SetPasswordForm
from core.models import User, Trip, DoctorReferral, Admission, Specialization, Qualification, Area, Address, AgentAssignment, PatientReferral, DoctorCommissionProfile


class AgentCreationForm(UserCreationForm):
    """Form for creating new agent accounts."""
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            
    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'advisor'  # Set role to advisor
        if commit:
            user.save()
        return user


class AgentUpdateForm(forms.ModelForm):
    """Form for updating agent details (without password)."""
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            else:
                field.widget.attrs['class'] = 'form-control'


class AgentPasswordForm(SetPasswordForm):
    """Form for admin to set/reset agent password."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'


class TripCreateForm(forms.ModelForm):
    """Form for creating trips and assigning to agents."""
    
    agent = forms.ModelChoiceField(
        queryset=User.objects.filter(role='advisor', is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Assign to Agent'
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
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Area Name'}),
            'street': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Street Address'}),
            'landmark': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Landmark'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'pincode': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Pincode'}),
            'region': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Region (e.g. Vidarbha)'}),
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
        fields = ['area', 'street', 'pincode', 'landmark']
        widgets = {
            'street': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Street/Building'}),
            'pincode': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Pincode'}),
            'landmark': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Near...'}),
        }


class DoctorForm(forms.ModelForm):
    """Form for manually creating/editing doctors - assigned to agents later via trips."""
    
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
        
        # Format doctor choices to show agent info
        self.fields['referred_by_doctor'].label_from_instance = lambda obj: f"{obj.name} (Agent: {obj.agent.username})" if obj.agent else obj.name
        self.fields['referred_to_doctor'].label_from_instance = lambda obj: obj.name


class DoctorCommissionForm(forms.ModelForm):
    """Form for editing commission rates and discount."""
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
        queryset=User.objects.filter(role='advisor'),
        empty_label="Select Agent",
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Assign to Agent"
    )


class AgentAssignmentForm(forms.ModelForm):
    """Form for creating a new agent assignment to an area."""
    
    agent = forms.ModelChoiceField(
        queryset=User.objects.filter(role='advisor', is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Select Agent'
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

