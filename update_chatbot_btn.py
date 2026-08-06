import re

landing_path = r'd:\Projects\GroupSathi\templates\landing\landing.html'

with open(landing_path, 'r', encoding='utf-8') as f:
    content = f.read()

new_css = """
    /* Chatbot Label & Floating */
    .chatbot-toggle-container {
        position: fixed;
        bottom: 20px;
        right: 20px;
        z-index: 10000;
        display: flex;
        align-items: center;
        gap: 12px;
        cursor: pointer;
    }

    .chatbot-label {
        background: white;
        color: var(--gs-primary);
        padding: 8px 16px;
        border-radius: 30px;
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.15);
        font-family: var(--font-heading);
        font-weight: 600;
        font-size: 0.95rem;
        display: flex;
        align-items: center;
        position: relative;
        animation: float-label 3s ease-in-out infinite;
    }

    .chatbot-label::after {
        content: '';
        position: absolute;
        right: -8px;
        top: 50%;
        transform: translateY(-50%);
        border-width: 8px 0 8px 8px;
        border-style: solid;
        border-color: transparent transparent transparent white;
    }

    @keyframes float-label {
        0% { transform: translateY(0px); }
        50% { transform: translateY(-5px); }
        100% { transform: translateY(0px); }
    }

    .chatbot-btn-animated {
        width: 60px;
        height: 60px;
        border-radius: 50%;
        padding: 0;
        border: 3px solid white;
        overflow: hidden;
        box-shadow: 0 8px 25px rgba(59, 130, 246, 0.5);
        animation: pulse-ring 2s infinite;
        transition: transform 0.3s;
    }

    .chatbot-btn-animated:hover {
        transform: scale(1.1);
    }

    @keyframes pulse-ring {
        0% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.7); }
        70% { box-shadow: 0 0 0 15px rgba(59, 130, 246, 0); }
        100% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0); }
    }
"""

if '.chatbot-toggle-container' not in content:
    content = content.replace('</style>', new_css + '\n</style>')

old_button = """<button id="chatbot-toggle" class="chatbot-toggle-btn" style="padding:0; overflow:hidden;">
    <img src="{% static 'images/GroupSathi.png' %}" alt="AI" style="width:100%; height:100%; object-fit:cover;">
</button>"""

new_button = """<div class="chatbot-toggle-container" id="chatbot-toggle-wrapper">
    <div class="chatbot-label" id="chatbot-label-text">
        <span>Need Help? <strong>Ask AI</strong></span>
        <i class="bi bi-robot ms-2 text-primary fs-5"></i>
    </div>
    <button id="chatbot-toggle" class="chatbot-btn-animated bg-white">
        <img src="{% static 'images/GroupSathi.png' %}" alt="AI" style="width:100%; height:100%; object-fit:cover;">
    </button>
</div>"""

if old_button in content:
    content = content.replace(old_button, new_button)

# Also update the JS to toggle on the wrapper as well, or just let the button handle it
# Actually, the user might click the label instead of the button, so we should bind the event to the wrapper or label as well
# Let's find the JS section
js_toggle = "toggleBtn.addEventListener('click', () => {"
new_js_toggle = """
        const toggleWrapper = document.getElementById('chatbot-toggle-wrapper');
        const labelText = document.getElementById('chatbot-label-text');
        
        const toggleChatbot = () => {
            widget.style.display = widget.style.display === 'flex' ? 'none' : 'flex';
            if (widget.style.display === 'flex') {
                labelText.style.display = 'none'; // Hide label when open
            }
        };

        toggleBtn.addEventListener('click', toggleChatbot);
        labelText.addEventListener('click', toggleChatbot);
"""
# Replace the original event listener
content = re.sub(r"toggleBtn\.addEventListener\('click',\s*\(\)\s*=>\s*\{[^}]+\}\);", new_js_toggle, content)

with open(landing_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated chatbot button")
