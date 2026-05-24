"""
Landing page view for GroupSathi.
"""

from django.shortcuts import render, redirect


def _is_flutter_request(request):
    """
    Detect if the request originates from the Flutter app.

    Detection methods (either is sufficient):
    - User-Agent starts with 'Dart/' (default Dart/Flutter HTTP client)
    - Custom header X-App-Client: flutter is present
    """
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    custom_client = request.META.get('HTTP_X_APP_CLIENT', '')
    return user_agent.startswith('Dart/') or custom_client.lower() == 'flutter'


def landing_page_view(request):
    """Render the landing page for unauthenticated users.

    Website visitors see the landing page.
    Flutter app requests are redirected directly to the login page.
    """
    if request.session.get('user_id'):
        return redirect('dashboard')

    # Skip landing page for Flutter app — send it straight to login
    if _is_flutter_request(request):
        return redirect('login')

    return render(request, 'landing/landing.html')
