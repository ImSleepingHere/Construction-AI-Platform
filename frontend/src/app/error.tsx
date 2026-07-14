"use client";

import { useEffect } from "react";
import Link from "next/link";
import { AlertTriangle } from "lucide-react";

import { Button } from "@/components/ui/button";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 py-24 text-center">
      <AlertTriangle className="size-10 text-destructive" />
      <div>
        <h1 className="text-lg font-semibold tracking-tight">Something went wrong</h1>
        <p className="max-w-md text-sm text-muted-foreground">
          {error.message || "An unexpected error occurred while loading this page."}
        </p>
      </div>
      <div className="flex gap-2">
        <Button variant="outline" onClick={reset}>
          Try again
        </Button>
        <Button render={<Link href="/" />}>Back to dashboard</Button>
      </div>
    </div>
  );
}
