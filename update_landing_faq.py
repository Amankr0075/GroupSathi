import re

landing_path = r'd:\Projects\GroupSathi\templates\landing\landing.html'

with open(landing_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. New CSS for APK Button Animation and enhanced FAQ categories
new_css = """
    /* APK Button Animation */
    .apk-btn-animated {
        position: relative;
        overflow: hidden;
        animation: pulse-shadow 2s infinite;
        z-index: 1;
    }
    
    .apk-btn-animated::before {
        content: '';
        position: absolute;
        top: 0; left: -100%;
        width: 100%; height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent);
        transition: all 0.5s ease;
        animation: shine 3s infinite;
        z-index: -1;
    }

    @keyframes pulse-shadow {
        0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
        70% { box-shadow: 0 0 0 15px rgba(16, 185, 129, 0); }
        100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
    }

    @keyframes shine {
        0% { left: -100%; }
        20% { left: 100%; }
        100% { left: 100%; }
    }

    /* FAQ Category Headers */
    .faq-category {
        font-family: var(--font-heading);
        font-weight: 700;
        color: var(--gs-primary);
        margin-top: 2rem;
        margin-bottom: 1rem;
        font-size: 1.5rem;
        border-bottom: 2px solid rgba(59, 130, 246, 0.1);
        padding-bottom: 0.5rem;
    }
"""

# Insert new CSS just before </style>
if '.apk-btn-animated' not in content:
    content = content.replace('</style>', new_css + '\n</style>')

# 2. Add class to APK button
old_apk_btn = '<a href="{% url \'download_apk\' %}" class="btn btn-pro btn-pro-accent px-4 py-3 fs-5">'
new_apk_btn = '<a href="{% url \'download_apk\' %}" class="btn btn-pro btn-pro-accent px-4 py-3 fs-5 apk-btn-animated">'
content = content.replace(old_apk_btn, new_apk_btn)

# 3. Massive FAQ HTML Replacement
massive_faq_html = """
<!-- FAQ Section -->
<section id="faq" class="py-5 faq-section">
    <div class="container">
        <div class="faq-header" data-aos="fade-up">
            <h2>Frequently Asked <span>Questions</span></h2>
            <p class="text-muted">Everything you need to know about the GroupSathi platform, from features to security.</p>
        </div>
        
        <div class="row justify-content-center">
            <div class="col-lg-10">
                <div class="accordion" id="faqAccordion">
                    
                    <!-- CATEGORY: GENERAL & FACILITIES -->
                    <h3 class="faq-category" data-aos="fade-up">General & Facilities</h3>
                    
                    <div class="accordion-item" data-aos="fade-up" data-aos-delay="50">
                        <h2 class="accordion-header" id="headingGen1">
                            <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseGen1" aria-expanded="false" aria-controls="collapseGen1">
                                What is GroupSathi and how does it help Self Help Groups?
                            </button>
                        </h2>
                        <div id="collapseGen1" class="accordion-collapse collapse" aria-labelledby="headingGen1" data-bs-parent="#faqAccordion">
                            <div class="accordion-body">
                                GroupSathi is a digital ledger and management platform. It helps Self Help Groups (SHGs) transition from traditional paper-based record-keeping to a 100% transparent, automated digital ecosystem. It tracks monthly contributions, calculates interest, manages loans, and generates instant reports.
                            </div>
                        </div>
                    </div>

                    <div class="accordion-item" data-aos="fade-up" data-aos-delay="100">
                        <h2 class="accordion-header" id="headingGen2">
                            <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseGen2" aria-expanded="false" aria-controls="collapseGen2">
                                Do you provide the funds or act as a bank?
                            </button>
                        </h2>
                        <div id="collapseGen2" class="accordion-collapse collapse" aria-labelledby="headingGen2" data-bs-parent="#faqAccordion">
                            <div class="accordion-body">
                                No. GroupSathi is strictly a software management tool. We do not collect, hold, or transfer any real money through our platform. All physical cash remains completely under the control and responsibility of the group members and leaders.
                            </div>
                        </div>
                    </div>

                    <div class="accordion-item" data-aos="fade-up" data-aos-delay="150">
                        <h2 class="accordion-header" id="headingGen3">
                            <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseGen3" aria-expanded="false" aria-controls="collapseGen3">
                                Can I use GroupSathi on my mobile phone?
                            </button>
                        </h2>
                        <div id="collapseGen3" class="accordion-collapse collapse" aria-labelledby="headingGen3" data-bs-parent="#faqAccordion">
                            <div class="accordion-body">
                                Yes! You can access the platform via our responsive website on any device, and Android users can download the official GroupSathi APK for a native app experience.
                            </div>
                        </div>
                    </div>

                    <!-- CATEGORY: CORE FUNCTIONS -->
                    <h3 class="faq-category" data-aos="fade-up">Core Functions (EMI, Loans & Settlements)</h3>

                    <div class="accordion-item" data-aos="fade-up" data-aos-delay="200">
                        <h2 class="accordion-header" id="headingFunc1">
                            <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseFunc1" aria-expanded="false" aria-controls="collapseFunc1">
                                How are loans and interest managed?
                            </button>
                        </h2>
                        <div id="collapseFunc1" class="accordion-collapse collapse" aria-labelledby="headingFunc1" data-bs-parent="#faqAccordion">
                            <div class="accordion-body">
                                Group leaders can approve loan requests through the dashboard. The system automatically calculates compound or flat interest based on the group's predefined rate, and adds it to the member's outstanding dues.
                            </div>
                        </div>
                    </div>

                    <div class="accordion-item" data-aos="fade-up" data-aos-delay="250">
                        <h2 class="accordion-header" id="headingFunc2">
                            <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseFunc2" aria-expanded="false" aria-controls="collapseFunc2">
                                How is the final group settlement calculated?
                            </button>
                        </h2>
                        <div id="collapseFunc2" class="accordion-collapse collapse" aria-labelledby="headingFunc2" data-bs-parent="#faqAccordion">
                            <div class="accordion-body">
                                GroupSathi uses a deterministic, single-pass calculation system. A member's final payout equals their Total Paid EMI plus their Share of the Group's Profit (collected interest and fines), minus any Outstanding Dues (unpaid loans, fines, or EMIs).
                            </div>
                        </div>
                    </div>
                    
                    <div class="accordion-item" data-aos="fade-up" data-aos-delay="300">
                        <h2 class="accordion-header" id="headingFunc3">
                            <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseFunc3" aria-expanded="false" aria-controls="collapseFunc3">
                                Can we generate financial reports?
                            </button>
                        </h2>
                        <div id="collapseFunc3" class="accordion-collapse collapse" aria-labelledby="headingFunc3" data-bs-parent="#faqAccordion">
                            <div class="accordion-body">
                                Yes. Group leaders can generate instantaneous, professional PDF reports outlining total cash available, distributable profit, member contributions, and final payout plans for audit purposes.
                            </div>
                        </div>
                    </div>

                    <!-- CATEGORY: SUBSCRIPTIONS & PRICING -->
                    <h3 class="faq-category" data-aos="fade-up">Subscriptions & Pricing</h3>

                    <div class="accordion-item" data-aos="fade-up" data-aos-delay="350">
                        <h2 class="accordion-header" id="headingSub1">
                            <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseSub1" aria-expanded="false" aria-controls="collapseSub1">
                                Is GroupSathi free to use?
                            </button>
                        </h2>
                        <div id="collapseSub1" class="accordion-collapse collapse" aria-labelledby="headingSub1" data-bs-parent="#faqAccordion">
                            <div class="accordion-body">
                                GroupSathi is currently free for early adopters. We believe in providing robust financial tools to rural groups without immediate cost barriers.
                            </div>
                        </div>
                    </div>
                    
                    <div class="accordion-item" data-aos="fade-up" data-aos-delay="400">
                        <h2 class="accordion-header" id="headingSub2">
                            <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseSub2" aria-expanded="false" aria-controls="collapseSub2">
                                Will I have to pay in the future?
                            </button>
                        </h2>
                        <div id="collapseSub2" class="accordion-collapse collapse" aria-labelledby="headingSub2" data-bs-parent="#faqAccordion">
                            <div class="accordion-body">
                                In the future, the platform may introduce a nominal subscription fee for advanced features or for managing larger groups. However, transparency is our core value, and any pricing changes will be communicated well in advance.
                            </div>
                        </div>
                    </div>

                    <!-- CATEGORY: SECURITY & PRIVACY -->
                    <h3 class="faq-category" data-aos="fade-up">Security, Privacy & Terms</h3>

                    <div class="accordion-item" data-aos="fade-up" data-aos-delay="450">
                        <h2 class="accordion-header" id="headingSec1">
                            <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseSec1" aria-expanded="false" aria-controls="collapseSec1">
                                How secure is our financial data?
                            </button>
                        </h2>
                        <div id="collapseSec1" class="accordion-collapse collapse" aria-labelledby="headingSec1" data-bs-parent="#faqAccordion">
                            <div class="accordion-body">
                                Extremely secure. We use industry-standard encryption for data at rest and in transit. Your group's ledger is completely private and only accessible to verified members and leaders of that specific group.
                            </div>
                        </div>
                    </div>

                    <div class="accordion-item" data-aos="fade-up" data-aos-delay="500">
                        <h2 class="accordion-header" id="headingSec2">
                            <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseSec2" aria-expanded="false" aria-controls="collapseSec2">
                                How is my personal information handled? (Privacy Policy)
                            </button>
                        </h2>
                        <div id="collapseSec2" class="accordion-collapse collapse" aria-labelledby="headingSec2" data-bs-parent="#faqAccordion">
                            <div class="accordion-body">
                                GroupSathi only collects information necessary to maintain accurate records. We do not sell your data to third parties. For full details, please refer to our Privacy Policy linked in the footer.
                            </div>
                        </div>
                    </div>

                    <div class="accordion-item" data-aos="fade-up" data-aos-delay="550">
                        <h2 class="accordion-header" id="headingSec3">
                            <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseSec3" aria-expanded="false" aria-controls="collapseSec3">
                                What are the Terms and Conditions of use?
                            </button>
                        </h2>
                        <div id="collapseSec3" class="accordion-collapse collapse" aria-labelledby="headingSec3" data-bs-parent="#faqAccordion">
                            <div class="accordion-body">
                                By using GroupSathi, you agree that it is a record-keeping tool and you are solely responsible for the physical handling of cash. You also agree to our fair usage policies. Detailed Terms & Conditions can be accessed via the footer modal.
                            </div>
                        </div>
                    </div>

                    <!-- CATEGORY: AI & SUPPORT -->
                    <h3 class="faq-category" data-aos="fade-up">AI Assistant & Support</h3>

                    <div class="accordion-item" data-aos="fade-up" data-aos-delay="600">
                        <h2 class="accordion-header" id="headingAI1">
                            <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseAI1" aria-expanded="false" aria-controls="collapseAI1">
                                What does the AI Assistant do?
                            </button>
                        </h2>
                        <div id="collapseAI1" class="accordion-collapse collapse" aria-labelledby="headingAI1" data-bs-parent="#faqAccordion">
                            <div class="accordion-body">
                                Powered by advanced language models, the GroupSathi AI Assistant helps you navigate the platform, explains financial calculations, and provides instant support for common queries related to SHG management.
                            </div>
                        </div>
                    </div>

                    <div class="accordion-item" data-aos="fade-up" data-aos-delay="650">
                        <h2 class="accordion-header" id="headingAI2">
                            <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseAI2" aria-expanded="false" aria-controls="collapseAI2">
                                How do I contact human support?
                            </button>
                        </h2>
                        <div id="collapseAI2" class="accordion-collapse collapse" aria-labelledby="headingAI2" data-bs-parent="#faqAccordion">
                            <div class="accordion-body">
                                If the AI Assistant cannot resolve your issue, you can reach out to our dedicated support team via the Contact form in the application, or by emailing support@groupsathi.org.
                            </div>
                        </div>
                    </div>

                </div>
            </div>
        </div>
    </div>
</section>
"""

import re
# Find the existing FAQ section and replace it
# The existing section starts with <!-- FAQ Section --> and ends with </section>
faq_pattern = re.compile(r'<!-- FAQ Section -->.*?</section>', re.DOTALL)
content = faq_pattern.sub(massive_faq_html, content)

with open(landing_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated landing.html with expanded FAQ and animated APK button")
