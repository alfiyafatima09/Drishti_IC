export default function DashboardPage() {
  return (
    <div className="flex flex-1 flex-col gap-4 p-4">
      <div className="grid auto-rows-min gap-4 md:grid-cols-3">
        <div className="aspect-video rounded-xl border border-zinc-200 bg-zinc-100/50 dark:border-zinc-800 dark:bg-zinc-800/50" />
        <div className="aspect-video rounded-xl border border-zinc-200 bg-zinc-100/50 dark:border-zinc-800 dark:bg-zinc-800/50" />
        <div className="aspect-video rounded-xl border border-zinc-200 bg-zinc-100/50 dark:border-zinc-800 dark:bg-zinc-800/50" />
      </div>
      <div className="min-h-[100vh] flex-1 rounded-xl border border-zinc-200 bg-zinc-100/50 md:min-h-min dark:border-zinc-800 dark:bg-zinc-800/50" />
    </div>
  )
}
