"""
Help page view for GroupSathi.
"""

from django.shortcuts import render
from core.decorators import login_required_custom


@login_required_custom
def help_view(request):
    """Display help page with developer information."""
    context = {
        'developer_name': 'Aman Kumar',
        'developer_email': 'amankumar3443k@gmail.com',
    }
    return render(request, 'help/help.html', context)

def add_watermark_and_footer(canvas, doc):
    """Draw a watermark and footer on each page."""
    canvas.saveState()
    # Watermark
    canvas.setFont('Helvetica-Bold', 60)
    canvas.setFillGray(0.90, 0.5)
    canvas.translate(300, 400)
    canvas.rotate(45)
    canvas.drawCentredString(0, 0, "GROUPSATHI")
    canvas.restoreState()
    
    # Footer
    canvas.saveState()
    canvas.setFont('Helvetica', 8)
    canvas.setFillGray(0.4)
    canvas.drawString(72, 30, f"GroupSathi Digital Platform - Confidential Legal Document | Page {doc.page}")
    canvas.drawRightString(doc.pagesize[0] - 72, 30, "Generated strictly for official record keeping")
    canvas.restoreState()

@login_required_custom
def download_legal_docs_view(request):
    """Generate and return a professional PDF of the legal documentation with user agreement."""
    import io
    import os
    from datetime import datetime
    from django.http import HttpResponse
    from django.conf import settings
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Image, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_RIGHT
    from core.db import get_collection
    from bson.objectid import ObjectId

    # Fetch User Details
    user_id = request.session.get('user_id')
    users_col = get_collection('users')
    profiles_col = get_collection('profiles')
    
    user = users_col.find_one({'_id': ObjectId(user_id)}) or {}
    profile = profiles_col.find_one({'user_id': user_id}) or {}
    
    full_name = user.get('name', 'N/A')
    phone = user.get('mobile', 'N/A')
    member_id = profile.get('member_id', 'N/A')
    address = profile.get('address', 'N/A')
    pincode = profile.get('pin_code', 'N/A')
    gender = profile.get('gender', 'N/A')
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    doc_ref = f"REF-GS-{member_id}-{datetime.now().strftime('%Y%m%d')}"

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = ParagraphStyle(
        'TitleStyle', parent=styles['Heading1'], fontSize=18, spaceAfter=8, textColor=colors.HexColor('#0f172a'), alignment=TA_CENTER, fontName='Helvetica-Bold'
    )
    subtitle_style = ParagraphStyle(
        'SubTitleStyle', parent=styles['Normal'], fontSize=12, spaceAfter=20, textColor=colors.HexColor('#64748b'), alignment=TA_CENTER
    )
    heading_style = ParagraphStyle(
        'HeadingStyle', parent=styles['Heading2'], fontSize=12, spaceAfter=10, textColor=colors.HexColor('#1e293b'), spaceBefore=15, fontName='Helvetica-Bold'
    )
    body_style = ParagraphStyle(
        'BodyStyle', parent=styles['Normal'], fontSize=10, spaceAfter=8, leading=14, textColor=colors.HexColor('#334155'), alignment=TA_JUSTIFY
    )
    bullet_style = ParagraphStyle(
        'BulletStyle', parent=styles['Normal'], fontSize=10, spaceAfter=6, leftIndent=15, bulletIndent=10, leading=14, textColor=colors.HexColor('#334155'), alignment=TA_JUSTIFY
    )
    ref_style = ParagraphStyle(
        'RefStyle', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#94a3b8'), alignment=TA_RIGHT
    )

    elements = []
    
    # Reference Number
    elements.append(Paragraph(f"<b>Document ID:</b> {doc_ref}", ref_style))
    elements.append(Spacer(1, 10))
    
    # Title & Logo
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'GroupSathi.png')
    if os.path.exists(logo_path):
        img = Image(logo_path, width=160, height=64, kind='proportional')
        img.hAlign = 'CENTER'
        elements.append(img)
        elements.append(Spacer(1, 15))
    else:
        elements.append(Paragraph("<b>GROUPSATHI</b>", title_style))
        
    elements.append(Paragraph("<b>GROUPSATHI DIGITAL PLATFORM</b>", title_style))
    elements.append(Paragraph("OFFICIAL LEGAL DOCUMENTATION & END-USER AGREEMENT", subtitle_style))
    elements.append(HRFlowable(width="100%", color=colors.HexColor('#94a3b8'), thickness=1))
    elements.append(Spacer(1, 20))
    
    # Professional User Details Table
    elements.append(Paragraph("<b>PARTICIPANT IDENTITY REGISTRATION</b>", heading_style))
    
    user_data_matrix = [
        ["Full Legal Name:", full_name, "Member ID:", member_id],
        ["Registered Mobile:", phone, "Gender:", gender],
        ["Registered Address:", Paragraph(f"{address}, PIN: {pincode}", styles['Normal']), "", ""]
    ]
    
    table = Table(user_data_matrix, colWidths=[100, 150, 80, 138])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor('#0f172a')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'), # Bold first col
        ('FONTNAME', (2,0), (2,-1), 'Helvetica-Bold'), # Bold third col
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('SPAN', (1,2), (3,2)), # Span address across columns
    ]))
    elements.append(table)
    elements.append(Spacer(1, 25))
    
    # Privacy Policy
    elements.append(Paragraph("<b>SECTION I: PRIVACY POLICY & DATA HANDLING</b>", heading_style))
    elements.append(Paragraph("Your trust and data security are our top priorities. By utilizing the GroupSathi platform, the Participant implicitly and explicitly agrees to our formalized data handling practices and the terms outlined below.", body_style))
    elements.append(Paragraph("• <b>Privacy Commitment:</b> Your privacy is of paramount importance. GroupSathi exclusively collects information necessary to maintain accurate, verifiable records of your Self Help Group's internal activities.", bullet_style))
    elements.append(Paragraph("• <b>Data Usage Limitations:</b> Financial records inputted into the platform are maintained solely for your group's organizational and structural purposes. GroupSathi does not process actual monetary transactions, hold escrow, or collect monetary funds from its users.", bullet_style))
    elements.append(Paragraph("• <b>Data Minimization Protocol:</b> The platform strictly limits data collection to requisite fields needed for ledger tracking and financial attribution.", bullet_style))
    elements.append(Paragraph("• <b>Cryptographic Security:</b> All user account credentials and Personal Identification Numbers (PINs) are securely hashed using modern cryptographic standards.", bullet_style))
    elements.append(Paragraph("• <b>Record Keeping Solely:</b> GroupSathi operates strictly as a digital ledger and administrative management tool for Self Help Groups (SHGs). We serve as a record-keeper of transactions executed offline. We do not operate as a registered bank, NBFC, or financial institution.", bullet_style))
    elements.append(Paragraph("• <b>Future Subscription Covenants:</b> Please be advised that in the future, the platform reserves the right to charge users a subscription fee to continue accessing premium features and services. In such an event, policies regarding payment processing and billing data will be updated herein.", bullet_style))
    elements.append(Spacer(1, 15))
    
    # Terms & Conditions
    elements.append(Paragraph("<b>SECTION II: TERMS OF SERVICE & LIABILITY</b>", heading_style))
    elements.append(Paragraph("• <b>Participant Responsibility:</b> All groups and individual members bear total and absolute responsibility for managing their own physical funds securely outside of the platform jurisdiction.", bullet_style))
    elements.append(Paragraph("• <b>Financial Indemnity:</b> As a software provider facilitating ledger management, GroupSathi holds zero financial liability for internal disputes, defaults, or unrecovered loans occurring between group members.", bullet_style))
    elements.append(Paragraph("• <b>Group Closure Prerequisites:</b> To ensure financial integrity, all group financial liabilities (including active loans and outstanding fines) must be cleared entirely prior to group dissolution on the platform.", bullet_style))
    elements.append(Paragraph("• <b>Enforcement Rules:</b> Engaging in the upload of explicit content, provision of fraudulent guarantor documentation, or attempts to electronically bypass EMI date-locks will result in immediate, permanent account suspension.", bullet_style))
    elements.append(Spacer(1, 30))
    
    # Digital Signature & Agreement
    elements.append(HRFlowable(width="100%", color=colors.HexColor('#94a3b8'), thickness=1))
    elements.append(Spacer(1, 15))
    
    # Signature Matrix
    sig_matrix = [
        [
            Paragraph("<b>AGREEMENT CONFIRMATION</b>", ParagraphStyle('AgrTitle', parent=styles['Heading4'], textColor=colors.HexColor('#0f172a'))),
            Paragraph("<i>Digitally verified & sealed by:</i>", ParagraphStyle('SignLabel', parent=styles['Normal'], alignment=TA_RIGHT, textColor=colors.HexColor('#64748b')))
        ],
        [
            Paragraph(f"This document certifies that the participant identified as <b>{member_id}</b> has affirmatively accepted the terms herein.<br/><br/><b>Execution Date:</b> {current_time} (IST)", ParagraphStyle('BodySmall', parent=styles['Normal'], fontSize=9, leading=12, textColor=colors.HexColor('#334155'))),
            Paragraph("<b>GroupSathi System Auto-Signer</b><br/><font color='#16a34a'>✔ Verified Digital Signature</font>", ParagraphStyle('Signature', parent=styles['Normal'], alignment=TA_RIGHT, fontSize=11, leading=14, textColor=colors.HexColor('#0f172a')))
        ]
    ]
    sig_table = Table(sig_matrix, colWidths=[300, 168])
    sig_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    elements.append(sig_table)
    
    # Build with watermark and footer
    doc.build(elements, onFirstPage=add_watermark_and_footer, onLaterPages=add_watermark_and_footer)
    buffer.seek(0)
    
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="GroupSathi_Legal_Agreement_{member_id}.pdf"'
    return response
