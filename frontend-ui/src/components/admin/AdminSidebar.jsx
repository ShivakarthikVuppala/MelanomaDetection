import { useAuth } from '../AuthContext';

const FONT = "'Inter', 'Segoe UI', system-ui, sans-serif";

const navItems = [
  { key: 'dashboard', label: 'Dashboard',  icon: 'fa-chart-pie' },
  { key: 'users',     label: 'Users',      icon: 'fa-users'     },
  { key: 'settings',  label: 'Settings',   icon: 'fa-cog'       },
];

export default function AdminSidebar({ activePage, onNavigate }) {
  const { user, logout } = useAuth();
  const initials = ((user?.first_name?.[0] || '') + (user?.last_name?.[0] || '')).toUpperCase() || 'A';

  return (
    <aside style={{
      width: '240px', minWidth: '240px', height: '100vh',
      background: '#0f172a', color: '#e2e8f0',
      display: 'flex', flexDirection: 'column',
      fontFamily: FONT, position: 'sticky', top: 0,
    }}>
      {/* Brand */}
      <div style={{
        padding: '26px 22px 20px',
        borderBottom: '1px solid rgba(255,255,255,0.07)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            width: '36px', height: '36px', borderRadius: '10px',
            background: '#0F766E', display: 'flex', alignItems: 'center',
            justifyContent: 'center', fontSize: '18px',
          }}>
            🔬
          </div>
          <div>
            <div style={{ fontWeight: 800, fontSize: '15px', color: '#f8fafc', lineHeight: 1.1 }}>
              MelaDetect AI
            </div>
            <div style={{
              fontSize: '10.5px', fontWeight: 700, color: '#ef4444',
              textTransform: 'uppercase', letterSpacing: '0.1em',
            }}>
              Admin Panel
            </div>
          </div>
        </div>
      </div>

      {/* Nav items */}
      <nav style={{ flex: 1, padding: '14px 10px', overflowY: 'auto' }}>
        {navItems.map(item => {
          const active = activePage === item.key;
          return (
            <button
              key={item.key}
              onClick={() => onNavigate(item.key)}
              style={{
                width: '100%', display: 'flex', alignItems: 'center', gap: '12px',
                padding: '11px 14px', borderRadius: '10px', marginBottom: '4px',
                background: active ? 'rgba(15,118,110,0.25)' : 'transparent',
                color: active ? '#5eead4' : '#94a3b8',
                border: 'none', cursor: 'pointer', textAlign: 'left',
                fontSize: '14px', fontWeight: active ? 700 : 500,
                transition: 'background .15s, color .15s',
                fontFamily: FONT,
              }}
              onMouseEnter={e => { if (!active) { e.currentTarget.style.background = 'rgba(255,255,255,0.05)'; e.currentTarget.style.color = '#e2e8f0'; }}}
              onMouseLeave={e => { if (!active) { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#94a3b8'; }}}
            >
              <i className={`fas ${item.icon}`} style={{ width: '18px', textAlign: 'center', fontSize: '15px' }} />
              {item.label}
              {active && (
                <span style={{
                  marginLeft: 'auto', width: '6px', height: '6px',
                  borderRadius: '50%', background: '#5eead4',
                }} />
              )}
            </button>
          );
        })}
      </nav>

      {/* Footer — user info + logout */}
      <div style={{
        padding: '14px 10px 18px',
        borderTop: '1px solid rgba(255,255,255,0.07)',
      }}>
        {user && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: '10px',
            padding: '10px 12px', marginBottom: '8px',
          }}>
            <div style={{
              width: '34px', height: '34px', borderRadius: '50%',
              background: '#ef4444', color: '#fff',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontWeight: 800, fontSize: '13px', flexShrink: 0,
            }}>
              {initials}
            </div>
            <div style={{ minWidth: 0 }}>
              <div style={{ fontSize: '13px', fontWeight: 700, color: '#f1f5f9', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {user.first_name} {user.last_name}
              </div>
              <div style={{ fontSize: '11.5px', color: '#64748b', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {user.email}
              </div>
            </div>
          </div>
        )}
        <button
          onClick={logout}
          style={{
            width: '100%', display: 'flex', alignItems: 'center', gap: '10px',
            padding: '10px 14px', borderRadius: '10px',
            background: 'rgba(239,68,68,0.1)', color: '#f87171',
            border: 'none', cursor: 'pointer', fontSize: '13.5px', fontWeight: 600,
            fontFamily: FONT, transition: 'background .15s',
          }}
          onMouseEnter={e => e.currentTarget.style.background = 'rgba(239,68,68,0.18)'}
          onMouseLeave={e => e.currentTarget.style.background = 'rgba(239,68,68,0.1)'}
        >
          <i className="fas fa-sign-out-alt" /> Log Out
        </button>
      </div>
    </aside>
  );
}
