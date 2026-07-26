"""
Daily Update Engine
"""

from backend.download import download_all


def update():
    print("Starting update...")
    download_all()
    print("Update completed.")


if __name__ == "__main__":
    update()
