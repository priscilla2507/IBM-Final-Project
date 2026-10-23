import React, { useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  Thermometer,
  Camera,
  Map,
  Wallet,
  ChevronLeft,
  ChevronRight,
  Leaf,
  Menu,
  X,
  MapPin,
  ShieldCheck,
  MessageCircle,
  ScanSearch,
} from 'lucide-react'

const NAV_ITEMS = [
  { path: '/', label: 'Dashboard', sublabel: 'Overview & microclimate', icon: LayoutDashboard, exact: true },
  { path: '/heat-risk', label: 'Heat Risk Analysis', sublabel: 'Field survey assessment', icon: Thermometer },
  { path: '/personal-assessment', label: 'Personal Assessment', sublabel: 'Personal heat-risk profile', icon: ShieldCheck },
  { path: '/heat-assistant', label: 'Heat Assistant', sublabel: 'AI heat-safety chat', icon: MessageCircle },
  { path: '/photo-analysis', label: 'Photo Analysis', sublabel: 'AI shade & canopy CV', icon: Camera },
  { path: '/area-analysis', label: 'Area Analysis', sublabel: 'Image + budget optimizer', icon: ScanSearch },
  { path: '/vulnerability-map', label: 'Vulnerability Map', sublabel: 'GIS heat hotspots & shelters', icon: Map },
  { path: '/budget-optimizer', label: 'Budget Optimizer', sublabel: 'Mitigation ROI & allocation', icon: Wallet },
]

export default function Sidebar() {
  const [mobileOpen, setMobileOpen] = useState(false)
  const location = useLocation()

  const SidebarContent = () => (
    <div className="flex flex-col h-full" style={{ backgroundColor: '#0d1117' }}>
      {/* Logo */}
      <div className="px-4 pt-5 pb-4 border-b border-gray-800">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
            style={{ background: 'linear-gradient(135deg, #1d4ed8, #7c3aed)' }}>
            <Leaf size={18} className="text-white" />
          </div>
          <div>
            <div className="text-sm font-bold leading-tight">
              <span className="text-white">Chhaya</span>
              <span className="text-orange-400"> Rakshak</span>
              <span className="ml-1.5 text-xs bg-blue-600 text-white px-1.5 py-0.5 rounded font-semibold">AI</span>
            </div>
            <div className="text-xs text-gray-500 mt-0.5">Urban Heat Resilience • HYD</div>
          </div>
        </div>

        {/* Location chip */}
        <div className="flex items-center gap-2 px-2.5 py-2 rounded-lg border border-gray-700 cursor-pointer hover:border-gray-600 transition-colors"
          style={{ backgroundColor: '#161b22' }}>
          <div className="w-2 h-2 rounded-full bg-green-400 flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <div className="text-xs font-semibold text-white truncate">GHMC Hyderabad Core</div>
            <div className="text-xs text-gray-500">17.38°N, 78.48°E</div>
          </div>
        </div>
      </div>

      {/* Nav section label */}
      <div className="px-4 pt-4 pb-1">
        <span className="text-xs font-semibold text-gray-600 uppercase tracking-widest">Decision Modules</span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-1 space-y-0.5 overflow-y-auto">
        {NAV_ITEMS.map(({ path, label, sublabel, icon: Icon, exact }) => {
          const isActive = exact ? location.pathname === path : location.pathname.startsWith(path)
          return (
            <NavLink
              key={path}
              to={path}
              onClick={() => setMobileOpen(false)}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-150 group ${
                isActive
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'
              }`}
            >
              <Icon size={17} className={`flex-shrink-0 ${isActive ? 'text-white' : 'text-gray-500 group-hover:text-gray-300'}`} />
              <div className="flex-1 min-w-0">
                <div className={`text-sm font-medium leading-tight truncate ${isActive ? 'text-white' : ''}`}>{label}</div>
                <div className={`text-xs leading-tight mt-0.5 truncate ${isActive ? 'text-blue-200' : 'text-gray-600'}`}>{sublabel}</div>
              </div>
              {isActive && (
                <ChevronRight size={14} className="flex-shrink-0 text-blue-200" />
              )}
            </NavLink>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="px-4 py-4 border-t border-gray-800">
        <div className="px-2.5 py-2.5 rounded-lg" style={{ backgroundColor: '#161b22' }}>
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-semibold text-gray-300">GHMC Heat Action Plan</span>
            <span className="text-xs bg-gray-700 text-gray-400 px-1.5 py-0.5 rounded font-mono">v1.0</span>
          </div>
          <div className="text-xs text-gray-500 leading-relaxed">
            Urban Heat Island (UHI) Monitoring &amp; Mitigation Decision Support System.
          </div>
        </div>
      </div>
    </div>
  )

  return (
    <>
      {/* Mobile toggle */}
      <button
        className="lg:hidden fixed top-4 left-4 z-50 w-9 h-9 text-white rounded-lg flex items-center justify-center shadow-lg"
        style={{ backgroundColor: '#0d1117' }}
        onClick={() => setMobileOpen(!mobileOpen)}
        aria-label="Toggle navigation"
      >
        {mobileOpen ? <X size={18} /> : <Menu size={18} />}
      </button>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div className="lg:hidden fixed inset-0 bg-black/60 z-40" onClick={() => setMobileOpen(false)} />
      )}

      {/* Mobile sidebar */}
      <aside
        className={`lg:hidden fixed top-0 left-0 h-full w-64 z-50 transform transition-transform duration-300 ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
        style={{ backgroundColor: '#0d1117' }}
      >
        <SidebarContent />
      </aside>

      {/* Desktop sidebar */}
      <aside
        className="hidden lg:flex flex-col w-56 flex-shrink-0"
        style={{ backgroundColor: '#0d1117', minHeight: '100vh' }}
      >
        <SidebarContent />
      </aside>
    </>
  )
}
