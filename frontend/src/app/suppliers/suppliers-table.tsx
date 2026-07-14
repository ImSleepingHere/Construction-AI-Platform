"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { StatusBadge } from "@/components/status-badge";
import { formatPercent } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Supplier } from "@/lib/types";

type SortKey = "supplier_name" | "category" | "city" | "po_count" | "on_time_rate";

const COLUMNS: { key: SortKey; label: string; align?: "right" }[] = [
  { key: "supplier_name", label: "Name" },
  { key: "category", label: "Category" },
  { key: "city", label: "City" },
  { key: "po_count", label: "PO Count", align: "right" },
  { key: "on_time_rate", label: "On-time Rate", align: "right" },
];

export function SuppliersTable({ suppliers }: { suppliers: Supplier[] }) {
  const router = useRouter();
  const [category, setCategory] = useState("all");
  const [city, setCity] = useState("all");
  const [sortKey, setSortKey] = useState<SortKey>("supplier_name");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  const categories = useMemo(
    () => Array.from(new Set(suppliers.map((s) => s.category))).sort(),
    [suppliers],
  );
  const cities = useMemo(
    () => Array.from(new Set(suppliers.map((s) => s.city))).sort(),
    [suppliers],
  );

  const filtered = useMemo(() => {
    const result = suppliers.filter((s) => {
      if (category !== "all" && s.category !== category) return false;
      if (city !== "all" && s.city !== city) return false;
      return true;
    });

    return result.sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      let cmp: number;
      if (typeof av === "string" && typeof bv === "string") {
        cmp = av.localeCompare(bv);
      } else {
        cmp = (av ?? -1 as number) < (bv ?? -1 as number) ? -1 : (av ?? -1) > (bv ?? -1) ? 1 : 0;
      }
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [suppliers, category, city, sortKey, sortDir]);

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-2">
        <Select value={category} onValueChange={(v) => setCategory(v ?? "all")}>
          <SelectTrigger>
            <SelectValue placeholder="Category" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All categories</SelectItem>
            {categories.map((c) => (
              <SelectItem key={c} value={c}>
                {c}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={city} onValueChange={(v) => setCity(v ?? "all")}>
          <SelectTrigger>
            <SelectValue placeholder="City" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All cities</SelectItem>
            {cities.map((c) => (
              <SelectItem key={c} value={c}>
                {c}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <span className="text-sm text-muted-foreground">
          {filtered.length} of {suppliers.length} suppliers
        </span>
      </div>

      {filtered.length === 0 ? (
        <p className="py-12 text-center text-sm text-muted-foreground">
          No suppliers match your filters.
        </p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              {COLUMNS.map((col) => (
                <TableHead key={col.key} className={col.align === "right" ? "text-right" : ""}>
                  <button
                    type="button"
                    onClick={() => toggleSort(col.key)}
                    className={cn(
                      "inline-flex items-center gap-1 hover:text-foreground",
                      col.align === "right" && "flex-row-reverse",
                    )}
                  >
                    {col.label}
                    {sortKey === col.key ? (
                      sortDir === "asc" ? (
                        <ArrowUp className="size-3.5" />
                      ) : (
                        <ArrowDown className="size-3.5" />
                      )
                    ) : (
                      <ArrowUpDown className="size-3.5 opacity-40" />
                    )}
                  </button>
                </TableHead>
              ))}
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.map((supplier) => (
              <TableRow
                key={supplier.id}
                className="cursor-pointer"
                onClick={() => router.push(`/suppliers/${supplier.id}`)}
              >
                <TableCell className="font-medium">{supplier.supplier_name}</TableCell>
                <TableCell>{supplier.category}</TableCell>
                <TableCell>{supplier.city}</TableCell>
                <TableCell className="text-right tabular-nums">{supplier.po_count}</TableCell>
                <TableCell className="text-right tabular-nums">
                  {supplier.on_time_rate !== null ? formatPercent(supplier.on_time_rate) : "—"}
                </TableCell>
                <TableCell>
                  <StatusBadge status={supplier.status} />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
