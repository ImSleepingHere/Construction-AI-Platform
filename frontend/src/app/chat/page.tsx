"use client";

import { useEffect, useRef, useState } from "react";
import { Send } from "lucide-react";
import { toast } from "sonner";

import { chat } from "@/lib/api";
import { formatLatency } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { MeetingIntelligenceCard } from "@/components/agent-results/MeetingIntelligenceCard";
import { SupplierRiskCard } from "@/components/agent-results/SupplierRiskCard";
import { WeeklyReportCard } from "@/components/agent-results/WeeklyReportCard";
import type {
  DomainAgentName,
  MeetingAnalysis,
  SupplierRiskAssessment,
  WeeklyReport,
} from "@/lib/types";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text?: string;
  agentUsed?: DomainAgentName | null;
  structured?: unknown;
  latencyMs?: number;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  async function handleSend() {
    const text = input.trim();
    if (!text || sending) return;

    setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: "user", text }]);
    setInput("");
    setSending(true);

    try {
      const result = await chat({ message: text });
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          agentUsed: result.agent_used,
          structured: result.agent_used ? result.response : undefined,
          text: result.agent_used ? undefined : String(result.response),
          latencyMs: result.latency_ms,
        },
      ]);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="flex h-[calc(100vh-7rem)] flex-col">
      <div className="mb-4">
        <h1 className="text-2xl font-semibold tracking-tight">Chat</h1>
        <p className="text-sm text-muted-foreground">
          Ask anything — routed automatically to the right agent.
        </p>
      </div>

      <ScrollArea className="flex-1 rounded-lg border">
        <div className="flex flex-col gap-4 p-4">
          {messages.length === 0 && (
            <p className="py-12 text-center text-sm text-muted-foreground">
              Try &quot;Assess supplier 1&quot; or &quot;What is a purchase order?&quot;
            </p>
          )}
          {messages.map((m) => (
            <MessageBubble key={m.id} message={m} />
          ))}
          {sending && (
            <div className="flex flex-col gap-2">
              <Skeleton className="h-4 w-40" />
              <Skeleton className="h-16 w-2/3" />
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </ScrollArea>

      <form
        className="mt-4 flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          void handleSend();
        }}
      >
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Message the platform…"
          disabled={sending}
          autoFocus
        />
        <Button type="submit" disabled={sending || !input.trim()}>
          <Send className="size-4" />
          Send
        </Button>
      </form>
    </div>
  );
}

function AgentResultView({
  agentUsed,
  data,
}: {
  agentUsed: DomainAgentName;
  data: unknown;
}) {
  switch (agentUsed) {
    case "meeting_intelligence":
      return <MeetingIntelligenceCard data={data as MeetingAnalysis} />;
    case "supplier_risk":
      return <SupplierRiskCard data={data as SupplierRiskAssessment} />;
    case "executive_report":
      return <WeeklyReportCard data={data as WeeklyReport} />;
  }
}

function MessageBubble({ message }: { message: ChatMessage }) {
  if (message.role === "user") {
    return (
      <div className="ml-auto max-w-[75%] rounded-lg bg-primary px-3 py-2 text-sm text-primary-foreground">
        {message.text}
      </div>
    );
  }

  return (
    <div className="flex max-w-[85%] flex-col gap-1.5">
      <div className="flex items-center gap-2">
        {message.agentUsed && <Badge variant="secondary">via {message.agentUsed}</Badge>}
        {message.latencyMs !== undefined && (
          <span className="text-xs text-muted-foreground">
            {formatLatency(message.latencyMs)}
          </span>
        )}
      </div>
      {message.agentUsed && message.structured ? (
        <AgentResultView agentUsed={message.agentUsed} data={message.structured} />
      ) : (
        <div className="rounded-lg bg-muted px-3 py-2 text-sm">{message.text}</div>
      )}
    </div>
  );
}
