from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from soulstrader.models import SmartRecommendation, SmartAnalysisSession, RiskProfile
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Disable or delete all user accounts except testuser1 to minimize API calls'

    def add_arguments(self, parser):
        parser.add_argument(
            '--delete',
            action='store_true',
            help='Delete users instead of just disabling them',
        )
        parser.add_argument(
            '--keep',
            nargs='+',
            default=['testuser1'],
            help='List of usernames to keep (default: testuser1)',
        )

    def handle(self, *args, **options):
        keep_users = options['keep']
        delete_mode = options['delete']
        
        self.stdout.write(f"Keeping users: {', '.join(keep_users)}")
        
        # Get all users except the ones to keep
        users_to_process = User.objects.exclude(username__in=keep_users)
        
        if not users_to_process.exists():
            self.stdout.write(self.style.SUCCESS("No users to process - all users are in the keep list"))
            return
        
        self.stdout.write(f"Found {users_to_process.count()} users to process")
        
        # Show what we're about to do
        for user in users_to_process:
            self.stdout.write(f"  - {user.username} (ID: {user.id})")
        
        if delete_mode:
            self.stdout.write(self.style.WARNING("DELETE MODE: Users will be permanently deleted"))
        else:
            self.stdout.write(self.style.WARNING("DISABLE MODE: Users will be disabled (is_active=False)"))
        
        # Confirm action
        confirm = input("\nProceed? (yes/no): ").lower().strip()
        if confirm != 'yes':
            self.stdout.write("Operation cancelled")
            return
        
        processed_count = 0
        
        for user in users_to_process:
            try:
                if delete_mode:
                    # Delete user and all related data
                    self.stdout.write(f"Deleting user: {user.username}")
                    
                    # Delete related data first
                    SmartRecommendation.objects.filter(user=user).delete()
                    SmartAnalysisSession.objects.filter(user=user).delete()
                    RiskProfile.objects.filter(user=user).delete()
                    
                    # Delete the user
                    user.delete()
                    self.stdout.write(self.style.SUCCESS(f"  ✓ Deleted {user.username}"))
                else:
                    # Disable user
                    self.stdout.write(f"Disabling user: {user.username}")
                    user.is_active = False
                    user.save()
                    self.stdout.write(self.style.SUCCESS(f"  ✓ Disabled {user.username}"))
                
                processed_count += 1
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ Error processing {user.username}: {e}"))
        
        if delete_mode:
            self.stdout.write(self.style.SUCCESS(f"\nSuccessfully deleted {processed_count} users"))
        else:
            self.stdout.write(self.style.SUCCESS(f"\nSuccessfully disabled {processed_count} users"))
        
        # Show remaining active users
        remaining_users = User.objects.filter(is_active=True)
        self.stdout.write(f"\nRemaining active users ({remaining_users.count()}):")
        for user in remaining_users:
            self.stdout.write(f"  - {user.username}")
