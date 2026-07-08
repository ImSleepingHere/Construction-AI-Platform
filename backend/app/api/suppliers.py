from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.construction import Supplier
from app.schemas.construction import SupplierRead

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


@router.get("", response_model=list[SupplierRead])
def list_suppliers(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> list[Supplier]:
    return db.query(Supplier).order_by(Supplier.id).offset(offset).limit(limit).all()