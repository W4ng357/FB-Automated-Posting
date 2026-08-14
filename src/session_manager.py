from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
# __file__ is src/session_manager.py, and .resolve() is needed to get the absolute path of the file
# Which is /home/wanwy/Documents/Prj/FB-Automated-Posting/src/
# Adding .parent take us back to the previous directory
# Which is /home/wanwy/Documents/Prj/FB-Automated-Posting/src/
# .parent.parent means ROOT_DIR is /home/wanwy/Documents/Prj/FB-Automated-Posting
SESSIONS_DIR = ROOT_DIR / "browser_sessions"


def get_session_path(account_name: str) -> Path:
    return SESSIONS_DIR / account_name


def session_exists(account_name: str) -> bool:
    return get_session_path(account_name).is_dir()


def get_session(account_name: str) -> Path:
    session_path =  get_session_path(account_name)

    if not session_path.is_dir():
        raise FileNotFoundError(
            f"Session directory not found for account '{account_name}': {session_path}"
        )

    return session_path

def list_sessions() -> list[str]:
      if not SESSIONS_DIR.exists():
          return []

      session_names = []

      for path in SESSIONS_DIR.iterdir():
          # iterdir() dùng để liệt kê tất cả các tệp và thư mục trong một thư mục.
          # Nó trả về một trình lặp (iterator) chứa các đối tượng Path đại diện cho từng tệp và thư mục con trong thư mục đó.
          if path.is_dir():
              session_names.append(path.name)

      session_names = sorted(session_names)

      return session_names


if __name__ == "__main__":
    print(list_sessions())
