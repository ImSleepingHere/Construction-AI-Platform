"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { cn } from "@/lib/utils";
import type { WeeklyReport } from "@/lib/types";

export function WeeklyReportCard({ data }: { data: WeeklyReport }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between gap-2">
          Weekly Report — week of {data.week_of}
          <Badge variant="outline">{Math.round(data.confidence * 100)}% confidence</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <p className="text-sm">{data.executive_summary}</p>

        <div className="flex flex-col gap-2">
          {data.sections.map((section, i) => (
            <ReportSection key={i} section={section} defaultOpen={i === 0} />
          ))}
        </div>

        {data.top_recommendations.length > 0 && (
          <div>
            <h4 className="mb-2 text-sm font-medium">Top recommendations</h4>
            <ul className="list-disc space-y-1 pl-4 text-sm">
              {data.top_recommendations.map((rec, i) => (
                <li key={i}>{rec}</li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function ReportSection({
  section,
  defaultOpen,
}: {
  section: WeeklyReport["sections"][number];
  defaultOpen: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <Collapsible open={open} onOpenChange={setOpen} className="rounded-md border">
      <CollapsibleTrigger className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-sm font-medium">
        {section.title}
        <ChevronDown
          className={cn("size-4 shrink-0 text-muted-foreground transition-transform", open && "rotate-180")}
        />
      </CollapsibleTrigger>
      <CollapsibleContent className="border-t px-3 py-2">
        <ul className="list-disc space-y-1 pl-4 text-sm">
          {section.key_points.map((point, i) => (
            <li key={i}>{point}</li>
          ))}
        </ul>
        {section.supporting_data.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {section.supporting_data.map((datum, i) => (
              <Badge key={i} variant="secondary" className="font-normal">
                {datum}
              </Badge>
            ))}
          </div>
        )}
      </CollapsibleContent>
    </Collapsible>
  );
}
