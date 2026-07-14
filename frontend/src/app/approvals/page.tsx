"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Check, Loader2, X } from "lucide-react";

import { approveRequest, listApprovals, rejectRequest } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { ApprovalRequest } from "@/lib/types";

export default function ApprovalsPage() {
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<ApprovalRequest | null>(null);
  const [reviewer, setReviewer] = useState("");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState<"approve" | "reject" | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const page = await listApprovals({ status: "pending", limit: 50 });
      setApprovals(page.items);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not load approvals.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Fetch on mount (and this effect is the only caller that runs
    // automatically -- handleReview calls `load` again after a review, which
    // is a user-triggered refresh, not an effect). The lint rule below
    // flags this because it traces into `load`'s own setState calls, but
    // "fetch data when this component mounts" is exactly what an effect is
    // for -- there's no non-effect way to do this without duplicating the
    // fetch logic.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  function openRow(approval: ApprovalRequest) {
    setSelected(approval);
    setReviewer("");
    setNotes("");
  }

  async function handleReview(action: "approve" | "reject") {
    if (!selected || !reviewer.trim()) return;
    setSubmitting(action);
    try {
      const fn = action === "approve" ? approveRequest : rejectRequest;
      await fn(selected.id, { reviewer: reviewer.trim(), notes: notes.trim() || undefined });
      toast.success(action === "approve" ? "Approved." : "Rejected.");
      setSelected(null);
      await load();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setSubmitting(null);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Approvals</h1>
        <p className="text-sm text-muted-foreground">
          Human-in-the-loop queue for actions awaiting review.
        </p>
      </div>

      {loading ? (
        <div className="flex flex-col gap-2">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
      ) : approvals.length === 0 ? (
        <p className="py-12 text-center text-sm text-muted-foreground">
          No pending approvals right now.
        </p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>ID</TableHead>
              <TableHead>Workflow</TableHead>
              <TableHead>Action type</TableHead>
              <TableHead>Reasoning</TableHead>
              <TableHead>Created</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {approvals.map((a) => (
              <TableRow key={a.id} className="cursor-pointer" onClick={() => openRow(a)}>
                <TableCell className="text-muted-foreground">#{a.id}</TableCell>
                <TableCell className="font-medium">{a.workflow}</TableCell>
                <TableCell>
                  <Badge variant="outline">{a.action_type}</Badge>
                </TableCell>
                <TableCell className="max-w-md truncate">{a.reasoning}</TableCell>
                <TableCell>{formatDateTime(a.created_at)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      <Dialog open={selected !== null} onOpenChange={(open) => !open && setSelected(null)}>
        <DialogContent className="sm:max-w-xl">
          {selected && (
            <>
              <DialogHeader>
                <DialogTitle>
                  {selected.workflow} — {selected.action_type}
                </DialogTitle>
                <DialogDescription>Approval request #{selected.id}</DialogDescription>
              </DialogHeader>

              <div className="flex max-h-[50vh] flex-col gap-4 overflow-y-auto">
                <div>
                  <h4 className="mb-1 text-sm font-medium">Reasoning</h4>
                  <p className="text-sm text-muted-foreground">{selected.reasoning}</p>
                </div>

                <div>
                  <h4 className="mb-1 text-sm font-medium">Payload</h4>
                  <pre className="overflow-x-auto rounded-md bg-muted p-2.5 text-xs">
                    {JSON.stringify(selected.payload, null, 2)}
                  </pre>
                </div>

                <div>
                  <h4 className="mb-1 text-sm font-medium">Source IDs</h4>
                  <pre className="overflow-x-auto rounded-md bg-muted p-2.5 text-xs">
                    {JSON.stringify(selected.source_ids, null, 2)}
                  </pre>
                </div>

                <div className="flex flex-col gap-2">
                  <Input
                    placeholder="Reviewer name"
                    value={reviewer}
                    onChange={(e) => setReviewer(e.target.value)}
                  />
                  <Textarea
                    placeholder="Notes (optional)"
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    rows={2}
                  />
                </div>
              </div>

              <DialogFooter>
                <Button
                  variant="destructive"
                  disabled={!reviewer.trim() || submitting !== null}
                  onClick={() => void handleReview("reject")}
                >
                  {submitting === "reject" ? (
                    <Loader2 className="size-4 animate-spin" />
                  ) : (
                    <X className="size-4" />
                  )}
                  Reject
                </Button>
                <Button
                  disabled={!reviewer.trim() || submitting !== null}
                  onClick={() => void handleReview("approve")}
                >
                  {submitting === "approve" ? (
                    <Loader2 className="size-4 animate-spin" />
                  ) : (
                    <Check className="size-4" />
                  )}
                  Approve
                </Button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
