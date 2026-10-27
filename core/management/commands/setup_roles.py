
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create the standard CMS role groups"

    GROUP_NAMES = [
        "Administrator",
        "Doctor",
        "Receptionist",
        "Pharmacist",
        "LabTechnician",
    ]

    def handle(self, *args, **options):
        for name in self.GROUP_NAMES:
            group, created = Group.objects.get_or_create(name=name)

            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"Created group: {name}")
                )
            else:
                self.stdout.write(f"Group already exists: {name}")

        self.stdout.write(
            self.style.SUCCESS("CMS role groups are ready.")
        )
