"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { ChevronLeft, ChevronRight } from "lucide-react";

import { listAuditLogs } from "@/lib/api";
import { formatDateTime, formatLatency } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { AIAuditLog } from "@/lib/types";

const PAGE_SIZE = 50;
const WORKFLOWS = ["hello_world", "meeting_intelligence", "supplier_risk", "executive_report", "chat"];

export default function AuditLogPage() {
  const [logs, setLogs] = useState<AIAuditLog[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [workflow, setWorkflow] = useState("all");
  const [outputValid, setOutputValid] = useState("all");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<AIAuditLog | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const result = await listAuditLogs({
        workflow: workflow === "all" ? undefined : workflow,
        output_valid: outputValid === "all" ? undefined : outputValid === "true",
        date_from: dateFrom ? new Date(dateFrom).toISOString() : undefined,
        date_to: dateTo ? new Date(`${dateTo}T23:59:59`).toISOString() : undefined,
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      });
      setLogs(result.items);
      setTotal(result.total);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not load audit logs.");
    } finally {
      setLoading(false);
    }
  }, [workflow, outputValid, dateFrom, dateTo, page]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- fetch on mount/filter change, see approvals/page.tsx
    void load();
  }, [load]);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const toolCallTrace = selected?.metadata_json?.tool_call_trace;

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Audit Log</h1>
        <p className="text-sm text-muted-foreground">{total} logged LLM calls.</p>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Select
          value={workflow}
          onValueChange={(v) => {
            setWorkflow(v ?? "all");
            setPage(0);
          }}
        >
          <SelectTrigger>
            <SelectValue placeholder="Workflow" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All workflows</SelectItem>
            {WORKFLOWS.map((w) => (
              <SelectItem key={w} value={w}>
                {w}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select
          value={outputValid}
          onValueChange={(v) => {
            setOutputValid(v ?? "all");
            setPage(0);
          }}
        >
          <SelectTrigger>
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            <SelectItem value="true">Valid</SelectItem>
            <SelectItem value="false">Failed</SelectItem>
          </SelectContent>
        </Select>

        <Input
          type="date"
          value={dateFrom}
          onChange={(e) => {
            setDateFrom(e.target.value);
            setPage(0);
          }}
          className="w-auto"
        />
        <span className="text-sm text-muted-foreground">to</span>
        <Input
          type="date"
          value={dateTo}
          onChange={(e) => {
            setDateTo(e.target.value);
            setPage(0);
          }}
          className="w-auto"
        />
      </div>

      {loading ? (
        <div className="flex flex-col gap-2">
          <Skeleton className="h-9 w-full" />
          <Skeleton className="h-9 w-full" />
          <Skeleton className="h-9 w-full" />
        </div>
      ) : logs.length === 0 ? (
        <p className="py-12 text-center text-sm text-muted-foreground">
          No audit log entries match your filters.
        </p>
      ) : (
        <>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>Workflow</TableHead>
                <TableHead>Model</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Latency</TableHead>
                <TableHead>Created</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {logs.map((log) => (
                <TableRow key={log.id} className="cursor-pointer" onClick={() => setSelected(log)}>
                  <TableCell className="text-muted-foreground">#{log.id}</TableCell>
                  <TableCell className="font-medium">{log.workflow}</TableCell>
                  <TableCell className="text-xs text-muted-foreground">{log.model || "—"}</TableCell>
                  <TableCell>
                    <Badge variant={log.output_valid ? "secondary" : "destructive"}>
                      {log.output_valid ? "valid" : "failed"}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {formatLatency(log.latency_ms)}
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {formatDateTime(log.created_at)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              Page {page + 1} of {totalPages}
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page === 0}
                onClick={() => setPage((p) => Math.max(0, p - 1))}
              >
                <ChevronLeft className="size-4" />
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={page + 1 >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
                <ChevronRight className="size-4" />
              </Button>
            </div>
          </div>
        </>
      )}

      <Dialog open={selected !== null} onOpenChange={(open) => !open && setSelected(null)}>
        <DialogContent className="sm:max-w-2xl">
          {selected && (
            <>
              <DialogHeader>
                <DialogTitle>
                  {selected.workflow} — #{selected.id}
                </DialogTitle>
                <DialogDescription>{formatDateTime(selected.created_at)}</DialogDescription>
              </DialogHeader>

              <div className="flex max-h-[60vh] flex-col gap-4 overflow-y-auto">
                {selected.error && (
                  <div>
                    <h4 className="mb-1 text-sm font-medium text-destructive">Error</h4>
                    <p className="text-sm text-destructive">{selected.error}</p>
                  </div>
                )}

                <div>
                  <h4 className="mb-1 text-sm font-medium">Prompt</h4>
                  <pre className="max-h-40 overflow-auto rounded-md bg-muted p-2.5 text-xs whitespace-pre-wrap">
                    {selected.prompt}
                  </pre>
                </div>

                <div>
                  <h4 className="mb-1 text-sm font-medium">Output</h4>
                  <pre className="max-h-40 overflow-auto rounded-md bg-muted p-2.5 text-xs whitespace-pre-wrap">
                    {selected.output ?? "—"}
                  </pre>
                </div>

                {selected.retrieved_source_ids && selected.retrieved_source_ids.length > 0 && (
                  <div>
                    <h4 className="mb-1 text-sm font-medium">Retrieved sources</h4>
                    <pre className="overflow-x-auto rounded-md bg-muted p-2.5 text-xs">
                      {JSON.stringify(selected.retrieved_source_ids, null, 2)}
                    </pre>
                  </div>
                )}

                {Array.isArray(toolCallTrace) && toolCallTrace.length > 0 && (
                  <div>
                    <h4 className="mb-1 text-sm font-medium">Tool call trace</h4>
                    <pre className="overflow-x-auto rounded-md bg-muted p-2.5 text-xs">
                      {JSON.stringify(toolCallTrace, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
