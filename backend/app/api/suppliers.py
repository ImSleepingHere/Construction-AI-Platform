from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.construction import NCR, PurchaseOrder, Supplier
from app.schemas.construction import NCRRead, PurchaseOrderRead, SupplierRead

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


@router.get("", response_model=list[SupplierRead])
def list_suppliers(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> list[Supplier]:
    return db.query(Supplier).order_by(Supplier.id).offset(offset).limit(limit).all()


@router.get("/{supplier_id}", response_model=SupplierRead)
def get_supplier(supplier_id: int, db: Session = Depends(get_db)) -> Supplier:
    supplier = db.get(Supplier, supplier_id)
    if supplier is None:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier


@router.get("/{supplier_id}/purchase-orders", response_model=list[PurchaseOrderRead])
def list_supplier_purchase_orders(
    supplier_id: int, limit: int = 100, offset: int = 0, db: Session = Depends(get_db)
) -> list[PurchaseOrder]:
    return (
        db.query(PurchaseOrder)
        .filter(PurchaseOrder.supplier_id == supplier_id)
        .order_by(PurchaseOrder.issue_date.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get("/{supplier_id}/ncrs", response_model=list[NCRRead])
def list_supplier_ncrs(
    supplier_id: int, limit: int = 100, offset: int = 0, db: Session = Depends(get_db)
) -> list[NCR]:
    return (
        db.query(NCR)
        .filter(NCR.supplier_id == supplier_id)
        .order_by(NCR.issue_date.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
