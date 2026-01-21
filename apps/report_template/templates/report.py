def get_report_template_string():
    return """
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{report_title}}</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        @page {
            size: A4;
            margin: 0;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            font-size: 10pt;
            line-height: 1.4;
            color: #222222;
            background: #FFFFFF;
            margin: 3mm;
            padding: 0;
        }

        .header {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            margin-bottom: 12px;
            padding: 10px 12px;
            background: #1a3a6b;
            border-radius: 0;
            box-shadow: none;
            border-bottom: 3px solid #2A4F8F;
        }

        .header-left {
            display: flex;
            align-items: center;
            flex: 1;
        }

        .header-logo {
            background: white;
            padding: 6px;
            border-radius: 0;
            box-shadow: none;
            margin-right: 12px;
            border: 1px solid #ffffff;
        }

        .header-logo img {
            max-width: 50px;
            max-height: 50px;
            display: block;
        }

        .header-info {
            flex: 1;
        }

        .clinic-name {
            font-size: 16pt;
            font-weight: bold;
            color: #ffffff;
            margin-bottom: 4px;
            text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
        }

        .clinic-details {
            font-size: 8.5pt;
            color: #e8f0ff;
            line-height: 1.4;
        }

        .clinic-details div {
            margin-bottom: 1px;
            display: flex;
            align-items: center;
        }

        .clinic-details strong {
            color: #ffffff;
            min-width: 60px;
            font-weight: 600;
        }

        .header-right {
            background: rgba(255, 255, 255, 0.98);
            padding: 10px;
            border-radius: 0;
            text-align: center;
            min-width: 110px;
            box-shadow: none;
            border: 1px solid #ffffff;
        }

        .report-id {
            font-size: 8.5pt;
            color: #444444;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 5px;
        }

        .report-id-value {
            font-size: 11pt;
            color: #222222;
            font-weight: bold;
            font-family: 'Courier New', monospace;
        }

        .report-date {
            font-size: 9pt;
            color: #444444;
            margin-top: 8px;
            padding-top: 8px;
            border-top: 1px solid #CCCCCC;
        }

        .report-title {
            text-align: center;
            font-size: 14pt;
            font-weight: bold;
            color: #222222;
            margin: 12px 0 10px 0;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            position: relative;
            padding-bottom: 6px;
        }

        .report-title::after {
            content: '';
            position: absolute;
            bottom: 0;
            left: 50%;
            transform: translateX(-50%);
            width: 80px;
            height: 3px;
            background: #2A4F8F;
            border-radius: 2px;
        }

        .patient-info {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 0;
            margin-bottom: 12px;
            border: 1px solid #2A4F8F;
            border-radius: 0;
            background: #FFFFFF;
            overflow: hidden;
        }

        .patient-name-container {
            grid-column: 1 / -1;
            padding: 6px 12px;
            background: #E8EEF7;
            border-bottom: 1px solid #2A4F8F;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .patient-name {
            font-size: 12pt;
            font-weight: 700;
            color: #1a3a6b;
            margin-bottom: 0;
        }

        .patient-id {
            font-size: 9pt;
            color: #666666;
            font-weight: 500;
        }

        .patient-id strong {
            color: #1a3a6b;
            font-weight: 600;
        }

        .patient-info-item {
            display: flex;
            align-items: center;
            padding: 6px 10px;
            border-right: 1px solid #E0E0E0;
            border-bottom: 1px solid #E0E0E0;
        }

        .patient-info-item:nth-child(3n+1) {
            border-right: 1px solid #E0E0E0;
        }

        .patient-info-item:nth-child(3n) {
            border-right: none;
        }

        .patient-info-item:nth-last-child(-n+2) {
            border-bottom: none;
        }

        .patient-info-label {
            font-weight: 600;
            color: #1a3a6b;
            font-size: 8.5pt;
            margin-right: 5px;
        }

        .patient-info-value {
            color: #222222;
            font-weight: 500;
            font-size: 9pt;
        }

        .report-body {
            margin-bottom: 20px;
        }

        .report-section {
            margin-bottom: 12px;
            page-break-inside: avoid;
            border-left: 3px solid #2A4F8F;
            padding-left: 10px;
        }

        .section-title {
            font-size: 11pt;
            font-weight: bold;
            color: #222222;
            margin-bottom: 6px;
            text-transform: uppercase;
            letter-spacing: 0.3px;
            display: flex;
            align-items: center;
        }

        .section-title::before {
            content: '';
            width: 6px;
            height: 6px;
            background: #2A4F8F;
            border-radius: 50%;
            margin-right: 8px;
            margin-left: -16px;
        }

        .section-content {
            padding-left: 8px;
            text-align: justify;
            color: #444444;
            line-height: 1.5;
        }

        .section-content p {
            margin-bottom: 8px;
        }

        .section-content ul,
        .section-content ol {
            margin-left: 20px;
            margin-bottom: 8px;
        }

        .section-content li {
            margin-bottom: 4px;
        }

        .section-content table {
            width: 100%;
            border-collapse: collapse;
            margin: 8px 0;
            box-shadow: none;
        }

        .section-content table th,
        .section-content table td {
            border: 1px solid #CCCCCC;
            padding: 6px 8px;
            text-align: left;
        }

        .section-content table th {
            background: #2A4F8F;
            color: white;
            font-weight: 600;
        }

        .section-content table tr:nth-child(even) {
            background-color: #F5F7FB;
        }

        .section-content h1,
        .section-content h2,
        .section-content h3,
        .section-content h4 {
            color: #222222;
            margin-top: 10px;
            margin-bottom: 6px;
            font-weight: 600;
        }

        .section-content h1 {
            font-size: 12pt;
        }

        .section-content h2 {
            font-size: 11.5pt;
        }

        .section-content h3 {
            font-size: 11pt;
        }

        .section-content strong {
            color: #222222;
            font-weight: 600;
        }

        /* Enhanced Patient Questions Section */
        .questions-section {
            background: #F8F9FA;
            border: 1px solid #2A4F8F;
            border-radius: 0;
            padding: 15px;
            margin-bottom: 15px;
            page-break-inside: avoid;
        }

        .questions-title {
            font-size: 12pt;
            font-weight: bold;
            color: #2A4F8F;
            margin-bottom: 12px;
            text-align: center;
            text-transform: uppercase;
            letter-spacing: 0.3px;
        }

        .question-item {
            margin-bottom: 12px;
            background: white;
            border-radius: 0;
            padding: 10px;
            box-shadow: none;
            border: 1px solid #E0E0E0;
            page-break-inside: avoid;
        }

        .question-item:last-child {
            margin-bottom: 0;
        }

        .question-header {
            display: flex;
            align-items: flex-start;
            margin-bottom: 8px;
        }

        .question-number {
            background: #2A4F8F;
            color: white;
            font-weight: bold;
            min-width: 22px;
            height: 22px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-right: 8px;
            font-size: 9pt;
            flex-shrink: 0;
        }

        .question-text {
            font-weight: 600;
            color: #222222;
            font-size: 10pt;
            line-height: 1.4;
            flex: 1;
        }

        .answer-container {
            padding-left: 30px;
            border-left: 2px solid #CCCCCC;
            margin-left: 11px;
        }

        .answer-label {
            font-weight: 600;
            color: #2A4F8F;
            font-size: 9pt;
            margin-bottom: 4px;
            display: block;
        }

        .answer-text {
            color: #444444;
            line-height: 1.5;
            text-align: justify;
        }

        .answer-text p {
            margin-bottom: 6px;
        }

        .answer-text p:last-child {
            margin-bottom: 0;
        }

        .signature-container {
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            margin-top: 20px;
            padding-top: 12px;
            border-top: 1px solid #CCCCCC;
            page-break-inside: avoid;
        }

        .signature-block {
            text-align: center;
            min-width: 160px;
        }

        .signature-image {
            max-width: 140px;
            max-height: 45px;
            margin-bottom: 6px;
        }

        .signature-line {
            border-top: 1px solid #222222;
            margin-bottom: 4px;
        }

        .signature-label {
            font-size: 8.5pt;
            color: #444444;
            font-weight: 600;
        }

        .signature-name {
            font-size: 10pt;
            color: #222222;
            font-weight: bold;
            margin-top: 3px;
        }

        .signature-credentials {
            font-size: 9pt;
            color: #444444;
            font-style: italic;
        }

        .footer-note {
            margin-top: 12px;
            padding: 8px 10px;
            background: #F8F9FA;
            border-left: 3px solid #2A4F8F;
            border-radius: 0;
            font-size: 8pt;
            color: #444444;
            line-height: 1.4;
        }

        @media print {
            .header {
                box-shadow: none;
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }

            .questions-section {
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }
        }
    </style>
</head>

<body>
    <div class="header">
        <div class="header-left">
            <div class="header-logo">
                <img src="{{clinic_logo_url}}" alt="Clinic Logo">
            </div>
            <div class="header-info">
                <div class="clinic-name">{{clinic_name}}</div>
                <div class="clinic-details">
                    <div><strong>Address:</strong> {{clinic_address}}</div>
                    <div><strong>Phone:</strong> {{clinic_phone}}</div>
                    <div><strong>Email:</strong> {{clinic_email}}</div>
                    <div><strong>Website:</strong> {{clinic_website}}</div>
                </div>
            </div>
        </div>
    </div>

    <div class="report-title">{{report_title}}</div>

    <div class="patient-info">
        <div class="patient-name-container">
            <div class="patient-name">{{patient_name}}</div>
            <div class="patient-id"><strong>Patient ID:</strong> {{patient_id}}</div>
        </div>
        <div class="patient-info-item">
            <span class="patient-info-label">Age:</span>
            <span class="patient-info-value">{{patient_age}}</span>
        </div>
        <div class="patient-info-item">
            <span class="patient-info-label">Gender:</span>
            <span class="patient-info-value">{{patient_gender}}</span>
        </div>
        <div class="patient-info-item">
            <span class="patient-info-label">Blood Group:</span>
            <span class="patient-info-value">{{patient_blood_group}}</span>
        </div>
        <div class="patient-info-item">
            <span class="patient-info-label">Phone:</span>
            <span class="patient-info-value">{{patient_phone}}</span>
        </div>
        <div class="patient-info-item">
            <span class="patient-info-label">Email:</span>
            <span class="patient-info-value">{{patient_email}}</span>
        </div>
    </div>

    <div class="report-body">
        <div class="report-section">
            <div class="section-title">Clinical Findings</div>
            <div class="section-content">
                {{findings}}
            </div>
        </div>

        <div class="report-section">
            <div class="section-title">Observations</div>
            <div class="section-content">
                {{observations}}
            </div>
        </div>

        <div class="report-section">
            <div class="section-title">Medical Opinion</div>
            <div class="section-content">
                {{medical_opinion}}
            </div>
        </div>

        <div class="report-section">
            <div class="section-title">Responses to Patient Questions</div>
            <div class="section-content">
                {{patient_questions_responses}}
            </div>
        </div>
    </div>

    <div class="signature-container">
        <div class="signature-block">
            <img src="{{doctor_signature_url}}" alt="Doctor Signature" class="signature-image">
            <div class="signature-line"></div>
            <div class="signature-label">Authorized Medical Professional</div>
            <div class="signature-name">{{doctor_name}}</div>
            <div class="signature-credentials">{{doctor_credentials}}</div>
        </div>
        <div class="signature-block">
            <div style="height: 45px;"></div>
            <div class="signature-line"></div>
            <div class="signature-label">Date of Issue</div>
            <div class="signature-name">{{report_date}}</div>
        </div>
    </div>

    <div class="footer-note">
        <strong>Confidentiality Notice:</strong> This medical report contains confidential information intended solely
        for the patient named above. Unauthorized disclosure or distribution is prohibited. If you have received this
        document in error, please contact {{clinic_phone}} immediately.
    </div>
</body>
</html>
""".strip()