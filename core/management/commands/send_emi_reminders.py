"""
Management command to send automated 24-hour EMI reminders for all active groups.
Run this daily via a cron job or task scheduler:

  python manage.py send_emi_reminders

Windows Task Scheduler example:
  Program: python
  Arguments: manage.py send_emi_reminders
  Start In: D:\\Projects\\GroupSathi
"""

from django.core.management.base import BaseCommand
from core.utils import check_and_send_all_active_reminders


class Command(BaseCommand):
    help = 'Send automated 24-hour EMI reminders and loan/interest alerts to group members.'

    def handle(self, *args, **options):
        self.stdout.write('Checking and sending automated EMI reminders...')
        try:
            check_and_send_all_active_reminders()
            self.stdout.write(self.style.SUCCESS('Done! Reminders sent to qualifying groups.'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error sending reminders: {e}'))
