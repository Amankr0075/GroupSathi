"""
Calculator views for GroupSathi.
"""

from django.shortcuts import render
from core.decorators import login_required_custom

@login_required_custom
def calculator_view(request):
    """Render the high-fidelity mobile calculator & simple interest calculator page."""
    return render(request, 'calculator/calculator.html')
