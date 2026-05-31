from __future__ import annotations

import secrets


def main() -> None:
    print(f"ADMIN_BOOTSTRAP_TOKEN={secrets.token_urlsafe(48)}")
    print(f"API_KEY_PEPPER={secrets.token_urlsafe(48)}")


if __name__ == "__main__":
    main()
