from django.shortcuts import render

def ratelimit_error_view(request, exception=None):
    """Custom view for handling ratelimit exceptions."""
    return render(request, 'errors/429.html', status=429)
