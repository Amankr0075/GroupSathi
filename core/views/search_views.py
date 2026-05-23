"""
Search member views for GroupSathi.
"""

from django.shortcuts import render
from core.decorators import login_required_custom
from core.db import get_collection


@login_required_custom
def search_member_view(request):
    """Search for a member by Member ID."""
    result = None
    searched = False

    if request.method == 'POST' or request.GET.get('member_id'):
        member_id = (request.POST.get('member_id') or request.GET.get('member_id', '')).strip()
        if member_id:
            searched = True
            profiles = get_collection('profiles')
            profile = profiles.find_one({'member_id': member_id})
            if profile:
                # Check if searcher is in same group
                user_id = request.session['user_id']
                gm = get_collection('group_members')
                searcher_groups = set()
                for m in gm.find({'user_id': user_id, 'status': 'active'}):
                    searcher_groups.add(m['group_id'])

                target_groups = set()
                for m in gm.find({'user_id': profile['user_id'], 'status': 'active'}):
                    target_groups.add(m['group_id'])

                is_group_member = bool(searcher_groups & target_groups)

                result = {
                    'profile': profile,
                    'is_group_member': is_group_member,
                }

    return render(request, 'search/search_member.html', {
        'result': result, 'searched': searched,
    })
