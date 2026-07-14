import Link from "next/link";
import { CalendarDays, FileBarChart, ShieldAlert } from "lucide-react";

import { getMetricsOverview, listAgents, listAuditLogs, listProjects } from "@/lib/api";
import { formatCurrency, formatLatency, formatNumber, formatRelativeTime } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { StatusBadge } from "@/components/status-badge";
import { ActivityChart, type DailyActivityPoint } from "@/components/dashboard/activity-chart";
import type { AIAuditLog } from "@/lib/types";

// Live ops dashboard -- always fetch fresh data, never cache.
export const dynamic = "force-dynamic";

function buildActivityBuckets(auditLogs: AIAuditLog[]): DailyActivityPoint[] {
  const counts = new Map<string, number>();
  for (let i = 6; i >= 0; i--) {
    const d = new Date();
    d.setUTCDate(d.getUTCDate() - i);
    counts.set(d.toISOString().slice(0, 10), 0);
  }

  for (const log of auditLogs) {
    const key = new Date(log.created_at).toISOString().slice(0, 10);
    if (counts.has(key)) counts.set(key, (counts.get(key) ?? 0) + 1);
  }

  return Array.from(counts.entries()).map(([key, runs]) => ({
    label: new Date(`${key}T00:00:00Z`).toLocaleDateString(undefined, {
      weekday: "short",
      day: "numeric",
      timeZone: "UTC",
    }),
    runs,
  }));
}

export default async function DashboardPage() {
  const [overview, agents, recentLogs, chartLogs, projects] = await Promise.all([
    getMetricsOverview().catch(() => null),
    listAgents().catch(() => []),
    listAuditLogs({ limit: 5 }).catch(() => null),
    listAuditLogs({ limit: 200 }).catch(() => null),
    listProjects({ limit: 100 }).catch(() => []),
  ]);

  const atRiskProjects = projects.filter((p) => p.status === "Delayed").slice(0, 5);
  const activityData = buildActivityBuckets(chartLogs?.items ?? []);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <p className="text-sm text-muted-foreground">
          Overview of the AI agent framework and portfolio status.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Total Projects" value={formatNumber(projects.length)} />
        <StatCard label="Active Agents" value={formatNumber(agents.length)} />
        <StatCard
          label="Recent AI Runs"
          value={overview ? formatNumber(overview.total_llm_calls) : "—"}
        />
        <StatCard
          label="Estimated Cost"
          value={overview ? formatCurrency(overview.estimated_cost_usd) : "—"}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>AI activity, last 7 days</CardTitle>
            <CardDescription>Agent + chat runs logged per day.</CardDescription>
          </CardHeader>
          <CardContent>
            <ActivityChart data={activityData} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Quick actions</CardTitle>
            <CardDescription>Jump straight into a workflow.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            <Button render={<Link href="/meetings" />} variant="secondary" className="justify-start gap-2">
              <CalendarDays className="size-4" />
              Analyze a meeting
            </Button>
            <Button render={<Link href="/suppliers" />} variant="secondary" className="justify-start gap-2">
              <ShieldAlert className="size-4" />
              Assess a supplier
            </Button>
            <Button render={<Link href="/reports" />} variant="secondary" className="justify-start gap-2">
              <FileBarChart className="size-4" />
              Generate weekly report
            </Button>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Recent activity</CardTitle>
            <CardDescription>Last 5 agent/chat runs.</CardDescription>
          </CardHeader>
          <CardContent>
            {recentLogs && recentLogs.items.length > 0 ? (
              <ul className="flex flex-col divide-y">
                {recentLogs.items.map((log) => (
                  <li key={log.id} className="flex items-center justify-between gap-3 py-2.5">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="truncate text-sm font-medium">{log.workflow}</span>
                        <Badge variant={log.output_valid ? "secondary" : "destructive"}>
                          {log.output_valid ? "valid" : "failed"}
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        {formatRelativeTime(log.created_at)}
                      </p>
                    </div>
                    <span className="shrink-0 text-xs text-muted-foreground">
                      {formatLatency(log.latency_ms)}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted-foreground">No agent runs yet.</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Top at-risk projects</CardTitle>
            <CardDescription>Projects currently marked Delayed.</CardDescription>
          </CardHeader>
          <CardContent>
            {atRiskProjects.length > 0 ? (
              <ul className="flex flex-col divide-y">
                {atRiskProjects.map((project) => (
                  <li key={project.id} className="flex items-center justify-between gap-3 py-2.5">
                    <div className="min-w-0">
                      <Link
                        href={`/projects/${project.id}`}
                        className="truncate text-sm font-medium hover:underline"
                      >
                        {project.project_name}
                      </Link>
                      <p className="text-xs text-muted-foreground">{project.city}</p>
                    </div>
                    <StatusBadge status={project.status} />
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted-foreground">No delayed projects right now.</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <CardContent className="py-2">
        <p className="text-sm text-muted-foreground">{label}</p>
        <p className="text-2xl font-semibold tracking-tight">{value}</p>
      </CardContent>
    </Card>
  );
}
