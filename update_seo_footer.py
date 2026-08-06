import re

# 1. Update base.html with SEO Meta tags
base_path = r'd:\Projects\GroupSathi\templates\base.html'
with open(base_path, 'r', encoding='utf-8') as f:
    base_content = f.read()

meta_tags = """
    <meta name="author" content="Aman Kumar">
    <link rel="author" href="https://www.linkedin.com/in/amanxelon">
    <meta property="og:title" content="GroupSathi">
    <meta property="og:url" content="https://groupsathi.duckdns.org/">
    <meta property="og:type" content="website">
    <meta property="og:description" content="GroupSathi - Smart Management for Self Help Groups. Available as a Web App and Android App. Developed and founded by Aman Kumar.">
    <link rel="canonical" href="https://groupsathi.duckdns.org/">
"""
if 'name="author"' not in base_content:
    base_content = base_content.replace('<title>', meta_tags + '    <title>')
    with open(base_path, 'w', encoding='utf-8') as f:
        f.write(base_content)
    print("base.html updated with SEO meta tags.")

# 2. Update landing.html footer
landing_path = r'd:\Projects\GroupSathi\templates\landing\landing.html'
with open(landing_path, 'r', encoding='utf-8') as f:
    landing_content = f.read()

old_footer = """<footer class="bg-dark text-white py-4 text-center mt-auto">
    <div class="container">
        <div class="d-flex justify-content-center gap-3 mb-3">
            <a href="#" class="text-white-50 text-decoration-none" data-bs-toggle="modal"
                data-bs-target="#termsModal"><small>Terms & Conditions</small></a>
            <span class="text-white-50">|</span>
            <a href="#" class="text-white-50 text-decoration-none" data-bs-toggle="modal"
                data-bs-target="#privacyModal"><small>Privacy Policy</small></a>
        </div>
        <p class="text-muted mb-0">&copy; 2026 GroupSathi. All rights reserved. Empowering rural India.</p>
    </div>
</footer>"""

new_footer = """<footer class="bg-dark text-white py-4 text-center mt-auto">
    <div class="container">
        <div class="d-flex justify-content-center gap-3 mb-3">
            <a href="#faq" class="text-white-50 text-decoration-none"><small>FAQs</small></a>
            <span class="text-white-50">|</span>
            <a href="#" class="text-white-50 text-decoration-none" data-bs-toggle="modal"
                data-bs-target="#termsModal"><small>Terms & Conditions</small></a>
            <span class="text-white-50">|</span>
            <a href="#" class="text-white-50 text-decoration-none" data-bs-toggle="modal"
                data-bs-target="#privacyModal"><small>Privacy Policy</small></a>
        </div>
        <p class="text-light mb-2">&copy; 2026 GroupSathi. All rights reserved. Empowering rural India.</p>
        <p class="text-white-50 mb-0" style="font-size: 0.85rem;">GroupSathi is available as a Web App and Android App.<br>Developed and Founded by <a href="https://www.linkedin.com/in/amanxelon" target="_blank" class="text-white text-decoration-none fw-bold">Aman Kumar</a></p>
    </div>
</footer>"""

# The exact indentation might differ, so we'll use regex if direct replace fails
if old_footer in landing_content:
    landing_content = landing_content.replace(old_footer, new_footer)
else:
    # Use regex to find the footer
    footer_pattern = re.compile(r'<footer class="bg-dark text-white py-4 text-center mt-auto">.*?</footer>', re.DOTALL)
    landing_content = footer_pattern.sub(new_footer, landing_content)

with open(landing_path, 'w', encoding='utf-8') as f:
    f.write(landing_content)
print("landing.html updated with FAQ link, SEO footer, and fixed copyright.")
