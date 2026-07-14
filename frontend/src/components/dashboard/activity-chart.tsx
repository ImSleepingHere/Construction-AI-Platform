"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export interface DailyActivityPoint {
  /** e.g. "Mon 14" */
  label: string;
  runs: number;
}

export function ActivityChart({ data }: { data: DailyActivityPoint[] }) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} className="stroke-border" />
        <XAxis
          dataKey="label"
          tickLine={false}
          axisLine={false}
          fontSize={12}
          className="fill-muted-foreground"
        />
        <YAxis
          allowDecimals={false}
          tickLine={false}
          axisLine={false}
          fontSize={12}
          className="fill-muted-foreground"
          width={32}
        />
        <Tooltip
          cursor={{ fill: "var(--muted)" }}
          contentStyle={{
            background: "var(--popover)",
            color: "var(--popover-foreground)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius)",
            fontSize: 12,
          }}
        />
        <Bar dataKey="runs" fill="var(--primary)" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
