from rest_framework import serializers

from .models import Membership, Organization, PilotApplication, User


class UserSummarySerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "display_name"]


class MembershipSerializer(serializers.ModelSerializer):
    user = UserSummarySerializer(read_only=True)

    class Meta:
        model = Membership
        fields = ["id", "user", "role", "active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["id", "name", "slug", "status", "created_at", "updated_at"]
        read_only_fields = ["id", "slug", "created_at", "updated_at"]


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class CreateOrganizationSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    slug = serializers.SlugField(max_length=220, required=False, allow_blank=True)


class AddMembershipSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(
        choices=Membership.Role.choices, default=Membership.Role.VIEWER
    )


class UpdateMembershipSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=Membership.Role.choices, required=False)
    active = serializers.BooleanField(required=False)


class PilotApplicationSerializer(serializers.ModelSerializer):
    company_website = serializers.CharField(
        required=False, allow_blank=True, max_length=500, write_only=True
    )

    class Meta:
        model = PilotApplication
        fields = [
            "contact_name",
            "email",
            "organization_name",
            "website",
            "country_or_region",
            "team_size",
            "primary_need",
            "plan_interest",
            "notes",
            "consent_to_contact",
            "source",
            "utm_source",
            "utm_medium",
            "utm_campaign",
            "referrer",
            "company_website",
        ]
        extra_kwargs = {
            "contact_name": {"trim_whitespace": True},
            "email": {"validators": []},
            "organization_name": {"trim_whitespace": True},
            "website": {"required": False, "allow_blank": True},
            "country_or_region": {"required": False, "allow_blank": True},
            "notes": {"required": False, "allow_blank": True, "max_length": 2000},
            "consent_to_contact": {"required": True},
            "source": {"required": False},
            "utm_source": {"required": False, "allow_blank": True},
            "utm_medium": {"required": False, "allow_blank": True},
            "utm_campaign": {"required": False, "allow_blank": True},
            "referrer": {"required": False, "allow_blank": True},
        }

    def validate_email(self, value):
        return value.strip().lower()

    def validate_consent_to_contact(self, value):
        if value is not True:
            raise serializers.ValidationError(
                "Please agree so we can contact you about the pilot."
            )
        return value


class PilotVerificationSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=2048, trim_whitespace=True)
