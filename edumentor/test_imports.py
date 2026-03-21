
import sys
import os

print("CWD:", os.getcwd())
print("sys.path:", sys.path)

try:
    from routes.auth import auth_bp
    print("auth_bp imported")
except Exception as e:
    print("Failed to import routes.auth:", e)

try:
    from routes.main import main_bp
    print("main_bp imported")
except Exception as e:
    print("Failed to import routes.main:", e)

try:
    from routes.roadmap import roadmap_bp
    print("roadmap_bp imported")
except Exception as e:
    print("Failed to import routes.roadmap:", e)
