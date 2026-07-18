import re

chatbot_html = """
<!-- Floating Chatbot Widget -->
<div id="landing-chatbot-widget" class="chatbot-widget">
    <div class="chatbot-header">
        <span><i class="bi bi-robot me-2"></i>AI Assistant</span>
        <button id="chatbot-close" class="btn-close btn-close-white" aria-label="Close"></button>
    </div>
    <div class="chatbot-body" id="chatbot-messages">
        <div class="chat-message bot-message">
            Hello! I am the GroupSathi AI. Ask me anything about our platform, features, or how we empower Self Help Groups!
        </div>
    </div>
    <div class="chatbot-footer">
        <input type="text" id="chatbot-input" class="form-control" placeholder="Ask a question..." autocomplete="off">
        <button id="chatbot-send" class="btn btn-primary"><i class="bi bi-send"></i></button>
    </div>
</div>

<button id="chatbot-toggle" class="chatbot-toggle-btn">
    <i class="bi bi-chat-dots-fill"></i>
</button>
"""

chatbot_css = """
    /* Chatbot Widget Styles */
    .chatbot-widget {
        position: fixed;
        bottom: 80px;
        right: 20px;
        width: 320px;
        background: white;
        border-radius: 16px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.15);
        display: none;
        flex-direction: column;
        z-index: 10000;
        border: 1px solid rgba(0,0,0,0.1);
        overflow: hidden;
        animation: scaleUp 0.3s ease-out;
    }
    @keyframes scaleUp { from { transform: scale(0.9); opacity: 0; } to { transform: scale(1); opacity: 1; } }
    .chatbot-header {
        background: var(--gs-primary);
        color: white;
        padding: 12px 16px;
        font-weight: 600;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .chatbot-body {
        height: 250px;
        overflow-y: auto;
        padding: 16px;
        background: #f8fafc;
        display: flex;
        flex-direction: column;
        gap: 10px;
    }
    .chat-message {
        padding: 10px 14px;
        border-radius: 14px;
        font-size: 0.9rem;
        max-width: 85%;
        line-height: 1.4;
    }
    .bot-message {
        background: white;
        color: var(--gs-dark);
        border-bottom-left-radius: 4px;
        align-self: flex-start;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .user-message {
        background: var(--gs-secondary);
        color: white;
        border-bottom-right-radius: 4px;
        align-self: flex-end;
        box-shadow: 0 2px 5px rgba(59,130,246,0.3);
    }
    .chatbot-footer {
        padding: 12px;
        background: white;
        border-top: 1px solid rgba(0,0,0,0.05);
        display: flex;
        gap: 8px;
    }
    .chatbot-footer input {
        border-radius: 20px;
        font-size: 0.9rem;
    }
    .chatbot-footer button {
        border-radius: 50%;
        width: 40px;
        height: 40px;
        padding: 0;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .chatbot-toggle-btn {
        position: fixed;
        bottom: 20px;
        right: 20px;
        width: 55px;
        height: 55px;
        border-radius: 50%;
        background: linear-gradient(135deg, var(--gs-secondary), var(--gs-primary));
        color: white;
        border: none;
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        font-size: 1.5rem;
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
        cursor: pointer;
        transition: transform 0.3s;
    }
    .chatbot-toggle-btn:hover {
        transform: scale(1.1);
    }
"""

chatbot_js = """
<script>
    document.addEventListener("DOMContentLoaded", function() {
        const toggleBtn = document.getElementById('chatbot-toggle');
        const widget = document.getElementById('landing-chatbot-widget');
        const closeBtn = document.getElementById('chatbot-close');
        const sendBtn = document.getElementById('chatbot-send');
        const inputField = document.getElementById('chatbot-input');
        const messagesContainer = document.getElementById('chatbot-messages');

        toggleBtn.addEventListener('click', () => {
            widget.style.display = widget.style.display === 'flex' ? 'none' : 'flex';
        });

        closeBtn.addEventListener('click', () => {
            widget.style.display = 'none';
        });

        const sendMessage = () => {
            const text = inputField.value.trim();
            if (!text) return;

            // Add user message
            const userMsg = document.createElement('div');
            userMsg.className = 'chat-message user-message';
            userMsg.textContent = text;
            messagesContainer.appendChild(userMsg);
            
            inputField.value = '';
            messagesContainer.scrollTop = messagesContainer.scrollHeight;

            // Add typing indicator
            const typingMsg = document.createElement('div');
            typingMsg.className = 'chat-message bot-message';
            typingMsg.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Thinking...';
            messagesContainer.appendChild(typingMsg);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;

            // Send to public API
            fetch("{% url 'chatbot_public_ask' %}", {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': '{{ csrf_token }}'
                },
                body: JSON.stringify({ text: text })
            })
            .then(res => res.json())
            .then(data => {
                messagesContainer.removeChild(typingMsg);
                const botMsg = document.createElement('div');
                botMsg.className = 'chat-message bot-message';
                botMsg.textContent = data.response || "Sorry, I couldn't understand that.";
                messagesContainer.appendChild(botMsg);
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            })
            .catch(err => {
                messagesContainer.removeChild(typingMsg);
                const errorMsg = document.createElement('div');
                errorMsg.className = 'chat-message bot-message text-danger';
                errorMsg.textContent = "Network error. Please try again later.";
                messagesContainer.appendChild(errorMsg);
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            });
        };

        sendBtn.addEventListener('click', sendMessage);
        inputField.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
    });
</script>
"""

with open('templates/landing/landing.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Insert CSS
content = content.replace("</style>", f"{chatbot_css}\n</style>")

parts = content.split("{% endblock %}")
if len(parts) >= 3:
    # First endblock is for content block. Second is for extra_js block.
    # parts[0] + chatbot_html + endblock + parts[1] + chatbot_js + endblock + parts[2] 
    # But wait, there are 3 endblocks in the original template!
    # block extra_css ... endblock (parts[0], then parts[1])
    # block content ... endblock (parts[1], then parts[2])
    # block extra_js ... endblock (parts[2], then parts[3])
    
    # Let's verify by just injecting using regular expressions to be absolutely safe.
    pass

# Better approach:
# Replace the end of block content
content = content.replace("</footer>", f"</footer>\n{chatbot_html}")
# Replace the end of block extra_js
content = content.replace("</script>\n{% endblock %}", f"</script>\n{chatbot_js}\n{{% endblock %}}")

with open('templates/landing/landing.html', 'w', encoding='utf-8') as f:
    f.write(content)
