import { listSuppliers } from "@/lib/api";
import { SuppliersTable } from "./suppliers-table";

export const dynamic = "force-dynamic";

export default async function SuppliersPage() {
  const suppliers = await listSuppliers({ limit: 100 });

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Suppliers</h1>
        <p className="text-sm text-muted-foreground">{suppliers.length} suppliers on record.</p>
      </div>

      {suppliers.length === 0 ? (
        <p className="py-12 text-center text-sm text-muted-foreground">No suppliers found.</p>
      ) : (
        <SuppliersTable suppliers={suppliers} />
      )}
    </div>
  );
}
