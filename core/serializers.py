from rest_framework import serializers
from .models import User, Task, DoctorReferral, PatientReferral, Trip, OvernightStay, Specialization, Qualification, Area, Address

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'role']

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

class TripSerializer(serializers.ModelSerializer):
    doctor_referrals = DoctorReferralSerializer(many=True, read_only=True)
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
