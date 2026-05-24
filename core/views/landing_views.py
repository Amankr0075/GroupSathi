"""
Landing page view for GroupSathi.
"""

from django.shortcuts import render, redirect

def landing_page_view(request):
    """Render the landing page for unauthenticated users."""
    if request.session.get('user_id'):
        return redirect('dashboard')
    
    return render(request, 'landing/landing.html')
