"""
Help page view for GroupSathi.
"""

from django.shortcuts import render
from core.decorators import login_required_custom


@login_required_custom
def help_view(request):
    """Display help page with developer information."""
    context = {
        'developer_name': 'Aman Kumar',
        'developer_email': 'amankumar3443k@gmail.com',
    }
    return render(request, 'help/help.html', context)
