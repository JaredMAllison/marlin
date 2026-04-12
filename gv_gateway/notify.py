import subprocess


def send(title: str, body: str) -> None:
    subprocess.run(["notify-send", title, body], check=True)
