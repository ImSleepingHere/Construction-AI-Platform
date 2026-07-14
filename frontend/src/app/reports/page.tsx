"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { FileBarChart, Loader2 } from "lucide-react";

import { listAuditLogs, runAgent } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { WeeklyReportCard } from "@/components/agent-results/WeeklyReportCard";
import type { AIAuditLog, WeeklyReport } from "@/lib/types";

/** executive_report is scheduled every Monday 09:00 UTC (see backend/app/main.py). */
function nextMondayNineUTC(): Date {
  const now = new Date();
  const result = new Date(now);
  result.setUTCHours(9, 0, 0, 0);
  const day = result.getUTCDay(); // 0 = Sunday, 1 = Monday, ...
  let daysUntilMonday = (1 - day + 7) % 7;
  if (daysUntilMonday === 0 && result.getTime() <= now.getTime()) daysUntilMonday = 7;
  result.setUTCDate(result.getUTCDate() + daysUntilMonday);
  return result;
}

function parseWeekOf(output: string | null): string {
  if (!output) return "—";
  try {
    const parsed = JSON.parse(output) as Partial<WeeklyReport>;
    return parsed.week_of ?? "—";
  } catch {
    return "—";
  }
}

export default function ReportsPage() {
  const [reports, setReports] = useState<AIAuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [selectedLogId, setSelectedLogId] = useState<number | null>(null);
  const [selectedReport, setSelectedReport] = useState<WeeklyReport | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const page = await listAuditLogs({ workflow: "executive_report", limit: 20 });
      setReports(page.items);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not load reports.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- fetch on mount, see approvals/page.tsx for rationale
    void load();
  }, [load]);

  function viewReport(log: AIAuditLog) {
    if (!log.output) {
      toast.error("This report has no output to display.");
      return;
    }
    try {
      setSelectedReport(JSON.parse(log.output) as WeeklyReport);
      setSelectedLogId(log.id);
    } catch {
      toast.error("Could not parse this report's output.");
    }
  }

  async function handleGenerate() {
    setGenerating(true);
    try {
      const res = await runAgent<WeeklyReport>("executive_report", {});
      if (!res.output_valid) {
        toast.error(res.error ?? "Report generation failed.");
        return;
      }
      setSelectedReport(res);
      setSelectedLogId(res.audit_log_id);
      toast.success("Weekly report generated.");
      await load();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Reports</h1>
          <p className="text-sm text-muted-foreground">
            Scheduled: every Monday 09:00 UTC. Next run: {formatDateTime(nextMondayNineUTC().toISOString())}
          </p>
        </div>
        <Button onClick={handleGenerate} disabled={generating}>
          {generating ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <FileBarChart className="size-4" />
          )}
          Generate this week&apos;s report
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[360px_1fr]">
        <div>
          <h2 className="mb-3 text-sm font-medium text-muted-foreground">Previous reports</h2>
          {loading ? (
            <div className="flex flex-col gap-2">
              <Skeleton className="h-9 w-full" />
              <Skeleton className="h-9 w-full" />
            </div>
          ) : reports.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">
              No reports generated yet.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Week of</TableHead>
                  <TableHead>Generated</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {reports.map((log) => (
                  <TableRow
                    key={log.id}
                    className={cn("cursor-pointer", selectedLogId === log.id && "bg-muted")}
                    onClick={() => viewReport(log)}
                  >
                    <TableCell className="font-medium">{parseWeekOf(log.output)}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {formatDateTime(log.created_at)}
                    </TableCell>
                    <TableCell>
                      <Badge variant={log.output_valid ? "secondary" : "destructive"}>
                        {log.output_valid ? "valid" : "failed"}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </div>

        <div>
          {selectedReport ? (
            <WeeklyReportCard data={selectedReport} />
          ) : (
            <p className="py-12 text-center text-sm text-muted-foreground">
              Generate a report or select a previous one to view it here.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
