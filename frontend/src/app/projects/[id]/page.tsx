import { notFound } from "next/navigation";
import Link from "next/link";

import {
  getProject,
  listProjectMeetings,
  listProjectNCRs,
  listProjectPurchaseOrders,
  listProjectSafetyEvents,
} from "@/lib/api";
import { ApiError } from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/format";
import { StatusBadge } from "@/components/status-badge";
import { RunWeeklyReportButton } from "@/components/agent-actions/RunWeeklyReportButton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export const dynamic = "force-dynamic";

export default async function ProjectDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const projectId = Number(id);
  if (!Number.isInteger(projectId) || projectId < 1) notFound();

  let project;
  try {
    project = await getProject(projectId);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) notFound();
    throw err;
  }

  const [meetings, purchaseOrders, ncrs, safetyEvents] = await Promise.all([
    listProjectMeetings(projectId),
    listProjectPurchaseOrders(projectId),
    listProjectNCRs(projectId),
    listProjectSafetyEvents(projectId),
  ]);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold tracking-tight">{project.project_name}</h1>
            <StatusBadge status={project.status} />
          </div>
          <p className="text-sm text-muted-foreground">
            {project.project_code} · {project.project_type} · {project.city}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 rounded-lg border p-4 md:grid-cols-4">
        <Fact label="Client" value={project.client_name} />
        <Fact label="Budget" value={formatCurrency(project.budget)} />
        <Fact label="Start date" value={formatDate(project.start_date)} />
        <Fact label="Planned finish" value={formatDate(project.planned_finish)} />
        {project.actual_finish && (
          <Fact label="Actual finish" value={formatDate(project.actual_finish)} />
        )}
      </div>

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="meetings">Meetings ({meetings.length})</TabsTrigger>
          <TabsTrigger value="pos">Purchase Orders ({purchaseOrders.length})</TabsTrigger>
          <TabsTrigger value="ncrs">NCRs ({ncrs.length})</TabsTrigger>
          <TabsTrigger value="safety">Safety Events ({safetyEvents.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-4">
          <RunWeeklyReportButton />
        </TabsContent>

        <TabsContent value="meetings" className="mt-4">
          {meetings.length === 0 ? (
            <EmptyState label="No meetings for this project yet." />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Title</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Date</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {meetings.map((m) => (
                  <TableRow key={m.id}>
                    <TableCell className="font-medium">
                      <Link href={`/meetings?meeting=${m.id}`} className="hover:underline">
                        {m.title}
                      </Link>
                    </TableCell>
                    <TableCell>{m.meeting_type}</TableCell>
                    <TableCell>{formatDate(m.meeting_date)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </TabsContent>

        <TabsContent value="pos" className="mt-4">
          {purchaseOrders.length === 0 ? (
            <EmptyState label="No purchase orders for this project yet." />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>PO Number</TableHead>
                  <TableHead>Supplier</TableHead>
                  <TableHead>Promised</TableHead>
                  <TableHead>Actual</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Delay (days)</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {purchaseOrders.map((po) => (
                  <TableRow key={po.id}>
                    <TableCell className="font-medium">{po.po_number}</TableCell>
                    <TableCell>
                      <Link href={`/suppliers/${po.supplier_id}`} className="hover:underline">
                        #{po.supplier_id}
                      </Link>
                    </TableCell>
                    <TableCell>{formatDate(po.promised_delivery)}</TableCell>
                    <TableCell>{po.actual_delivery ? formatDate(po.actual_delivery) : "—"}</TableCell>
                    <TableCell>
                      <StatusBadge status={po.is_late ? "Delayed" : po.status} />
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {po.delay_days > 0 ? po.delay_days : "—"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </TabsContent>

        <TabsContent value="ncrs" className="mt-4">
          {ncrs.length === 0 ? (
            <EmptyState label="No NCRs for this project yet." />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Type</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead>Supplier</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Date</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {ncrs.map((ncr) => (
                  <TableRow key={ncr.id}>
                    <TableCell className="font-medium">{ncr.ncr_type}</TableCell>
                    <TableCell className="max-w-xs truncate">{ncr.description}</TableCell>
                    <TableCell>
                      {ncr.supplier_id ? (
                        <Link href={`/suppliers/${ncr.supplier_id}`} className="hover:underline">
                          #{ncr.supplier_id}
                        </Link>
                      ) : (
                        "—"
                      )}
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
        </TabsContent>

        <TabsContent value="safety" className="mt-4">
          {safetyEvents.length === 0 ? (
            <EmptyState label="No safety events for this project yet." />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Severity</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead>Corrective action</TableHead>
                  <TableHead>Date</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {safetyEvents.map((e) => (
                  <TableRow key={e.id}>
                    <TableCell>
                      <StatusBadge status={e.severity} />
                    </TableCell>
                    <TableCell className="max-w-xs truncate">{e.description}</TableCell>
                    <TableCell className="max-w-xs truncate">{e.corrective_action}</TableCell>
                    <TableCell>{formatDate(e.event_date)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </TabsContent>
      </Tabs>
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

function EmptyState({ label }: { label: string }) {
  return <p className="py-8 text-center text-sm text-muted-foreground">{label}</p>;
}
