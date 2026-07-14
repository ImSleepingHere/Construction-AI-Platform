import { notFound } from "next/navigation";
import Link from "next/link";

import { ApiError, getSupplier, listMemories, listSupplierNCRs, listSupplierPurchaseOrders } from "@/lib/api";
import { formatDate, formatPercent, formatRelativeTime } from "@/lib/format";
import { StatusBadge } from "@/components/status-badge";
import { RunSupplierRiskButton } from "@/components/agent-actions/RunSupplierRiskButton";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export const dynamic = "force-dynamic";

export default async function SupplierDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const supplierId = Number(id);
  if (!Number.isInteger(supplierId) || supplierId < 1) notFound();

  let supplier;
  try {
    supplier = await getSupplier(supplierId);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) notFound();
    throw err;
  }

  const [purchaseOrders, ncrs, priorAssessments] = await Promise.all([
    listSupplierPurchaseOrders(supplierId),
    listSupplierNCRs(supplierId),
    listMemories({ category: "risk_assessment", search: supplier.supplier_name }),
  ]);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold tracking-tight">{supplier.supplier_name}</h1>
            <StatusBadge status={supplier.status} />
          </div>
          <p className="text-sm text-muted-foreground">
            {supplier.category} · {supplier.city} · #{supplier.id}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 rounded-lg border p-4 md:grid-cols-4">
        <Fact label="Purchase orders" value={String(supplier.po_count)} />
        <Fact
          label="On-time rate"
          value={supplier.on_time_rate !== null ? formatPercent(supplier.on_time_rate) : "—"}
        />
        <Fact label="Open NCRs" value={String(ncrs.filter((n) => n.status === "Open").length)} />
        <Fact label="Total NCRs" value={String(ncrs.length)} />
      </div>

      <RunSupplierRiskButton supplierId={supplierId} />

      {priorAssessments.items.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Previous risk assessments</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="flex flex-col divide-y">
              {priorAssessments.items.map((memory) => (
                <li key={memory.id} className="py-2.5 text-sm">
                  <p>{memory.content}</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {formatRelativeTime(memory.created_at)} · confidence{" "}
                    {Math.round(memory.confidence * 100)}%
                  </p>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <section>
          <h2 className="mb-3 text-lg font-medium">Delivery history</h2>
          {purchaseOrders.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">
              No purchase orders for this supplier yet.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>PO Number</TableHead>
                  <TableHead>Project</TableHead>
                  <TableHead>Promised</TableHead>
                  <TableHead className="text-right">Delay (days)</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {purchaseOrders.map((po) => (
                  <TableRow key={po.id}>
                    <TableCell className="font-medium">{po.po_number}</TableCell>
                    <TableCell>
                      <Link href={`/projects/${po.project_id}`} className="hover:underline">
                        #{po.project_id}
                      </Link>
                    </TableCell>
                    <TableCell>{formatDate(po.promised_delivery)}</TableCell>
                    <TableCell className="text-right tabular-nums">
                      {po.delay_days > 0 ? po.delay_days : "—"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </section>

        <section>
          <h2 className="mb-3 text-lg font-medium">Quality issues</h2>
          {ncrs.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">
              No NCRs for this supplier yet.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Type</TableHead>
                  <TableHead>Project</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Date</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {ncrs.map((ncr) => (
                  <TableRow key={ncr.id}>
                    <TableCell className="font-medium">{ncr.ncr_type}</TableCell>
                    <TableCell>
                      <Link href={`/projects/${ncr.project_id}`} className="hover:underline">
                        #{ncr.project_id}
                      </Link>
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={ncr.status} />
                    </TableCell>
                    <TableCell>{formatDate(ncr.issue_date)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </section>
      </div>
    </div>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-sm font-medium">{value}</p>
    </div>
  );
}
