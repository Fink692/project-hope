from rest_framework import serializers

from .models import (
    Membership,
    Organization,
    OrganizationInvitation,
    PilotApplication,
    User,
)


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

    def validate_email(self, value):
        return value.strip().lower()


class MfaChallengeSerializer(serializers.Serializer):
    challenge = serializers.CharField(max_length=2048, trim_whitespace=True)
    code = serializers.CharField(max_length=32, trim_whitespace=True)


class MfaEnrollmentBeginSerializer(serializers.Serializer):
    current_password = serializers.CharField(
        max_length=256, trim_whitespace=False, write_only=True
    )


class MfaEnrollmentConfirmSerializer(serializers.Serializer):
    enrollment_token = serializers.CharField(max_length=4096, trim_whitespace=True)
    code = serializers.RegexField(r"^[0-9]{6}$", trim_whitespace=True)


class MfaStepUpSerializer(serializers.Serializer):
    current_password = serializers.CharField(
        max_length=256, trim_whitespace=False, write_only=True
    )
    code = serializers.CharField(max_length=32, trim_whitespace=True)


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.strip().lower()


class PasswordResetTokenSerializer(serializers.Serializer):
    uid = serializers.CharField(max_length=256, trim_whitespace=True)
    token = serializers.CharField(max_length=256, trim_whitespace=True)


class PasswordResetConfirmSerializer(PasswordResetTokenSerializer):
    password = serializers.CharField(
        max_length=256, trim_whitespace=False, write_only=True
    )
    password_confirm = serializers.CharField(
        max_length=256, trim_whitespace=False, write_only=True
    )

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "The passwords do not match."}
            )
        return attrs


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


class OrganizationInvitationSerializer(serializers.ModelSerializer):
    invited_by = UserSummarySerializer(read_only=True)
    effective_status = serializers.SerializerMethodField()
    delivery_status = serializers.SerializerMethodField()

    class Meta:
        model = OrganizationInvitation
        fields = [
            "id",
            "email",
            "role",
            "status",
            "effective_status",
            "delivery_status",
            "invited_by",
            "expires_at",
            "email_sent_at",
            "email_attempts",
            "accepted_at",
            "revoked_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_effective_status(self, invitation):
        from django.utils import timezone

        if (
            invitation.status == OrganizationInvitation.Status.PENDING
            and invitation.expires_at <= timezone.now()
        ):
            return "expired"
        return invitation.status

    def get_delivery_status(self, invitation):
        if invitation.email_sent_at is not None:
            return "sent"
        if invitation.email_attempts:
            return "retrying"
        return "pending"


class CreateOrganizationInvitationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(
        choices=Membership.Role.choices, default=Membership.Role.STAFF
    )

    def validate_email(self, value):
        return value.strip().lower()


class InvitationTokenSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=2048, trim_whitespace=True)


class AcceptOrganizationInvitationSerializer(InvitationTokenSerializer):
    first_name = serializers.CharField(
        max_length=150, required=False, allow_blank=True, trim_whitespace=True
    )
    last_name = serializers.CharField(
        max_length=150, required=False, allow_blank=True, trim_whitespace=True
    )
    password = serializers.CharField(
        max_length=256,
        required=False,
        allow_blank=True,
        trim_whitespace=False,
        write_only=True,
    )
    password_confirm = serializers.CharField(
        max_length=256,
        required=False,
        allow_blank=True,
        trim_whitespace=False,
        write_only=True,
    )

    def validate(self, attrs):
        password = attrs.get("password", "")
        confirmation = attrs.get("password_confirm", "")
        if password != confirmation:
            raise serializers.ValidationError(
                {"password_confirm": "The passwords do not match."}
            )
        return attrs


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
