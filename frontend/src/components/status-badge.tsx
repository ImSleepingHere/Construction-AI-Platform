import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

/**
 * Semantic color mapping shared across every status/severity string in the
 * app (project status, PO status, NCR status, safety severity, risk
 * severity, approval status, ...). Falls back to a neutral outline badge
 * for anything unrecognized.
 */
const STATUS_STYLES: Record<string, string> = {
  active: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400",
  delivered: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400",
  completed: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400",
  closed: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400",
  approved: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400",
  low: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400",

  "on hold": "bg-amber-500/15 text-amber-700 dark:text-amber-400",
  "under corrective action": "bg-amber-500/15 text-amber-700 dark:text-amber-400",
  medium: "bg-amber-500/15 text-amber-700 dark:text-amber-400",
  pending: "bg-amber-500/15 text-amber-700 dark:text-amber-400",

  delayed: "bg-red-500/15 text-red-700 dark:text-red-400",
  open: "bg-red-500/15 text-red-700 dark:text-red-400",
  rejected: "bg-red-500/15 text-red-700 dark:text-red-400",
  high: "bg-red-500/15 text-red-700 dark:text-red-400",

  cancelled: "bg-muted text-muted-foreground",
};

export function StatusBadge({ status, className }: { status: string; className?: string }) {
  const style = STATUS_STYLES[status.toLowerCase()];
  return (
    <Badge variant="outline" className={cn("border-transparent font-medium", style, className)}>
      {status}
    </Badge>
  );
}
