import { ListSkeleton, CardSkeleton } from "@/components/ui/skeleton";

export default function Loading() {
  return (
    <div className="min-h-screen bg-paper-50">
      <div className="mx-auto max-w-7xl px-4 py-6 md:px-6 md:py-8">
        <CardSkeleton />
        <div className="mt-6">
          <ListSkeleton count={5} />
        </div>
      </div>
    </div>
  );
}
