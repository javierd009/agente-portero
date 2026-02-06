"""Reports API - Incident and maintenance reports"""
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from infrastructure.database import get_session
from domain.models import Report
from domain.models.report import ReportCreate, ReportRead, ReportUpdate

router = APIRouter()


def get_tenant_id(x_tenant_id: UUID = Header(..., description="Tenant/Condominium ID")) -> UUID:
    """Extract tenant ID from header for multi-tenant isolation"""
    return x_tenant_id


@router.get("/", response_model=List[ReportRead])
async def list_reports(
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    report_type: Optional[str] = None,
    resident_id: Optional[UUID] = None,
):
    """List all reports for a condominium"""
    query = select(Report).where(Report.condominium_id == tenant_id)

    if status:
        query = query.where(Report.status == status)

    if report_type:
        query = query.where(Report.report_type == report_type)

    if resident_id:
        query = query.where(Report.resident_id == resident_id)

    query = query.offset(skip).limit(limit).order_by(Report.created_at.desc())
    result = await session.execute(query)
    return result.scalars().all()


@router.post("/", response_model=ReportRead, status_code=201)
async def create_report(
    report: ReportCreate,
    session: AsyncSession = Depends(get_session),
):
    """
    Create a new report
    Note: No tenant_id header required - comes from payload
    Used by WhatsApp service
    """
    db_report = Report.model_validate(report)
    session.add(db_report)
    await session.commit()
    await session.refresh(db_report)
    return db_report


@router.get("/{report_id}", response_model=ReportRead)
async def get_report(
    report_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Get a specific report by ID"""
    query = select(Report).where(
        Report.id == report_id,
        Report.condominium_id == tenant_id
    )
    result = await session.execute(query)
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    return report


@router.patch("/{report_id}", response_model=ReportRead)
async def update_report(
    report_id: UUID,
    report_update: ReportUpdate,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Update a report (change status, assign, resolve)"""
    query = select(Report).where(
        Report.id == report_id,
        Report.condominium_id == tenant_id
    )
    result = await session.execute(query)
    db_report = result.scalar_one_or_none()

    if not db_report:
        raise HTTPException(status_code=404, detail="Report not found")

    update_data = report_update.model_dump(exclude_unset=True)

    # Auto-set resolved_at if status changes to resolved
    if update_data.get("status") == "resolved" and db_report.status != "resolved":
        update_data["resolved_at"] = datetime.utcnow()

    for key, value in update_data.items():
        setattr(db_report, key, value)

    db_report.updated_at = datetime.utcnow()

    session.add(db_report)
    await session.commit()
    await session.refresh(db_report)
    return db_report


@router.delete("/{report_id}", status_code=204)
async def delete_report(
    report_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Delete a report"""
    query = select(Report).where(
        Report.id == report_id,
        Report.condominium_id == tenant_id
    )
    result = await session.execute(query)
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    await session.delete(report)
    await session.commit()
    return None


@router.get("/stats/summary")
async def get_report_stats(
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Get report statistics for a condominium"""
    # Count reports by status
    query = select(Report).where(Report.condominium_id == tenant_id)
    result = await session.execute(query)
    all_reports = result.scalars().all()

    stats = {
        "total": len(all_reports),
        "by_status": {},
        "by_type": {},
        "by_urgency": {},
        "pending": 0,
        "in_progress": 0,
        "resolved": 0,
    }

    for report in all_reports:
        # By status
        stats["by_status"][report.status] = stats["by_status"].get(report.status, 0) + 1

        # By type
        stats["by_type"][report.report_type] = stats["by_type"].get(report.report_type, 0) + 1

        # By urgency
        stats["by_urgency"][report.urgency] = stats["by_urgency"].get(report.urgency, 0) + 1

        # Quick counts
        if report.status == "pending":
            stats["pending"] += 1
        elif report.status == "in_progress":
            stats["in_progress"] += 1
        elif report.status == "resolved":
            stats["resolved"] += 1

    return stats
