from django.core.management.base import BaseCommand
from accounts.models import WorkProgress, User

class Command(BaseCommand):
    help = "Seed sample work progress"

    def handle(self, *args, **kwargs):
        user = User.objects.first()
        if not user:
            self.stdout.write("❌ No users found. Create at least one user first.")
            return
        
        sample_data = [
            ("Oil Change", "Routine oil replacement service", "Completed"),
            ("Brake Inspection", "Front & rear brake safety check", "In Progress"),
            ("Tire Rotation", "Tyre alignment & balancing", "Pending"),
            ("Engine Diagnostics", "Scanning engine performance issues", "Completed"),
            ("Battery Check", "Testing battery output", "Pending"),
        ]

        for work, desc, status in sample_data:
            WorkProgress.objects.create(
                user=user,
                work_type=work,
                description=desc,
                status=status
            )

        self.stdout.write("✔ Sample work progress added successfully!")
