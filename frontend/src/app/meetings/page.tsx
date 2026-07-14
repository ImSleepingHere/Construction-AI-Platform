import { listMeetings, listProjects } from "@/lib/api";
import { MeetingsBrowser } from "./meetings-browser";

export const dynamic = "force-dynamic";

export default async function MeetingsPage() {
  const [meetings, projects] = await Promise.all([
    listMeetings({ limit: 300 }),
    listProjects({ limit: 100 }),
  ]);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Meetings</h1>
        <p className="text-sm text-muted-foreground">
          Browse recorded meetings or analyze notes on demand.
        </p>
      </div>

      {meetings.length === 0 ? (
        <p className="py-12 text-center text-sm text-muted-foreground">No meetings found.</p>
      ) : (
        <MeetingsBrowser meetings={meetings} projects={projects} />
      )}
    </div>
  );
}
