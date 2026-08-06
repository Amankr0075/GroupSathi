import re

landing_path = r'd:\Projects\GroupSathi\templates\landing\landing.html'

with open(landing_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update the Footer Link
# Replace: <a href="#faq" class="text-white-50 text-decoration-none"><small>FAQs</small></a>
# With: <a href="#" class="text-white-50 text-decoration-none" data-bs-toggle="modal" data-bs-target="#faqModal"><small>FAQs</small></a>
content = content.replace(
    '<a href="#faq" class="text-white-50 text-decoration-none"><small>FAQs</small></a>',
    '<a href="#" class="text-white-50 text-decoration-none" data-bs-toggle="modal" data-bs-target="#faqModal"><small>FAQs</small></a>'
)

# 2. Extract the massive accordion from the FAQ section
# The FAQ section starts with <!-- FAQ Section --> and ends with </section>
faq_pattern = re.compile(r'<!-- FAQ Section -->.*?<div class="accordion" id="faqAccordion">(.*?)</div>\s*</div>\s*</div>\s*</div>\s*</section>', re.DOTALL)
match = faq_pattern.search(content)

if match:
    accordion_content = match.group(1)
    
    # We will remove the old FAQ section and replace it with nothing.
    content = faq_pattern.sub('', content)
    
    # Now we create the FAQ Modal HTML
    faq_modal_html = f"""
<!-- FAQ Modal -->
<div class="modal fade" id="faqModal" tabindex="-1" aria-labelledby="faqModalLabel" aria-hidden="true">
    <div class="modal-dialog modal-xl modal-dialog-centered modal-dialog-scrollable">
        <div class="modal-content" style="background: linear-gradient(135deg, var(--gs-light), #FFFFFF);">
            <div class="modal-header border-0 pb-0">
                <div class="w-100 text-center position-relative">
                    <h2 class="modal-title fw-bold" id="faqModalLabel" style="color: var(--gs-primary); font-size: 2rem;">
                        Frequently Asked <span style="background: linear-gradient(135deg, #3B82F6, #10B981); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">Questions</span>
                    </h2>
                    <p class="text-muted mb-0">Everything you need to know about the GroupSathi platform.</p>
                </div>
                <button type="button" class="btn-close position-absolute top-0 end-0 m-3" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            <div class="modal-body p-4 p-md-5">
                <div class="accordion" id="faqAccordion">
                    {accordion_content}
                </div>
            </div>
        </div>
    </div>
</div>
"""
    # Insert the FAQ modal right before the Terms Modal
    # <!-- Modals for Policies --> is a good anchor point
    if '<!-- Modals for Policies -->' in content:
        content = content.replace('<!-- Modals for Policies -->', faq_modal_html + '\n<!-- Modals for Policies -->')
    else:
        # Just append it before closing body tag or any other modal
        content = content.replace('</body>', faq_modal_html + '\n</body>')

with open(landing_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated landing.html: Moved FAQ to a modal.")
