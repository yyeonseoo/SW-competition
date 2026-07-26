interface Props {
  avatarLabel: string;
}

export default function AppHeader({ avatarLabel }: Props) {
  return (
    <header className="app-header">
      <div className="brand">
        <span className="logo">KW</span>
        <span className="name">KW-LIFE</span>
      </div>
      <nav className="header-nav">
        <a href="#" className="active">
          대시보드
        </a>
      </nav>
      <div className="header-right">
        <div className="avatar">{avatarLabel}</div>
      </div>
    </header>
  );
}
