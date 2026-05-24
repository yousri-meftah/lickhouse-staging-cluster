#!/usr/bin/env python3
import requests, getpass, sys

CH02 = "http://localhost:8124"

DATABASES = [
    "reporting_shop1_green",
    "reporting_shop2_green",
    "reporting_shop3_green",
    "reporting_shop4_green",
]

def query(sql, user, password):
    resp = requests.post(CH02, params={"user": user, "password": password}, data=sql.encode())
    if resp.status_code != 200:
        print(f"\nFailed:\n{resp.text}")
        sys.exit(1)
    return resp.text.strip()

def main():
    user = input("Username [default]: ").strip() or "default"
    password = getpass.getpass("Password: ")
    q = lambda sql: query(sql, user, password)

    total = 0
    for db in DATABASES:
        print(f"\n── {db}")
        tables = q(
            f"SELECT name FROM system.tables "
            f"WHERE database='{db}' AND engine LIKE 'Replicated%'"
        ).splitlines()
        for table in tables:
            q(f"SYSTEM RESTORE REPLICA `{db}`.`{table}`")
            print(f"  ✓ RESTORE {table}")
            total += 1

    print(f"\n{total} replicas restored in Keeper.")

if __name__ == "__main__":
    main()