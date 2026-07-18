import urllib.request, urllib.parse, re, http.cookiejar

try:
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    urllib.request.install_opener(opener)
    
    # GET to get csrf cookie
    resp = opener.open('http://127.0.0.1:8000/auth/staff-login/')
    html = resp.read().decode()
    
    csrftoken = ""
    for cookie in cj:
        if cookie.name == 'csrftoken':
            csrftoken = cookie.value
    
    csrf_input = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html)
    if csrf_input:
        csrf_token = csrf_input.group(1)
    else:
        csrf_token = csrftoken
        
    data = urllib.parse.urlencode({
        'csrfmiddlewaretoken': csrf_token,
        'email': 'amankumar3432k@gmail.com',
        'password': 'Aman@62478140'
    }).encode()
    
    req = urllib.request.Request('http://127.0.0.1:8000/auth/staff-login/', data=data, method='POST')
    req.add_header('Referer', 'http://127.0.0.1:8000/auth/staff-login/')
    opener.open(req)
except Exception as e:
    html = e.read().decode()
    match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
    if match:
        print("Error:", match.group(1))
        tb_match = re.search(r'Exception Value:(.*?)</pre>', html, re.DOTALL)
        if tb_match:
            print("Traceback snippet:", tb_match.group(1)[:500].strip())
        else:
            print(html[:500])
    else:
        print("Raw:", html[:500])
