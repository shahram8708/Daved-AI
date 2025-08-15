
from flask import Blueprint

codegen = Blueprint('codegen', __name__)

from . import routes