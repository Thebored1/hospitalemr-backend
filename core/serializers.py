from rest_framework import serializers
from .models import User, Task, DoctorReferral, DoctorVisit, PatientReferral, Trip, OvernightStay, Specialization, Qualification, Area, Address, ClientLog

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'role']


class ClientLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientLog
        fields = [
            'id',
            'user',
            'level',
            'message',
            'logger',
            'context',
            'device_id',
            'app_version',
            'platform',
            'build_mode',
            'client_time',
            'ip_address',
            'created_at',
        ]
        read_only_fields = ['user', 'ip_address', 'created_at']

class SpecializationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Specialization
        fields = ['id', 'name']


class QualificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Qualification
        fields = ['id', 'name']

class TaskSerializer(serializers.ModelSerializer):
    raised_by_details = UserSerializer(source='raised_by', read_only=True)

    class Meta:
        model = Task
        fields = '__all__'
        read_only_fields = ['raised_by', 'raised_on']

class OvernightStaySerializer(serializers.ModelSerializer):
    class Meta:
        model = OvernightStay
        fields = '__all__'
        read_only_fields = ['created_at']

class AreaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Area
        fields = '__all__'

class AddressSerializer(serializers.ModelSerializer):
    area_details = AreaSerializer(source='area', read_only=True)
    area = serializers.PrimaryKeyRelatedField(
        queryset=Area.objects.all(), write_only=True, required=False
    )
    class Meta:
        model = Address
        fields = '__all__'

class DoctorReferralSerializer(serializers.ModelSerializer):
    agent_details = UserSerializer(source='agent', read_only=True)
    address_details = AddressSerializer(required=False, allow_null=True)
    
    class Meta:
        model = DoctorReferral
        fields = '__all__'
        read_only_fields = ['agent', 'created_at']
    
    def to_internal_value(self, data):
        # Handle backward compatibility for mobile app sending flat address fields
        # Convert flat fields (area, street, city, pin) to nested address_details structure
        
        # Check if any legacy address fields are present
        legacy_fields = ['area', 'street', 'city', 'pin']
        if any(field in data for field in legacy_fields):
            # Create a mutable copy if it's a QueryDict
            if hasattr(data, 'dict'):
                data = data.dict()
            else:
                data = dict(data) # Ensure mutation works for standard dicts
            
            # Extract fields
            area_name = data.pop('area', None)
            street = data.pop('street', None)
            city = data.pop('city', None)
            pincode = data.pop('pin', None)
            
            # Look up or create Area by name and city
            area_obj = None
            if area_name:
                from core.models import Area
                # If city is not provided, try to find area by name alone
                if city:
                    area_obj, _ = Area.objects.get_or_create(name=area_name, defaults={'city': city})
                else:
                    area_obj = Area.objects.filter(name=area_name).first()
                    if not area_obj:
                        area_obj = Area.objects.create(name=area_name, city=city or '')
            
            # Build address_details structure if we have address data
            if area_name == "":
                # Explicitly nullify address if area was cleared
                data['address_details'] = None
            elif area_obj or street is not None or pincode is not None:
                address_details = {}
                if street is not None:
                    address_details['street'] = street
                if pincode is not None:
                    address_details['pincode'] = pincode
                if area_obj:
                    # In DRF nested serializers, the key is the field name
                    address_details['area'] = area_obj.id
                
                # Only set if we have actual data to save
                if address_details:
                    data['address_details'] = address_details
        
        return super().to_internal_value(data)

    def create(self, validated_data):
        address_data = validated_data.pop('address_details', None)
        doctor = DoctorReferral.objects.create(**validated_data)
        if address_data is not None:
            address = Address.objects.create(**address_data)
            doctor.address_details = address
            doctor.save()
        return doctor

    def update(self, instance, validated_data):
        has_address = 'address_details' in validated_data
        address_data = validated_data.pop('address_details', None)
        
        # Update doctor fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update address
        if has_address:
            if address_data is None:
                instance.address_details = None
                instance.save()
            else:
                if instance.address_details:
                    for attr, value in address_data.items():
                        setattr(instance.address_details, attr, value)
                    instance.address_details.save()
                else:
                    # Require area to create new Address
                    if 'area' in address_data and address_data['area'] is not None:
                        address = Address.objects.create(**address_data)
                        instance.address_details = address
                        instance.save()
        
        return instance


class TripDoctorVisitSerializer(serializers.ModelSerializer):
    """Backwards-compatible trip timeline entry payload for mobile app."""

    id = serializers.IntegerField(source='doctor.id', read_only=True)
    trip = serializers.IntegerField(source='trip.id', read_only=True)
    name = serializers.CharField(source='doctor.name', read_only=True)
    contact_number = serializers.CharField(source='doctor.contact_number', read_only=True)
    specialization = serializers.CharField(source='doctor.specialization', read_only=True)
    degree_qualification = serializers.CharField(source='doctor.degree_qualification', read_only=True)
    email = serializers.EmailField(source='doctor.email', read_only=True, allow_null=True)
    additional_expenses = serializers.CharField(source='doctor.additional_expenses', read_only=True, allow_null=True)
    address_details = AddressSerializer(source='doctor.address_details', read_only=True)
    is_internal = serializers.BooleanField(source='doctor.is_internal', read_only=True)

    class Meta:
        model = DoctorVisit
        fields = [
            'id',
            'trip',
            'name',
            'contact_number',
            'specialization',
            'degree_qualification',
            'email',
            'remarks',
            'additional_details',
            'additional_expenses',
            'status',
            'visit_image',
            'visit_lat',
            'visit_long',
            'created_at',
            'address_details',
            'is_internal',
        ]

class TripSerializer(serializers.ModelSerializer):
    doctor_referrals = serializers.SerializerMethodField()
    overnight_stays = OvernightStaySerializer(many=True, read_only=True)
    agent_details = UserSerializer(source='agent', read_only=True)
    trip_number = serializers.SerializerMethodField()

    class Meta:
        model = Trip
        fields = '__all__'
        read_only_fields = ['agent', 'start_time', 'end_time']

    def get_trip_number(self, obj):
        # Calculate trip number for this agent (rank ordered by ID)
        return Trip.objects.filter(agent=obj.agent, id__lte=obj.id).count()

    def get_doctor_referrals(self, obj):
        visits = obj.doctor_visits.select_related(
            'doctor',
            'doctor__address_details',
            'doctor__address_details__area',
        ).order_by('-created_at')
        if visits.exists():
            return TripDoctorVisitSerializer(visits, many=True).data
        # Backward compatibility for older rows before DoctorVisit migration.
        return DoctorReferralSerializer(obj.doctor_referrals.all(), many=True).data

class PatientReferralSerializer(serializers.ModelSerializer):
    agent_details = UserSerializer(source='agent', read_only=True)
    referred_by_doctor_details = DoctorReferralSerializer(source='referred_by_doctor', read_only=True)
    referred_to_doctor_details = DoctorReferralSerializer(source='referred_to_doctor', read_only=True)
    status = serializers.CharField(required=False)

    class Meta:
        model = PatientReferral
        fields = '__all__'
        read_only_fields = ['agent', 'reported_on']

    def validate_status(self, value):
        # Normalize status from mobile app (case/blank)
        if value is None or value == '':
            return 'Pending'
        normalized = value.strip()
        mapping = {
            'pending': 'Pending',
            'in progress': 'Pending',
            'admitted': 'Admitted',
            'dismissed': 'Dismissed',
        }
        key = normalized.lower()
        if key in mapping:
            return mapping[key]
        return value
