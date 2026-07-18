import requests
session = requests.Session()

# 1. Login using admin endpoint
login_url = "http://127.0.0.1:8000/auth/staff-login/"
r = session.get(login_url)
csrf_token = session.cookies.get('csrftoken')

login_data = {
    'email': 'amankumar3432k@gmail.com',
    'password': 'Aman@62478140',
    'csrfmiddlewaretoken': csrf_token
}
r = session.post(login_url, data=login_data, headers={'Referer': login_url})
print("Login status:", r.status_code)

# Check if session exists
print("Cookies after login:", session.cookies.get_dict())

# 2. Ask Chatbot
ask_url = "http://127.0.0.1:8000/api/chatbot/ask/"
headers = {
    'X-CSRFToken': session.cookies.get('csrftoken'),
    'Content-Type': 'application/json',
    'Referer': 'http://127.0.0.1:8000/dashboard/'
}
payload = {
    'message': 'Hello'
}
r = session.post(ask_url, json=payload, headers=headers)
print("Ask status:", r.status_code)
print("Ask response:", r.text)
