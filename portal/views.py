from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, TemplateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.db.models import Count, Q, Sum, F
from django.utils import timezone

from core.models import User, Trip, DoctorReferral, PatientReferral, OvernightStay, Admission, Area, Address, AgentAssignment, DoctorCommissionProfile, PaymentCategory, AgentAssignmentDoctorStatus
from .forms import AgentCreationForm, AgentUpdateForm, AgentPasswordForm, TripCreateForm, DoctorAssignmentForm, AdmissionForm, DoctorForm, AgentSelectionForm, AreaForm, AddressForm, AgentAssignmentForm
from core.serializers import (
    UserSerializer, DoctorReferralSerializer, PatientReferralSerializer, 
    TripSerializer, AreaSerializer, AddressSerializer
)


# Require staff/admin access for all portal views
class PortalMixin:
    """Base mixin for all portal views - requires staff access."""
    
    @method_decorator(staff_member_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)


class DashboardView(PortalMixin, TemplateView):
    """Admin dashboard with summary statistics."""
    template_name = 'portal/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_agents'] = User.objects.filter(role='advisor').count()
        context['active_agents'] = User.objects.filter(role='advisor', is_active=True).count()
        context['total_trips'] = Trip.objects.count()
        context['ongoing_trips'] = Trip.objects.filter(status='ONGOING').count()
        context['completed_trips'] = Trip.objects.filter(status='COMPLETED').count()
        context['total_doctor_referrals'] = DoctorReferral.objects.count()
        context['total_patient_referrals'] = PatientReferral.objects.count()
        
        # Recent trips
        context['recent_trips'] = Trip.objects.select_related('agent').order_by('-start_time')[:5]
        
        return context


# ============ Agent Management ============

class AgentListView(PortalMixin, ListView):
    """List all agents (advisors)."""
    model = User
    template_name = 'portal/agents/list.html'
    context_object_name = 'agents'
    
    def get_queryset(self):
        queryset = User.objects.filter(role='advisor').annotate(
            trip_count=Count('trips')
        ).order_by('-date_joined')
        
        # Search
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(
                Q(username__icontains=q) |
                Q(first_name__icontains=q) |
                Q(last_name__icontains=q) |
                Q(email__icontains=q)
            )
            
        # Filter
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
            
        return queryset


class AgentCreateView(PortalMixin, CreateView):
    """Create a new agent."""
    model = User
    form_class = AgentCreationForm
    template_name = 'portal/agents/form.html'
    success_url = reverse_lazy('portal:agent_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create New Agent'
        context['button_text'] = 'Create Agent'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, f'Agent "{form.instance.username}" created successfully.')
        return super().form_valid(form)


class AgentUpdateView(PortalMixin, UpdateView):
    """Edit an existing agent."""
    model = User
    form_class = AgentUpdateForm
    template_name = 'portal/agents/form.html'
    success_url = reverse_lazy('portal:agent_list')
    
    def get_queryset(self):
        return User.objects.filter(role='advisor')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Edit Agent: {self.object.username}'
        context['button_text'] = 'Save Changes'
        context['is_edit'] = True
        return context
    
    def form_valid(self, form):
        messages.success(self.request, f'Agent "{form.instance.username}" updated successfully.')
        return super().form_valid(form)


class AgentPasswordChangeView(PortalMixin, View):
    """Change agent password."""
    template_name = 'portal/agents/password.html'
    
    def get_agent(self, pk):
        return get_object_or_404(User, pk=pk, role='advisor')
    
    def get(self, request, pk):
        agent = self.get_agent(pk)
        form = AgentPasswordForm(user=agent)
        return render(request, self.template_name, {'form': form, 'agent': agent})
    
    def post(self, request, pk):
        agent = self.get_agent(pk)
        form = AgentPasswordForm(user=agent, data=request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f'Password for "{agent.username}" changed successfully.')
            return redirect('portal:agent_list')
        return render(request, self.template_name, {'form': form, 'agent': agent})


class AgentDeleteView(PortalMixin, DeleteView):
    """Delete an agent."""
    model = User
    template_name = 'portal/agents/delete.html'
    success_url = reverse_lazy('portal:agent_list')
    context_object_name = 'agent'
    
    def get_queryset(self):
        return User.objects.filter(role='advisor')
    
    def form_valid(self, form):
        messages.success(self.request, f'Agent "{self.object.username}" deleted successfully.')
        return super().form_valid(form)


# ============ Trip Management ============

class TripListView(PortalMixin, ListView):
    """List all trips with details."""
    model = Trip
    template_name = 'portal/trips/list.html'
    context_object_name = 'trips'
    
    def get_queryset(self):
        queryset = Trip.objects.select_related('agent').annotate(
            doctor_count=Count('doctor_referrals'),
            stay_count=Count('overnight_stays')
        ).order_by('-start_time')
        
        # Search
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(
                Q(id__icontains=q) |
                Q(start_location__icontains=q) |
                Q(end_location__icontains=q) |
                Q(agent__username__icontains=q) |
                Q(agent__first_name__icontains=q)
            )
            
        # Filter
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
            
        agent_id = self.request.GET.get('agent')
        if agent_id:
            queryset = queryset.filter(agent_id=agent_id)
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Pass agents for filter dropdown
        context['agents'] = User.objects.filter(role='advisor', is_active=True)
        return context


class TripCreateView(PortalMixin, CreateView):
    """Create a new trip and assign to an agent."""
    model = Trip
    form_class = TripCreateForm
    template_name = 'portal/trips/form.html'
    success_url = reverse_lazy('portal:trip_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create New Trip'
        context['button_text'] = 'Create Trip'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, f'Trip created and assigned to {form.instance.agent.username}.')
        return super().form_valid(form)


class TripDetailView(PortalMixin, DetailView):
    """View full trip details including referrals and stays."""
    model = Trip
    template_name = 'portal/trips/detail.html'
    context_object_name = 'trip'
    
    def get_queryset(self):
        return Trip.objects.select_related('agent').prefetch_related(
            'doctor_referrals', 'overnight_stays'
        )


class AssignDoctorsView(PortalMixin, View):
    """Assign doctors to a trip for the agent to visit."""
    template_name = 'portal/trips/assign_doctors.html'
    
    def get_trip(self, pk):
        return get_object_or_404(Trip.objects.select_related('agent'), pk=pk)
    
    def get(self, request, pk):
        trip = self.get_trip(pk)
        form = DoctorAssignmentForm()
        doctors = trip.doctor_referrals.all()
        return render(request, self.template_name, {
            'trip': trip,
            'form': form,
            'doctors': doctors
        })
    
    def post(self, request, pk):
        trip = self.get_trip(pk)
        form = DoctorAssignmentForm(request.POST)
        
        if form.is_valid():
            DoctorReferral.objects.create(
                trip=trip,
                agent=trip.agent,
                name=form.cleaned_data['name'],
                specialization=form.cleaned_data.get('specialization').name if form.cleaned_data.get('specialization') else '',
                contact_number=form.cleaned_data.get('contact_number', ''),
                area=form.cleaned_data.get('area', ''),
                street=form.cleaned_data.get('street', ''),
                city=form.cleaned_data.get('city', ''),
                pin=form.cleaned_data.get('pin', ''),
                status='Assigned'
            )
            messages.success(request, f'Doctor "{form.cleaned_data["name"]}" assigned to trip.')
            return redirect('portal:trip_assign_doctors', pk=pk)
        
        doctors = trip.doctor_referrals.all()
        return render(request, self.template_name, {
            'trip': trip,
            'form': form,
            'doctors': doctors
        })


# ============ Doctor Master Table ============

class DoctorListView(PortalMixin, ListView):
    """Master list of all doctors across all trips."""
    model = DoctorReferral
    template_name = 'portal/doctors/list.html'
    context_object_name = 'doctors'
    
    def get_queryset(self):
        queryset = DoctorReferral.objects.select_related('agent', 'trip', 'address_details__area').order_by('-created_at')
        
        # Search
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(
                Q(name__icontains=q) |
                Q(specialization__icontains=q) |
                Q(contact_number__icontains=q) |
                Q(email__icontains=q) |
                Q(address_details__area__name__icontains=q) |
                Q(address_details__area__city__icontains=q)
            )
            
        agent_id = self.request.GET.get('agent')
        if agent_id:
            queryset = queryset.filter(agent_id=agent_id)
        
        # Get all area IDs that have an active agent assignment
        assigned_area_ids = set(
            AgentAssignment.objects.values_list('area_id', flat=True)
        )
        
        # Deduplicate by name - keep only the most recent entry per unique doctor name
        seen_names = set()
        unique_doctors = []
        for doctor in queryset:
            name_key = doctor.name.lower().strip()
            if name_key not in seen_names:
                seen_names.add(name_key)
                doctor.visit_count = DoctorReferral.objects.filter(name__iexact=doctor.name).count()
                # Compute assignment status dynamically
                area_id = getattr(getattr(getattr(doctor, 'address_details', None), 'area', None), 'id', None)
                doctor.is_assigned = area_id is not None and area_id in assigned_area_ids
                unique_doctors.append(doctor)
        
        # Filter by status after computing
        status = self.request.GET.get('status')
        if status == 'Assigned':
            unique_doctors = [d for d in unique_doctors if d.is_assigned]
        elif status == 'Not Assigned':
            unique_doctors = [d for d in unique_doctors if not d.is_assigned]
        
        return unique_doctors

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['agents'] = User.objects.filter(role='advisor', is_active=True)
        return context


class DoctorDetailView(PortalMixin, DetailView):
    """View full doctor details."""
    model = DoctorReferral
    template_name = 'portal/doctors/detail.html'
    context_object_name = 'doctor'
    
    def get_queryset(self):
        return DoctorReferral.objects.select_related('agent', 'trip')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get visit history - all entries with the same doctor name (excluding current)
        doctor = self.object
        context['visit_history'] = DoctorReferral.objects.filter(
            name=doctor.name
        ).exclude(pk=doctor.pk).select_related('agent', 'trip').order_by('-created_at')
        return context


class DoctorCreateView(PortalMixin, CreateView):
    """Manually create a new doctor with nested address."""
    model = DoctorReferral
    form_class = DoctorForm
    template_name = 'portal/doctors/form.html'
    success_url = reverse_lazy('portal:doctor_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add New Doctor'
        context['button_text'] = 'Create Doctor'
        if self.request.POST:
            context['address_form'] = AddressForm(self.request.POST)
        else:
            context['address_form'] = AddressForm()
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        address_form = context['address_form']
        
        # If it's an internal doctor, we don't need address validation
        is_internal = form.cleaned_data.get('is_internal', False)
        
        if is_internal or address_form.is_valid():
            self.object = form.save(commit=False)
            
            if is_internal:
                self.object.address_details = None
            else:
                # Create address first
                address = address_form.save()
                self.object.address_details = address
                
            self.object.save()
            messages.success(self.request, f'Doctor "{self.object.name}" created successfully.')
            return redirect(self.success_url)
        else:
            return self.render_to_response(self.get_context_data(form=form))


class DoctorUpdateView(PortalMixin, UpdateView):
    """Edit an existing doctor and their address."""
    model = DoctorReferral
    form_class = DoctorForm
    template_name = 'portal/doctors/form.html'
    success_url = reverse_lazy('portal:doctor_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Edit Doctor: {self.object.name}'
        context['button_text'] = 'Save Changes'
        context['is_edit'] = True
        
        # Populate address form with existing instance or empty
        address_instance = self.object.address_details
        if self.request.POST:
            context['address_form'] = AddressForm(self.request.POST, instance=address_instance)
        else:
            context['address_form'] = AddressForm(instance=address_instance)
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        address_form = context['address_form']
        
        is_internal = form.cleaned_data.get('is_internal', False)
        
        if is_internal or address_form.is_valid():
            self.object = form.save(commit=False)
            
            if is_internal:
                self.object.address_details = None
            else:
                # Save address only if it's changed and valid
                if address_form.has_changed():
                    address = address_form.save()
                    self.object.address_details = address
            
            self.object.save()
            messages.success(self.request, f'Doctor "{self.object.name}" updated successfully.')
            return redirect(self.success_url)
        else:
            return self.render_to_response(self.get_context_data(form=form))


from django.forms import modelformset_factory
from .forms import DoctorCommissionForm

class DoctorCommissionUpdateView(PortalMixin, TemplateView):
    """Manage commission profiles for a doctor."""
    template_name = 'portal/doctors/commission_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        doctor = get_object_or_404(DoctorReferral, pk=self.kwargs['pk'])
        context['doctor'] = doctor
        context['title'] = f'Manage Commissions: {doctor.name}'
        
        # Ensure profiles exist for all payment categories
        for cat in PaymentCategory.objects.all():
            DoctorCommissionProfile.objects.get_or_create(
                doctor=doctor,
                payment_category=cat
            )
            
        CommissionFormSet = modelformset_factory(
            DoctorCommissionProfile,
            form=DoctorCommissionForm,
            extra=0,
            can_delete=False
        )
        
        if self.request.POST:
            formset = CommissionFormSet(self.request.POST, queryset=doctor.commission_profiles.select_related('payment_category').all())
        else:
            formset = CommissionFormSet(queryset=doctor.commission_profiles.select_related('payment_category').all())
            
        context['formset'] = formset
        return context
    
    def post(self, request, *args, **kwargs):
        context = self.get_context_data()
        formset = context['formset']
        
        if formset.is_valid():
            formset.save()
            messages.success(request, 'Commission rates updated successfully.')
            return redirect('portal:doctor_list')
            
        return self.render_to_response(context)


# ============ Area Management ============

class AreaListView(PortalMixin, ListView):
    """List all areas and assigned agents."""
    model = Area
    template_name = 'portal/areas/list.html'
    context_object_name = 'areas'
    paginate_by = 50
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Area Management'
        return context

class AreaCreateView(PortalMixin, CreateView):
    """Create a new Area."""
    model = Area
    form_class = AreaForm
    template_name = 'portal/areas/form.html'
    success_url = reverse_lazy('portal:area_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add New Area'
        context['button_text'] = 'Create Area'
        return context
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Log assignment if agent is selected during creation
        if form.instance.agent:
            AgentAssignment.objects.create(
                agent=form.instance.agent,
                area=self.object,
                notes=f"Assigned upon Area Creation on {timezone.now().date()}"
            )
            
        messages.success(self.request, f'Area "{form.instance.name}" created successfully.')
        return response

class AreaUpdateView(PortalMixin, UpdateView):
    """Edit Area details."""
    model = Area
    form_class = AreaForm
    template_name = 'portal/areas/form.html'
    success_url = reverse_lazy('portal:area_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Edit Area: {self.object.name}'
        context['button_text'] = 'Save Changes'
        context['is_edit'] = True
        return context
    
    def form_valid(self, form):
        # Check if agent has changed
        old_agent = Area.objects.get(pk=self.object.pk).agent
        new_agent = form.cleaned_data.get('agent')
        
        response = super().form_valid(form)
        
        if new_agent and (new_agent != old_agent):
            AgentAssignment.objects.create(
                agent=new_agent,
                area=self.object,
                notes=f"Assigned via Area Edit on {timezone.now().date()}"
            )
            
        messages.success(self.request, f'Area "{form.instance.name}" updated successfully.')
        return response


# ============ Admission & Billing ============

class AdmissionListView(PortalMixin, ListView):
    """List all admission records."""
    model = Admission
    template_name = 'portal/admissions/list.html'
    context_object_name = 'admissions'
    
    def get_queryset(self):
        queryset = Admission.objects.select_related(
            'referred_by_doctor',
            'referred_by_doctor__agent',
            'patient_referral',
            'patient_referral__agent',
        ).order_by('-admission_date')
        
        # Search
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(
                Q(patient_name__icontains=q) |
                Q(id__icontains=q) |
                Q(referred_by_doctor__name__icontains=q)
            )
            
        # Filter
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
            
        adm_type = self.request.GET.get('type')
        if adm_type:
            queryset = queryset.filter(admission_type=adm_type)
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_opd'] = Admission.objects.filter(admission_type='OPD').count()
        context['total_ipd'] = Admission.objects.filter(admission_type='IPD').count()
        context['admitted_count'] = Admission.objects.filter(status='ADMITTED').count()
        return context


class AdmissionCreateView(PortalMixin, CreateView):
    """Create a new admission record."""
    model = Admission
    form_class = AdmissionForm
    template_name = 'portal/admissions/form.html'
    success_url = reverse_lazy('portal:admission_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'New Admission'
        context['button_text'] = 'Create Admission'
        context['patient_referrals'] = PatientReferral.objects.filter(status='Pending').order_by('patient_name')
        return context
    
    def form_valid(self, form):
        response = super().form_valid(form)
        referral = self.object.patient_referral
        if not referral and self.object.patient_name:
            referral = PatientReferral.objects.filter(
                patient_name__iexact=self.object.patient_name
            ).order_by('-reported_on').first()
            if referral:
                self.object.patient_referral = referral
                self.object.save(update_fields=['patient_referral'])
        if referral and referral.status != 'Admitted':
            referral.status = 'Admitted'
            referral.save(update_fields=['status'])
        messages.success(self.request, f'Admission for "{self.object.patient_name}" created successfully.')
        return response


class AdmissionUpdateView(PortalMixin, UpdateView):
    """Update an admission record (edit billing)."""
    model = Admission
    form_class = AdmissionForm
    template_name = 'portal/admissions/form.html'
    success_url = reverse_lazy('portal:admission_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Edit Admission: {self.object.patient_name}'
        context['button_text'] = 'Save Changes'
        context['is_edit'] = True
        if self.object.patient_referral:
            context['patient_referrals'] = PatientReferral.objects.filter(
                Q(status='Pending') | Q(pk=self.object.patient_referral_id)
            ).order_by('patient_name')
        else:
            context['patient_referrals'] = PatientReferral.objects.filter(status='Pending').order_by('patient_name')
        return context
    
    def form_valid(self, form):
        response = super().form_valid(form)
        referral = self.object.patient_referral
        if not referral and self.object.patient_name:
            referral = PatientReferral.objects.filter(
                patient_name__iexact=self.object.patient_name
            ).order_by('-reported_on').first()
            if referral:
                self.object.patient_referral = referral
                self.object.save(update_fields=['patient_referral'])
        if referral and referral.status != 'Admitted':
            referral.status = 'Admitted'
            referral.save(update_fields=['status'])
        messages.success(self.request, f'Admission for "{self.object.patient_name}" updated successfully.')
        return response


class AdmissionDetailView(PortalMixin, DetailView):
    """View full admission details with billing breakdown."""
    model = Admission
    template_name = 'portal/admissions/detail.html'
    context_object_name = 'admission'
    
    def get_queryset(self):
        return Admission.objects.select_related('referred_by_doctor', 'referred_by_doctor__agent')


class AdmissionDischargeView(PortalMixin, View):
    """Mark an admission as discharged and update linked referral status."""

    def post(self, request, pk):
        admission = get_object_or_404(Admission, pk=pk)
        if admission.status != 'DISCHARGED':
            admission.status = 'DISCHARGED'
            if not admission.discharge_date:
                admission.discharge_date = timezone.now()
            admission.save(update_fields=['status', 'discharge_date'])

            referral = admission.patient_referral
            if referral and referral.status != 'Dismissed':
                referral.status = 'Dismissed'
                referral.save(update_fields=['status'])

            messages.success(request, f'Admission #{admission.id} discharged.')
        else:
            messages.info(request, f'Admission #{admission.id} is already discharged.')
        return redirect('portal:admission_detail', pk=pk)

class ReportsDashboardView(PortalMixin, TemplateView):
    template_name = 'portal/reports/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # --- Filters for Dropdowns ---
        context['areas'] = Area.objects.all().order_by('name')
        context['agents'] = User.objects.filter(role='advisor', is_active=True).order_by('username')
        context['doctors_list'] = DoctorReferral.objects.all().order_by('name')
        context['specializations'] = DoctorReferral.objects.values_list('specialization', flat=True).distinct().order_by('specialization')

        # --- Base Queryset for Admissions ---
        admissions = Admission.objects.all()
        
        # --- Apply Filters from GET ---
        area_id = self.request.GET.get('area')
        agent_id = self.request.GET.get('agent')
        doctor_id = self.request.GET.get('doctor')
        spec = self.request.GET.get('specialization')
        date_start = self.request.GET.get('date_start')
        date_end = self.request.GET.get('date_end')

        filter_q = Q()
        if area_id:
            filter_q &= Q(referred_by_doctor__address_details__area_id=area_id)
        if agent_id:
            filter_q &= Q(patient_referral__agent_id=agent_id)
        if doctor_id:
            filter_q &= Q(referred_by_doctor_id=doctor_id)
        if spec:
            filter_q &= Q(referred_by_doctor__specialization__iexact=spec)
        if date_start:
            filter_q &= Q(created_at__date__gte=date_start)
        if date_end:
            filter_q &= Q(created_at__date__lte=date_end)

        # Use the filtered dataset for ALL reports to ensure consistency
        filtered_admissions = admissions.filter(filter_q)

        # --- 1. Doctor-wise Revenue Report ---
        doctor_revenue = filtered_admissions.filter(referred_by_doctor__isnull=False).values(
            'referred_by_doctor__name'
        ).annotate(
            total_revenue=Sum(
                F('bed_charges') + F('nursing_charges') + F('doctor_consultation_charges') + 
                F('investigation_charges') + F('procedural_surgical_charges') + 
                F('anaesthesia_charges') + F('surgeon_charges') + F('other_charges')
            ),
            opd_count=Count('id', filter=Q(admission_type='OPD')),
            ipd_count=Count('id', filter=Q(admission_type='IPD'))
        ).order_by('-total_revenue')

        # --- 1b. Merge with All Doctors in Context (to show 0 revenue doctors) ---
        # Fetch all doctors that match the current filter context
        doc_init_q = Q()
        if area_id: doc_init_q &= Q(address_details__area_id=area_id)
        if spec: doc_init_q &= Q(specialization__iexact=spec)
        if doctor_id: doc_init_q &= Q(id=doctor_id)
        if agent_id: 
            # Check legacy agent field OR area-based assignment
            doc_init_q &= (Q(agent_id=agent_id) | Q(address_details__area__agent_id=agent_id))
        
        doctors_in_context = DoctorReferral.objects.filter(doc_init_q).values('name')
        
        # Start with everyone who actually has revenue for this period to ensure no data loss
        full_doctor_stats = list(doctor_revenue)
        existing_names = {d['referred_by_doctor__name'] for d in full_doctor_stats}
        
        # Add assigned doctors who referred no patients (0 revenue)
        for doc in doctors_in_context:
            doc_name = doc['name']
            if doc_name not in existing_names:
                full_doctor_stats.append({
                    'referred_by_doctor__name': doc_name,
                    'total_revenue': 0,
                    'opd_count': 0,
                    'ipd_count': 0
                })
        
        # Sort by total revenue descending
        full_doctor_stats.sort(key=lambda x: x.get('total_revenue', 0) or 0, reverse=True)

        
        # --- 2. Agent-wise Revenue Report ---
        agent_revenue = filtered_admissions.filter(patient_referral__agent__isnull=False).values(
            'patient_referral__agent__username'
        ).annotate(
            total_revenue=Sum(
                F('bed_charges') + F('nursing_charges') + F('doctor_consultation_charges') + 
                F('investigation_charges') + F('procedural_surgical_charges') + 
                F('anaesthesia_charges') + F('surgeon_charges') + F('other_charges')
            ),
            opd_count=Count('id', filter=Q(admission_type='OPD')),
            ipd_count=Count('id', filter=Q(admission_type='IPD'))
        ).order_by('-total_revenue')

        # --- 2b. Merge with All Agents (to show 0 revenue agents) ---
        # Only if no specific agent is selected, or if selected, ensure they appear
        # Simple approach: Get all advisors, or filtered agent
        agent_qs = User.objects.filter(role='advisor', is_active=True)
        if agent_id:
            agent_qs = agent_qs.filter(id=agent_id)
        
        all_agents = agent_qs.values('username')
        
        # Start with actual revenue data to ensure accuracy
        full_agent_stats = list(agent_revenue)
        existing_agent_names = {a['patient_referral__agent__username'] for a in full_agent_stats}
        
        # Add active agents who have no referrals in this period
        for agent in all_agents:
            username = agent['username']
            if username not in existing_agent_names:
                full_agent_stats.append({
                    'patient_referral__agent__username': username,
                    'total_revenue': 0,
                    'opd_count': 0,
                    'ipd_count': 0
                })
        full_agent_stats.sort(key=lambda x: x.get('total_revenue', 0) or 0, reverse=True)

        
        # --- 3. Category-wise Patient Details ---
        category_stats = filtered_admissions.values(
            'payment_category__name'
        ).annotate(
            patient_count=Count('id'),
            total_revenue=Sum(
                F('bed_charges') + F('nursing_charges') + F('doctor_consultation_charges') + 
                F('investigation_charges') + F('procedural_surgical_charges') + 
                F('anaesthesia_charges') + F('surgeon_charges') + F('other_charges')
            )
        ).order_by('-patient_count')

        # --- 3b. Merge with All Categories ---
        all_cats = PaymentCategory.objects.values('name')
        cat_map = {c['payment_category__name']: c for c in category_stats}
        
        full_category_stats = []
        for cat in all_cats:
            cat_name = cat['name']
            if cat_name in cat_map:
                full_category_stats.append(cat_map[cat_name])
            else:
                full_category_stats.append({
                    'payment_category__name': cat_name,
                    'patient_count': 0,
                    'total_revenue': 0
                })
        full_category_stats.sort(key=lambda x: x.get('patient_count', 0) or 0, reverse=True)
        
        # --- 4. Custom Analytics / Explorer Stats ---
        explorer_stats = filtered_admissions.aggregate(
            total_revenue=Sum(
                F('bed_charges') + F('nursing_charges') + F('doctor_consultation_charges') + 
                F('investigation_charges') + F('procedural_surgical_charges') + 
                F('anaesthesia_charges') + F('surgeon_charges') + F('other_charges')
            ),
            patient_count=Count('id'),
            opd_count=Count('id', filter=Q(admission_type='OPD')),
            ipd_count=Count('id', filter=Q(admission_type='IPD'))
        )

        # Count of unique doctors in the filtered context
        doc_q = Q()
        if area_id: doc_q &= Q(address_details__area_id=area_id)
        if spec: doc_q &= Q(specialization__iexact=spec)
        if doctor_id: doc_q &= Q(id=doctor_id)
        if agent_id: doc_q &= Q(agent_id=agent_id)
        explorer_stats['doctor_count'] = DoctorReferral.objects.filter(doc_q).count()

        # --- 5. Total Summary Stats (Filtered) ---
        total_summary = filtered_admissions.aggregate(
            total_revenue=Sum(
                F('bed_charges') + F('nursing_charges') + F('doctor_consultation_charges') + 
                F('investigation_charges') + F('procedural_surgical_charges') + 
                F('anaesthesia_charges') + F('surgeon_charges') + F('other_charges')
            ),
            total_patients=Count('id'),
            opd_total=Count('id', filter=Q(admission_type='OPD')),
            ipd_total=Count('id', filter=Q(admission_type='IPD'))
        )
        
        # Provide a cleaner filters dict for the template to avoid complex logic/formatting issues
        context['filters_data'] = {
            'area_id': int(area_id) if area_id and area_id.isdigit() else None,
            'agent_id': int(agent_id) if agent_id and agent_id.isdigit() else None,
            'doctor_id': int(doctor_id) if doctor_id and doctor_id.isdigit() else None,
            'specialization': spec,
            'date_start': date_start,
            'date_end': date_end,
        }

        context['has_filters'] = any([area_id, agent_id, doctor_id, spec, date_start, date_end])

        context.update({
            'doctor_revenue': full_doctor_stats,
            'agent_revenue': full_agent_stats,
            'category_stats': full_category_stats,
            'explorer_stats': explorer_stats,
            'filtered_admissions': filtered_admissions.select_related('patient_referral', 'referred_by_doctor', 'payment_category').order_by('-created_at'),
            'total_summary': total_summary,
            'title': 'Hospital Reports Dashboard',
            'filters': self.request.GET,
            'active_tab': self.request.GET.get('active_tab', 'patients')
        })
        return context


class DoctorAssignmentView(PortalMixin, ListView):
    """View to bulk assign doctors to agents."""
    model = DoctorReferral
    template_name = 'portal/doctors/assign.html'
    context_object_name = 'doctors'
    paginate_by = 50

    def get_queryset(self):
        queryset = DoctorReferral.objects.all().order_by('name')
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | 
                Q(address_details__area__name__icontains=search) | 
                Q(address_details__area__city__icontains=search) | 
                Q(specialization__icontains=search)
            )
        
        status = self.request.GET.get('status')
        if status == 'unassigned':
            queryset = queryset.filter(agent__isnull=True)
        elif status == 'assigned':
            queryset = queryset.filter(agent__isnull=False)
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = AgentSelectionForm()
        context['title'] = 'Assign Doctors to Agents'
        context['current_status'] = self.request.GET.get('status', 'all')
        return context
    
    def post(self, request, *args, **kwargs):
        form = AgentSelectionForm(request.POST)
        if form.is_valid():
            agent = form.cleaned_data['agent']
            doctor_ids = request.POST.getlist('doctor_ids')
            
            if doctor_ids:
                # Filter out doctors who are currently on an ONGOING trip
                busy_doctors = DoctorReferral.objects.filter(
                    id__in=doctor_ids, 
                    trip__status='ONGOING'
                ).select_related('trip')
                
                busy_ids = [d.id for d in busy_doctors]
                available_ids = [d_id for d_id in doctor_ids if int(d_id) not in busy_ids]
                
                # Perform the update on available doctors
                updated_count = 0
                if available_ids:
                    updated_count = DoctorReferral.objects.filter(id__in=available_ids).update(agent=agent, status='Assigned')
                    messages.success(request, f'Successfully assigned {updated_count} doctors to {agent.username}.')
                
                # Warn about busy doctors
                if busy_doctors:
                    names = ", ".join([d.name for d in busy_doctors])
                    messages.warning(request, f'Skipped {len(busy_doctors)} doctors ({names}) because they are currently on an active Trip. Please wait for the trip to complete.')
            else:
                messages.warning(request, 'No doctors selected.')
        else:
            messages.error(request, 'Invalid assignment.')
        
        return redirect('portal:doctor_assignment')

class AgentAssignmentListView(PortalMixin, ListView):
    """List history of agent assignments."""
    model = AgentAssignment
    template_name = 'portal/agents/assignment_list.html'
    context_object_name = 'assignments'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = AgentAssignment.objects.select_related('agent', 'area').order_by('-assigned_at')
        
        # Filter by Agent
        agent_id = self.request.GET.get('agent')
        if agent_id:
            queryset = queryset.filter(agent_id=agent_id)
            
        # Filter by Area
        area_id = self.request.GET.get('area')
        if area_id:
            queryset = queryset.filter(area_id=area_id)
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['agents'] = User.objects.filter(role='advisor', is_active=True)
        context['areas'] = Area.objects.all()
        
        # Calculate completion status using per-assignment visit tracking
        from core.models import AgentAssignmentDoctorStatus
        for assignment in context['assignments']:
            # Get unique doctors currently in this area
            from core.models import DoctorReferral
            raw_area_doctors = DoctorReferral.objects.filter(address_details__area=assignment.area, is_internal=False).order_by('-created_at')
            seen_names = set()
            area_doctors = []
            for d in raw_area_doctors:
                name_key = d.name.lower().strip()
                if name_key not in seen_names:
                    seen_names.add(name_key)
                    area_doctors.append(d)
                    
            total_area_doctors = len(area_doctors)
            
            # Now properly calculate visited and total enabled based ON the deduplicated doctors list
            visited_count = 0
            total_enabled = 0
            
            for doctor in area_doctors:
                status_obj, created = AgentAssignmentDoctorStatus.objects.get_or_create(
                    assignment=assignment,
                    doctor=doctor,
                    defaults={'is_active': True, 'is_visited': False}
                )
                if status_obj.is_active:
                    total_enabled += 1
                    if status_obj.is_visited:
                        visited_count += 1
            
            # If for some reason all are disabled, show 0/0.
            assignment.is_complete = (total_enabled > 0 and visited_count == total_enabled)
            assignment.completion_stats = f"{visited_count}/{total_enabled}"
            
        return context


class AgentAssignmentCreateView(PortalMixin, CreateView):
    """Create a new agent assignment."""
    model = AgentAssignment
    form_class = AgentAssignmentForm
    template_name = 'portal/agents/assignment_form.html'
    success_url = reverse_lazy('portal:agent_assignment_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'New Agent Assignment'
        context['button_text'] = 'Assign Agent'
        context['areas_exist'] = Area.objects.exists()
        return context
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Side-effect: Update the Area's current agent
        assignment = form.instance
        area = assignment.area
        agent = assignment.agent
        
        area.agent = agent
        area.save()
        
        # Auto-create fresh doctor status entries for this assignment
        # Each assignment starts with all doctors unvisited
        from core.models import AgentAssignmentDoctorStatus
        raw_doctors_in_area = DoctorReferral.objects.filter(
            address_details__area=area,
            is_internal=False
        ).order_by('-created_at')
        
        seen_names = set()
        doctors_in_area = []
        for d in raw_doctors_in_area:
            name_key = d.name.lower().strip()
            if name_key not in seen_names:
                seen_names.add(name_key)
                doctors_in_area.append(d)
                
        for doctor in doctors_in_area:
            AgentAssignmentDoctorStatus.objects.get_or_create(
                assignment=assignment,
                doctor=doctor,
                defaults={'is_active': True, 'is_visited': False}
            )
            
            # Reset global doctor status to Assigned so the portal doesn't show confusing 
            # "Referred" but "Pending Visit" statuses
            if doctor.status != 'Assigned':
                doctor.status = 'Assigned'
                doctor.save(update_fields=['status'])
        
        messages.success(self.request, f"Assigned {agent.username} to {area.name} ({len(doctors_in_area)} doctors)")
        return response


class AgentAssignmentDetailView(PortalMixin, DetailView):
    """View details of an agent assignment."""
    model = AgentAssignment
    template_name = 'portal/agents/assignment_detail.html'
    context_object_name = 'assignment'
    
    def get_queryset(self):
        return AgentAssignment.objects.select_related('agent', 'area')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        assignment = self.object
        
        # Get doctors in this area, deduplicated by name
        raw_doctors = DoctorReferral.objects.filter(
            address_details__area=assignment.area,
            is_internal=False
        ).select_related('agent', 'trip', 'address_details').order_by('-created_at')
        
        seen_names = set()
        doctors = []
        for d in raw_doctors:
            name_key = d.name.lower().strip()
            if name_key not in seen_names:
                seen_names.add(name_key)
                doctors.append(d)
        
        # Annotate each doctor with their disabled status for this assignment
        from core.models import AgentAssignmentDoctorStatus
        for doctor in doctors:
            try:
                status = AgentAssignmentDoctorStatus.objects.get(
                    assignment=assignment,
                    doctor=doctor
                )
                doctor.is_disabled_in_assignment = not status.is_active
                doctor.is_visited_in_assignment = status.is_visited
                doctor.visit_trip_in_assignment = status.visit_trip
            except AgentAssignmentDoctorStatus.DoesNotExist:
                # If no status record exists, doctor is enabled by default
                doctor.is_disabled_in_assignment = False
                doctor.is_visited_in_assignment = False
                doctor.visit_trip_in_assignment = None
        
        context['doctors'] = doctors
        context['doctor_count'] = len(doctors)
        return context


class AgentAssignmentDeleteView(PortalMixin, DeleteView):
    """Delete an agent assignment."""
    model = AgentAssignment
    success_url = reverse_lazy('portal:agent_assignment_list')

    def get(self, request, *args, **kwargs):
        # No confirmation page, POST-only
        return redirect(self.success_url)

    def form_valid(self, form):
        # Sync: If this assignment is the current one for the Area, clear it
        assignment = self.get_object()
        area = assignment.area
        user_agent_id = assignment.agent_id
        
        # 1. Clear Area.agent if it matches
        if area.agent_id == user_agent_id:
            area.agent = None
            area.save()
        
        # 2. Clear individual Doctor assignments in this area for this agent
        # This fixes the "Ghost Doctors" issue in the app
        DoctorReferral.objects.filter(
            address_details__area=area,
            agent_id=user_agent_id
        ).update(agent=None, status='Pending')
            
        messages.success(self.request, 'Assignment deleted successfully.')
        return super().form_valid(form)


# ============ Patient Referrals ============

class PatientReferralListView(PortalMixin, ListView):
    """List all patient referrals."""
    model = PatientReferral
    template_name = 'portal/patients/list.html'
    context_object_name = 'patients'
    ordering = ['-reported_on']
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('agent')
        
        # Search
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(
                Q(patient_name__icontains=q) |
                Q(agent__username__icontains=q) |
                Q(illness__icontains=q)
            )
            
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
            
        return queryset


class PatientReferralStatusUpdateView(PortalMixin, View):
    """Update patient referral status (Pending/Admitted/Dismissed)."""
    allowed_statuses = {'Pending', 'Admitted', 'Dismissed'}

    def post(self, request, pk):
        referral = get_object_or_404(PatientReferral, pk=pk)
        new_status = request.POST.get('status')

        if new_status not in self.allowed_statuses:
            messages.error(request, 'Invalid status update.')
        elif referral.status == new_status:
            messages.info(request, f'Status already {new_status}.')
        else:
            referral.status = new_status
            referral.save(update_fields=['status'])
            messages.success(request, f'Patient "{referral.patient_name}" marked as {new_status}.')

        return redirect(request.META.get('HTTP_REFERER', reverse_lazy('portal:patient_list')))

        return redirect(request.META.get('HTTP_REFERER', reverse_lazy('portal:patient_list')))


from django.http import JsonResponse
@staff_member_required
def get_commission_rates(request):
    """API to fetch commission rates for a doctor and payment category."""
    doctor_id = request.GET.get('doctor_id')
    category_id = request.GET.get('category')  # Now this is a PaymentCategory PK
    
    if not doctor_id or not category_id:
        return JsonResponse({'error': 'Missing parameters'}, status=400)
    
    try:
        profile = DoctorCommissionProfile.objects.get(
            doctor_id=doctor_id, 
            payment_category_id=category_id
        )
        
        return JsonResponse({
            'bed_charges_rate': profile.bed_charges_rate,
            'nursing_charges_rate': profile.nursing_charges_rate,
            'doctor_consultation_charges_rate': profile.doctor_consultation_charges_rate,
            'investigation_charges_rate': profile.investigation_charges_rate,
            'procedural_surgical_charges_rate': profile.procedural_surgical_charges_rate,
            'anaesthesia_charges_rate': profile.anaesthesia_charges_rate,
            'surgeon_charges_rate': profile.surgeon_charges_rate,
            'other_charges_rate': profile.other_charges_rate,
            'discount_percentage': profile.discount_percentage,
        })
    except DoctorCommissionProfile.DoesNotExist:
        # Return all zeros if no profile exists
        return JsonResponse({
            'bed_charges_rate': 0.0,
            'nursing_charges_rate': 0.0,
            'doctor_consultation_charges_rate': 0.0,
            'investigation_charges_rate': 0.0,
            'procedural_surgical_charges_rate': 0.0,
            'anaesthesia_charges_rate': 0.0,
            'surgeon_charges_rate': 0.0,
            'other_charges_rate': 0.0,
            'discount_percentage': 0.0,
        })


class PaymentCategoryCreateView(PortalMixin, CreateView):
    """Quick-add view for creating payment categories."""
    model = PaymentCategory
    fields = ['name', 'code']
    template_name = 'portal/payment_category_form.html'

    def get_success_url(self):
        next_url = self.request.GET.get('next') or self.request.POST.get('next')
        if next_url:
            return next_url
        return reverse_lazy('portal:admission_create')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add Payment Category'
        context['next'] = self.request.GET.get('next', '')
        return context

    def form_valid(self, form):
        messages.success(self.request, f'Payment category "{form.instance.name}" created.')
        return super().form_valid(form)


# ============ Doctor Toggle for Agent Assignments ============

from django.http import JsonResponse
from core.models import AgentAssignmentDoctorStatus

@staff_member_required
def toggle_doctor_assignment_status(request, assignment_id, doctor_id):
    """Toggle doctor active/inactive status for a specific agent assignment."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)
    
    try:
        assignment = get_object_or_404(AgentAssignment, pk=assignment_id)
        doctor = get_object_or_404(DoctorReferral, pk=doctor_id)
        
        # Get or create status record
        status, created = AgentAssignmentDoctorStatus.objects.get_or_create(
            assignment=assignment,
            doctor=doctor,
            defaults={'is_active': True}
        )
        
        # Toggle status
        status.is_active = not status.is_active
        status.save()
        
        return JsonResponse({
            'success': True,
            'is_active': status.is_active,
            'message': f"Doctor {'enabled' if status.is_active else 'disabled'} successfully."
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

