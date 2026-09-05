export function GovernmentFooter() {
  const lastUpdated = new Date().toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });

  return (
    <footer className="shrink-0 border-t border-slate-300 bg-white px-6 py-4 text-xs text-slate-500">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="font-semibold text-slate-700">Government of India</p>
          <p>CPSE Material Harmonization Platform</p>
        </div>
        <nav className="flex flex-wrap gap-x-4 gap-y-1">
          <a href="#" className="hover:text-brand-600 hover:underline">Accessibility</a>
          <a href="#" className="hover:text-brand-600 hover:underline">Privacy</a>
          <a href="#" className="hover:text-brand-600 hover:underline">Terms of Use</a>
          <a href="#" className="hover:text-brand-600 hover:underline">Help</a>
          <a href="#" className="hover:text-brand-600 hover:underline">Contact</a>
        </nav>
        <div className="text-right">
          <p>Last Updated: {lastUpdated}</p>
          <p className="font-semibold uppercase tracking-wide text-warning-600">Prototype for Demonstration</p>
        </div>
      </div>
    </footer>
  );
}
