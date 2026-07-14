from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.construction import NCR, PurchaseOrder, Supplier
from app.schemas.construction import NCRRead, PurchaseOrderRead, SupplierRead

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


def _supplier_read_with_stats(
    supplier: Supplier, po_count: int, late_count: int
) -> SupplierRead:
    on_time_rate = round((po_count - late_count) / po_count, 3) if po_count > 0 else None
    return SupplierRead(
        id=supplier.id,
        supplier_name=supplier.supplier_name,
        category=supplier.category,
        city=supplier.city,
        status=supplier.status,
        po_count=po_count,
        on_time_rate=on_time_rate,
    )


@router.get("", response_model=list[SupplierRead])
def list_suppliers(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> list[SupplierRead]:
    po_count_col = func.count(PurchaseOrder.id)
    late_count_col = func.coalesce(
        func.sum(case((PurchaseOrder.is_late == 1, 1), else_=0)), 0
    )

    rows = (
        db.query(Supplier, po_count_col, late_count_col)
        .outerjoin(PurchaseOrder, PurchaseOrder.supplier_id == Supplier.id)
        .group_by(Supplier.id)
        .order_by(Supplier.id)
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [
        _supplier_read_with_stats(supplier, po_count, late_count)
        for supplier, po_count, late_count in rows
    ]


@router.get("/{supplier_id}", response_model=SupplierRead)
def get_supplier(supplier_id: int, db: Session = Depends(get_db)) -> SupplierRead:
    supplier = db.get(Supplier, supplier_id)
    if supplier is None:
        raise HTTPException(status_code=404, detail="Supplier not found")

    po_count_col = func.count(PurchaseOrder.id)
    late_count_col = func.coalesce(
        func.sum(case((PurchaseOrder.is_late == 1, 1), else_=0)), 0
    )
    po_count, late_count = (
        db.query(po_count_col, late_count_col)
        .filter(PurchaseOrder.supplier_id == supplier_id)
        .one()
    )

    return _supplier_read_with_stats(supplier, po_count, late_count)


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
