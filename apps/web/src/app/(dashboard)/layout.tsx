import { Sidebar } from "@/components/Sidebar";

// Auth guard is skipped in dev when GOOGLE credentials are placeholders
export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto bg-neutral-50 p-6">
        {children}
      </main>
    </div>
  );
}
