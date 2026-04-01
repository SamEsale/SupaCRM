import requests

BASE_URL = "http://127.0.0.1:8000"

TENANT_ID = "tenant-demo"

ADMIN_EMAIL = "admin@tenant-demo.com"
ADMIN_PASSWORD = "AdminPassword123!"

USER_EMAIL = "user@tenant-demo.com"
USER_PASSWORD = "UserPassword123!"


def login(email, password):
    res = requests.post(
        f"{BASE_URL}/auth/login",
        json={
            "tenant_id": TENANT_ID,
            "email": email,
            "password": password,
        },
    )
    return res.json()


def call(endpoint, token, method="GET"):
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Id": TENANT_ID,
    }

    if method == "GET":
        return requests.get(f"{BASE_URL}{endpoint}", headers=headers)
    elif method == "POST":
        return requests.post(f"{BASE_URL}{endpoint}", headers=headers)
    else:
        raise ValueError("Unsupported method")


def print_result(label, response):
    print(f"{label}: status={response.status_code}")


def main():
    print("=== RBAC TEST START ===")

    # LOGIN ADMIN
    admin_login = login(ADMIN_EMAIL, ADMIN_PASSWORD)
    admin_token = admin_login["access_token"]

    # LOGIN USER (create this user next step)
    user_login = login(USER_EMAIL, USER_PASSWORD)
    user_token = user_login["access_token"]

    print("\n--- CRM READ ---")
    print_result(
        "admin crm read",
        call("/crm/contacts", admin_token),
    )
    print_result(
        "user crm read",
        call("/crm/contacts", user_token),
    )

    print("\n--- CRM WRITE ---")
    print_result(
        "admin crm write",
        call("/crm/contacts", admin_token, method="POST"),
    )
    print_result(
        "user crm write (should fail)",
        call("/crm/contacts", user_token, method="POST"),
    )

    print("\n--- TENANT ADMIN ---")
    print_result(
        "admin tenant access",
        call("/tenants/me", admin_token),
    )
    print_result(
        "user tenant access (should fail)",
        call("/tenants/me", user_token),
    )

    print("\n=== RBAC TEST END ===")


if __name__ == "__main__":
    main()