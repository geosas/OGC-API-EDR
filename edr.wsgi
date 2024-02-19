import sys
import os
sys.path.insert(1, os.path.dirname(os.path.abspath(__file__)))

from api import app
application = app