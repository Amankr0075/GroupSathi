import re

landing_path = r'd:\Projects\GroupSathi\templates\landing\landing.html'

with open(landing_path, 'r', encoding='utf-8') as f:
    content = f.read()

new_css = """
    /* Feature Card Hover & Icon Animations */
    .feature-card:hover {
        transform: translateY(-10px) !important;
        box-shadow: 0 20px 40px rgba(0,0,0,0.1) !important;
        border-color: rgba(59, 130, 246, 0.2) !important;
    }

    .icon-pulse {
        animation: icon-pulse-anim 2s infinite;
    }
    @keyframes icon-pulse-anim {
        0% { transform: scale(1); }
        50% { transform: scale(1.15); }
        100% { transform: scale(1); }
    }

    .icon-ring {
        animation: icon-ring-anim 2.5s infinite;
        transform-origin: top center;
    }
    @keyframes icon-ring-anim {
        0%, 100% { transform: rotate(0deg); }
        10%, 30%, 50% { transform: rotate(15deg); }
        20%, 40% { transform: rotate(-15deg); }
        60% { transform: rotate(0deg); }
    }

    .icon-float {
        animation: icon-float-anim 3s ease-in-out infinite;
    }
    @keyframes icon-float-anim {
        0% { transform: translateY(0); }
        50% { transform: translateY(-8px); }
        100% { transform: translateY(0); }
    }

    .icon-beat {
        animation: icon-beat-anim 1.5s infinite;
    }
    @keyframes icon-beat-anim {
        0%, 100% { transform: scale(1); }
        25% { transform: scale(1.1); }
        50% { transform: scale(1); }
        75% { transform: scale(1.1); }
    }
"""

if '.icon-float' not in content:
    content = content.replace('</style>', new_css + '\n</style>')

# Replace the specific icons with the animated classes
content = content.replace('<i class="bi bi-people-fill"></i>', '<i class="bi bi-people-fill icon-pulse"></i>')
content = content.replace('<i class="bi bi-bell-fill"></i>', '<i class="bi bi-bell-fill icon-ring"></i>')
content = content.replace('<i class="bi bi-robot"></i>', '<i class="bi bi-robot icon-float"></i>')
content = content.replace('<i class="bi bi-exclamation-octagon"></i>', '<i class="bi bi-exclamation-octagon icon-beat"></i>')

with open(landing_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated feature cards with live animations.")
