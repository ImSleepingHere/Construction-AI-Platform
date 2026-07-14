import Link from "next/link";
import { FileQuestion } from "lucide-react";

import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 py-24 text-center">
      <FileQuestion className="size-10 text-muted-foreground" />
      <div>
        <h1 className="text-lg font-semibold tracking-tight">Page not found</h1>
        <p className="text-sm text-muted-foreground">
          The page you&apos;re looking for doesn&apos;t exist or may have moved.
        </p>
      </div>
      <Button render={<Link href="/" />}>Back to dashboard</Button>
    </div>
  );
}
