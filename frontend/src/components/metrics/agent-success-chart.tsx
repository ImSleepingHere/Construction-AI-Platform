"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export interface AgentSuccessPoint {
  workflow: string;
  successRate: number;
}

export function AgentSuccessChart({ data }: { data: AgentSuccessPoint[] }) {
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} className="stroke-border" />
        <XAxis dataKey="workflow" tickLine={false} axisLine={false} fontSize={11} />
        <YAxis
          domain={[0, 100]}
          tickFormatter={(v: number) => `${v}%`}
          tickLine={false}
          axisLine={false}
          fontSize={12}
          width={36}
        />
        <Tooltip
          cursor={{ fill: "var(--muted)" }}
          formatter={(value) => [`${value}%`, "Success rate"]}
          contentStyle={{
            background: "var(--popover)",
            color: "var(--popover-foreground)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius)",
            fontSize: 12,
          }}
        />
        <Bar dataKey="successRate" fill="var(--chart-3)" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
