import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { MeetingAnalysis } from "@/lib/types";

const SEVERITY_VARIANT = {
  low: "secondary",
  medium: "outline",
  high: "destructive",
} as const;

export function MeetingIntelligenceCard({ data }: { data: MeetingAnalysis }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between gap-2">
          Meeting Analysis
          <Badge variant="outline">
            {Math.round(data.confidence * 100)}% confidence
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <p className="text-sm">{data.summary}</p>

        <Tabs defaultValue="action_items">
          <TabsList>
            <TabsTrigger value="action_items">
              Action Items ({data.action_items.length})
            </TabsTrigger>
            <TabsTrigger value="decisions">Decisions ({data.decisions.length})</TabsTrigger>
            <TabsTrigger value="risks">Risks ({data.risks.length})</TabsTrigger>
          </TabsList>

          <TabsContent value="action_items" className="mt-3">
            {data.action_items.length === 0 ? (
              <EmptyNote>No action items extracted.</EmptyNote>
            ) : (
              <ul className="flex flex-col gap-2">
                {data.action_items.map((item, i) => (
                  <li key={i} className="rounded-md border p-2.5 text-sm">
                    <div className="flex items-start justify-between gap-2">
                      <span>{item.description}</span>
                      <Badge variant={SEVERITY_VARIANT[item.priority]} className="shrink-0">
                        {item.priority}
                      </Badge>
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Owner: {item.owner}
                      {item.due_date ? ` · Due ${item.due_date}` : ""}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </TabsContent>

          <TabsContent value="decisions" className="mt-3">
            {data.decisions.length === 0 ? (
              <EmptyNote>No decisions extracted.</EmptyNote>
            ) : (
              <ul className="flex flex-col gap-2">
                {data.decisions.map((d, i) => (
                  <li key={i} className="rounded-md border p-2.5 text-sm">
                    <p>{d.description}</p>
                    {d.rationale && (
                      <p className="mt-1 text-xs text-muted-foreground">Why: {d.rationale}</p>
                    )}
                    {d.owner && (
                      <p className="mt-1 text-xs text-muted-foreground">Owner: {d.owner}</p>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </TabsContent>

          <TabsContent value="risks" className="mt-3">
            {data.risks.length === 0 ? (
              <EmptyNote>No risks extracted.</EmptyNote>
            ) : (
              <ul className="flex flex-col gap-2">
                {data.risks.map((risk, i) => (
                  <li key={i} className="rounded-md border p-2.5 text-sm">
                    <div className="flex items-start justify-between gap-2">
                      <span>{risk.description}</span>
                      <Badge variant={SEVERITY_VARIANT[risk.severity]} className="shrink-0">
                        {risk.severity}
                      </Badge>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}

function EmptyNote({ children }: { children: React.ReactNode }) {
  return <p className="text-sm text-muted-foreground">{children}</p>;
}
