import os

landing_path = r'd:\Projects\GroupSathi\templates\landing\landing.html'

css_to_add = """
    /* FAQ Section Styles */
    .faq-section {
        background: linear-gradient(135deg, var(--gs-light), #FFFFFF);
        position: relative;
        overflow: hidden;
    }

    .faq-section::before {
        content: '';
        position: absolute;
        top: -50px;
        right: -50px;
        width: 300px;
        height: 300px;
        background: radial-gradient(circle, rgba(59, 130, 246, 0.05) 0%, rgba(255, 255, 255, 0) 70%);
        border-radius: 50%;
    }

    .faq-header {
        text-align: center;
        margin-bottom: 3rem;
    }

    .faq-header h2 {
        font-weight: 800;
        color: var(--gs-primary);
        font-size: 2.5rem;
    }

    .faq-header h2 span {
        background: linear-gradient(135deg, #3B82F6, #10B981);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .accordion-item {
        border: none;
        background: rgba(255, 255, 255, 0.7);
        backdrop-filter: blur(10px);
        border-radius: 16px !important;
        margin-bottom: 1rem;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.03);
        transition: all 0.3s ease;
    }

    .accordion-item:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.06);
    }

    .accordion-button {
        background: transparent !important;
        font-family: var(--font-heading);
        font-weight: 600;
        font-size: 1.1rem;
        color: var(--gs-primary);
        padding: 1.25rem 1.5rem;
        border: none;
        border-radius: 16px !important;
        box-shadow: none !important;
    }

    .accordion-button:not(.collapsed) {
        color: var(--gs-secondary);
        background: rgba(59, 130, 246, 0.03) !important;
    }

    .accordion-button::after {
        background-size: 1.25rem;
        transition: all 0.3s ease;
    }

    .accordion-body {
        padding: 0 1.5rem 1.25rem 1.5rem;
        color: var(--gs-slate);
        line-height: 1.7;
        font-size: 1rem;
    }
"""

html_to_add = """
<!-- FAQ Section -->
<section id="faq" class="py-5 faq-section">
    <div class="container">
        <div class="faq-header" data-aos="fade-up">
            <h2>Frequently Asked <span>Questions</span></h2>
            <p class="text-muted">Everything you need to know about the GroupSathi platform.</p>
        </div>
        
        <div class="row justify-content-center">
            <div class="col-lg-8">
                <div class="accordion" id="faqAccordion">
                    
                    <!-- Question 1 -->
                    <div class="accordion-item" data-aos="fade-up" data-aos-delay="100">
                        <h2 class="accordion-header" id="headingOne">
                            <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseOne" aria-expanded="false" aria-controls="collapseOne">
                                What is GroupSathi?
                            </button>
                        </h2>
                        <div id="collapseOne" class="accordion-collapse collapse" aria-labelledby="headingOne" data-bs-parent="#faqAccordion">
                            <div class="accordion-body">
                                GroupSathi is a comprehensive digital ledger and management platform designed specifically for Self Help Groups (SHGs). It helps groups securely track monthly contributions (EMI), manage loans, apply fines, and calculate final settlement payouts.
                            </div>
                        </div>
                    </div>

                    <!-- Question 2 -->
                    <div class="accordion-item" data-aos="fade-up" data-aos-delay="200">
                        <h2 class="accordion-header" id="headingTwo">
                            <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseTwo" aria-expanded="false" aria-controls="collapseTwo">
                                Is GroupSathi a bank or financial institution?
                            </button>
                        </h2>
                        <div id="collapseTwo" class="accordion-collapse collapse" aria-labelledby="headingTwo" data-bs-parent="#faqAccordion">
                            <div class="accordion-body">
                                No. GroupSathi is strictly a record-keeping and management tool. We do not collect, hold, or transfer real money. Your group remains fully responsible for physically managing its own funds.
                            </div>
                        </div>
                    </div>

                    <!-- Question 3 -->
                    <div class="accordion-item" data-aos="fade-up" data-aos-delay="300">
                        <h2 class="accordion-header" id="headingThree">
                            <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseThree" aria-expanded="false" aria-controls="collapseThree">
                                How is the final settlement (payout) calculated?
                            </button>
                        </h2>
                        <div id="collapseThree" class="accordion-collapse collapse" aria-labelledby="headingThree" data-bs-parent="#faqAccordion">
                            <div class="accordion-body">
                                We use a highly deterministic, single-pass calculation. A member's final payout is their total paid contributions plus their proportional share of the group's collected profit (interest and fines), minus any outstanding dues (like unpaid loans or fines).
                            </div>
                        </div>
                    </div>

                    <!-- Question 4 -->
                    <div class="accordion-item" data-aos="fade-up" data-aos-delay="400">
                        <h2 class="accordion-header" id="headingFour">
                            <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseFour" aria-expanded="false" aria-controls="collapseFour">
                                Can I be a member of multiple groups?
                            </button>
                        </h2>
                        <div id="collapseFour" class="accordion-collapse collapse" aria-labelledby="headingFour" data-bs-parent="#faqAccordion">
                            <div class="accordion-body">
                                Yes! GroupSathi allows users to seamlessly join and manage multiple Self Help Groups from a single account.
                            </div>
                        </div>
                    </div>

                    <!-- Question 5 -->
                    <div class="accordion-item" data-aos="fade-up" data-aos-delay="500">
                        <h2 class="accordion-header" id="headingFive">
                            <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseFive" aria-expanded="false" aria-controls="collapseFive">
                                How does the AI Assistant work?
                            </button>
                        </h2>
                        <div id="collapseFive" class="accordion-collapse collapse" aria-labelledby="headingFive" data-bs-parent="#faqAccordion">
                            <div class="accordion-body">
                                The GroupSathi AI Assistant is available 24/7 to help you navigate the platform, understand your group's financial health, and answer questions about platform features.
                            </div>
                        </div>
                    </div>

                    <!-- Question 6 -->
                    <div class="accordion-item" data-aos="fade-up" data-aos-delay="600">
                        <h2 class="accordion-header" id="headingSix">
                            <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseSix" aria-expanded="false" aria-controls="collapseSix">
                                Can I generate reports for our group meetings?
                            </button>
                        </h2>
                        <div id="collapseSix" class="accordion-collapse collapse" aria-labelledby="headingSix" data-bs-parent="#faqAccordion">
                            <div class="accordion-body">
                                Absolutely. Group leaders can instantly generate and download detailed, professional PDF reports of all transactions, member balances, and settlement plans.
                            </div>
                        </div>
                    </div>

                    <!-- Question 7 -->
                    <div class="accordion-item" data-aos="fade-up" data-aos-delay="700">
                        <h2 class="accordion-header" id="headingSeven">
                            <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseSeven" aria-expanded="false" aria-controls="collapseSeven">
                                How is my group's data secured?
                            </button>
                        </h2>
                        <div id="collapseSeven" class="accordion-collapse collapse" aria-labelledby="headingSeven" data-bs-parent="#faqAccordion">
                            <div class="accordion-body">
                                All financial records and user data are securely encrypted and stored. We ensure that only authorized group members and leaders can access your group's private ledger.
                            </div>
                        </div>
                    </div>

                </div>
            </div>
        </div>
    </div>
</section>
"""

with open(landing_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Inject CSS
if '</style>' in content and '.faq-section' not in content:
    content = content.replace('</style>', css_to_add + '\n</style>')

# Inject HTML
footer_tag = '<footer class="bg-dark text-white py-4 text-center mt-auto">'
if footer_tag in content and 'id="faq"' not in content:
    content = content.replace(footer_tag, html_to_add + '\n' + footer_tag)

with open(landing_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Done")
