import urllib.request
import json
import uuid
import sys

BASE = "http://127.0.0.1:8000/api/v1/onboarding"

def make_request(path, method='GET', data=None):
    req = urllib.request.Request(BASE + path, method=method)
    req.add_header('Content-Type', 'application/json')
    req.add_header('Accept', 'application/json')
    try:
        body = json.dumps(data).encode('utf-8') if data else b""
        req_data = body if method in ('POST', 'PUT', 'PATCH') else None
        with urllib.request.urlopen(req, data=req_data) as response:
            res = response.read()
            return response.status, json.loads(res) if res else None
    except urllib.error.HTTPError as e:
        res = e.read()
        return e.code, json.loads(res) if res else {"error": "No body"}

print("============== Ledger Onboarding API Test Suite ==============")

# -------------------------------------------------------------------
# 1. PROFILE API
# -------------------------------------------------------------------
print("\n--- Testing Profile APIs ---")
user_id = str(uuid.uuid4())[:8]
payload = {
    "display_name": f"User_{user_id}",
    "base_currency": "INR",
    "financial_year_start_month": 4,
    "tax_regime": "NEW",
    "date_format": "DD/MM/YYYY",
    "number_format": "INDIAN"
}
status, profile = make_request('/profiles', 'POST', payload)
print(f"POST /profiles -> {status}")
pid = profile['id']

status, _ = make_request('/profiles', 'GET')
print(f"GET /profiles -> {status}")

status, _ = make_request(f'/profiles/{pid}', 'GET')
print(f"GET /profiles/{pid} -> {status}")

payload['display_name'] += "_updated"
status, _ = make_request(f'/profiles/{pid}', 'PUT', payload)
print(f"PUT /profiles/{pid} -> {status}")

status, _ = make_request(f'/profiles/{pid}', 'PATCH', {"base_currency": "USD"})
print(f"PATCH /profiles/{pid} -> {status}")

status, _ = make_request(f'/profiles/{pid}/status', 'GET')
print(f"GET /profiles/{pid}/status -> {status}")

# -------------------------------------------------------------------
# 2. COA API
# -------------------------------------------------------------------
print("\n--- Testing COA APIs ---")
status, _ = make_request('/coa/initialize', 'POST')
print(f"POST /coa/initialize -> {status} (Note: 409 means already init)")

status, coa_tree = make_request('/coa/tree', 'GET')
print(f"GET /coa/tree -> {status}")

status, _ = make_request('/coa/status', 'GET')
print(f"GET /coa/status -> {status}")

def find_leaf(nodes, name):
    for n in nodes:
        if n['name'].lower() == name.lower() and not n.get('is_placeholder'):
            return n['id']
        if n.get('children'):
            res = find_leaf(n['children'], name)
            if res: return res
    return None

cash_id = find_leaf(coa_tree, "Cash in Hand")

status, _ = make_request(f'/coa/accounts/{cash_id}', 'GET')
print(f"GET /coa/accounts/{cash_id} -> {status}")

# Create custom category under "Cash" placeholder (Code 1200)
parent_id = next(n['id'] for n in coa_tree if n['name'] == 'Assets')
status, cat = make_request('/coa/categories', 'POST', {"parent_id": parent_id, "name": f"Temp Asset {user_id}"})
print(f"POST /coa/categories -> {status}")
if status == 201:
    cat_id = cat['id']
    status, _ = make_request(f'/coa/accounts/{cat_id}/rename', 'PUT', {"new_name": "Renamed Asset"})
    print(f"PUT /coa/accounts/{cat_id}/rename -> {status}")

    status, _ = make_request(f'/coa/accounts/{cat_id}', 'DELETE')
    print(f"DELETE /coa/accounts/{cat_id} -> {status}")


# -------------------------------------------------------------------
# 3. INSTITUTIONS API
# -------------------------------------------------------------------
print("\n--- Testing Institutions APIs ---")
inst_payload = {"name": f"TestInst_{user_id}", "institution_type": "BANK"}
status, inst = make_request('/institutions', 'POST', inst_payload)
print(f"POST /institutions -> {status}")
iid = inst['id']

status, _ = make_request('/institutions', 'GET')
print(f"GET /institutions -> {status}")

status, _ = make_request(f'/institutions/{iid}', 'GET')
print(f"GET /institutions/{iid} -> {status}")

inst_payload['name'] += "_updated"
status, _ = make_request(f'/institutions/{iid}', 'PUT', inst_payload)
print(f"PUT /institutions/{iid} -> {status}")


# -------------------------------------------------------------------
# 4. ACCOUNTS API
# -------------------------------------------------------------------
print("\n--- Testing Accounts APIs ---")
print("POST /accounts/bank ->", make_request('/accounts/bank', 'POST', {"display_name": "Bank1", "institution_id": iid, "account_number_masked": "1111", "bank_account_type": "SAVINGS"})[0])
print("POST /accounts/credit-card ->", make_request('/accounts/credit-card', 'POST', {"display_name": "CC1", "institution_id": iid, "last_four_digits": "2222", "credit_limit": 50000, "billing_cycle_day": 5, "interest_rate_annual": 0})[0])
print("POST /accounts/loan ->", make_request('/accounts/loan', 'POST', {"display_name": "Loan1", "institution_id": iid, "loan_type": "PERSONAL", "principal_amount": 100000, "interest_rate": 10.5, "tenure_months": 24, "emi_amount": 4700, "start_date": "2026-01-01"})[0])
print("POST /accounts/brokerage ->", make_request('/accounts/brokerage', 'POST', {"display_name": "Broker1", "institution_id": iid, "demat_id": "D123", "default_cost_basis_method": "FIFO"})[0])
print("POST /accounts/fixed-deposit ->", make_request('/accounts/fixed-deposit', 'POST', {"display_name": "FD1", "institution_id": iid, "principal_amount": 10000, "interest_rate": 6.5, "start_date": "2026-01-01", "maturity_date": "2027-01-01", "compounding_frequency": "QUARTERLY"})[0])
print("POST /accounts/cash ->", make_request('/accounts/cash', 'POST', {"display_name": "Wallet1"})[0])

# These currently hit stubbed exceptions or return empty responses
print("GET /accounts ->", make_request('/accounts', 'GET')[0])
print("GET /accounts/999 ->", make_request('/accounts/999', 'GET')[0])
print("DELETE /accounts/999 ->", make_request('/accounts/999', 'DELETE')[0])


# -------------------------------------------------------------------
# 5. OPENING BALANCES
# -------------------------------------------------------------------
print("\n--- Testing Opening Balances APIs ---")
print(f"POST /opening-balances ->", make_request('/opening-balances', 'POST', {"account_id": cash_id, "amount": 1000, "as_of_date": "2026-03-15", "notes": "Test Single"})[0])
print(f"POST /opening-balances/bulk ->", make_request('/opening-balances/bulk', 'POST', {"balances": [{"account_id": cash_id, "amount": 2000, "as_of_date": "2026-03-15", "notes": "Test Bulk"}]})[0])


# -------------------------------------------------------------------
# 6. NET WORTH
# -------------------------------------------------------------------
print("\n--- Testing Net Worth API ---")
status, response = make_request('/networth', 'GET')
print(f"GET /networth -> {status}")
print("Net Worth:", response.get('net_worth', 0))


# -------------------------------------------------------------------
# Cleanup
# -------------------------------------------------------------------
print("\n--- Cleanup ---")
status, _ = make_request(f'/institutions/{iid}', 'DELETE')
print(f"DELETE /institutions/{iid} -> {status}")

status, _ = make_request(f'/profiles/{pid}', 'DELETE')
print(f"DELETE /profiles/{pid} -> {status}")

print("\nDONE!")
