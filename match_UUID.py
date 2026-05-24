#!/usr/bin/env python3
import requests, getpass, sys

CH01 = "http://localhost:8123"
CH02 = "http://localhost:8124"

# Only the 4 reporting databases — skip system/default/INFORMATION_SCHEMA
DATABASES = [
    "reporting_shop1_green",
    "reporting_shop2_green",
    "reporting_shop3_green",
    "reporting_shop4_green",
]

def query(host, sql, user, password):
    resp = requests.post(host, params={"user": user, "password": password}, data=sql.encode())
    if resp.status_code != 200:
        print(f"\nFailed on:\n{sql}\n\nError:\n{resp.text}")
        sys.exit(1)
    return resp.text.strip()

def main():
    user = input("Username [default]: ").strip() or "default"
    password = getpass.getpass("Password: ")

    q1 = lambda sql: query(CH01, sql, user, password)
    q2 = lambda sql: query(CH02, sql, user, password)

    total = 0
    for db in DATABASES:
        print(f"\n── {db}")
        # get all replicated tables in this db from ch02
        tables = q2(
            f"SELECT name FROM system.tables "
            f"WHERE database='{db}' AND engine LIKE 'Replicated%'"
        ).splitlines()

        for table in tables:
            # read ch02's UUID — this is the source of truth
            uuid = q2(
                f"SELECT uuid FROM system.tables "
                f"WHERE database='{db}' AND name='{table}'"
            )
            # get the full CREATE statement from ch02
            ddl = q2(f"SHOW CREATE TABLE `{db}`.`{table}` FORMAT TSVRaw")
            # inject ch02's UUID into the CREATE statement
            ddl = ddl.replace(
                f"CREATE TABLE {db}.{table}",
                f"CREATE TABLE {db}.{table} UUID '{uuid}'",
                1
            )
            # safety check — abort if injection failed
            if uuid not in ddl:
                print(f"  ✗ UUID injection failed for {db}.{table}")
                sys.exit(1)

            # drop the orphaned table on ch01 (wrong UUID), recreate with correct one
            q1(f"DROP TABLE IF EXISTS `{db}`.`{table}` SYNC")
            q1(ddl)
            print(f"  ✓ {table}  uuid={uuid[:8]}...")
            total += 1

    print(f"\n{total} tables realigned on ch01.")

if __name__ == "__main__":
    main()