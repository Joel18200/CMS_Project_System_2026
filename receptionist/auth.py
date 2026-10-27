from rest_framework.permissions import BasePermission


class IsReceptionist(BasePermission):
    message = "Only authorized Receptionists can access this endpoint."

    def has_permission(self, request, view):
        user = request.user

        return (
            user
            and user.is_authenticated
            and user.groups.filter(name="Receptionist").exists()
        )