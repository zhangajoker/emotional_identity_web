import getpass

from argon2 import PasswordHasher

from db import get_connection


password_hasher = PasswordHasher()


def main() -> None:
    conn = None

    try:
        conn = get_connection()

        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, username, display_name
                FROM users
                WHERE is_active = 1
                ORDER BY id
                """
            )
            users = cursor.fetchall()

        if not users:
            print("当前没有可重置密码的账号")
            return

        print("当前账号：")
        for user in users:
            print(
                f"  {user['id']}: "
                f"{user['username']} "
                f"({user['display_name']})"
            )

        username = input("\n请输入要重置的用户名: ").strip().lower()
        if not username:
            print("用户名不能为空")
            return

        new_password = getpass.getpass("请输入新密码（至少 8 位）: ")
        confirm_password = getpass.getpass("请再次输入新密码: ")

        if new_password != confirm_password:
            print("两次输入的密码不一致")
            return

        if len(new_password) < 8:
            print("密码至少需要 8 个字符")
            return

        if len(new_password) > 128:
            print("密码不能超过 128 个字符")
            return

        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id
                FROM users
                WHERE username = %s
                  AND is_active = 1
                LIMIT 1
                """,
                (username,),
            )
            user = cursor.fetchone()

            if user is None:
                print("没有找到这个账号")
                return

            cursor.execute(
                """
                UPDATE users
                SET password_hash = %s
                WHERE id = %s
                """,
                (
                    password_hasher.hash(new_password),
                    user["id"],
                ),
            )
            cursor.execute(
                """
                UPDATE auth_sessions
                SET revoked_at = UTC_TIMESTAMP()
                WHERE user_id = %s
                  AND revoked_at IS NULL
                """,
                (user["id"],),
            )

        print(f"账号 {username} 的密码已重置，所有旧会话已失效。")
    finally:
        if conn is not None and conn.open:
            conn.close()


if __name__ == "__main__":
    main()
