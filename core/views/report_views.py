"""
Report views for GroupSathi with comprehensive PDF generation.
"""

import io
from datetime import datetime, timedelta
import os
from django.conf import settings
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    PageBreak, HRFlowable, Image
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from core.decorators import login_required_custom
from core.db import get_collection
from core.utils import get_group_balance
from django_ratelimit.decorators import ratelimit


# --- Color Palette ---
PRIMARY_DARK = colors.HexColor('#1a1a2e')
PRIMARY_MID = colors.HexColor('#16213e')
PRIMARY_LIGHT = colors.HexColor('#0f3460')
ACCENT = colors.HexColor('#e94560')
BG_LIGHT = colors.HexColor('#f0f4f8')
BG_ROW_ALT = colors.HexColor('#f5f7fa')
WATERMARK_COLOR = colors.Color(0.85, 0.85, 0.85, alpha=0.35)


# --- Base English Labels (source for translation) ---
_BASE_LABELS = {
    'app_subtitle': 'Smart Management for Self Help Groups',
    'group_code': 'Group Code',
    'report_all': 'Report: All Records',
    'report_from': 'Report Date: From {start}',
    'report_until': 'Report Date: Until {end}',
    'report_range': 'Report Date: {start} to {end}',
    'sec_leaders': 'Group Leaders and Co-Leaders',
    'sec_members': 'All Group Members',
    'sec_financial': 'Financial Summary',
    'sec_emi': 'EMI Payments - Member Wise',
    'sec_loans': 'Loan Details - Complete History',
    'sec_waiver': 'Fine Waiver Requests - Historical Logs',
    'col_no': 'No', 'col_name': 'Name', 'col_member_id': 'Member ID',
    'col_role': 'Role', 'col_joined': 'Joined', 'col_amount': 'Amount',
    'col_date': 'Date', 'col_status': 'Status',
    'col_interest': 'Interest', 'col_remaining': 'Remaining',
    'col_issued': 'Issued', 'col_completed': 'Completed',
    'col_reason': 'Reason', 'col_requested': 'Date Requested',
    'col_borrower': 'Borrower',
    'lbl_members': 'Total Members', 'lbl_emi': 'Monthly EMI',
    'lbl_interest_rate': 'Interest Rate', 'lbl_fine': 'Late Fine per Month',
    'lbl_emi_collected': 'Total EMI Collected', 'lbl_int_collected': 'Total Interest Collected',
    'lbl_late_fine': 'Total Late Fine', 'lbl_pend_int': 'Pending Interest',
    'lbl_balance': 'Final Amount in Group',
    'no_emi': 'No EMI payments recorded.',
    'no_loans': 'No loan records found for the selected period.',
    'no_waiver': 'No fine waiver requests recorded for the selected period.',
    'generated': 'Generated on {dt} | GroupSathi 2026',
    'page': 'Page {n}',
    'header': 'GroupSathi - Smart Management for Self Help Groups',
}


def _get_labels(lang_code):
    """Return English labels to ensure standard PDF font compatibility (no broken characters)."""
    lbl = dict(_BASE_LABELS)
    lbl['generated'] = 'Generated on {dt} | GroupSathi \u00a9 2026'
    lbl['header'] = 'GroupSathi \u2014 Smart Management for Self Help Groups'
    lbl['sec_emi'] = 'EMI Payments \u2014 Member Wise'
    lbl['sec_loans'] = 'Loan Details \u2014 Complete History'
    lbl['sec_waiver'] = 'Fine Waiver Requests \u2014 Historical Logs'
    lbl['sec_leaders'] = 'Group Leaders & Co-Leaders'
    lbl['col_no'] = '#'
    return lbl



def _make_watermark_footer(lbl):
    """Return a canvas callback that draws watermark + header/footer using given labels."""
    def _draw(canvas, doc):
        from django.conf import settings
        import os
        
        # --- Watermark Image (Top Right) ---
        canvas.saveState()
        logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'GroupSathi.png')
        if os.path.exists(logo_path):
            try:
                # Draw the logo at the top right so it doesn't obscure the table data
                canvas.drawImage(logo_path, A4[0] - 80, A4[1] - 80, width=50, height=50, mask='auto')
            except Exception:
                pass
        canvas.restoreState()

        # --- Text Watermark (Centered & Faint) ---
        canvas.saveState()
        canvas.translate(A4[0] / 2, A4[1] / 2)
        canvas.setFont('Helvetica-Bold', 65)
        canvas.setFillColor(WATERMARK_COLOR)
        canvas.rotate(35)
        canvas.drawCentredString(0, 0, "GroupSathi")
        canvas.restoreState()

        # --- Header ---
        canvas.saveState()
        canvas.setStrokeColor(ACCENT)
        canvas.setLineWidth(2)
        canvas.line(40, A4[1] - 35, A4[0] - 40, A4[1] - 35)
        canvas.setFont('Helvetica-Bold', 8)
        canvas.setFillColor(PRIMARY_DARK)
        canvas.drawString(40, A4[1] - 30, lbl['header'])
        canvas.restoreState()

        # --- Footer ---
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor('#cccccc'))
        canvas.setLineWidth(0.5)
        # Raised the line to fit 3 lines of text
        canvas.line(40, 50, A4[0] - 40, 50)
        
        canvas.setFont('Helvetica', 7)
        canvas.setFillColor(colors.grey)
        
        # Line 1: Timestamp & Page number
        timestamp_str = lbl['generated'].format(dt=datetime.now().strftime('%d/%m/%Y %H:%M:%S'))
        canvas.drawString(40, 38, timestamp_str)
        canvas.drawRightString(A4[0] - 40, 38, lbl['page'].format(n=canvas.getPageNumber()))
        
        # Line 2: Disclaimer
        disclaimer = "DISCLAIMER: This is a system generated report and it does not require any physical signature of GroupSathi."
        canvas.drawCentredString(A4[0] / 2, 26, disclaimer)
        
        # Line 3: Privacy Policy & Terms
        policies = "By using GroupSathi, you agree to our Privacy Policy and Terms & Conditions."
        canvas.drawCentredString(A4[0] / 2, 14, policies)
        
        canvas.restoreState()
    return _draw


def _heading(text, styles):
    """Return a styled section heading paragraph."""
    style = ParagraphStyle(
        'SectionHead', parent=styles['Heading2'],
        fontSize=13, textColor=PRIMARY_DARK,
        spaceBefore=14, spaceAfter=6,
        borderPadding=(0, 0, 4, 0),
    )
    return Paragraph(f"<b>{text}</b>", style)


def _std_table_style(has_header=True):
    """Return a reusable professional table style."""
    base = [
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#d0d0d0')),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]
    if has_header:
        base += [
            ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_DARK),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8.5),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, BG_ROW_ALT]),
        ]
    return TableStyle(base)


@login_required_custom
def reports_view(request):
    """Show report options for user's groups."""
    user_id = request.session['user_id']
    gm = get_collection('group_members')
    groups_col = get_collection('groups')
    memberships = list(gm.find({'user_id': user_id, 'status': 'active'}))
    user_groups = []
    for m in memberships:
        g = groups_col.find_one({'group_id': m['group_id']})
        if g:
            user_groups.append(g)
    return render(request, 'reports/reports.html', {'user_groups': user_groups})


@login_required_custom
@ratelimit(key='ip', rate='10/h', block=True)
def generate_report_pdf(request, group_id):
    """Generate a comprehensive PDF report for a group filtered by date."""
    user_id = request.session['user_id']
    gm = get_collection('group_members')
    membership = gm.find_one({'group_id': group_id, 'user_id': user_id, 'status': 'active'})
    if not membership:
        messages.error(request, 'Access denied.')
        return redirect('reports')

    groups = get_collection('groups')
    group = groups.find_one({'group_id': group_id})
    if not group:
        messages.error(request, 'Group not found.')
        return redirect('reports')

    # Parse filter dates from query params
    from_date_str = request.GET.get('from_date', '')
    to_date_str = request.GET.get('to_date', '')
    lang = request.GET.get('lang', 'en')
    lbl = _get_labels(lang)

    date_start = None
    date_end = None
    
    if from_date_str:
        try:
            date_start = datetime.strptime(from_date_str, '%Y-%m-%d').replace(hour=0, minute=0, second=0, microsecond=0)
        except ValueError:
            pass
            
    if to_date_str:
        try:
            date_end = datetime.strptime(to_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59, microsecond=999999)
        except ValueError:
            pass

    profiles = get_collection('profiles')

    # ── Build PDF ──
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=0.7 * inch, bottomMargin=0.6 * inch,
        leftMargin=0.6 * inch, rightMargin=0.6 * inch,
    )
    styles = getSampleStyleSheet()
    elements = []

    # ── Title Section ──
    app_title_style = ParagraphStyle(
        'AppTitle', parent=styles['Title'],
        fontSize=22, textColor=ACCENT, alignment=TA_CENTER,
        spaceAfter=2,
    )
    group_title_style = ParagraphStyle(
        'GroupTitle', parent=styles['Title'],
        fontSize=16, textColor=PRIMARY_DARK, alignment=TA_CENTER,
        spaceAfter=2,
    )
    sub_style = ParagraphStyle(
        'SubInfo', parent=styles['Normal'],
        fontSize=9, textColor=colors.grey, alignment=TA_CENTER,
    )

    logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'GroupSathi.png')
    if os.path.exists(logo_path):
        # Using mask='auto' removes the background color (uses the top-left pixel color as transparent)
        img = Image(logo_path, width=1.8*inch, height=1.8*inch, mask='auto')
        img.hAlign = 'CENTER'
        elements.append(img)
        elements.append(Spacer(1, 0.1 * inch))
    else:
        elements.append(Paragraph("GroupSathi", app_title_style))
        elements.append(Paragraph("Smart Management for Self Help Groups", sub_style))
        elements.append(Spacer(1, 0.15 * inch))

    elements.append(HRFlowable(width="100%", thickness=1.5, color=ACCENT))
    elements.append(Spacer(1, 0.15 * inch))
    elements.append(Paragraph(f"{group['name']}", group_title_style))
    elements.append(Paragraph(f"{lbl['group_code']}: <b>{group['group_id']}</b>", sub_style))

    if date_start and date_end:
        elements.append(Paragraph(f"<b>{lbl['report_range'].format(start=date_start.strftime('%d %b %Y'), end=date_end.strftime('%d %b %Y'))}</b>", sub_style))
    elif date_start:
        elements.append(Paragraph(f"<b>{lbl['report_from'].format(start=date_start.strftime('%d %b %Y'))}</b>", sub_style))
    elif date_end:
        elements.append(Paragraph(f"<b>{lbl['report_until'].format(end=date_end.strftime('%d %b %Y'))}</b>", sub_style))
    else:
        elements.append(Paragraph(lbl['report_all'], sub_style))
    elements.append(Spacer(1, 0.25 * inch))

    # ── Section 1: Group Leaders & Co-Leaders ──
    elements.append(_heading(lbl['sec_leaders'], styles))
    leaders = list(gm.find({'group_id': group_id, 'status': 'active', 'role': {'$in': ['leader', 'co-leader']}}))
    leader_data = [[lbl['col_no'], lbl['col_name'], lbl['col_member_id'], lbl['col_role'], lbl['col_joined']]]
    for i, m in enumerate(leaders, 1):
        p = profiles.find_one({'user_id': m['user_id']})
        name = p.get('full_name', 'N/A') if p else 'N/A'
        mid = p.get('member_id', 'N/A') if p else 'N/A'
        joined = m.get('joined_at', '').strftime('%d/%m/%Y') if m.get('joined_at') else 'N/A'
        leader_data.append([str(i), name, mid, m.get('role', '').title(), joined])
    t_leaders = Table(leader_data, colWidths=[0.4*inch, 2.2*inch, 1.1*inch, 1.1*inch, 1.2*inch])
    t_leaders.setStyle(_std_table_style())
    elements.append(t_leaders)
    elements.append(Spacer(1, 0.25*inch))

    # ── Section 2: All Group Members ──
    elements.append(_heading(lbl['sec_members'], styles))
    all_members = list(gm.find({'group_id': group_id, 'status': 'active'}))
    mem_data = [[lbl['col_no'], lbl['col_name'], lbl['col_member_id'], lbl['col_role'], lbl['col_joined']]]
    for i, m in enumerate(all_members, 1):
        p = profiles.find_one({'user_id': m['user_id']})
        name = p.get('full_name', 'N/A') if p else 'N/A'
        mid = p.get('member_id', 'N/A') if p else 'N/A'
        joined = m.get('joined_at', '').strftime('%d/%m/%Y') if m.get('joined_at') else 'N/A'
        mem_data.append([str(i), name, mid, m.get('role', 'member').title(), joined])
    t_members = Table(mem_data, colWidths=[0.4*inch, 2.2*inch, 1.1*inch, 1.1*inch, 1.2*inch])
    t_members.setStyle(_std_table_style())
    elements.append(t_members)
    elements.append(Spacer(1, 0.25*inch))

    # ── Section 3: Financial Summary ──
    elements.append(_heading(lbl['sec_financial'], styles))
    
    # Calculate extra stats
    txns = get_collection('transactions')
    txn_match = {'group_id': group_id}
    if date_start and date_end:
        txn_match['created_at'] = {'$gte': date_start, '$lte': date_end}
    elif date_start:
        txn_match['created_at'] = {'$gte': date_start}
    elif date_end:
        txn_match['created_at'] = {'$lte': date_end}

    pipeline_emi = [{'$match': {**txn_match, 'type': 'emi_payment'}}, {'$group': {'_id': None, 'total': {'$sum': '$amount'}}}]
    pipeline_int = [{'$match': {**txn_match, 'type': 'interest_payment'}}, {'$group': {'_id': None, 'total': {'$sum': '$amount'}}}]
    
    emi_collected_res = list(txns.aggregate(pipeline_emi))
    total_emi_collected = emi_collected_res[0]['total'] if emi_collected_res else 0.0
    
    int_collected_res = list(txns.aggregate(pipeline_int))
    total_interest_collected = int_collected_res[0]['total'] if int_collected_res else 0.0

    emi_reqs = get_collection('emi_requests')
    emi_reqs_match = {'group_id': group_id, 'status': 'approved'}
    if date_start and date_end:
         emi_reqs_match['created_at'] = {'$gte': date_start, '$lte': date_end}
    elif date_start:
         emi_reqs_match['created_at'] = {'$gte': date_start}
    elif date_end:
         emi_reqs_match['created_at'] = {'$lte': date_end}
    pipeline_fine = [{'$match': emi_reqs_match}, {'$group': {'_id': None, 'total': {'$sum': '$fine_amount'}}}]
    fine_res = list(emi_reqs.aggregate(pipeline_fine))
    total_late_fine = fine_res[0]['total'] if fine_res else 0.0

    loans_col = get_collection('loans')
    loans_match = {'group_id': group_id, 'status': {'$in': ['approved', 'active']}}
    if date_start and date_end:
        loans_match['created_at'] = {'$gte': date_start, '$lte': date_end}
    elif date_start:
         loans_match['created_at'] = {'$gte': date_start}
    elif date_end:
         loans_match['created_at'] = {'$lte': date_end}
         
    pipeline_pend_int = [{'$match': loans_match}, {'$group': {'_id': None, 'total': {'$sum': '$interest_amount'}}}]
    pend_int_res = list(loans_col.aggregate(pipeline_pend_int))
    total_pending_interest = pend_int_res[0]['total'] if pend_int_res else 0.0

    balance = get_group_balance(group_id)
    members_count = len(all_members)
    
    summary_data = [
        [lbl['lbl_members'], str(members_count), lbl['lbl_emi'], f"\u20B9{group['emi_amount']:,.2f}"],
        [lbl['lbl_interest_rate'], f"{group['interest_rate']}%", lbl['lbl_fine'], f"\u20B9{group.get('fine_amount', 0):,.2f}"],
        [lbl['lbl_emi_collected'], f"\u20B9{total_emi_collected:,.2f}", lbl['lbl_int_collected'], f"\u20B9{total_interest_collected:,.2f}"],
        [lbl['lbl_late_fine'], f"\u20B9{total_late_fine:,.2f}", lbl['lbl_pend_int'], f"\u20B9{total_pending_interest:,.2f}"],
        [lbl['lbl_balance'], f"\u20B9{balance:,.2f}", '', '']
    ]
    t_summary = Table(summary_data, colWidths=[1.8 * inch, 1.2 * inch, 1.8 * inch, 1.2 * inch])
    t_summary.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), BG_LIGHT),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#d0d0d0')),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
    ]))
    elements.append(t_summary)
    elements.append(Spacer(1, 0.25 * inch))

    # ── Section 4: EMI Payments by Each Member ──
    elements.append(PageBreak())
    elements.append(_heading(lbl['sec_emi'], styles))

    emi_records = get_collection('emi_records')
    emi_query = {'group_id': group_id}
    if date_start and date_end:
        emi_query['payment_date'] = {'$gte': date_start, '$lt': date_end}

    no_emi_style = ParagraphStyle('NoEmi', parent=styles['Normal'], fontSize=9, textColor=colors.grey)

    for m in all_members:
        p = profiles.find_one({'user_id': m['user_id']})
        member_name = p.get('full_name', 'Unknown') if p else 'Unknown'
        member_emi_query = dict(emi_query)
        member_emi_query['user_id'] = m['user_id']
        member_emis = list(emi_records.find(member_emi_query).sort('payment_date', -1))

        label_style = ParagraphStyle(
            'MemberLabel', parent=styles['Normal'],
            fontSize=9.5, textColor=PRIMARY_MID, spaceBefore=8, spaceAfter=3,
        )
        elements.append(Paragraph(
            f"<b>{member_name}</b> ({m.get('role', 'member').title()})", label_style
        ))

        if member_emis:
            emi_tbl_data = [[lbl['col_no'], lbl['col_amount'], lbl['col_date'], lbl['col_status']]]
            for idx, emi in enumerate(member_emis, 1):
                amt = f"\u20B9{emi.get('amount', 0):,.2f}"
                dt = emi.get('payment_date', '').strftime('%d/%m/%Y') if emi.get('payment_date') else 'N/A'
                status = emi.get('status', 'N/A').title()
                emi_tbl_data.append([str(idx), amt, dt, status])
            t_emi = Table(emi_tbl_data, colWidths=[0.4*inch, 1.8*inch, 1.5*inch, 1.3*inch])
            t_emi.setStyle(_std_table_style())
            elements.append(t_emi)
        else:
            elements.append(Paragraph(lbl['no_emi'], no_emi_style))

        elements.append(Spacer(1, 0.1 * inch))

    # ── Section 5: Loan Details ──
    elements.append(PageBreak())
    elements.append(_heading(lbl['sec_loans'], styles))

    loans_col = get_collection('loans')
    loan_query = {'group_id': group_id}
    if date_start and date_end:
        loan_query['created_at'] = {'$gte': date_start, '$lt': date_end}

    all_loans = list(loans_col.find(loan_query).sort('created_at', -1))

    if all_loans:
        loan_tbl_data = [[lbl['col_no'], lbl['col_borrower'], lbl['col_amount'], lbl['col_interest'], lbl['col_remaining'], lbl['col_status'], lbl['col_issued'], lbl['col_completed']]]
        for idx, loan in enumerate(all_loans, 1):
            p = profiles.find_one({'user_id': loan['user_id']})
            name = p.get('full_name', 'N/A') if p else 'N/A'
            amt = f"\u20B9{loan.get('amount', 0):,.2f}"
            interest = f"\u20B9{loan.get('interest_amount', 0):,.2f}"
            remaining = f"\u20B9{loan.get('remaining_amount', 0):,.2f}"
            status = loan.get('status', 'N/A').title()
            issued = loan.get('created_at', '').strftime('%d/%m/%Y') if loan.get('created_at') else 'N/A'
            completed = loan['updated_at'].strftime('%d/%m/%Y') if loan.get('status') == 'completed' and loan.get('updated_at') else '—'
            loan_tbl_data.append([str(idx), name, amt, interest, remaining, status, issued, completed])
        t_loans = Table(loan_tbl_data, colWidths=[0.35*inch, 1.3*inch, 0.9*inch, 0.85*inch, 0.85*inch, 0.7*inch, 0.75*inch, 0.8*inch])
        t_loans.setStyle(_std_table_style())
        elements.append(t_loans)
    else:
        elements.append(Paragraph(lbl['no_loans'], no_emi_style))

    # ── Section 6: Fine Waiver Requests ──
    elements.append(PageBreak())
    elements.append(_heading(lbl['sec_waiver'], styles))

    fwh = get_collection('fine_waiver_history')
    waiver_query = {'group_id': group_id}
    if date_start and date_end:
        waiver_query['created_at'] = {'$gte': date_start, '$lt': date_end}

    all_waivers = list(fwh.find(waiver_query).sort('created_at', -1))

    if all_waivers:
        waiver_tbl_data = [[lbl['col_no'], lbl['col_name'], lbl['col_reason'], lbl['col_requested'], lbl['col_status']]]
        for idx, wav in enumerate(all_waivers, 1):
            w_member = wav.get('member_name', 'N/A')
            w_reason = wav.get('reason', 'N/A')
            if len(w_reason) > 50:
                w_reason = w_reason[:47] + '...'
            w_date = wav.get('created_at', '').strftime('%d/%m/%Y') if wav.get('created_at') else 'N/A'
            w_status = wav.get('status', 'Pending').title()
            waiver_tbl_data.append([str(idx), w_member, w_reason, w_date, w_status])
        t_waivers = Table(waiver_tbl_data, colWidths=[0.4*inch, 1.7*inch, 2.7*inch, 1.1*inch, 1.1*inch])
        t_waivers.setStyle(_std_table_style())
        elements.append(t_waivers)
    else:
        elements.append(Paragraph(lbl['no_waiver'], no_emi_style))

    # ── Build document ──
    cb = _make_watermark_footer(lbl)
    doc.build(elements, onFirstPage=cb, onLaterPages=cb)
    buf.seek(0)

    safe_name = group['name'].replace(' ', '_')
    if date_start and date_end:
        date_suffix = f"{date_start.strftime('%d_%m_%Y')}_to_{date_end.strftime('%d_%m_%Y')}"
    elif date_start:
        date_suffix = f"From_{date_start.strftime('%d_%m_%Y')}"
    elif date_end:
        date_suffix = f"Until_{date_end.strftime('%d_%m_%Y')}"
    else:
        date_suffix = 'All'
    filename = f"GroupSathi_{safe_name}_{date_suffix}_Report.pdf"

    response = HttpResponse(buf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
def _make_settlement_watermark_footer():
    def watermark_cb(canvas, doc):
        canvas.saveState()
        page_width, page_height = A4
        
        # Watermark
        canvas.setFont('Helvetica-Bold', 45)
        canvas.setStrokeColorRGB(0.9, 0.9, 0.9)
        canvas.setFillColorRGB(0.92, 0.92, 0.92)
        canvas.translate(page_width/2, page_height/2)
        canvas.rotate(45)
        canvas.drawCentredString(0, 0, "GROUPSATHI SETTLEMENT")
        canvas.restoreState()
        
        # Footer Disclaimer
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.gray)
        disclaimer = (
            "This report is generated by system and does not require any physical signature of GroupSathi. "
            "This report will be verified by group leaders,"
        )
        disclaimer2 = "and all reports are calculated based on the transaction only."
        canvas.drawCentredString(page_width/2, 0.6 * inch, disclaimer)
        canvas.drawCentredString(page_width/2, 0.45 * inch, disclaimer2)
        canvas.restoreState()
    return watermark_cb


@login_required_custom
@ratelimit(key='ip', rate='10/h', block=True)
def generate_settlement_pdf(request, group_id):
    """Generate a settlement distribution plan PDF."""
    user_id = request.session['user_id']
    groups = get_collection('groups')
    group = groups.find_one({'group_id': group_id})
    if not group:
        messages.error(request, 'Group not found.')
        return redirect('my_groups')

    gm = get_collection('group_members')
    membership = gm.find_one({'group_id': group_id, 'user_id': user_id, 'status': 'active'})
    if not membership:
        messages.error(request, 'Access denied.')
        return redirect('my_groups')

    from core.utils import calculate_settlement_plan
    plan_data_res = calculate_settlement_plan(group_id)
    if not plan_data_res:
        messages.error(request, 'Unable to calculate settlement plan.')
        return redirect('group_detail', group_id=group_id)
        
    total_cash = plan_data_res['total_cash']
    group_profit = plan_data_res['group_profit']
    total_group_contributions = plan_data_res['total_group_contributions']
    total_final_payout = plan_data_res['total_final_payout']
    member_plans = plan_data_res['member_plans']

    # Build PDF
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=0.7 * inch, bottomMargin=1.0 * inch,
        leftMargin=0.6 * inch, rightMargin=0.6 * inch,
    )
    styles = getSampleStyleSheet()
    elements = []

    app_title_style = ParagraphStyle(
        'AppTitle', parent=styles['Title'],
        fontSize=22, textColor=ACCENT, alignment=TA_CENTER, spaceAfter=2,
    )
    group_title_style = ParagraphStyle(
        'GroupTitle', parent=styles['Title'],
        fontSize=16, textColor=PRIMARY_DARK, alignment=TA_CENTER, spaceAfter=2,
    )
    sub_style = ParagraphStyle(
        'SubInfo', parent=styles['Normal'],
        fontSize=9, textColor=colors.grey, alignment=TA_CENTER,
    )

    logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'GroupSathi.png')
    if os.path.exists(logo_path):
        img = Image(logo_path, width=1.8*inch, height=1.8*inch, mask='auto')
        img.hAlign = 'CENTER'
        elements.append(img)
        elements.append(Spacer(1, 0.1 * inch))
    else:
        elements.append(Paragraph("GroupSathi", app_title_style))
        elements.append(Paragraph("Empowering Self Help Groups with Digital Ledgers", sub_style))
        elements.append(Spacer(1, 0.15 * inch))

    elements.append(HRFlowable(width="100%", thickness=1.5, color=ACCENT))
    elements.append(Spacer(1, 0.15 * inch))
    elements.append(Paragraph(f"{group['name']} - Settlement Report", group_title_style))
    elements.append(Paragraph(f"Group ID: <b>{group['group_id']}</b> | Date: <b>{datetime.now().strftime('%d %b %Y')}</b>", sub_style))
    elements.append(Spacer(1, 0.25 * inch))

    # Summary
    summary_data = [
        ['Total Cash Available', f"Rs. {total_cash:,.2f}"],
        ['Distributable Profit', f"Rs. {group_profit:,.2f}"],
        ['Total Paid Contributions', f"Rs. {total_group_contributions:,.2f}"],
        ['Total Final Payout', f"Rs. {total_final_payout:,.2f}"]
    ]
    t_summary = Table(summary_data, colWidths=[3*inch, 2*inch])
    t_summary.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8f9fa')),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor('#333333')),
        ('ALIGN', (0,0), (0,-1), 'LEFT'),
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#dee2e6')),
    ]))
    elements.append(t_summary)
    elements.append(Spacer(1, 0.25 * inch))

    # Formula
    formula_style = ParagraphStyle('Formula', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#0d6efd'))
    elements.append(Paragraph("<b>Calculations (Single-Pass Deterministic):</b>", formula_style))
    elements.append(Paragraph("1. Member Contribution = Total EMI/contributions actually paid", formula_style))
    elements.append(Paragraph("2. Group Profit = Only collected interest + collected fines", formula_style))
    elements.append(Paragraph("3. Profit Share = Group Profit * (Member Contribution / Total Group Contributions)", formula_style))
    elements.append(Paragraph("4. Net Payout = max(0, Contribution + Profit Share - Deductions)", formula_style))
    elements.append(Spacer(1, 0.25 * inch))

    # Member Plan Table
    plan_data = [['Member Name', 'Contribution', 'Profit Share', 'Gross Settl.', 'Deductions', 'Net Payout']]
    for p in member_plans:
        payout_str = f"+Rs. {p['final_payout']:,.2f}" if p['final_payout'] > 0 else "Rs. 0.00"
        if p['remaining_due'] > 0:
            payout_str = f"Owes Rs. {p['remaining_due']:,.2f}"
            
        plan_data.append([
            f"{p['name']} ({p['role'].title()})",
            f"Rs. {p['paid_contribution']:,.2f}",
            f"Rs. {p['profit_share']:,.2f}",
            f"Rs. {p['gross_settlement']:,.2f}",
            f"-Rs. {p['total_deduction']:,.2f}" if p['total_deduction'] > 0 else "Rs. 0.00",
            payout_str
        ])
    
    t_plan = Table(plan_data, colWidths=[1.8*inch, 1.0*inch, 1.0*inch, 1.1*inch, 1.1*inch, 1.0*inch])
    t_plan.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_DARK),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
    ]))
    elements.append(t_plan)

    cb = _make_settlement_watermark_footer()
    doc.build(elements, onFirstPage=cb, onLaterPages=cb)
    buf.seek(0)

    safe_name = group['name'].replace(' ', '_')
    filename = f"GroupSathi_{safe_name}_Settlement_Report.pdf"

    response = HttpResponse(buf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
