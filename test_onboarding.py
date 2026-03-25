import urllib.request
import json
import uuid

BASE = "http://127.0.0.1:8000/api/v1/onboarding"

def post(path, data=None):
    req = urllib.request.Request(BASE + path, method='POST')
    req.add_header('Content-Type', 'application/json')
    try:
        body = json.dumps(data).encode() if data else b""
        with urllib.request.urlopen(req, data=body) as response:
            res = response.read()
            return json.loads(res) if res else None
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.read().decode()}")
        return None

def get(path):
    req = urllib.request.Request(BASE + path, method='GET')
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read())

user_id = str(uuid.uuid4())[:8]
post('/profile/', {"display_name": "Test " + user_id, "base_currency": "INR", "financial_year_start_month": 4, "tax_regime": "NEW", "date_format": "DD/MM/YYYY", "number_format": "INDIAN"})
post('/coa/initialize')
inst = post('/institutions/', {"name": "Test Bank", "institution_type": "BANK"})

coa = get('/coa/tree')
def find_leaf(nodes, name):
    for n in nodes:
        if n['name'].lower() == name.lower() and not n.get('is_placeholder'):
            return n['id']
        if n.get('children'):
            res = find_leaf(n['children'], name)
            if res: return res
    return None

cash_id = find_leaf(coa['items'], "Cash in Hand")
print("Cash ID:", cash_id)

bank = post('/accounts/bank', {"display_name": "HDFC", "institution_id": inst['id'], "account_number_masked": "1234", "bank_account_type": "SAVINGS"})
card = post('/accounts/credit-card', {"display_name": "Axis", "institution_id": inst['id'], "last_four_digits": "0000", "credit_limit": 10000, "billing_cycle_day": 1, "interest_rate_annual": 0})

entries = []
if cash_id: entries.append({"account_id": cash_id, "balance_amount": 5000, "balance_date": "2026-03-15"})
entries.append({"account_id": bank['coa']['id'], "balance_amount": 25000, "balance_date": "2026-03-15"})
entries.append({"account_id": card['coa']['id'], "balance_amount": 5000, "balance_date": "2026-03-15"})

bulk = post('/opening-balances/bulk', {"entries": entries})

nw = post('/net-worth/compute?date=2026-03-15')
print("NET WORTH COMPUTED:", json.dumps(nw, indent=2))
