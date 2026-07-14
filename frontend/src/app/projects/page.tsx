import { listProjects } from "@/lib/api";
import { ProjectsTable } from "./projects-table";

export const dynamic = "force-dynamic";

export default async function ProjectsPage() {
  const projects = await listProjects({ limit: 100 });

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Projects</h1>
        <p className="text-sm text-muted-foreground">{projects.length} projects in the portfolio.</p>
      </div>

      {projects.length === 0 ? (
        <p className="py-12 text-center text-sm text-muted-foreground">No projects found.</p>
      ) : (
        <ProjectsTable projects={projects} />
      )}
    </div>
  );
}
