import { getMetricsAgents, getMetricsOverview, getMetricsTools, listAuditLogs } from "@/lib/api";
import { formatCurrency, formatNumber, formatPercent } from "@/lib/format";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { CallsPerDayChart, type CallsPerDayPoint } from "@/components/metrics/calls-per-day-chart";
import {
  LatencyHistogramChart,
  type LatencyBucket,
} from "@/components/metrics/latency-histogram-chart";
import { AgentSuccessChart, type AgentSuccessPoint } from "@/components/metrics/agent-success-chart";
import type { AIAuditLog } from "@/lib/types";

// Observability page -- always fetch fresh data, never cache.
export const dynamic = "force-dynamic";

const HISTORY_DAYS = 14;
const AUDIT_SAMPLE_LIMIT = 500;

function buildCallsPerDay(auditLogs: AIAuditLog[]): CallsPerDayPoint[] {
  const counts = new Map<string, number>();
  for (let i = HISTORY_DAYS - 1; i >= 0; i--) {
    const d = new Date();
    d.setUTCDate(d.getUTCDate() - i);
    counts.set(d.toISOString().slice(0, 10), 0);
  }

  for (const log of auditLogs) {
    const key = new Date(log.created_at).toISOString().slice(0, 10);
    if (counts.has(key)) counts.set(key, (counts.get(key) ?? 0) + 1);
  }

  return Array.from(counts.entries()).map(([key, calls]) => ({
    label: new Date(`${key}T00:00:00Z`).toLocaleDateString(undefined, {
      month: "numeric",
      day: "numeric",
      timeZone: "UTC",
    }),
    calls,
  }));
}

const LATENCY_BUCKETS: { label: string; max: number }[] = [
  { label: "0-1s", max: 1000 },
  { label: "1-2s", max: 2000 },
  { label: "2-5s", max: 5000 },
  { label: "5-10s", max: 10000 },
  { label: "10s+", max: Infinity },
];

function buildLatencyHistogram(auditLogs: AIAuditLog[]): LatencyBucket[] {
  const counts = new Map(LATENCY_BUCKETS.map((b) => [b.label, 0]));

  for (const log of auditLogs) {
    if (log.latency_ms === null) continue;
    const bucket = LATENCY_BUCKETS.find((b) => log.latency_ms! <= b.max);
    if (bucket) counts.set(bucket.label, (counts.get(bucket.label) ?? 0) + 1);
  }

  return LATENCY_BUCKETS.map((b) => ({ label: b.label, count: counts.get(b.label) ?? 0 }));
}

export default async function MetricsPage() {
  const [overview, agents, tools, auditPage] = await Promise.all([
    getMetricsOverview().catch(() => null),
    getMetricsAgents().catch(() => []),
    getMetricsTools().catch(() => []),
    listAuditLogs({ limit: AUDIT_SAMPLE_LIMIT }).catch(() => null),
  ]);

  const auditLogs = auditPage?.items ?? [];
  const callsPerDay = buildCallsPerDay(auditLogs);
  const latencyHistogram = buildLatencyHistogram(auditLogs);
  const agentSuccess: AgentSuccessPoint[] = agents.map((m) => ({
    workflow: m.workflow,
    successRate: Math.round(m.success_rate * 100),
  }));

  const totalRuns = agents.reduce((sum, m) => sum + m.total_runs, 0);
  const weightedSuccessRate =
    totalRuns > 0
      ? agents.reduce((sum, m) => sum + m.success_rate * m.total_runs, 0) / totalRuns
      : null;

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Metrics</h1>
        <p className="text-sm text-muted-foreground">
          Observability for the AI agent framework -- LLM calls, latency, and tool usage.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          label="Total LLM Calls"
          value={overview ? formatNumber(overview.total_llm_calls) : "—"}
        />
        <StatCard
          label="Total Tokens"
          value={overview ? formatNumber(overview.total_tokens) : "—"}
        />
        <StatCard
          label="Estimated Cost"
          value={overview ? formatCurrency(overview.estimated_cost_usd) : "—"}
        />
        <StatCard
          label="Success Rate"
          value={weightedSuccessRate !== null ? formatPercent(weightedSuccessRate) : "—"}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>LLM calls per day</CardTitle>
            <CardDescription>Last {HISTORY_DAYS} days, from a sample of the most recent {AUDIT_SAMPLE_LIMIT} audit log entries.</CardDescription>
          </CardHeader>
          <CardContent>
            <CallsPerDayChart data={callsPerDay} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Latency distribution</CardTitle>
            <CardDescription>Bucketed response times across the sampled calls.</CardDescription>
          </CardHeader>
          <CardContent>
            <LatencyHistogramChart data={latencyHistogram} />
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Success rate by agent</CardTitle>
            <CardDescription>Share of runs that produced valid output.</CardDescription>
          </CardHeader>
          <CardContent>
            {agentSuccess.length > 0 ? (
              <AgentSuccessChart data={agentSuccess} />
            ) : (
              <p className="py-12 text-center text-sm text-muted-foreground">
                No agent runs recorded yet.
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Tool invocations</CardTitle>
            <CardDescription>Usage across all agent tool calls.</CardDescription>
          </CardHeader>
          <CardContent>
            {tools.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Tool</TableHead>
                    <TableHead className="text-right">Invocations</TableHead>
                    <TableHead className="text-right">Avg output size</TableHead>
                    <TableHead className="text-right">Error rate</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {tools.map((t) => (
                    <TableRow key={t.tool}>
                      <TableCell className="font-medium">{t.tool}</TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatNumber(t.total_invocations)}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatNumber(Math.round(t.avg_output_size_chars))} chars
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatPercent(t.error_rate)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <p className="py-12 text-center text-sm text-muted-foreground">
                No tool invocations recorded yet.
              </p>
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
