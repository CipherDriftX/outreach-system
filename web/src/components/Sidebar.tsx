import { NavLink } from "react-router-dom";

const NAV = [
  { to: "/", label: "Dashboard", icon: "◫" },
  { to: "/signals", label: "Signals", icon: "⚡" },
  { to: "/leads", label: "Leads", icon: "◆" },
  { to: "/offers", label: "Offers", icon: "✧" },
  { to: "/settings", label: "Settings", icon: "⚙" },
];

export default function Sidebar() {
  return (
    <aside className="w-[240px] min-w-[240px] h-screen bg-[#0e0e16] border-r border-[#1e1e2e] flex flex-col">
      <div className="px-5 py-6 border-b border-[#1e1e2e]">
        <h1 className="text-base font-semibold tracking-tight text-[#e4e4ec]">
          Outreach OS
        </h1>
        <p className="text-xs text-[#606078] mt-1 font-mono">Plarix</p>
      </div>
      <nav className="flex-1 px-3 py-4 space-y-1">
        {NAV.map(({ to, label, icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                isActive
                  ? "bg-[#1a1a28] text-[#4a8fe7] font-medium"
                  : "text-[#9898b0] hover:text-[#e4e4ec] hover:bg-[#14141e]"
              }`
            }
          >
            <span className="text-base w-5 text-center">{icon}</span>
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="px-5 py-4 border-t border-[#1e1e2e] text-xs text-[#606078] font-mono">
        v0.1.0
      </div>
    </aside>
  );
}