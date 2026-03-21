import sys
import os

# Ensure the current directory is in sys.path so local 'routes' package is found
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

print(f"Python Version: {sys.version}")
print(f"Current Working Directory: {os.getcwd()}")
print(f"Project Root Added to Path: {current_dir}")

try:
    import routes
    print(f"✅ Successfully imported 'routes' package from {routes.__file__}")
except ImportError as e:
    print(f"❌ Failed to import 'routes' package: {e}")

try:
    from routes import auth
    print(f"Successfully imported 'routes.auth' module from {auth.__file__}")
except ImportError as e:
    print(f"Failed to import 'routes.auth' module: {e}")

try:
    from routes.auth import auth_bp
    print(f"Successfully imported 'auth_bp' from 'routes.auth'")
except ImportError as e:
    print(f"Failed to import 'auth_bp' from 'routes.auth': {e}")
