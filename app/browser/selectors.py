# KARI selectors. Prefer stable semantic attributes/text over generated Angular classes.
LOGIN_EMAIL = '#email, input[name="email"], input[type="email"]'
LOGIN_PASSWORD = '#password, input[name="password"], input[type="password"]'
LOGIN_SUBMIT = 'button.btn-submit, button[type="submit"], button:has-text("Sign in")'
RECAPTCHA = 'iframe[src*="recaptcha"], iframe[title*="reCAPTCHA"], .g-recaptcha'

DEMO_TRIGGER = 'button.cb-cta, button.w-cta, input.cb-demo-inp'
ASK_KARI_BUTTON = 'button.cb-cta, button.w-cta, button:has-text("Ask KARI")'
CHAT_INPUT = 'textarea.ta, textarea:not([readonly]), input[placeholder*="Ask" i], [contenteditable="true"]'
CHAT_SEND = 'button.snd, button[aria-label*="send" i]'

# Source chips/filters on the live chatbot page.
SOURCE_NAME = 'span.src-name'

# Drug list and PIP selectors from live DOM
SEARCH_INPUT = 'textarea.ta, textarea[placeholder*="Ask" i], input[placeholder*="Ask" i]'
RESULT_ROW = '.dl-row'
ROW_CHECKBOX = 'label.dl-checkbox-label, input[type="checkbox"]'
PDF_BUTTON = 'button.dl-pdf-btn, .dl-pdf-btn, button[title*="PIP PDF" i]'
COMPARISON_PDF_BUTTON = 'button.cmp-th-pdf, .cmp-th-pdf, button:has(img[src*="pdf_file_icon"])'
COMPARE_BUTTON = 'button.dl-compare-btn, .dl-compare-btn, button:has-text("Compare")'
COMPARISON_ROOT = '.cmp-table, .cmp-section-group, [data-section-key], .comparison-container'
SECTION_GROUP = 'tbody.cmp-section-group'
SECTION_ROW = 'tr.cmp-sec-row'
SECTION_CONTENT = 'tr.cmp-sec-content'
