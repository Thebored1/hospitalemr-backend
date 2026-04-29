from rest_framework import viewsets, status, mixins
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.exceptions import ValidationError
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from .models import Task, DoctorReferral, DoctorVisit, PatientReferral, Trip, OvernightStay, Specialization, Qualification, Area, Address, User, AgentAssignment, AgentAssignmentDoctorStatus, ClientLog
from .serializers import TaskSerializer, DoctorReferralSerializer, TripDoctorVisitSerializer, PatientReferralSerializer, TripSerializer, OvernightStaySerializer, SpecializationSerializer, QualificationSerializer, AreaSerializer, AddressSerializer, ClientLogSerializer
from .permissions import DynamicAPIPermission

class SpecializationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing doctor specializations"""
    queryset = Specialization.objects.all()
    serializer_class = SpecializationSerializer
    permission_classes = [IsAuthenticated, DynamicAPIPermission]


class QualificationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing doctor qualifications"""
    queryset = Qualification.objects.all()
    serializer_class = QualificationSerializer
    permission_classes = [IsAuthenticated, DynamicAPIPermission]

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
    permission_classes = [IsAuthenticated, DynamicAPIPermission]

    def perform_create(self, serializer):
        # Automatically set raised_by to the current user
        serializer.save(raised_by=self.request.user)

class TripViewSet(viewsets.ModelViewSet):
    queryset = Trip.objects.all()
    serializer_class = TripSerializer
    permission_classes = [IsAuthenticated, DynamicAPIPermission]

    def get_queryset(self):
        # Filter trips by the current agent
        return Trip.objects.filter(agent=self.request.user).prefetch_related(
            'doctor_visits__doctor__address_details__area',
            'doctor_referrals__address_details__area',
            'overnight_stays',
        )

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
        # After trip completion, update assignment statuses for completed visits
        try:
            from core.models import AgentAssignmentDoctorStatus, AgentAssignment
            visits = trip.doctor_visits.select_related(
                'doctor',
                'doctor__address_details',
                'doctor__address_details__area',
            )
            for visit in visits:
                doctor = visit.doctor
                if not doctor or doctor.is_internal:
                    continue
                area = getattr(getattr(doctor, 'address_details', None), 'area', None)
                if area is None:
                    continue
                is_complete = bool(
                    doctor.contact_number and str(doctor.contact_number).strip() and
                    doctor.specialization and str(doctor.specialization).strip() and
                    doctor.degree_qualification and str(doctor.degree_qualification).strip() and
                    doctor.address_details and
                    doctor.address_details.area and
                    doctor.address_details.pincode and str(doctor.address_details.pincode).strip() and
                    visit.visit_image
                )
                if visit.status != 'Referred' or not is_complete:
                    continue

                current_assignment = AgentAssignment.objects.filter(
                    agent=trip.agent,
                    area=area
                ).order_by('-assigned_at').first()
                if current_assignment is None:
                    continue

                AgentAssignmentDoctorStatus.objects.get_or_create(
                    assignment=current_assignment,
                    doctor=doctor,
                    defaults={'is_active': True}
                )
                AgentAssignmentDoctorStatus.objects.filter(
                    assignment=current_assignment,
                    doctor__name__iexact=doctor.name
                ).update(
                    is_visited=True,
                    visit_trip=trip,
                    visited_at=timezone.now()
                )
        except Exception as e:
            print(f"Trip completion assignment update error: {e}")
        serializer = self.get_serializer(trip)
        return Response(serializer.data)

class AreaViewSet(viewsets.ModelViewSet):
    serializer_class = AreaSerializer
    permission_classes = [IsAuthenticated, DynamicAPIPermission]


class ClientLogViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = ClientLog.objects.all()
    serializer_class = ClientLogSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        return [IsAdminUser(), DynamicAPIPermission()]

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        ip_address = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if ip_address:
            ip_address = ip_address.split(',')[0].strip()
        else:
            ip_address = self.request.META.get('REMOTE_ADDR')
        serializer.save(user=user, ip_address=ip_address)

    def get_queryset(self):
        if self.request.user.is_staff:
            return Area.objects.all()
        # Backward-compatible assignment resolution:
        # 1) AgentAssignment history (new source of truth)
        # 2) Area.agent pointer (legacy/admin edits)
        assignment_area_ids = set(
            AgentAssignment.objects.filter(agent=self.request.user).values_list(
                'area_id', flat=True
            )
        )
        legacy_area_ids = set(
            Area.objects.filter(agent=self.request.user).values_list('id', flat=True)
        )
        assigned_area_ids = assignment_area_ids | legacy_area_ids
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
    permission_classes = [IsAuthenticated, DynamicAPIPermission]

    def get_queryset(self):
        from django.db.models import Q
        from django.db.models.functions import Lower
        # Exclude internal doctors from the visit assigned list for all users
        queryset = DoctorReferral.objects.filter(is_internal=False).order_by('-created_at')
        
        # Support search for autocomplete
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(name__icontains=search).order_by('-created_at')
        else:
            if getattr(self.request.user, 'role', None) == 'advisor':
                # Only show doctors in areas CURRENTLY assigned to this agent
                # Use AgentAssignment and legacy Area.agent pointer for compatibility.
                assignment_area_ids = set(
                    AgentAssignment.objects.filter(
                        agent=self.request.user
                    ).values_list('area_id', flat=True).distinct()
                )
                legacy_area_ids = set(
                    Area.objects.filter(agent=self.request.user).values_list(
                        'id', flat=True
                    )
                )
                assigned_area_ids = assignment_area_ids | legacy_area_ids
                
                # Also fetch area names for debug/legacy
                assigned_area_names = Area.objects.filter(id__in=assigned_area_ids).values_list('name', flat=True)
                
                print(f"DEBUG: User={self.request.user}, Assigned Area IDs={list(assigned_area_ids)}")

                # Filter by doctors in assigned areas via Address link and exclude internal doctors
                # Note: 'area' field on DoctorReferral was removed, relying on address_details__area
                queryset = queryset.filter(
                    Q(address_details__area_id__in=assigned_area_ids),
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

                    # Name-level exclusion is required because assignment statuses are
                    # stored per DoctorReferral row. A new "Referred" row for the same
                    # doctor name should hide older "Assigned" rows in the same assignment.
                    excluded_name_keys = list(
                        AgentAssignmentDoctorStatus.objects.filter(
                            assignment_id__in=latest_assignment_ids
                        )
                        .filter(Q(is_active=False) | Q(is_visited=True))
                        .annotate(name_key=Lower('doctor__name'))
                        .values_list('name_key', flat=True)
                        .distinct()
                    )
                    if excluded_name_keys:
                        queryset = queryset.annotate(name_key=Lower('name')).exclude(
                            name_key__in=excluded_name_keys
                        )
                
                print(f"DEBUG: Found {queryset.count()} active doctors")
            
        return queryset
    
    def list(self, request, *args, **kwargs):
        """Override list to deduplicate by doctor identity for advisor/search use."""
        queryset = self.filter_queryset(self.get_queryset())

        should_dedupe = bool(request.query_params.get('search')) or getattr(
            request.user, 'role', None
        ) == 'advisor'
        if should_dedupe:
            seen_keys = set()
            unique_doctors = []
            for doctor in queryset:
                area_id = getattr(getattr(doctor, 'address_details', None), 'area_id', '')
                key = f"{doctor.name.lower().strip()}::{area_id}"
                if key not in seen_keys:
                    seen_keys.add(key)
                    unique_doctors.append(doctor)
            serializer = self.get_serializer(unique_doctors, many=True)
            return Response(serializer.data)

        return super().list(request, *args, **kwargs)

    def _mark_assignment_visited(self, doctor, visit=None):
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
                AgentAssignmentDoctorStatus.objects.get_or_create(
                    assignment=current_assignment,
                    doctor=doctor,
                    defaults={'is_active': True}
                )
                
                # A doctor is only "Visited" if they have all mandatory fields completed (not a partial draft)
                # Matches frontend _isIncomplete logic: contact, specialization, degree, area, pin, image
                visit_image = visit.visit_image if visit is not None else doctor.visit_image
                visit_status = visit.status if visit is not None else doctor.status
                visit_trip = visit.trip if visit is not None else doctor.trip
                is_complete = bool(
                    doctor.contact_number and str(doctor.contact_number).strip() and
                    doctor.specialization and str(doctor.specialization).strip() and
                    doctor.degree_qualification and str(doctor.degree_qualification).strip() and
                    doctor.address_details and
                    doctor.address_details.area and
                    doctor.address_details.pincode and str(doctor.address_details.pincode).strip() and
                    visit_image
                )
                
                # Only mark visited if status is actually Referred AND entry is complete
                if visit_status == 'Referred':
                    # Keep assignment state at doctor-name level. A visit for a doctor
                    # should hide all rows with the same name for this assignment.
                    same_name_statuses = AgentAssignmentDoctorStatus.objects.filter(
                        assignment=current_assignment,
                        doctor__name__iexact=doctor.name
                    )
                    if is_complete:
                        same_name_statuses.update(
                            is_visited=True,
                            visit_trip=visit_trip,
                            visited_at=timezone.now()
                        )
                    else:
                        same_name_statuses.update(
                            is_visited=False,
                            visit_trip=None,
                            visited_at=None
                        )

    def _get_trip_from_request(self, request, required=True):
        trip_id = request.data.get('trip') or request.data.get('trip_id')
        if not trip_id:
            if required:
                return None, Response({'error': 'trip is required'}, status=400)
            return None, None

        try:
            trip_id = int(str(trip_id))
        except (TypeError, ValueError):
            return None, Response({'error': 'Invalid trip id'}, status=400)

        trip_filters = {'id': trip_id}
        if getattr(request.user, 'role', None) == 'advisor':
            trip_filters['agent'] = request.user

        try:
            trip = Trip.objects.get(**trip_filters)
        except Trip.DoesNotExist:
            return None, Response({'error': 'Trip not found or not owned by you'}, status=404)
        return trip, None

    def _get_master_payload(self, request):
        visit_only_fields = {
            'trip',
            'trip_id',
            'doctor_id',
            'remarks',
            'additional_details',
            'status',
            'visit_lat',
            'visit_long',
            'visit_image',
            'id',
        }
        # Avoid QueryDict.copy() which deep-copies file handles and can error.
        data = {}
        for key in request.data:
            if key in visit_only_fields:
                continue
            data[key] = request.data.get(key)
        return data

    def _resolve_or_create_doctor(self, request):
        doctor = None
        doctor_id = request.data.get('doctor_id') or request.data.get('id')
        if doctor_id:
            try:
                doctor = DoctorReferral.objects.filter(id=int(str(doctor_id))).first()
            except (TypeError, ValueError):
                doctor = None

        if doctor is None:
            name = (request.data.get('name') or '').strip()
            if name:
                fallback_qs = DoctorReferral.objects.filter(name__iexact=name)
                area_name = (request.data.get('area') or '').strip()
                if area_name:
                    fallback_qs = fallback_qs.filter(
                        address_details__area__name__iexact=area_name
                    )
                doctor = fallback_qs.order_by('-created_at').first()

        master_payload = self._get_master_payload(request)

        if doctor is not None:
            if master_payload:
                serializer = self.get_serializer(
                    doctor,
                    data=master_payload,
                    partial=True,
                )
                serializer.is_valid(raise_exception=True)
                doctor = serializer.save()
            return doctor

        serializer = self.get_serializer(data=master_payload)
        serializer.is_valid(raise_exception=True)
        if getattr(request.user, 'role', None) == 'advisor':
            return serializer.save(agent=request.user)
        return serializer.save()

    def _upsert_doctor_visit(self, doctor, trip, request):
        is_draft = None
        if 'is_draft' in request.data:
            is_draft = self._coerce_bool(request.data.get('is_draft'))
        visit_defaults = {
            'status': request.data.get('status') or 'Referred',
        }
        for field in ['remarks', 'additional_details', 'visit_lat', 'visit_long']:
            if field in request.data:
                visit_defaults[field] = request.data.get(field)
        if is_draft is not None:
            visit_defaults['is_draft'] = is_draft

        visit, created = DoctorVisit.objects.get_or_create(
            doctor=doctor,
            trip=trip,
            defaults=visit_defaults,
        )

        changed = False
        if not created:
            for field in ['status', 'remarks', 'additional_details', 'visit_lat', 'visit_long']:
                if field in request.data:
                    value = request.data.get(field)
                    if getattr(visit, field) != value:
                        setattr(visit, field, value)
                        changed = True
            if is_draft is not None:
                if visit.is_draft != is_draft:
                    visit.is_draft = is_draft
                    changed = True

        if 'visit_image' in request.FILES:
            visit.visit_image = request.FILES['visit_image']
            changed = True

        if is_draft is not True:
            has_image = bool(visit.visit_image) or 'visit_image' in request.FILES
            if not has_image:
                raise ValidationError({'visit_image': 'This field is required for completed visits.'})

        if changed:
            visit.save()

        # Keep doctor-level visit fields synced to the latest trip visit for backward compatibility.
        doctor_update_fields = []
        if doctor.trip_id != trip.id:
            doctor.trip = trip
            doctor_update_fields.append('trip')
        if doctor.remarks != visit.remarks:
            doctor.remarks = visit.remarks
            doctor_update_fields.append('remarks')
        if doctor.additional_details != visit.additional_details:
            doctor.additional_details = visit.additional_details
            doctor_update_fields.append('additional_details')
        if doctor.status != visit.status:
            doctor.status = visit.status
            doctor_update_fields.append('status')
        if doctor.visit_lat != visit.visit_lat:
            doctor.visit_lat = visit.visit_lat
            doctor_update_fields.append('visit_lat')
        if doctor.visit_long != visit.visit_long:
            doctor.visit_long = visit.visit_long
            doctor_update_fields.append('visit_long')
        if visit.visit_image and doctor.visit_image != visit.visit_image:
            doctor.visit_image = visit.visit_image
            doctor_update_fields.append('visit_image')
        if doctor_update_fields:
            doctor.save(update_fields=doctor_update_fields)

        return visit, created

    def create(self, request, *args, **kwargs):
        # Advisor app flow: keep one doctor row and store per-trip visits separately.
        if getattr(request.user, 'role', None) == 'advisor':
            trip, err = self._get_trip_from_request(request, required=True)
            if err is not None:
                return err
            doctor = self._resolve_or_create_doctor(request)
            visit, created = self._upsert_doctor_visit(doctor, trip, request)
            self._mark_assignment_visited(doctor, visit=visit)
            code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
            return Response(TripDoctorVisitSerializer(visit).data, status=code)

        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        doctor = self.get_object()
        trip, err = self._get_trip_from_request(request, required=False)
        if err is not None:
            return err

        if trip is not None:
            master_payload = self._get_master_payload(request)
            if master_payload:
                serializer = self.get_serializer(
                    doctor,
                    data=master_payload,
                    partial=True,
                )
                serializer.is_valid(raise_exception=True)
                doctor = serializer.save()
            visit, _ = self._upsert_doctor_visit(doctor, trip, request)
            self._mark_assignment_visited(doctor, visit=visit)
            return Response(TripDoctorVisitSerializer(visit).data)

        serializer = self.get_serializer(doctor, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        doctor = serializer.save()
        self._mark_assignment_visited(doctor)
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        doctor = self.get_object()
        trip, err = self._get_trip_from_request(request, required=False)
        if err is not None:
            return err

        if trip is not None:
            master_payload = self._get_master_payload(request)
            if master_payload:
                serializer = self.get_serializer(
                    doctor,
                    data=master_payload,
                    partial=True,
                )
                serializer.is_valid(raise_exception=True)
                doctor = serializer.save()
            visit, _ = self._upsert_doctor_visit(doctor, trip, request)
            self._mark_assignment_visited(doctor, visit=visit)
            return Response(TripDoctorVisitSerializer(visit).data)

        serializer = self.get_serializer(doctor, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        doctor = serializer.save()
        self._mark_assignment_visited(doctor)
        return Response(serializer.data)

    def perform_create(self, serializer):
        if getattr(self.request.user, 'role', None) == 'advisor':
            doctor = serializer.save(agent=self.request.user)
        else:
            doctor = serializer.save()
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
        trip, err = self._get_trip_from_request(request, required=True)
        if err is not None:
            return err

        visit, _ = DoctorVisit.objects.get_or_create(
            doctor=doctor,
            trip=trip,
            defaults={
                'status': 'Referred',
            },
        )
        if doctor.trip_id != trip.id:
            doctor.trip = trip
            doctor.save(update_fields=['trip'])

        self._mark_assignment_visited(doctor, visit=visit)
        return Response(TripDoctorVisitSerializer(visit).data)

class OvernightStayViewSet(viewsets.ModelViewSet):
    queryset = OvernightStay.objects.all()
    serializer_class = OvernightStaySerializer
    permission_classes = [IsAuthenticated, DynamicAPIPermission]

    def get_queryset(self):
        return OvernightStay.objects.filter(trip__agent=self.request.user)

class PatientReferralViewSet(viewsets.ModelViewSet):
    queryset = PatientReferral.objects.all()
    serializer_class = PatientReferralSerializer
    permission_classes = [IsAuthenticated, DynamicAPIPermission]

    def get_queryset(self):
        return PatientReferral.objects.filter(agent=self.request.user)

    def perform_create(self, serializer):
        serializer.save(agent=self.request.user)
