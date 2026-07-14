"use client";

import { useState } from "react";
import { toast } from "sonner";
import { FileBarChart, Loader2 } from "lucide-react";

import { runAgent } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { WeeklyReportCard } from "@/components/agent-results/WeeklyReportCard";
import type { AgentRunResponse, WeeklyReport } from "@/lib/types";

/**
 * executive_report has no project-scoping input (see SKILL.md/schemas.py --
 * it takes only an optional week_of), so this always runs an unscoped,
 * portfolio-wide report. Labeled accordingly rather than implying it's
 * scoped to wherever this button is rendered.
 */
export function RunWeeklyReportButton() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AgentRunResponse<WeeklyReport> | null>(null);

  async function handleRun() {
    setLoading(true);
    try {
      const res = await runAgent<WeeklyReport>("executive_report", {});
      if (!res.output_valid) {
        toast.error(res.error ?? "Report generation failed.");
        return;
      }
      setResult(res);
      toast.success("Weekly report generated.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <Button onClick={handleRun} disabled={loading} className="w-fit">
        {loading ? (
          <Loader2 className="size-4 animate-spin" />
        ) : (
          <FileBarChart className="size-4" />
        )}
        Run Weekly Report
      </Button>
      <p className="text-xs text-muted-foreground">
        executive_report synthesizes across the whole portfolio — it doesn&apos;t support
        scoping to a single project.
      </p>
      {result && <WeeklyReportCard data={result} />}
    </div>
  );
}
