"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Loader2, ShieldAlert } from "lucide-react";

import { runAgent } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { SupplierRiskCard } from "@/components/agent-results/SupplierRiskCard";
import type { AgentRunResponse, SupplierRiskAssessment } from "@/lib/types";

export function RunSupplierRiskButton({ supplierId }: { supplierId: number }) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AgentRunResponse<SupplierRiskAssessment> | null>(null);

  async function handleRun() {
    setLoading(true);
    try {
      const res = await runAgent<SupplierRiskAssessment>("supplier_risk", {
        supplier_id: supplierId,
      });
      if (!res.output_valid) {
        toast.error(res.error ?? "Risk assessment failed.");
        return;
      }
      setResult(res);
      toast.success("Risk assessment complete.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <Button onClick={handleRun} disabled={loading} className="w-fit">
        {loading ? <Loader2 className="size-4 animate-spin" /> : <ShieldAlert className="size-4" />}
        Run Risk Assessment
      </Button>
      {result && <SupplierRiskCard data={result} />}
    </div>
  );
}
