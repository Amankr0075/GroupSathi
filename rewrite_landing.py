import os

html_content = """{% extends 'base.html' %}
{% load static %}

{% block title %}GroupSathi | Empowering Self Help Groups{% endblock %}

{% block extra_css %}
<!-- Modern Fonts & AOS -->
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<link href="https://unpkg.com/aos@2.3.1/dist/aos.css" rel="stylesheet">

<style>
    :root {
        --font-main: 'Plus Jakarta Sans', sans-serif;
        --font-heading: 'Outfit', sans-serif;
        --gs-primary: #0F172A;
        --gs-secondary: #3B82F6;
        --gs-accent: #10B981;
        --gs-dark: #020617;
        --gs-slate: #64748B;
        --gs-light: #F8FAFC;
    }

    body {
        font-family: var(--font-main);
        background-color: var(--gs-light);
        color: var(--gs-dark);
        overflow-x: hidden;
    }

    h1, h2, h3, h4, h5, h6 { font-family: var(--font-heading); }

    .bg-animation {
        position: fixed;
        top: 0; left: 0; width: 100%; height: 100%; z-index: -2;
        background: radial-gradient(120% 100% at 50% 0%, #FFFFFF 0%, #F1F5F9 100%);
    }

    /* Navbar */
    .landing-nav {
        background: rgba(255,255,255,0.8);
        backdrop-filter: blur(24px);
        border-bottom: 1px solid rgba(0, 0, 0, 0.04);
        padding: 1.2rem 0;
    }
    .gs-brand-v3 {
        font-family: var(--font-heading); font-weight: 800; font-size: 1.8rem;
        color: var(--gs-primary); letter-spacing: -0.5px;
    }

    /* Hero */
    .hero-v3 { padding: 180px 0 100px; position: relative; }
    .hero-title-v3 { font-size: clamp(2.5rem, 6vw, 4.5rem); font-weight: 800; line-height: 1.1; letter-spacing: -1.5px; color: var(--gs-primary); margin-bottom: 24px; }
    .hero-title-v3 span { background: linear-gradient(135deg, var(--gs-secondary), #8B5CF6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .hero-desc { font-size: 1.15rem; color: var(--gs-slate); line-height: 1.7; margin-bottom: 40px; }

    /* Buttons */
    .btn-pro { padding: 14px 32px; font-weight: 600; border-radius: 12px; transition: all 0.3s; white-space: nowrap; }
    .btn-pro-primary { background: var(--gs-primary); color: white !important; box-shadow: 0 8px 20px rgba(15, 23, 42, 0.15); }
    .btn-pro-primary:hover { transform: translateY(-2px); box-shadow: 0 12px 25px rgba(15, 23, 42, 0.25); background: var(--gs-dark); }
    .btn-pro-accent { background: var(--gs-accent); color: white !important; box-shadow: 0 8px 20px rgba(16, 185, 129, 0.15); }
    .btn-pro-accent:hover { transform: translateY(-2px); box-shadow: 0 12px 25px rgba(16, 185, 129, 0.25); background: #059669; }
    
    /* Image Wrappers with Logos */
    .hero-img-wrapper { position: relative; border-radius: 24px; overflow: hidden; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.15); }
    .hero-img-wrapper img.main-img { width: 100%; height: auto; transition: transform 0.8s ease; }
    .hero-img-wrapper:hover img.main-img { transform: scale(1.03); }
    .watermark-logo { position: absolute; bottom: 20px; right: 20px; height: 45px; opacity: 0.9; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.2); }

    .pulse-dot { position: absolute; top: 30px; right: 30px; width: 15px; height: 15px; background: #10B981; border-radius: 50%; box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); animation: pulse 2s infinite; }
    @keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); } 70% { box-shadow: 0 0 0 15px rgba(16, 185, 129, 0); } 100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); } }

    /* Infinite Marquee */
    .marquee-container { width: 100%; background: var(--gs-primary); color: white; padding: 20px 0; overflow: hidden; white-space: nowrap; position: relative; display: flex; align-items: center; }
    .marquee-content { display: inline-block; animation: marquee 30s linear infinite; font-family: var(--font-heading); font-weight: 500; font-size: 1.1rem; letter-spacing: 1px; }
    .marquee-content span { margin: 0 40px; color: rgba(255,255,255,0.8); }
    .marquee-content span b { color: #3B82F6; }
    @keyframes marquee { 0% { transform: translateX(0); } 100% { transform: translateX(-50%); } }

    /* Features Section */
    .features-section { padding: 120px 0; }
    .feature-title { font-size: 2.8rem; font-weight: 800; color: var(--gs-primary); margin-bottom: 20px; }
    .feature-subtitle { font-size: 1.2rem; color: var(--gs-slate); margin-bottom: 60px; max-width: 600px; }
    
    .feature-card { background: white; padding: 40px; border-radius: 20px; border: 1px solid rgba(0,0,0,0.05); box-shadow: 0 10px 30px rgba(0,0,0,0.02); transition: all 0.4s ease; height: 100%; }
    .feature-card:hover { transform: translateY(-10px); box-shadow: 0 20px 40px rgba(0,0,0,0.08); border-color: rgba(59,130,246,0.2); }
    .feature-icon { font-size: 2.5rem; color: var(--gs-secondary); margin-bottom: 24px; background: rgba(59,130,246,0.1); width: 80px; height: 80px; display: flex; align-items: center; justify-content: center; border-radius: 20px; }

    /* Live Mockup UI */
    .mockup-container { background: white; border-radius: 24px; padding: 20px; box-shadow: 0 25px 50px rgba(0,0,0,0.1); border: 1px solid rgba(0,0,0,0.05); position: relative; overflow: hidden; }
    .mockup-header { display: flex; justify-content: space-between; align-items: center; padding-bottom: 15px; border-bottom: 1px solid #f1f5f9; margin-bottom: 15px; }
    .mockup-title { font-weight: 700; font-family: var(--font-heading); }
    .mockup-item { display: flex; align-items: center; justify-content: space-between; padding: 12px; border-radius: 12px; background: #f8fafc; margin-bottom: 10px; animation: slideUp 0.5s ease-out backwards; }
    .mockup-item:nth-child(2) { animation-delay: 0.2s; }
    .mockup-item:nth-child(3) { animation-delay: 0.4s; }
    @keyframes slideUp { 0% { opacity: 0; transform: translateY(20px); } 100% { opacity: 1; transform: translateY(0); } }
    .btn-mockup { background: #10B981; color: white; border: none; padding: 6px 16px; border-radius: 20px; font-size: 0.8rem; font-weight: 600; animation: pulseBtn 2s infinite; }
    @keyframes pulseBtn { 0% { transform: scale(1); } 50% { transform: scale(1.05); } 100% { transform: scale(1); } }
    
    .tech-image { width: 100%; }
    
    /* Developer Portfolio Section */
    .portfolio-section { background: var(--gs-primary); color: white; padding: 60px 0; text-align: center; }
    .portfolio-link { color: var(--gs-secondary); text-decoration: none; font-weight: 700; transition: color 0.3s; font-size: 1.1rem; }
    .portfolio-link:hover { color: white; text-decoration: underline; }
</style>
{% endblock %}

{% block content %}
<div class="bg-animation"></div>

<!-- Navbar -->
<nav class="navbar navbar-expand-lg navbar-light fixed-top landing-nav">
    <div class="container">
        <a class="navbar-brand gs-brand-v3" href="{% url 'landing_page' %}">
            <img src="{% static 'images/GroupSathi.png' %}" alt="Logo" style="height: 40px; margin-right: 12px; border-radius: 12px;">
            <span class="gs-brand-v3">GroupSathi</span>
        </a>
        <button class="navbar-toggler border-0 shadow-none" type="button" data-bs-toggle="collapse" data-bs-target="#landingNavCollapse">
            <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="landingNavCollapse">
            <div class="ms-auto d-flex flex-column flex-lg-row gap-3 mt-3 mt-lg-0 align-items-lg-center">
                <a href="{% url 'download_apk' %}" class="btn btn-pro btn-pro-accent"><i class="bi bi-download me-2"></i>Download App</a>
                <a href="{% url 'login' %}" class="btn btn-pro" style="color: var(--gs-primary); border: 2px solid var(--gs-slate);">Login</a>
                <a href="{% url 'register' %}" class="btn btn-pro btn-pro-primary">Join Now</a>
            </div>
        </div>
    </div>
</nav>

<!-- Hero Section -->
<section class="hero-v3">
    <div class="container">
        <div class="row align-items-center">
            <div class="col-lg-6" data-aos="fade-right" data-aos-duration="1000">
                <div class="badge bg-primary bg-opacity-10 text-primary px-3 py-2 rounded-pill mb-4 fw-bold">🚀 Revolutionizing Rural Microfinance</div>
                <h1 class="hero-title-v3">Empowering <span>Self Help Groups</span> with Digital Ledgers</h1>
                <p class="hero-desc">GroupSathi replaces traditional paper logbooks with a 100% transparent, consensus-driven digital ecosystem. Manage loans, automate EMI tracking, and empower rural women to achieve financial independence.</p>
                <div class="d-flex flex-wrap gap-3 mt-4">
                    <a href="{% url 'register' %}" class="btn btn-pro btn-pro-primary px-4 py-3 fs-5">Get Started for Free <i class="bi bi-arrow-right ms-2"></i></a>
                    <a href="{% url 'download_apk' %}" class="btn btn-pro btn-pro-accent px-4 py-3 fs-5"><i class="bi bi-android2 me-2"></i>Download APK</a>
                </div>
            </div>
            <div class="col-lg-6 mt-5 mt-lg-0" data-aos="fade-left" data-aos-duration="1200" data-aos-delay="200">
                <div class="hero-img-wrapper">
                    <div class="pulse-dot"></div>
                    <img src="{% static 'images/shg_meeting.png' %}" alt="Rural women SHG meeting" class="main-img img-fluid">
                    <img src="{% static 'images/GroupSathi.png' %}" alt="GroupSathi Logo" class="watermark-logo">
                </div>
            </div>
        </div>
    </div>
</section>

<!-- Infinite Marquee -->
<div class="marquee-container">
    <div class="marquee-content">
        <span><b>LIVE:</b> Automated EMI Tracking Active</span>
        <span>100% Transparent Financial Ledgers</span>
        <span>Empowering Rural India Digitally</span>
        <span>Zero Hidden Fees</span>
        <span>Consensus-Driven Group Approvals</span>
        <span>AI-Powered Support Assistant</span>
        
        <!-- Duplicate for infinite loop -->
        <span><b>LIVE:</b> Automated EMI Tracking Active</span>
        <span>100% Transparent Financial Ledgers</span>
        <span>Empowering Rural India Digitally</span>
        <span>Zero Hidden Fees</span>
        <span>Consensus-Driven Group Approvals</span>
        <span>AI-Powered Support Assistant</span>
    </div>
</div>

<!-- Detailed Platform Description -->
<section class="features-section bg-white">
    <div class="container">
        <div class="text-center mb-5" data-aos="fade-up">
            <h2 class="feature-title">Complete Financial Inclusion</h2>
            <p class="feature-subtitle mx-auto">GroupSathi isn't just an app; it's a movement. We bring enterprise-grade financial transparency to the heart of rural India.</p>
        </div>
        
        <div class="row align-items-center mb-5">
            <div class="col-lg-6 order-lg-2 mb-5 mb-lg-0" data-aos="fade-left">
                <div class="hero-img-wrapper">
                    <img src="{% static 'images/rural_digital.png' %}" alt="Digital Technology in Rural India" class="main-img tech-image img-fluid">
                    <img src="{% static 'images/GroupSathi.png' %}" alt="GroupSathi Logo" class="watermark-logo">
                </div>
            </div>
            <div class="col-lg-6 order-lg-1 pe-lg-5" data-aos="fade-right">
                <h3 class="fw-bold mb-4">Digitizing Paper Logbooks</h3>
                <p class="text-muted fs-5 lh-lg mb-4">For decades, Self Help Groups have relied on vulnerable paper ledgers. GroupSathi brings these records into the digital age, ensuring that every contribution, loan disbursement, and fine is securely recorded and instantly visible to all members.</p>
                <ul class="list-unstyled lh-lg">
                    <li><i class="bi bi-check-circle-fill text-success me-2"></i> <strong>Immutable Records:</strong> No more lost or tampered logbooks.</li>
                    <li><i class="bi bi-check-circle-fill text-success me-2"></i> <strong>Instant Synchronization:</strong> Everyone sees the group balance in real-time.</li>
                    <li><i class="bi bi-check-circle-fill text-success me-2"></i> <strong>Automated Calculations:</strong> Complex interest rates are handled automatically by the system.</li>
                </ul>
            </div>
        </div>
        
        <div class="row mt-5">
            <div class="col-md-4 mb-4" data-aos="fade-up" data-aos-delay="100">
                <div class="feature-card">
                    <div class="feature-icon"><i class="bi bi-people-fill"></i></div>
                    <h4>Consensus Approvals</h4>
                    <p class="text-muted mt-3">Democracy is built into the code. Loan requests and fine waivers require a majority vote from active group members before they are processed. No single leader holds absolute financial power.</p>
                </div>
            </div>
            <div class="col-md-4 mb-4" data-aos="fade-up" data-aos-delay="200">
                <div class="feature-card">
                    <div class="feature-icon"><i class="bi bi-bell-fill"></i></div>
                    <h4>Live Notifications</h4>
                    <p class="text-muted mt-3">Stay informed the second a transaction occurs. Whether an EMI is due or a member has requested a loan extension, instant alerts keep the entire group aligned and responsible.</p>
                </div>
            </div>
            <div class="col-md-4 mb-4" data-aos="fade-up" data-aos-delay="300">
                <div class="feature-card">
                    <div class="feature-icon"><i class="bi bi-robot"></i></div>
                    <h4>AI Support Assistant</h4>
                    <p class="text-muted mt-3">Integrated Gemini AI is available 24/7 to answer questions, guide users through the app, and summarize complex administrative broadcasts, bridging the digital literacy gap.</p>
                </div>
            </div>
        </div>
    </div>
</section>

<!-- Live UI Mockup Simulation -->
<section class="section-spacing bg-light">
    <div class="container">
        <div class="row align-items-center">
            <div class="col-lg-5 mb-5 mb-lg-0" data-aos="fade-right">
                <h2 class="feature-title">Live Interactive Platform</h2>
                <p class="feature-subtitle">Experience real-time financial tracking. Our interface is designed to be intuitive, ensuring that managing loans is as simple as sending a text message.</p>
                <div class="d-flex flex-wrap gap-3">
                    <a href="{% url 'register' %}" class="btn btn-pro btn-pro-primary rounded-pill px-4 py-2 fw-bold">Explore the Dashboard</a>
                    <a href="{% url 'download_apk' %}" class="btn btn-pro btn-pro-accent rounded-pill px-4 py-2 fw-bold"><i class="bi bi-download me-2"></i>Get the App</a>
                </div>
            </div>
            <div class="col-lg-6 offset-lg-1" data-aos="fade-left">
                <!-- UI Mockup -->
                <div class="mockup-container">
                    <div class="mockup-header">
                        <span class="mockup-title"><i class="bi bi-activity text-primary me-2"></i>Live Loan Approvals</span>
                        <span class="badge bg-primary rounded-pill">Real-time</span>
                    </div>
                    
                    <div class="mockup-item">
                        <div>
                            <strong>Anjali Devi</strong> requested ,15,000<br>
                            <small class="text-muted">Purpose: Agriculture</small>
                        </div>
                        <button class="btn-mockup">Approve</button>
                    </div>
                    
                    <div class="mockup-item">
                        <div>
                            <strong>Priya Sharma</strong> paid EMI ,11,200<br>
                            <small class="text-muted">Status: Verified</small>
                        </div>
                        <span class="badge bg-success"><i class="bi bi-check-circle"></i> Done</span>
                    </div>
                    
                    <div class="mockup-item">
                        <div>
                            <strong>Kavita Singh</strong> requested fine waiver<br>
                            <small class="text-muted">Reason: Medical Emergency</small>
                        </div>
                        <button class="btn-mockup" style="background:#3B82F6;">Vote Now</button>
                    </div>
                </div>
            </div>
        </div>
    </div>
</section>

<!-- Developer Portfolio Section -->
<section class="portfolio-section">
    <div class="container" data-aos="fade-up">
        <h3 class="fw-bold mb-3">Engineered with Precision</h3>
        <p class="mb-4 text-white-50">Designed, developed, and maintained by a passionate full-stack developer dedicated to building impactful digital solutions.</p>
        <a href="https://amankr0075.github.io/FUTURE_FS_01/" target="_blank" rel="noopener noreferrer" class="portfolio-link">
            <i class="bi bi-briefcase me-2"></i>View Developer Portfolio
        </a>
    </div>
</section>

<!-- Footer -->
<footer class="bg-dark text-white py-4 text-center mt-auto">
    <div class="container">
        <div class="d-flex justify-content-center align-items-center mb-3">
            <img src="{% static 'images/GroupSathi.png' %}" alt="Logo" style="height: 30px; margin-right: 10px; border-radius:8px;">
            <h5 class="mb-0 fw-bold">GroupSathi</h5>
        </div>
        <p class="text-muted mb-0">&copy; 2026 GroupSathi. All rights reserved. Empowering rural India.</p>
    </div>
</footer>

{% endblock %}

{% block extra_js %}
<script src="https://unpkg.com/aos@2.3.1/dist/aos.js"></script>
<script>
    // Initialize Animations
    AOS.init({
        once: true,
        offset: 50,
        duration: 800
    });
</script>
{% endblock %}
"""

with open('templates/landing/landing.html', 'w', encoding='utf-8') as f:
    f.write(html_content)
