from fastapi import Depends
from app.dependencies.permissions import require_permission
from app.models.user import User

def require_cash_payment_process(current_user: User = Depends(require_permission('payments.process'))) -> User:
    return current_user
