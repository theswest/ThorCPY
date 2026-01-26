import PyInstaller.__main__

PyInstaller.__main__.run([
    "main.py",
    "--onefile",
    "--noconsole",
    "--clean",
    "--name=ThorCPY",

    "--add-data=config;config",
    "--add-data=bin;bin",
    "--add-data=logs;logs",
    "--add-data=assets/fonts;assets/fonts",
    "--add-data=assets/icon.png;assets",

    "--icon=assets/icon.ico",
])
