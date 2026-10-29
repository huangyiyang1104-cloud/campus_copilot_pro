import httpx

BASE = "http://127.0.0.1:8000"

admin = httpx.Client(base_url=BASE)
login = admin.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
admin_at = login.json()["access_token"]
headers = {"Authorization": f"Bearer {admin_at}"}
print("1 admin login:", login.status_code)

listed = admin.get("/api/users", headers=headers)
print("2 list:", listed.status_code, "| count:", len(listed.json()))

created = admin.post(
    "/api/users",
    headers=headers,
    json={
        "username": "crud_test",
        "password": "test1234",
        "name": "增删改查测试",
        "role": "student",
        "email": "crud@campus.edu",
        "phone": "13900000000",
        "status": 1,
    },
)
print("3 create:", created.status_code, created.json().get("id"), created.json().get("username"))
uid = created.json()["id"]

dup = admin.post(
    "/api/users",
    headers=headers,
    json={"username": "crud_test", "password": "test1234", "name": "重复", "role": "student"},
)
print("4 duplicate username:", dup.status_code, dup.json()["detail"]["code"])

updated = admin.put(
    f"/api/users/{uid}",
    headers=headers,
    json={"name": "改名成功", "email": "new@campus.edu"},
)
print("5 update:", updated.status_code, updated.json()["name"], updated.json()["email"])

student = httpx.Client(base_url=BASE)
stu_login = student.post("/api/auth/login", json={"username": "crud_test", "password": "test1234"})
print("6 new user login:", stu_login.status_code)
stu_at = stu_login.json()["access_token"]
forbidden = student.get("/api/users", headers={"Authorization": f"Bearer {stu_at}"})
print("7 student access user list:", forbidden.status_code, forbidden.json()["detail"]["code"])

disabled = admin.patch(f"/api/users/{uid}/status", headers=headers, json={"status": 0})
print("8 disable:", disabled.status_code, "| status:", disabled.json()["status"])
blocked = student.get("/api/auth/me", headers={"Authorization": f"Bearer {stu_at}"})
print("9 kicked user /me:", blocked.status_code, blocked.json()["detail"]["code"])

enabled = admin.put(f"/api/users/{uid}", headers=headers, json={"status": 1})
print("10 enable by update:", enabled.status_code, "| status:", enabled.json()["status"])

missing = admin.put("/api/users/999999", headers=headers, json={"name": "x"})
print("11 update missing:", missing.status_code, missing.json()["detail"]["code"])

deleted = admin.delete(f"/api/users/{uid}", headers=headers)
print("12 delete:", deleted.status_code, deleted.json())

gone = admin.put(f"/api/users/{uid}", headers=headers, json={"name": "x"})
print("13 update deleted:", gone.status_code, gone.json()["detail"]["code"])

print("14 list again:", len(admin.get("/api/users", headers=headers).json()))
