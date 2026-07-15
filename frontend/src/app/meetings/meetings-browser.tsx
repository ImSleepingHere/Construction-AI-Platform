"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { Loader2, Sparkles, Upload } from "lucide-react";

import { getMeeting, runAgent } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { extractPdfText } from "@/lib/pdf";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { MeetingIntelligenceCard } from "@/components/agent-results/MeetingIntelligenceCard";
import type { AgentRunResponse, Meeting, MeetingAnalysis, MeetingWithDecisions, Project } from "@/lib/types";

export function MeetingsBrowser({
  meetings,
  projects,
}: {
  meetings: Meeting[];
  projects: Project[];
}) {
  const [projectFilter, setProjectFilter] = useState("all");
  const [selectedId, setSelectedId] = useState<number | null>(meetings[0]?.id ?? null);
  const [selectedMeeting, setSelectedMeeting] = useState<MeetingWithDecisions | null>(null);
  const [loadingMeeting, setLoadingMeeting] = useState(false);
  const [notes, setNotes] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [extractingPdf, setExtractingPdf] = useState(false);
  const [uploadedFileName, setUploadedFileName] = useState<string | null>(null);
  const [result, setResult] = useState<AgentRunResponse<MeetingAnalysis> | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const projectName = useMemo(() => {
    const map = new Map(projects.map((p) => [p.id, p.project_name]));
    return (id: number) => map.get(id) ?? `Project #${id}`;
  }, [projects]);

  const filteredMeetings = useMemo(() => {
    if (projectFilter === "all") return meetings;
    const pid = Number(projectFilter);
    return meetings.filter((m) => m.project_id === pid);
  }, [meetings, projectFilter]);

  useEffect(() => {
    // Wrapped in an async function (rather than setState calls directly in
    // the effect body) so this reads as "subscribe to selectedId, fetch
    // when it changes" rather than a synchronous cascading-render pattern.
    let cancelled = false;

    async function load() {
      if (selectedId === null) {
        if (!cancelled) setSelectedMeeting(null);
        return;
      }
      setLoadingMeeting(true);
      setResult(null);
      try {
        const meeting = await getMeeting(selectedId);
        if (!cancelled) setSelectedMeeting(meeting);
      } catch {
        if (!cancelled) toast.error("Could not load meeting details.");
      } finally {
        if (!cancelled) setLoadingMeeting(false);
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [selectedId]);

  async function handleAnalyzeMeeting() {
    if (selectedId === null) return;
    setAnalyzing(true);
    try {
      const res = await runAgent<MeetingAnalysis>("meeting_intelligence", {
        meeting_id: selectedId,
      });
      if (!res.output_valid) {
        toast.error(res.error ?? "Analysis failed.");
        return;
      }
      setResult(res);
      toast.success("Meeting analyzed.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setAnalyzing(false);
    }
  }

  async function handlePdfSelected(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;

    if (file.type !== "application/pdf") {
      toast.error("Please choose a PDF file.");
      return;
    }

    setExtractingPdf(true);
    try {
      const text = await extractPdfText(file);
      if (!text) {
        toast.error("No extractable text found in this PDF (it may be a scanned image).");
        return;
      }
      setNotes(text);
      setUploadedFileName(file.name);
      toast.success(`Extracted text from ${file.name}.`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not read this PDF.");
    } finally {
      setExtractingPdf(false);
    }
  }

  async function handleAnalyzeNotes() {
    if (!notes.trim()) return;
    setAnalyzing(true);
    try {
      const res = await runAgent<MeetingAnalysis>("meeting_intelligence", { notes });
      if (!res.output_valid) {
        toast.error(res.error ?? "Analysis failed.");
        return;
      }
      setResult(res);
      toast.success("Notes analyzed.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setAnalyzing(false);
    }
  }

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[320px_1fr]">
      <div className="flex flex-col gap-3">
        <Select value={projectFilter} onValueChange={(v) => setProjectFilter(v ?? "all")}>
          <SelectTrigger className="w-full">
            <SelectValue placeholder="Filter by project" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All projects</SelectItem>
            {projects.map((p) => (
              <SelectItem key={p.id} value={String(p.id)}>
                {p.project_name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <ScrollArea className="h-[calc(100vh-14rem)] rounded-lg border">
          {filteredMeetings.length === 0 ? (
            <p className="p-4 text-sm text-muted-foreground">No meetings for this project.</p>
          ) : (
            <ul className="divide-y">
              {filteredMeetings.map((m) => (
                <li key={m.id}>
                  <button
                    type="button"
                    onClick={() => setSelectedId(m.id)}
                    className={cn(
                      "w-full px-3 py-2.5 text-left text-sm transition-colors hover:bg-muted",
                      selectedId === m.id && "bg-muted",
                    )}
                  >
                    <p className="font-medium">{m.title}</p>
                    <p className="text-xs text-muted-foreground">
                      {projectName(m.project_id)} · {formatDate(m.meeting_date)}
                    </p>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </ScrollArea>
      </div>

      <div className="flex flex-col gap-4">
        <Tabs defaultValue="meeting">
          <TabsList>
            <TabsTrigger value="meeting">Selected meeting</TabsTrigger>
            <TabsTrigger value="notes">Analyze notes / PDF</TabsTrigger>
          </TabsList>

          <TabsContent value="meeting" className="mt-4 flex flex-col gap-4">
            {loadingMeeting ? (
              <Skeleton className="h-32 w-full" />
            ) : selectedMeeting ? (
              <div className="rounded-lg border p-4">
                <h2 className="text-lg font-medium">{selectedMeeting.title}</h2>
                <p className="text-sm text-muted-foreground">
                  {projectName(selectedMeeting.project_id)} · {selectedMeeting.meeting_type} ·{" "}
                  {formatDate(selectedMeeting.meeting_date)}
                </p>
                {selectedMeeting.decisions.length > 0 && (
                  <div className="mt-3">
                    <h3 className="mb-1.5 text-sm font-medium">Decisions on file</h3>
                    <ul className="list-disc space-y-1 pl-4 text-sm">
                      {selectedMeeting.decisions.map((d) => (
                        <li key={d.id}>
                          {d.decision_text}{" "}
                          <span className="text-muted-foreground">— {d.owner}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                <Button onClick={handleAnalyzeMeeting} disabled={analyzing} className="mt-4">
                  {analyzing ? (
                    <Loader2 className="size-4 animate-spin" />
                  ) : (
                    <Sparkles className="size-4" />
                  )}
                  Analyze
                </Button>
              </div>
            ) : (
              <p className="py-8 text-center text-sm text-muted-foreground">
                Select a meeting from the list.
              </p>
            )}
          </TabsContent>

          <TabsContent value="notes" className="mt-4 flex flex-col gap-3">
            <div className="flex flex-wrap items-center gap-2">
              <input
                ref={fileInputRef}
                type="file"
                accept="application/pdf"
                className="hidden"
                onChange={handlePdfSelected}
              />
              <Button
                type="button"
                variant="outline"
                onClick={() => fileInputRef.current?.click()}
                disabled={extractingPdf}
              >
                {extractingPdf ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <Upload className="size-4" />
                )}
                Upload meeting PDF
              </Button>
              {uploadedFileName && (
                <span className="text-xs text-muted-foreground">
                  Extracted from {uploadedFileName} — edit below before analyzing if needed.
                </span>
              )}
            </div>

            <Textarea
              placeholder="Paste raw meeting notes here, or upload a PDF above…"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={8}
            />
            <Button onClick={handleAnalyzeNotes} disabled={analyzing || !notes.trim()} className="w-fit">
              {analyzing ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Sparkles className="size-4" />
              )}
              Analyze
            </Button>
          </TabsContent>
        </Tabs>

        {result && <MeetingIntelligenceCard data={result} />}
      </div>
    </div>
  );
}
