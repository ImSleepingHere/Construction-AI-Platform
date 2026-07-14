import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { SupplierRiskAssessment } from "@/lib/types";

const SEVERITY_VARIANT = {
  low: "secondary",
  medium: "outline",
  high: "destructive",
} as const;

const SEVERITY_BAR_COLOR = {
  low: "bg-emerald-500",
  medium: "bg-amber-500",
  high: "bg-red-500",
} as const;

export function SupplierRiskCard({ data }: { data: SupplierRiskAssessment }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between gap-2">
          <span>
            Supplier Risk — {data.supplier_name}{" "}
            <span className="font-normal text-muted-foreground">#{data.supplier_id}</span>
          </span>
          <Badge variant={SEVERITY_VARIANT[data.overall_severity]}>
            {data.overall_severity}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="flex items-center gap-3">
          <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
            <div
              className={cn(
                "h-full rounded-full transition-all",
                SEVERITY_BAR_COLOR[data.overall_severity],
              )}
              style={{ width: `${data.risk_score}%` }}
            />
          </div>
          <span className="w-10 text-right text-lg font-semibold tabular-nums">
            {data.risk_score}
          </span>
        </div>

        <p className="text-sm">{data.summary}</p>

        <div>
          <h4 className="mb-2 text-sm font-medium">
            Top concerns ({data.top_concerns.length})
          </h4>
          {data.top_concerns.length === 0 ? (
            <p className="text-sm text-muted-foreground">No concerns identified.</p>
          ) : (
            <ul className="flex flex-col gap-2">
              {data.top_concerns.map((concern, i) => (
                <li key={i} className="rounded-md border p-2.5 text-sm">
                  <div className="flex items-start justify-between gap-2">
                    <span>{concern.description}</span>
                    <Badge variant={SEVERITY_VARIANT[concern.severity]} className="shrink-0">
                      {concern.severity}
                    </Badge>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">{concern.evidence}</p>
                </li>
              ))}
            </ul>
          )}
        </div>

        {data.recommendations.length > 0 && (
          <div>
            <h4 className="mb-2 text-sm font-medium">Recommendations</h4>
            <ul className="list-disc space-y-1 pl-4 text-sm">
              {data.recommendations.map((rec, i) => (
                <li key={i}>{rec}</li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
