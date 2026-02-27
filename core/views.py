from rest_framework import viewsets, status
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from .models import Task, DoctorReferral, PatientReferral, Trip, OvernightStay, Specialization, Qualification, Area, Address, User, AgentAssignment, AgentAssignmentDoctorStatus
from .serializers import TaskSerializer, DoctorReferralSerializer, PatientReferralSerializer, TripSerializer, OvernightStaySerializer, SpecializationSerializer, QualificationSerializer, AreaSerializer, AddressSerializer

class SpecializationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing doctor specializations"""
    queryset = Specialization.objects.all()
    serializer_class = SpecializationSerializer
    permission_classes = [IsAuthenticated]


class QualificationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing doctor qualifications"""
    queryset = Qualification.objects.all()
    serializer_class = QualificationSerializer
    permission_classes = [IsAuthenticated]

class CustomAuthToken(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'username': user.username,
            'role': user.role
        })

class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        # Automatically set raised_by to the current user
        serializer.save(raised_by=self.request.user)

class TripViewSet(viewsets.ModelViewSet):
    queryset = Trip.objects.all()
    serializer_class = TripSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Filter trips by the current agent
        return Trip.objects.filter(agent=self.request.user)

    def perform_create(self, serializer):
        serializer.save(agent=self.request.user)

    @action(detail=False, methods=['get'])
    def current(self, request):
        # Get the current ongoing trip
        trip = Trip.objects.filter(agent=request.user, status='ONGOING').first()
        if trip:
            serializer = self.get_serializer(trip)
            return Response(serializer.data)
        return Response(None)

    @action(detail=True, methods=['patch'])
    def end_trip(self, request, pk=None):
        trip = self.get_object()
        if trip.status == 'COMPLETED':
             return Response({'error': 'Trip already completed'}, status=status.HTTP_400_BAD_REQUEST)
        
        trip.status = 'COMPLETED'
        trip.end_time = timezone.now()
        # Update other fields if provided appropriately
        if 'odometer_end_image' in request.data:
             trip.odometer_end_image = request.data['odometer_end_image']
        if 'total_kilometers' in request.data:
             trip.total_kilometers = request.data['total_kilometers']
        if 'additional_expenses' in request.data:
             trip.additional_expenses = request.data['additional_expenses']
        if 'end_lat' in request.data:
             trip.end_lat = request.data['end_lat']
        if 'end_long' in request.data:
             trip.end_long = request.data['end_long']
        
        trip.save()
        serializer = self.get_serializer(trip)
        return Response(serializer.data)

class AreaViewSet(viewsets.ModelViewSet):
    serializer_class = AreaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Area.objects.all()
        # Only return areas assigned to this agent via AgentAssignment
        assigned_area_ids = AgentAssignment.objects.filter(
            agent=self.request.user
        ).values_list('area_id', flat=True)
        return Area.objects.filter(id__in=assigned_area_ids)

    @action(detail=True, methods=['post'])
    def assign_agent(self, request, pk=None):
        area = self.get_object()
        agent_id = request.data.get('agent_id')
        if agent_id:
            try:
                agent = User.objects.get(id=agent_id, role='advisor')
                area.agent = agent
                area.save()
                return Response({'status': 'assigned'})
            except User.DoesNotExist:
                return Response({'error': 'Agent not found'}, status=400)
        return Response({'error': 'agent_id required'}, status=400)


class DoctorReferralViewSet(viewsets.ModelViewSet):
    queryset = DoctorReferral.objects.all()
    serializer_class = DoctorReferralSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        from django.db.models import Q
        # Exclude internal doctors from the visit assigned list for all users
        queryset = DoctorReferral.objects.filter(is_internal=False).order_by('-created_at')
        
        # Support search for autocomplete
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(name__icontains=search).order_by('-created_at')
        else:
            if getattr(self.request.user, 'role', None) == 'advisor':
                # Only show doctors in areas CURRENTLY assigned to this agent
                # Use Area.agent field (current assignment), NOT AgentAssignment (history log)
                assigned_area_ids = Area.objects.filter(
                    agent=self.request.user
                ).values_list('id', flat=True)
                
                # Also fetch area names to match legacy string 'area' field
                # (Though we are moving away from this, keeping for safety if dirty data exists)
                assigned_area_names = Area.objects.filter(id__in=assigned_area_ids).values_list('name', flat=True)
                
                print(f"DEBUG: User={self.request.user}, Assigned IDs={list(assigned_area_ids)}, Assigned Names={list(assigned_area_names)}")

                # Filter by doctors in assigned areas via Address link and exclude internal doctors
                # Note: 'area' field on DoctorReferral was removed, relying on address_details__area
                queryset = queryset.filter(
                    address_details__area_id__in=assigned_area_ids,
                    is_internal=False
                ).distinct().order_by('-created_at')
                
                # Exclude doctors disabled or already visited for the current assignment
                # Since an agent might be assigned multiple areas, find the LATEST assignment for EACH area.
                latest_assignment_ids = []
                for area_id in assigned_area_ids:
                    latest = AgentAssignment.objects.filter(
                        agent=self.request.user,
                        area_id=area_id
                    ).order_by('-assigned_at').first()
                    if latest:
                        latest_assignment_ids.append(latest.id)
                
                if latest_assignment_ids:
                    # Exclude disabled doctors
                    inactive_doctor_ids = AgentAssignmentDoctorStatus.objects.filter(
                        assignment_id__in=latest_assignment_ids,
                        is_active=False
                    ).values_list('doctor_id', flat=True)
                    
                    # Exclude already-visited doctors (per this assignment)
                    visited_doctor_ids = AgentAssignmentDoctorStatus.objects.filter(
                        assignment_id__in=latest_assignment_ids,
                        is_visited=True
                    ).values_list('doctor_id', flat=True)
                    
                    exclude_ids = set(inactive_doctor_ids) | set(visited_doctor_ids)
                    if exclude_ids:
                        queryset = queryset.exclude(id__in=exclude_ids)
                
                print(f"DEBUG: Found {queryset.count()} active doctors")
            
        return queryset
    
    def list(self, request, *args, **kwargs):
        """Override list to deduplicate by name for search results."""
        queryset = self.filter_queryset(self.get_queryset())
        
        # If searching, deduplicate by name (keep most recent)
        if request.query_params.get('search'):
            seen_names = set()
            unique_doctors = []
            for doctor in queryset:
                if doctor.name.lower() not in seen_names:
                    seen_names.add(doctor.name.lower())
                    unique_doctors.append(doctor)
            serializer = self.get_serializer(unique_doctors, many=True)
            return Response(serializer.data)
        
        return super().list(request, *args, **kwargs)

    def _mark_assignment_visited(self, doctor):
        """Helper to mark doctor visited in active assignment"""
        from django.utils import timezone
        
        # Find the active assignment
        if doctor.address_details and doctor.address_details.area:
            current_assignments = AgentAssignment.objects.filter(
                agent=self.request.user,
                area=doctor.address_details.area
            ).order_by('-assigned_at')
            
            if current_assignments.exists():
                current_assignment = current_assignments.first()
                status_obj, created = AgentAssignmentDoctorStatus.objects.get_or_create(
                    assignment=current_assignment,
                    doctor=doctor,
                    defaults={'is_active': True}
                )
                
                # A doctor is only "Visited" if they have all mandatory fields completed (not a partial draft)
                # Matches frontend _isIncomplete logic: contact, specialization, degree, area, pin, image
                is_complete = bool(
                    doctor.contact_number and str(doctor.contact_number).strip() and
                    doctor.specialization and str(doctor.specialization).strip() and
                    doctor.degree_qualification and str(doctor.degree_qualification).strip() and
                    doctor.address_details and
                    doctor.address_details.area and
                    doctor.address_details.pincode and str(doctor.address_details.pincode).strip() and
                    doctor.visit_image
                )
                
                # Only mark visited if status is actually Referred AND entry is complete
                if doctor.status == 'Referred':
                    if is_complete:
                        status_obj.is_visited = True
                        status_obj.visit_trip = doctor.trip
                        status_obj.visited_at = timezone.now()
                    else:
                        status_obj.is_visited = False
                        status_obj.visit_trip = None
                        status_obj.visited_at = None
                    status_obj.save()

    def perform_create(self, serializer):
        # Agent is set automatically; Trip should be passed in request body
        doctor = serializer.save(agent=self.request.user)
        self._mark_assignment_visited(doctor)

    def perform_update(self, serializer):
        doctor = serializer.save()
        self._mark_assignment_visited(doctor)

    @action(detail=False, methods=['get'])
    def master(self, request):
        """Get all unique doctors from the master table for dropdown selection.
        Returns deduplicated list by name, keeping the most recent entry."""
        queryset = DoctorReferral.objects.all().order_by('-created_at')
        
        # Deduplicate by name - keep only the most recent entry per unique doctor name
        seen_names = set()
        unique_doctors = []
        for doctor in queryset:
            name_key = doctor.name.lower().strip()
            if name_key not in seen_names:
                seen_names.add(name_key)
                unique_doctors.append(doctor)
        
        serializer = self.get_serializer(unique_doctors, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def mark_visited(self, request, pk=None):
        """Mark a doctor as visited by associating them with a trip"""
        doctor = self.get_object()
        trip_id = request.data.get('trip_id')
        
        if not trip_id:
            return Response({'error': 'trip_id is required'}, status=400)
        
        # Verify the trip belongs to this agent
        try:
            trip = Trip.objects.get(id=trip_id, agent=request.user)
        except Trip.DoesNotExist:
            return Response({'error': 'Trip not found or not owned by you'}, status=404)
        
        # Associate doctor with trip (backward compat)
        doctor.trip = trip
        doctor.save()
        
        # Also update per-assignment visit tracking
        # Find the current assignment for this agent's area
        from django.utils import timezone
        if doctor.address_details and doctor.address_details.area:
            current_assignments = AgentAssignment.objects.filter(
                agent=request.user,
                area=doctor.address_details.area
            ).order_by('-assigned_at')
            
            if current_assignments.exists():
                current_assignment = current_assignments.first()
                status_obj, created = AgentAssignmentDoctorStatus.objects.get_or_create(
                    assignment=current_assignment,
                    doctor=doctor,
                    defaults={'is_active': True}
                )
                status_obj.is_visited = True
                status_obj.visit_trip = trip
                status_obj.visited_at = timezone.now()
                status_obj.save()
        
        serializer = self.get_serializer(doctor)
        return Response(serializer.data)

class OvernightStayViewSet(viewsets.ModelViewSet):
    queryset = OvernightStay.objects.all()
    serializer_class = OvernightStaySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return OvernightStay.objects.filter(trip__agent=self.request.user)

class PatientReferralViewSet(viewsets.ModelViewSet):
    queryset = PatientReferral.objects.all()
    serializer_class = PatientReferralSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PatientReferral.objects.filter(agent=self.request.user)

    def perform_create(self, serializer):
        serializer.save(agent=self.request.user)
