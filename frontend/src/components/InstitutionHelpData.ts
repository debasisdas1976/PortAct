export interface InstitutionHelpEntry {
  id: string;
  name: string;
  category: 'bank' | 'credit_card' | 'demat' | 'government';
  formats: string;
  passwordRequired: boolean;
  passwordHint?: string;
  steps: string[];
  tips?: string[];
}

export const institutionHelpEntries: InstitutionHelpEntry[] = [
  // ── Banks ──
  {
    id: 'icici_bank',
    name: 'ICICI Bank',
    category: 'bank',
    formats: 'PDF / Excel',
    passwordRequired: false,
    steps: [
      'Log in to ICICI Bank Internet Banking at icicibank.com.',
      'Go to "Accounts & Deposits" from the top menu.',
      'Click "View Statement" under your savings or current account.',
      'Select the date range (3–6 months recommended).',
      'Click "Download" and choose PDF or Excel (XLS) format.',
      'Upload the downloaded file to PortAct.',
    ],
    tips: [
      'Both PDF and Excel formats are supported.',
      'PDF may require a password — typically your registered mobile number or date of birth.',
    ],
  },
  {
    id: 'hdfc_bank',
    name: 'HDFC Bank',
    category: 'bank',
    formats: 'PDF / Excel',
    passwordRequired: false,
    steps: [
      'Log in to HDFC Bank NetBanking at hdfcbank.com.',
      'Click on the "Accounts" tab at the top.',
      'Select "Statement of Accounts" from the dropdown.',
      'Choose your account and select the date range.',
      'Select format as "PDF" or "XLS/Delimited".',
      'Click "Get Statement" to download.',
    ],
    tips: [
      'Both PDF and Excel formats are supported.',
      'PDF statements are generally not password-protected.',
    ],
  },
  {
    id: 'sbi',
    name: 'State Bank of India (SBI)',
    category: 'bank',
    formats: 'PDF / Excel',
    passwordRequired: true,
    passwordHint: 'CIF number, or first 4 letters of your name (UPPERCASE) + DDMM (date of birth).',
    steps: [
      'Log in to SBI Internet Banking (OnlineSBI) at onlinesbi.sbi.',
      'Go to "My Accounts & Profile" → "Account Statement".',
      'Select the account number and date range.',
      'Choose format as "PDF" or "Excel".',
      'Download the statement file.',
    ],
    tips: [
      'SBI statements are often password-protected.',
      'The password is typically your CIF number or NAME (first 4 uppercase) + DDMM.',
      'Try both formats if one doesn\'t work.',
    ],
  },
  {
    id: 'axis_bank',
    name: 'Axis Bank',
    category: 'bank',
    formats: 'PDF',
    passwordRequired: false,
    steps: [
      'Log in to Axis Bank Internet Banking at axisbank.com.',
      'Go to "My Accounts" → "Detailed Statement".',
      'Select the account and date range.',
      'Choose PDF format and download.',
    ],
    tips: [
      'Only PDF format is currently supported.',
      'The PDF password, if any, is usually your registered mobile number.',
    ],
  },
  {
    id: 'kotak_bank',
    name: 'Kotak Mahindra Bank',
    category: 'bank',
    formats: 'PDF',
    passwordRequired: false,
    steps: [
      'Log in to Kotak Mahindra Bank NetBanking at kotak.com.',
      'Navigate to "My Accounts" → "Account Statement".',
      'Select your account, date range, and PDF format.',
      'Download the statement.',
    ],
    tips: [
      'Only PDF format is supported.',
      'Statements are usually not password-protected.',
    ],
  },
  {
    id: 'idfc_first_bank',
    name: 'IDFC First Bank',
    category: 'bank',
    formats: 'PDF / Excel',
    passwordRequired: false,
    steps: [
      'Log in to IDFC First Bank Internet Banking at idfcfirstbank.com.',
      'Navigate to "My Accounts" → "Statement".',
      'Select date range and download format (PDF or Excel).',
      'Click "Download Statement".',
    ],
    tips: [
      'Both PDF and Excel formats are supported.',
      'Statements are usually not password-protected.',
    ],
  },

  // ── Credit Cards ──
  {
    id: 'icici_cc',
    name: 'ICICI Credit Card',
    category: 'credit_card',
    formats: 'Excel',
    passwordRequired: false,
    steps: [
      'Log in to ICICI Bank Internet Banking at icicibank.com.',
      'Go to "Card Accounts" from the top menu.',
      'Click "View Statement" for your credit card.',
      'Select the billing cycle or date range.',
      'Download in Excel format (the parser requires Excel).',
    ],
    tips: [
      'Only Excel format is supported for ICICI credit card parsing.',
      'The Excel file should contain a sheet named "CCLastStatement".',
    ],
  },
  {
    id: 'idfc_first_cc',
    name: 'IDFC First Bank Credit Card',
    category: 'credit_card',
    formats: 'PDF',
    passwordRequired: false,
    steps: [
      'Log in to IDFC First Bank Internet Banking.',
      'Navigate to "Cards" → "Card Statement".',
      'Select the billing period.',
      'Download the statement in PDF format.',
    ],
    tips: ['Only PDF format is supported for IDFC First credit card statements.'],
  },
  {
    id: 'scapia_cc',
    name: 'Scapia Credit Card',
    category: 'credit_card',
    formats: 'PDF',
    passwordRequired: false,
    steps: [
      'Open the Scapia app on your phone.',
      'Go to the "Statements" section.',
      'Select the month or billing cycle.',
      'Tap "Download Statement" to get the PDF.',
      'Transfer the PDF to your computer if needed, then upload to PortAct.',
    ],
    tips: ['Scapia only provides PDF statements. These are usually not password-protected.'],
  },

  // ── Demat Brokers & Aggregators ──
  {
    id: 'zerodha',
    name: 'Zerodha',
    category: 'demat',
    formats: 'CSV / Excel',
    passwordRequired: false,
    steps: [
      'Log in to Zerodha Console at console.zerodha.com.',
      'Go to "Portfolio" → "Holdings".',
      'Click the download icon (top-right) to export as CSV or Excel.',
      'Alternatively, go to "Reports" → "Tradebook" for transaction history.',
    ],
    tips: [
      'The Holdings CSV is the easiest way to import current holdings.',
      'Use Tradebook CSV for transaction history.',
    ],
  },
  {
    id: 'groww',
    name: 'Groww',
    category: 'demat',
    formats: 'CSV / Excel',
    passwordRequired: false,
    steps: [
      'Log in to Groww at groww.in/dashboard.',
      'Go to the "Stocks" or "Mutual Funds" section.',
      'Click on "Statements" or "Reports".',
      'Select date range and download as CSV or Excel.',
    ],
    tips: [
      'Both CSV and Excel formats work.',
      'Holdings and transaction reports are supported.',
    ],
  },
  {
    id: 'icici_direct',
    name: 'ICICI Direct',
    category: 'demat',
    formats: 'CSV',
    passwordRequired: false,
    steps: [
      'Log in to ICICI Direct at icicidirect.com.',
      'Go to "Portfolio" → "My Holdings".',
      'Click "Download" to export as CSV.',
      'Alternatively, go to "Reports" for detailed transaction history.',
    ],
    tips: ['Only CSV format is supported for ICICI Direct.'],
  },
  {
    id: 'vested',
    name: 'Vested (US Stocks)',
    category: 'demat',
    formats: 'CSV',
    passwordRequired: false,
    steps: [
      'Log in to Vested at vestedfinance.com.',
      'Go to your portfolio / holdings page.',
      'Download the holdings report as CSV.',
    ],
    tips: [
      'This parser handles US stock holdings from Vested.',
      'Amounts are tracked in USD and automatically converted to INR.',
    ],
  },
  {
    id: 'indmoney',
    name: 'INDMoney (US Stocks)',
    category: 'demat',
    formats: 'CSV',
    passwordRequired: false,
    steps: [
      'Log in to the INDMoney app or website.',
      'Go to the "US Stocks" section.',
      'Download your holdings or transaction report as CSV.',
    ],
    tips: [
      'This parser handles US stock holdings from INDMoney.',
      'Amounts are tracked in USD and automatically converted to INR.',
    ],
  },
  {
    id: 'nsdl_cas',
    name: 'NSDL CAS (Consolidated Account Statement)',
    category: 'demat',
    formats: 'PDF',
    passwordRequired: true,
    passwordHint: 'PAN number (e.g., ABCDE1234F) or email used for registration, or combination of PAN + DOB.',
    steps: [
      'Visit cams-cra.com or nsdl.co.in → "Services" → "CAS".',
      'Request a Consolidated Account Statement (CAS) for your PAN.',
      'You can also request CAS via email from NSDL.',
      'The CAS PDF will be sent to your registered email.',
      'Download the PDF and upload to PortAct.',
    ],
    tips: [
      'CAS covers all your demat holdings, mutual funds, and other securities across all depositories.',
      'The PDF is always password-protected.',
    ],
  },
  {
    id: 'cdsl_cas',
    name: 'CDSL CAS (Consolidated Account Statement)',
    category: 'demat',
    formats: 'PDF',
    passwordRequired: false,
    steps: [
      'Visit cdslindia.com and navigate to the "CAS" section.',
      'Or request CAS by logging in to your CDSL account.',
      'Download the Consolidated Account Statement PDF.',
      'Upload to PortAct.',
    ],
    tips: ['CDSL CAS covers all your CDSL-held securities and mutual funds.'],
  },
  {
    id: 'mf_central',
    name: 'MF Central CAS',
    category: 'demat',
    formats: 'PDF',
    passwordRequired: false,
    steps: [
      'Visit mfcentral.com.',
      'Log in or register with your PAN and mobile number.',
      'Go to "Reports" → "CAS".',
      'Select "Detailed" CAS type and the time period.',
      'Download the PDF.',
    ],
    tips: [
      'MF Central provides a consolidated view of all your mutual fund holdings across all fund houses and RTAs (CAMS, KFintech).',
    ],
  },

  // ── Government Schemes ──
  {
    id: 'ppf',
    name: 'PPF (Public Provident Fund)',
    category: 'government',
    formats: 'PDF',
    passwordRequired: true,
    passwordHint: 'Same as your bank\'s statement password (varies by bank).',
    steps: [
      'Log in to the internet banking portal of the bank where your PPF account is held (e.g., SBI, ICICI, HDFC).',
      'Navigate to "PPF Account" or "Deposits" section.',
      'Download the PPF passbook or statement as PDF.',
    ],
    tips: [
      'The parser extracts deposits, interest credits, and account balance.',
      'Password format depends on the bank holding the PPF account.',
    ],
  },
  {
    id: 'pf',
    name: 'PF / EPF (Provident Fund)',
    category: 'government',
    formats: 'PDF',
    passwordRequired: true,
    passwordHint: 'UAN (Universal Account Number) or member e-SEWA password.',
    steps: [
      'Log in to EPFO Member Portal at member.epfindia.gov.in.',
      'Click on "Passbook" under "Our Services".',
      'Select your Member ID and download the passbook as PDF.',
    ],
    tips: [
      'The parser extracts employee contributions, employer contributions, and interest.',
    ],
  },
  {
    id: 'ssy',
    name: 'SSY (Sukanya Samriddhi Yojana)',
    category: 'government',
    formats: 'PDF',
    passwordRequired: true,
    passwordHint: 'Same as your bank or post office statement password.',
    steps: [
      'Log in to the internet banking portal of the bank or post office where your SSY account is held.',
      'Navigate to the SSY account section.',
      'Download the SSY passbook statement as PDF.',
    ],
    tips: ['SSY statements work similarly to PPF statements.'],
  },
  {
    id: 'nps',
    name: 'NPS (National Pension System)',
    category: 'government',
    formats: 'PDF',
    passwordRequired: true,
    passwordHint: 'PRAN (Permanent Retirement Account Number) or CRA login password.',
    steps: [
      'Log in to the NPS CRA portal (Protean eGov at cra-nsdl.com or KFintech CRA).',
      'Go to "Statement of Transaction" or "Holdings Statement".',
      'Download the NPS statement PDF.',
    ],
    tips: [
      'The parser extracts Tier 1 and Tier 2 holdings, NAV details, and contribution history.',
    ],
  },
];
