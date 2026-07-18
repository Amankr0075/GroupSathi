js_code = """
{% block extra_js %}
<script>
function summarizeWithAI() {
    const message = document.getElementById('id_message').value.trim();
    if (!message) {
        alert("Please enter a message first.");
        return;
    }
    
    const btn = document.getElementById('btn_ai');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Generating...';
    
    fetch("{% url 'ai_summarize' %}", {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        },
        body: JSON.stringify({ text: message })
    })
    .then(response => response.json())
    .then(data => {
        if (data.summary) {
            document.getElementById('id_title').value = data.summary;
        } else if (data.error) {
            alert("Error: " + data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert("Failed to generate title.");
    })
    .finally(() => {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-magic"></i> AI Generate Title';
    });
}
</script>
{% endblock %}
"""
with open('templates/admin/admin_broadcast.html', 'a') as f:
    f.write(js_code)
