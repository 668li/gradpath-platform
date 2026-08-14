import { LoadingState } from "@/components/ui/empty";

export default function Loading() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-paper-100">
      <div className="flex flex-col items-center gap-3">
        <LoadingState text="正在加载…" />
      </div>
    </div>
  );
}
