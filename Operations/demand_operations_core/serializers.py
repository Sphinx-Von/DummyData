from rest_framework import serializers
from .models import OperationalVisit, OperationalVisitStatusLog, OperationalTeam

class OperationalTeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = OperationalTeam
        fields = '__all__'

class OperationalVisitSerializer(serializers.ModelSerializer):
    # Optional: Display readable names instead of IDs
    # activity_name = serializers.CharField(source='activity.id', read_only=True)
    # assigned_to_name = serializers.CharField(source='assigned_to.team_member_name', read_only=True) # Assuming team member has a name field

    class Meta:
        model = OperationalVisit
        fields = '__all__'

from rest_framework import serializers
from django.core.files.storage import default_storage
from .models import OperationalVisitMedia, OperationalVisit

class OperationalVisitMediaSerializer(serializers.ModelSerializer):
    # This field handles the file upload input, but isn't stored directly in the DB
    image = serializers.FileField(write_only=True, required=True)

    class Meta:
        model = OperationalVisitMedia
        fields = ['id', 'visit', 'file', 'media_type', 'caption', 'created_at', 'image']
        read_only_fields = ['file', 'created_at']

    def create(self, validated_data):
        # Extract the file object
        image_file = validated_data.pop('image')

        # Save the file manually since the model field is a TextField
        # This saves to your MEDIA_ROOT/operational_media/filename
        file_path = default_storage.save(f"operational_media/{image_file.name}", image_file)

        # Add the path string to the validated data for the 'file' TextField
        validated_data['file'] = file_path

        return super().create(validated_data)   
    







from rest_framework import serializers
from .models import FollowUP


class ActivityItemSerializer(serializers.Serializer):
    plot_id = serializers.CharField()
    activity = serializers.CharField()
    type = serializers.ChoiceField(choices=[
        "CALLBACK",
        "FIELD_VISIT",
        "SEND_INFO",
        "PARKED",
        "CALL",          
    ])
    scheduled_date = serializers.DateTimeField()


from rest_framework import serializers
from .models import FollowUP

class FollowupBulkCreateSerializer(serializers.Serializer):
    farmer_id = serializers.CharField()
    priority = serializers.ChoiceField(choices=["LOW", "MEDIUM", "HIGH"])
    notes = serializers.CharField(allow_blank=True, required=False)
    activities = ActivityItemSerializer(many=True)

    def create(self, validated_data):
        request = self.context.get("request")
        user = request.user  # authenticated user from the token/session

        farmer_id = validated_data["farmer_id"]
        priority = validated_data["priority"]
        notes = validated_data.get("notes", "")
        activities = validated_data["activities"]

        created = []

        for item in activities:
            followup_type = item["type"]

            # Map incoming type to your model choices
            if followup_type == "CALL":
                followup_type = FollowUP.FollowUpType.CALL_BACK

            fu = FollowUP.objects.create(
                followup_type=followup_type,
                farmer_id=str(farmer_id),
                plot_id=str(item["plot_id"]),
                activity=item["activity"],
                scheduled_date=item["scheduled_date"],
                notes=notes,
                status=FollowUP.Status.PENDING,
                priority=priority,
                created_by=user,  # or owner=user / user=user based on your model
            )
            created.append(fu)

        return created

class FollowUPSerializer(serializers.ModelSerializer):
    class Meta:
        model = FollowUP
        fields = "__all__"
