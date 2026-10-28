from rest_framework.permissions import BasePermission

class IsReceptionist(BasePermission):
    # Show this message when the user is not authorized.
    message = "Only authorized Receptionists can access this endpoint."

    def has_permission(self, request, view):
        # JWT authentication identifies the user for this request.
        user = request.user

        # Reject anonymous users who have not logged in.
        if not user or not user.is_authenticated:
            return False

        # Allow only users who have a linked ReceptionistProfile.
        return hasattr(user, "receptionist_profile")
